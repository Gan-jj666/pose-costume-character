#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pick3in1.py — 交互式三合一选择器（双击运行）

不用记编号，用菜单一层层选：
  选姿势分类 → 选具体姿势 → 选视角
  选衣装季节 → 选品类 → 选具体衣装
  选人像发型 → 选具体人像
  然后直接生成

用法：
  python3 pick3in1.py
"""

import json
import os
import re
import subprocess
import sys
from collections import OrderedDict

GALLERY = os.environ.get("PCC_GALLERY", "")   # 必填
HERE = os.path.dirname(os.path.abspath(__file__))



# ---------------- 基础 UI ----------------
def clear():
    os.system("clear" if os.name != "nt" else "cls")


def title(text):
    w = 60
    print("=" * w)
    print(f"  {text}")
    print("=" * w)


def ask(prompt, default=""):
    s = input(f"{prompt}" + (f" [{default}]" if default else "") + "：").strip()
    return s or default


def choose(prompt, items, allow_back=True, allow_skip=False):
    """
    items: [(显示文字, 返回值)]
    返回选中项的返回值；-1=返回上一级；None=跳过
    """
    print()
    for i, (label, _) in enumerate(items, 1):
        print(f"  {i:>3}. {label}")
    if allow_skip:
        print(f"    0. 跳过（不指定）")
    if allow_back:
        print(f"    q. 返回上一级")

    while True:
        s = input(f"\n{prompt}：").strip().lower()
        if s == "q" and allow_back:
            return -1
        if s == "0" and allow_skip:
            return None
        if s.isdigit():
            n = int(s)
            if 1 <= n <= len(items):
                return items[n - 1][1]
        print("  ⚠️ 输入无效，请重试")


def pause():
    input("\n按回车继续…")


# ---------------- 数据 ----------------
def load(name):
    with open(os.path.join(GALLERY, "data", name), encoding="utf-8") as f:
        return json.load(f)


def check_gallery():
    if not os.path.isdir(GALLERY):
        print("❌ 找不到图库")
        print("   请设置环境变量 PCC_GALLERY 指向图库根目录。")
        pause()
        sys.exit(1)


# ---------------- 选姿势 ----------------
def pick_pose():
    d = load("poses.json")
    poses = d["poses"]

    while True:
        clear()
        title("第一步：选姿势")

        # 按分类分组
        cats = OrderedDict()
        for p in poses:
            cats.setdefault(p["category"], []).append(p)

        items = [(f"{c}（{len(v)} 组）", c) for c, v in cats.items()]
        cat = choose("选分类", items, allow_skip=True)
        if cat is None:
            return None, "front"
        if cat == -1:
            return -1, None

        # 该类下的具体姿势
        group = cats[cat]
        while True:
            clear()
            title(f"姿势 · {cat}（{len(group)} 组）")
            items = []
            for p in group:
                items.append((f"{p['no']}  {p['names']['zh']}", p))
            p = choose("选姿势", items)
            if p == -1:
                break

            # 选视角
            clear()
            title(f"{p['no']}  {p['names']['zh']}")
            print(f"  {p['names']['en']}")
            ang_names = {"front": "正面", "high": "俯视", "low": "仰视",
                         "side": "侧面", "diagonal": "斜侧", "diag": "斜侧"}
            items = []
            for v in p["variants"]:
                a = v["angle"]
                items.append((ang_names.get(a, a), a))
            a = choose("选视角", items, allow_skip=False)
            if a == -1:
                continue
            return p, a


# ---------------- 选衣装 ----------------
def pick_costume():
    d = load("costumes.json")
    costumes = d["costumes"]

    while True:
        clear()
        title("第二步：选衣装")

        # 按季节
        cats = OrderedDict()
        for c in costumes:
            cats.setdefault(c["cat"], []).append(c)
        cat_names = {x["key"]: x["names"]["zh"] for x in d["categories"]}

        items = [(f"{cat_names.get(k,k)}（{len(v)} 套）", k) for k, v in cats.items()]
        cat = choose("选季节", items, allow_skip=True)
        if cat is None:
            return None
        if cat == -1:
            return -1

        group = cats[cat]

        # 按品类二级筛选
        while True:
            clear()
            title(f"衣装 · {cat_names.get(cat,cat)}（{len(group)} 套）")
            groups = OrderedDict()
            for c in group:
                groups.setdefault(c["group"], []).append(c)
            grp_names = {x["key"]: x["names"]["zh"] for x in d["groups"]}

            items = [(f"【全部】{len(group)} 套", "__all__")]
            for g, v in groups.items():
                items.append((f"{grp_names.get(g,g)}（{len(v)} 套）", g))
            g = choose("选品类", items, allow_back=True)
            if g == -1:
                break

            subset = group if g == "__all__" else groups[g]

            # 具体衣装（分页显示）
            page = 0
            per_page = 20
            while True:
                clear()
                total = len(subset)
                pages = (total + per_page - 1) // per_page
                title(f"衣装 · {grp_names.get(g, g) if g!='__all__' else '全部'}"
                      f"（{total} 套，第 {page+1}/{pages} 页）")

                start = page * per_page
                chunk = subset[start:start + per_page]
                items = []
                for c in chunk:
                    tags = ", ".join(c["tags"][:4])
                    items.append((f"{c['id']}  [{c['color']}] {tags}", c))

                nav = []
                if page > 0:
                    nav.append((f"« 上一页", "__prev__"))
                if page < pages - 1:
                    nav.append((f"下一页 »", "__next__"))

                s = input("\n输入编号选择"
                          + ("，或 p 翻页" if pages > 1 else "")
                          + "，q 返回：").strip().lower()
                if s == "q":
                    break
                if s == "p" and pages > 1:
                    page = (page + 1) % pages
                    continue
                if s.isdigit():
                    n = int(s)
                    if 1 <= n <= len(chunk):
                        return chunk[n - 1]
                print("  ⚠️ 输入无效")


# ---------------- 选人像 ----------------
def pick_face():
    d = load("faces.json")
    images = d["images"]

    while True:
        clear()
        title("第三步：选人像")

        # 分区
        secs = OrderedDict()
        for f in images:
            secs.setdefault(f["sec"], []).append(f)
        sec_names = {x["key"]: x["names"]["zh"] for x in d["sections"]}

        items = [(f"{sec_names.get(k,k)}（{len(v)} 张）", k) for k, v in secs.items()]
        sec = choose("选分区", items, allow_skip=True)
        if sec is None:
            return None
        if sec == -1:
            return -1

        group = secs[sec]

        # 按发型
        while True:
            clear()
            title(f"人像 · {sec_names.get(sec,sec)}（{len(group)} 张）")
            hairs = OrderedDict()
            for f in group:
                hairs.setdefault(f["hair"], []).append(f)
            hair_names = {x["key"]: x["names"]["zh"] for x in d["hairs"]}

            items = [(f"【全部】{len(group)} 张", "__all__")]
            for h, v in hairs.items():
                items.append((f"{hair_names.get(h,h)}（{len(v)} 张）", h))
            h = choose("选发型", items)
            if h == -1:
                break

            subset = group if h == "__all__" else hairs[h]

            page = 0
            per_page = 20
            while True:
                clear()
                total = len(subset)
                pages = (total + per_page - 1) // per_page
                title(f"人像 · {hair_names.get(h,h) if h!='__all__' else '全部'}"
                      f"（{total} 张，第 {page+1}/{pages} 页）")

                start = page * per_page
                chunk = subset[start:start + per_page]
                for i, f in enumerate(chunk, 1):
                    style = (f.get("style") or "")[:28]
                    print(f"  {i:>3}. {f['id'][:12]}  {style}")

                s = input("\n输入编号选择"
                          + ("，或 p 翻页" if pages > 1 else "")
                          + "，q 返回：").strip().lower()
                if s == "q":
                    break
                if s == "p" and pages > 1:
                    page = (page + 1) % pages
                    continue
                if s.isdigit():
                    n = int(s)
                    if 1 <= n <= len(chunk):
                        return chunk[n - 1]
                print("  ⚠️ 输入无效")


# ---------------- 主流程 ----------------
def main():
    check_gallery()

    pose = costume = face = None
    angle = "front"

    while True:
        clear()
        title("三合一生成器")
        print("""
  姿势 × 服饰 × 人物 → 一张成品图

  用菜单挑选，不用记编号。
        """)

        # 选姿势
        r = pick_pose()
        if r[0] == -1:
            continue
        pose, angle = r

        # 选衣装
        c = pick_costume()
        if c == -1:
            continue
        costume = c

        # 选人像
        f = pick_face()
        if f == -1:
            continue
        face = f

        break

    # 确认
    clear()
    title("确认配置")
    if pose:
        print(f"  姿势   {pose['no']}  {pose['names']['zh']}  [{angle}]")
    if costume:
        print(f"  衣装   {costume['id']}  {costume['color']}/{costume['main']}")
    if face:
        print(f"  人像   {face['id']}  {face['hair']}")

    print()
    extra = ask("额外要求（可留空，如 cinematic lighting）")
    count = ask("生成张数", "1")
    try:
        count = max(1, min(4, int(count)))
    except ValueError:
        count = 1

    print("\n确认生成？(y/n)")
    if input().strip().lower() != "y":
        print("已取消")
        pause()
        return

    # 调 pose3in1
    cmd = [sys.executable, os.path.join(HERE, "pose3in1.py")]
    if pose:
        cmd += ["--pose", pose["no"], "--angle", angle]
    if costume:
        cmd += ["--costume", costume["id"]]
    if face:
        cmd += ["--face", face["id"]]
    if extra:
        cmd += ["--extra", extra]
    cmd += ["-n", str(count)]

    print("\n" + "=" * 60)
    subprocess.run(cmd)
    print("=" * 60)
    pause()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n已中断")
