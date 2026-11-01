#!/bin/bash
# 拉取参考图库
#
# 本项目是编排工具，不含图片素材。运行此脚本从上游拉取图库。
#
# 用法：
#   ./scripts/fetch-gallery.sh [目标目录]
#
# 默认目标：./gallery

set -e

cd "$(dirname "$0")/.." || exit 1
TARGET="${1:-./gallery}"

UPSTREAM="https://github.com/HRuiCcc/RuiC-PoseAtlas.git"

echo "════════════════════════════════════════════════════"
echo "  拉取参考图库"
echo "════════════════════════════════════════════════════"
echo ""
echo "  来源  $UPSTREAM"
echo "  目标  $TARGET"
echo "  体积  约 800MB（浅克隆，跳过完整历史）"
echo ""
echo "  ⚠️  图片版权归上游原作者所有，本项目不再分发。"
echo "      使用前请阅读上游仓库的授权条款。"
echo ""

if [ -d "$TARGET" ]; then
    echo "目标已存在：$TARGET"
    if [ -d "$TARGET/data" ]; then
        echo "看起来已经是图库了。"
        echo ""
        read -r -p "重新拉取？会删除现有目录 (y/N) " ans
        if [ "$ans" != "y" ] && [ "$ans" != "Y" ]; then
            echo "已取消"
            exit 0
        fi
        rm -rf "$TARGET"
    fi
fi

# 检查 git
if ! command -v git >/dev/null 2>&1; then
    echo "❌ 找不到 git，请先安装"
    exit 1
fi

echo "开始拉取…（约 800MB，视网络而定）"
echo ""

if git clone --depth 1 "$UPSTREAM" "$TARGET"; then
    echo ""
    echo "════════════════════════════════════════════════════"
    echo "  ✅ 完成"
    echo "════════════════════════════════════════════════════"
    echo ""
    echo "  图库位置：$(cd "$TARGET" && pwd)"
    echo ""
    echo "  接下来在上面那行路径前加上 PCC_GALLERY= 写进 .env："
    echo ""
    echo "    PCC_GALLERY=$(cd "$TARGET" && pwd)"
    echo ""
    echo "  然后运行 ./scripts/run.sh"
    echo ""
else
    echo ""
    echo "❌ 拉取失败"
    echo ""
    echo "  可能原因："
    echo "    - 网络问题，重试一次"
    echo "    - 磁盘空间不足（需要至少 2GB 可用）"
    echo "    - 上游仓库地址变了，请查看 README"
    echo ""
    exit 1
fi
