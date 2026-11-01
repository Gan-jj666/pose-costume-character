#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路径解析：优先外置卷，不可用时回退本地。"""

import os

# 可通过环境变量覆盖
VOLUME_ROOT = os.environ.get("PCC_VOLUME", "")   # 留空则始终用本地目录
VOLUME_SUBDIR = os.environ.get("PCC_VOLUME_SUBDIR", "AI生成图/三合一")
LOCAL_BASE = os.environ.get(
    "PCC_LOCAL_OUT",
    os.path.join(os.path.expanduser("~"), "WorkBuddy", "dt-output"),
)


def volume_writable(root=None):
    """真实写测试，而不是只看目录在不在。"""
    root = root or VOLUME_ROOT
    if not root or not os.path.isdir(root):
        return False
    probe = os.path.join(root, ".pcc_write_probe")
    try:
        with open(probe, "w") as f:
            f.write("ok")
        os.remove(probe)
        return True
    except OSError:
        return False


def resolve_outdir(subdir=None):
    """返回可用输出目录（自动创建）。"""
    if volume_writable():
        target = os.path.join(VOLUME_ROOT, VOLUME_SUBDIR)
    else:
        target = LOCAL_BASE
    if subdir:
        target = os.path.join(target, subdir)
    os.makedirs(target, exist_ok=True)
    return target


def cleanup_apple_double(directory):
    """清理 macOS 在非 HFS 卷上产生的 ._ 元数据文件。"""
    if not os.path.isdir(directory):
        return 0
    n = 0
    for root, _dirs, files in os.walk(directory):
        for f in files:
            if f.startswith("._"):
                try:
                    os.remove(os.path.join(root, f))
                    n += 1
                except OSError:
                    pass
    return n


def summarize(directory):
    """统计目录内真实图片数量与字节数。"""
    if not os.path.isdir(directory):
        return 0, 0
    count = size = 0
    for root, _dirs, files in os.walk(directory):
        for f in files:
            if f.startswith("._"):
                continue
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                count += 1
                try:
                    size += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
    return count, size
