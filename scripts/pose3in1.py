#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pose3in1.py — 姿势 × 服饰 × 人物 三合一生成

把三张参考图合成一张完整的角色成品图：
  姿势图决定动作，服饰图决定穿搭，人物图决定身份与画风。

两种后端：
  vision   （默认）视觉模型读图 → 编译结构化提示词 → 文生图
  direct   （可选）直接把三张图提交给支持多图参考的模型

配置通过环境变量或 .env 提供，见 README。
"""

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outpath import resolve_outdir, cleanup_apple_double

# ---------------- 配置 ----------------
API_BASE = os.environ.get(
    "PCC_API_BASE",
    "https://ws-ni63spexpelb9vr5.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
)
API_KEY = os.environ.get("PCC_API_KEY", "")
VL_MODEL = os.environ.get("PCC_VL_MODEL", "qwen3-vl-plus")
IMG_MODEL = os.environ.get("PCC_IMG_MODEL", "qwen-image-2.1-pro")
GALLERY = os.environ.get("PCC_GALLERY", "")   # 必填

ANGLES = {
    "front": ("正面", "front view"),
    "high": ("俯视", "high angle, looking down at the subject"),
    "low": ("仰视", "low angle, looking up at the subject"),
    "side": ("侧面", "side view"),
    "diagonal": ("斜侧", "three-quarter view"),
    "diag": ("斜侧", "three-quarter view"),
}

POSE_INSTR = (
    "This is a body pose reference. Output ONE English paragraph, max 60 words. "
    "Describe only the pose: torso orientation, each limb position (left and right separately), "
    "which leg bears weight, what the hands do, overall action "
    "(standing / sitting / kneeling / lying / squatting), camera angle. "
    "Never mention mannequin, line art, gray tone, or a model. English only."
)
COSTUME_INSTR = (
    "This is an outfit reference. Output ONE English paragraph of comma-separated phrases, "
    "max 50 words. Describe only the garments: item names, colors, materials, silhouette, "
    "layering order, shoes, accessories. Never mention the model's face, hair or stance. "
    "English only."
)
FACE_INSTR = (
    "This is a face reference. Output ONE English paragraph of comma-separated phrases, "
    "max 45 words. Describe only appearance: hairstyle and length, bangs, hair color, "
    "face shape, skin tone, facial features, apparent age, overall vibe. English only."
)


# ---------------- 工具 ----------------
def need_key():
    if not API_KEY:
        raise SystemExit(
            "缺少 API Key。请设置环境变量 PCC_API_KEY，\n"
            "或在项目根目录建 .env 文件写入 PCC_API_KEY=sk-xxx"
        )
    return API_KEY


def clean(text):
    """去掉非英文残留与重复标点，避免污染提示词。"""
    if not text:
        return ""
    text = re.sub(r"[\u4e00-\u9fff\u3040-\u30ff]+", "", text)
    text = re.sub(r"[.。,，]{2,}", ".", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .;,，")


def encode_image(path):
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "webp": "image/webp"}.get(ext)
    if not mime:
        raise SystemExit(f"不支持的图片格式: {path}")
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode(), mime


def vision_describe(image_path, instruction, timeout=180):
    """视觉模型读图，返回英文描述。"""
    key = need_key()
    b64, mime = encode_image(image_path)
    payload = {
        "model": VL_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": instruction},
                {"type": "image_url",
                 "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ],
        }],
        "max_tokens": 500,
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        f"{API_BASE}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    return d["choices"][0]["message"]["content"].strip()


def text2img(prompt, size="1024x1536", timeout=600, retries=3):
    """文生图，内置重试（长提示词容易触发超时）。"""
    key = need_key()
    payload = {"model": IMG_MODEL, "prompt": prompt, "n": 1, "size": size}
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                f"{API_BASE}/images/generations",
                data=json.dumps(payload).encode(),
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.loads(r.read())
            item = d["data"][0]
            if item.get("url"):
                with urllib.request.urlopen(item["url"], timeout=120) as r:
                    return r.read()
            if item.get("b64_json"):
                return base64.b64decode(item["b64_json"])
            raise RuntimeError("生图返回格式异常")
        except Exception as e:
            last = e
            if attempt < retries - 1:
                print(f"      第 {attempt + 1} 次失败，重试…", flush=True)
                time.sleep(3)
    raise last


# ---------------- 图库检索 ----------------
def _load(name):
    if not GALLERY:
        raise SystemExit(
            "缺少图库路径。请设置环境变量 PCC_GALLERY，\n"
            "或在项目根目录 .env 文件写入 PCC_GALLERY=/path/to/gallery"
        )
    path = os.path.join(GALLERY, "data", name)
    if not os.path.isfile(path):
        raise SystemExit(
            f"找不到图库数据: {path}\n"
            f"请用环境变量 PCC_GALLERY 指向图库根目录。"
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def find_pose(token):
    d = _load("poses.json")
    for p in d["poses"]:
        if p.get("id") == token or p.get("no") == token:
            return p
    up = token.upper()
    for p in d["poses"]:
        if p.get("no", "").upper() == up:
            return p
    for p in d["poses"]:
        if token.lower() in (p.get("id", "") + p.get("no", "")).lower():
            return p
    raise SystemExit(f"姿势未找到: {token}")


def find_costume(token):
    d = _load("costumes.json")
    for c in d["costumes"]:
        if c["id"].upper() == token.upper():
            return c
    for c in d["costumes"]:
        if token.upper() in c["id"].upper():
            return c
    raise SystemExit(f"服饰未找到: {token}")


def find_face(token):
    d = _load("faces.json")
    for f in d["images"]:
        if f["id"].startswith(token):
            return f
    raise SystemExit(f"人像未找到: {token}")


def pose_image_path(pose, angle):
    for v in pose.get("variants", []):
        if v["angle"] == angle:
            return os.path.join(GALLERY, v["full"])
    return os.path.join(GALLERY, pose["variants"][0]["full"])


# ---------------- 提示词编译 ----------------
def compile_prompt(pose_desc, costume_desc, face_desc, figure, angle, extra):
    """
    职责分离：三种参考各管一件事，明确禁止互相串味。
    这是整个流程最关键的一步。
    """
    parts = [
        "Create one finished portrait photograph of a single real human, "
        "not a collage, not a reference sheet, no text or watermark. "
    ]

    if face_desc:
        parts.append(f"[Identity] {face_desc}. Keep this face, hairstyle and body build. ")
    elif figure:
        parts.append(f"[Identity] {figure}. ")
    else:
        parts.append("[Identity] A young East Asian woman with short black hair. ")

    if pose_desc:
        parts.append(f"[Pose] {pose_desc}")
        ang = ANGLES.get(angle, ("", ""))[1]
        if ang:
            parts.append(f" Camera: {ang}.")
        parts.append(
            " Follow this gesture, weight distribution and limb placement exactly. "
            "Do not draw mannequins, joint balls, guide lines or faceless heads. "
        )

    if costume_desc:
        parts.append(
            f"[Outfit] {costume_desc}. "
            "Let the garment drape and wrinkle naturally with the pose. Fully clothed. "
        )

    parts.append(
        "[Style] Photorealistic, natural skin texture, soft studio lighting, "
        "50mm lens, simple neutral background, full body visible. "
    )

    if extra:
        parts.append(extra.strip().rstrip(".") + ". ")

    return "".join(parts).strip()


# ---------------- 主流程 ----------------
def main():
    ap = argparse.ArgumentParser(
        description="姿势 × 服饰 × 人物 三合一生成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例：
  python3 pose3in1.py --pose P008 --costume SPR-0165 --face ff580239863
  python3 pose3in1.py --pose P008 --angle high --costume SPR-0003 --figure "short black hair"
  python3 pose3in1.py --pose P008 --costume SPR-0165 --prompt-only
""",
    )
    ap.add_argument("--pose", help="姿势编号，如 P008")
    ap.add_argument("--angle", default="front",
                    help="视角：front / high / low / side / diagonal")
    ap.add_argument("--costume", help="服饰编号，如 SPR-0165")
    ap.add_argument("--face", help="人像 ID 前缀")
    ap.add_argument("--figure", help="人物文字描述（无 --face 时使用）")
    ap.add_argument("--extra", default="", help="附加要求")
    ap.add_argument("--size", default="1024x1536",
                    help="1024x1024 / 1024x1536 / 1536x1024")
    ap.add_argument("-n", "--count", type=int, default=1, help="生成张数")
    ap.add_argument("--tag", default="三合一", help="文件名前缀")
    ap.add_argument("--no-vision", action="store_true",
                    help="跳过视觉模型，直接用图库文字标签")
    ap.add_argument("--prompt-only", action="store_true", help="只输出提示词")
    ap.add_argument("--dry-run", action="store_true", help="只显示配置")
    args = ap.parse_args()

    if not args.pose and not args.costume:
        ap.error("至少需要 --pose 或 --costume")

    pose = find_pose(args.pose) if args.pose else None
    costume = find_costume(args.costume) if args.costume else None
    face = find_face(args.face) if args.face else None

    pose_img = pose_image_path(pose, args.angle) if pose else None
    costume_img = os.path.join(GALLERY, costume["image"]) if costume else None
    face_img = os.path.join(GALLERY, face["thumb"]) if face else None

    print("=" * 68)
    if pose:
        print(f"  姿势   {pose['no']}  {pose['names']['zh']}")
        print(f"         {pose_img}")
    if costume:
        print(f"  服饰   {costume['id']}  {costume['color']}/{costume['main']}")
        print(f"         {costume_img}")
    if face:
        print(f"  人物   {face['id']}  {face['hair']}")
        print(f"         {face_img}")
    elif args.figure:
        print(f"  人物   {args.figure}")
    print("=" * 68)

    pose_desc = costume_desc = face_desc = ""

    if args.no_vision:
        if pose:
            pose_desc = clean(pose["names"]["en"])
        if costume:
            costume_desc = ", ".join(costume["tags"])
        if face:
            face_desc = f"{face['hair']} hair"
            if face.get("style"):
                face_desc += f", {face['style']}"
    else:
        if pose_img and os.path.exists(pose_img):
            print("\n[1/3] 读取姿势…", flush=True)
            try:
                pose_desc = clean(vision_describe(pose_img, POSE_INSTR))
                print(f"      {pose_desc}")
            except Exception as e:
                print(f"      ⚠️ {e}")
                pose_desc = clean(pose["names"]["en"])

        if costume_img and os.path.exists(costume_img):
            print("\n[2/3] 读取服饰…", flush=True)
            try:
                costume_desc = clean(vision_describe(costume_img, COSTUME_INSTR))
                print(f"      {costume_desc}")
            except Exception as e:
                print(f"      ⚠️ {e}")
                costume_desc = ", ".join(costume["tags"])

        if face_img and os.path.exists(face_img):
            print("\n[3/3] 读取人物…", flush=True)
            try:
                face_desc = clean(vision_describe(face_img, FACE_INSTR))
                print(f"      {face_desc}")
            except Exception as e:
                print(f"      ⚠️ {e}")
                face_desc = f"{face['hair']} hair"

    prompt = compile_prompt(pose_desc, costume_desc, face_desc,
                            args.figure, args.angle, args.extra)

    print("\n" + "=" * 68)
    print("最终提示词：")
    print("=" * 68)
    print(prompt)
    print("=" * 68)

    if args.prompt_only:
        return 0
    if args.dry_run:
        print("\n[dry-run] 未生成")
        return 0

    outdir = resolve_outdir()
    print(f"\n输出: {outdir}")
    print(f"位置: {'外置卷 ✅' if '/Volumes/' in outdir else '本地'}")

    ok = 0
    for i in range(args.count):
        print(f"\n[{i + 1}/{args.count}] 生成中…", flush=True)
        try:
            data = text2img(prompt, args.size)
            stamp = time.strftime("%m%d_%H%M%S")
            parts = [args.tag]
            if pose:
                parts.append(pose["no"])
                if args.angle != "front":
                    parts.append(ANGLES.get(args.angle, ("", args.angle))[0])
            if costume:
                parts.append(costume["id"])
            if face:
                parts.append(face["id"][:8])
            parts.append(stamp)
            if args.count > 1:
                parts.append(str(i + 1))
            name = "_".join(p for p in parts if p) + ".png"
            path = os.path.join(outdir, name)
            with open(path, "wb") as f:
                f.write(data)
            print(f"      ✅ {name}  {len(data) // 1024}KB")
            ok += 1
        except Exception as e:
            print(f"      ❌ {type(e).__name__}: {e}")

    if "/Volumes/" in outdir:
        n = cleanup_apple_double(outdir)
        if n:
            print(f"\n清理 ._ 文件 {n} 个")

    print(f"\n完成 {ok}/{args.count} → {outdir}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
