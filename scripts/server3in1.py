#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
server3in1.py — 三合一网页版后端

同时提供静态文件与生成接口。
浏览器直接调模型 API 会被 CORS 拦，且 Key 不能落到前端，
所以生成动作放在这个本地服务里。

启动：python3 scripts/server3in1.py
访问：http://127.0.0.1:8125
"""

import base64
import http.server
import json
import os
import socketserver
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outpath import resolve_outdir, cleanup_apple_double
import pose3in1 as core

PORT = int(os.environ.get("PCC_PORT", "8125"))
ROOT = os.environ.get("PCC_GALLERY", "")   # 必填
STATIC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, fmt, *args):
        # 静音：浏览器探测请求会刷屏，真正的错误由 do_POST 返回
        pass

    def do_GET(self):
        # /app/* 走项目自带静态目录，其余走图库
        if self.path.startswith("/app/") or self.path == "/":
            rel = "combine.html" if self.path == "/" else self.path[len("/app/"):]
            path = os.path.join(STATIC, rel)
            if not os.path.isfile(path):
                self.send_error(404)
                return
            ctype = {
                ".html": "text/html; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".svg": "image/svg+xml",
            }.get(os.path.splitext(path)[1].lower(), "application/octet-stream")
            with open(path, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def do_POST(self):
        if self.path == "/api/open-folder":
            try:
                import subprocess
                d = resolve_outdir()
                subprocess.run(["open", d], check=True)
                self._json({"ok": True, "path": d})
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, 500)
            return

        if self.path != "/api/generate":
            self.send_error(404)
            return

        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n).decode())
        except Exception as e:
            self._json({"error": f"请求解析失败: {e}"}, 400)
            return

        try:
            t0 = time.time()
            logs = []

            pose = body.get("pose")
            costume = body.get("costume")
            face = body.get("face")
            figure = body.get("figure", "")
            angle = body.get("angle", "front")
            extra = body.get("extra", "")
            size = body.get("size", "1024x1536")

            pose_desc = costume_desc = face_desc = ""

            if pose and pose.get("image"):
                p = os.path.join(ROOT, pose["image"])
                if os.path.exists(p):
                    logs.append("读取姿势…")
                    pose_desc = core.clean(core.vision_describe(p, core.POSE_INSTR))
                    logs.append(f"姿势: {pose_desc[:70]}")

            if costume and costume.get("image"):
                p = os.path.join(ROOT, costume["image"])
                if os.path.exists(p):
                    logs.append("读取服饰…")
                    costume_desc = core.clean(core.vision_describe(p, core.COSTUME_INSTR))
                    logs.append(f"服饰: {costume_desc[:70]}")

            if face and face.get("thumb"):
                p = os.path.join(ROOT, face["thumb"])
                if os.path.exists(p):
                    logs.append("读取人物…")
                    face_desc = core.clean(core.vision_describe(p, core.FACE_INSTR))
                    logs.append(f"人物: {face_desc[:70]}")

            prompt = core.compile_prompt(pose_desc, costume_desc, face_desc,
                                         figure, angle, extra)
            logs.append("生成中…")

            data = core.text2img(prompt, size)

            outdir = resolve_outdir()
            stamp = time.strftime("%m%d_%H%M%S")
            parts = ["web"]
            if pose:
                parts.append(pose.get("no", ""))
            if costume:
                parts.append(costume.get("id", ""))
            if face:
                parts.append(face.get("id", "")[:8])
            parts.append(stamp)
            name = "_".join(p for p in parts if p) + ".png"
            path = os.path.join(outdir, name)
            with open(path, "wb") as f:
                f.write(data)

            cleanup_apple_double(outdir)
            elapsed = time.time() - t0
            logs.append(f"完成 {len(data) // 1024}KB {elapsed:.1f}s")

            self._json({
                "ok": True,
                "prompt": prompt,
                "logs": logs,
                "file": name,
                "path": path,
                "b64": base64.b64encode(data).decode(),
                "elapsed": round(elapsed, 1),
            })
        except urllib.error.HTTPError as e:
            self._json({"error": f"HTTP {e.code}: {e.read().decode()[:200]}"}, 500)
        except Exception as e:
            self._json({"error": f"{type(e).__name__}: {e}"}, 500)

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    if not ROOT:
        print("❌ 缺少 PCC_GALLERY，请见 README 配置章节")
        sys.exit(1)
    if not os.path.isdir(ROOT):
        print(f"❌ 图库不存在: {ROOT}")
        sys.exit(1)
    if not core.API_KEY:
        print("❌ 缺少 PCC_API_KEY，请见 README 配置章节")
        sys.exit(1)

    print("=" * 60)
    print("  Pose × Costume × Character")
    print("=" * 60)
    print(f"  图库    {ROOT}")
    print(f"  输出    {resolve_outdir()}")
    print(f"  地址    http://127.0.0.1:{PORT}")
    print("=" * 60)
    print("  Ctrl+C 停止")
    print()

    with ThreadedServer(("127.0.0.1", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n已停止")


if __name__ == "__main__":
    main()
