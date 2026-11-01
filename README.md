# Pose × Costume × Character

> ⚠️ **内容提示**
>
> 本项目依赖的参考图库面向成年创作者，包含内衣、泳装等成人向服饰分类，
> 部分内容不适合未成年人。请遵守所在地法律法规与平台规范，未成年人请勿使用。
>
> 图库与其中全部图片、原始数据、名称的版权归上游原作者所有，
> 本项目不再分发这些素材，也不对其内容负责。

---

**用三张参考图生成一张完整的角色成品图。**

姿势图决定动作，服饰图决定穿搭，人物图决定身份与画风。三份参考各管一件事，模型按职责分离合成，输出单幅人物照——不是拼贴，不是对照表。

```
姿势参考  ┐
服饰参考  ├─→  职责分离提示词  ─→  成品人物图
人物参考  ┘
```

> **这个仓库只含工具，不含图片素材。**
>
> 选图、生成都依赖一份本地参考图库。仓库不带图库，
> 因为那是别人的版权素材，不该由这里再分发一次。
>
> 图库从上游一键拉取：
>
> ```bash
> ./scripts/fetch-gallery.sh
> ```
>
> 约 800MB。图片版权归上游原作者所有，使用前请阅读其授权条款。

---

## 为什么需要「职责分离」

直接丢三张图给模型，常见结果是把三张图揉成一团：姿势图的人偶线条跑进成品，服饰模特的脸盖掉人物参考，衣服穿了一半。

本项目把每张图的职责写死，并明确禁止越界：

| 参考 | 采用 | 禁止迁移 |
| --- | --- | --- |
| 人物 | 五官、脸型、发型发色、肤色、体型比例 | 原衣服、原姿势 |
| 姿势 | 四肢位置、躯干转向、重心、支撑点、视角 | 人偶线条、关节球、无脸头部 |
| 服饰 | 版型、颜色、层次、材质、图案、配饰、鞋袜 | 模特的脸、发型、体型、站姿 |

提示词还强制声明「只交付一幅人物图，不制作拼贴、对照图、说明文字、水印」，防止模型偷懒输出三栏并排。

---

## 两种工作模式

### 一、网页版（看图选，选完直接出图）

```bash
python3 scripts/server3in1.py
```

打开 `http://127.0.0.1:8125`，三栏并排浏览缩略图，选中后点「生成图片」。

```
┌──────────┬──────────┬──────────┐
│  姿势    │  服饰    │  人物    │   看缩略图挑
└──────────┴──────────┴──────────┘
┌──────────────────────────────────┐
│ [1024×1536] [额外要求] [生成图片] │
├──────────────────────────────────┤
│        生成结果                   │
│  [保存] [打开文件夹] [复制路径]   │
└──────────────────────────────────┘
```

适合边看边挑，不记编号。

### 二、命令行版（可脚本化、可批量）

```bash
python3 scripts/pose3in1.py --pose P008 --costume SPR-0165 --face ff580239863
```

适合批处理、写进流水线、配合其他脚本。

---

## 安装

### 环境要求

- Python 3.9+
- 无需第三方库（只用标准库）

### 配置

需要两样东西：一个图库，一组模型 API 凭证。

**1. 拉取图库**

```bash
./scripts/fetch-gallery.sh
```

默认拉到 `./gallery`。也可以指定位置：

```bash
./scripts/fetch-gallery.sh ~/my-gallery
```

图库结构如下：

```
<图库根目录>/
├── data/
│   ├── poses.json       # 姿势索引
│   ├── costumes.json    # 服饰索引
│   ├── faces.json       # 人像索引
│   └── tags.json        # 标签三语词典（可选，用于中文搜索）
├── img/                 # 姿势原图
├── thumbs/              # 姿势缩略图
├── costume/
│   ├── img/
│   └── thumbs/
└── portrait/
    └── thumbs/
```

数据结构示例见 [docs/DATA-FORMAT.md](docs/DATA-FORMAT.md)。

**2. 环境变量**

```bash
export PCC_API_KEY="sk-..."              # 必填
export PCC_API_BASE="https://.../v1"     # 可选，OpenAI 兼容端点
export PCC_VL_MODEL="qwen3-vl-plus"      # 可选，视觉模型
export PCC_IMG_MODEL="qwen-image-2.1-pro" # 可选，生图模型
export PCC_GALLERY="/path/to/gallery"    # 必填，图库根目录
export PCC_PORT="8125"                   # 可选，网页版端口
```

也可以在同一目录建 `.env` 文件，启动脚本会自动读取（见 `scripts/run.sh`）。

**API Key 不要提交到仓库。** `.gitignore` 已排除 `.env`。

---

## 原理：为什么是两段式

多图参考生图（把三张图直接提交给模型）效果最好，但需要支持该能力的模型。

如果手头的模型只支持文生图，本项目提供两段式替代：

```
① 视觉模型分别读三张图
   ├─ 姿势 → "weight on the right leg, left leg lifted..."
   ├─ 服饰 → "cream lace-knit crop top, ruffled hem..."
   └─ 人物 → "shoulder-length brown hair, soft bangs..."
        ↓ 编译成职责分离的结构化提示词
② 文生图模型出图
```

视觉模型读图得到的信息量远大于图库自带的标签。同一个服饰条目，标签可能只有 `ivory, shorts, black, tights` 四个词，视觉模型能读出「蕾丝针织、交叉绑带、荷叶边、抽绳腰、露趾粗跟」这些可复现的细节。

代价是人物相似度只能做到「神似」——文字描述无法完整承载面部特征。要精确锁脸需要 IP-Adapter FaceID 一类的能力。

---

## 用法

### 基础

```bash
# 三项齐选
python3 scripts/pose3in1.py --pose P008 --costume SPR-0165 --face ff580239863

# 指定视角
python3 scripts/pose3in1.py --pose P008 --angle high --costume SPR-0165

# 人物用文字描述
python3 scripts/pose3in1.py --pose P008 --costume SPR-0003 \
    --figure "short black hair, cool pale skin, woman in her twenties"
```

### 调试

```bash
# 只看提示词，不出图
python3 scripts/pose3in1.py --pose P008 --costume SPR-0165 --prompt-only

# 只显示配置
python3 scripts/pose3in1.py --pose P008 --costume SPR-0165 --dry-run

# 跳过视觉模型，直接用图库标签（省钱、快）
python3 scripts/pose3in1.py --pose P008 --costume SPR-0165 --no-vision
```

### 批量

```bash
# 同配置出三张不同种子
python3 scripts/pose3in1.py --pose P008 --costume SPR-0165 --face ff5 -n 3

# 循环多组
for p in P001 P008 P031; do
  for c in SPR-0001 SPR-0165; do
    python3 scripts/pose3in1.py --pose $p --costume $c --face ff5
  done
done
```

---

## 参数

| 参数 | 说明 | 默认 |
| --- | --- | --- |
| `--pose` | 姿势编号 | — |
| `--angle` | 视角：front / high / low / side / diagonal | front |
| `--costume` | 服饰编号 | — |
| `--face` | 人像 ID 前缀 | — |
| `--figure` | 人物文字描述（`--face` 的替代） | — |
| `--extra` | 附加要求 | 空 |
| `--size` | 1024x1024 / 1024x1536 / 1536x1024 | 1024x1536 |
| `-n` | 生成张数 | 1 |
| `--tag` | 文件名前缀 | 三合一 |
| `--no-vision` | 跳过视觉模型 | false |
| `--prompt-only` | 只输出提示词 | false |
| `--dry-run` | 只显示配置 | false |

---

## 输出

输出位置由环境变量决定：

| 变量 | 作用 |
| --- | --- |
| `PCC_VOLUME` | 外置卷根路径，如 `/Volumes/MyDisk`。留空则不用外置卷 |
| `PCC_VOLUME_SUBDIR` | 卷内子目录，默认 `AI生成图/三合一` |
| `PCC_LOCAL_OUT` | 本地目录，外置卷不可用或未配置时使用 |

```
$PCC_VOLUME/$PCC_VOLUME_SUBDIR/     # 配置了外置卷且可写
$PCC_LOCAL_OUT/                     # 否则
```

「可写」通过真实写测试判断，不是只看目录存不存在。

文件名格式：`<前缀>_<姿势编号>_<视角>_<服饰编号>_<人像ID>_<时间戳>.png`

在非 HFS/APFS 卷上会自动清理 macOS 产生的 `._` 元数据文件。

---

## 已知限制

**姿势复杂时会走样。** 极端动作（如单腿抬至肩高并握踝）在纯文生图下正确率有限。同一个姿势多试几个种子通常能改善。

**人物相似度是「神似」。** 文字描述无法完整承载面部特征。要精确锁脸需要 IP-Adapter FaceID 一类的能力，本项目未包含。

**长提示词容易超时。** 已内置 3 次重试，仍失败多为服务端排队。

**依赖具体模型。** 视觉读图与生图质量取决于所配模型，本项目只做编排。

---

## 目录结构

```
pose-costume-character/
├── scripts/
│   ├── pose3in1.py       # 核心：读图 → 编译提示词 → 生图
│   ├── server3in1.py     # 网页版后端
│   ├── pick3in1.py       # 终端交互版
│   ├── outpath.py        # 输出路径解析
│   └── run.sh            # 一键启动
├── static/
│   └── combine.html      # 网页前端
├── docs/
│   ├── DATA-FORMAT.md    # 数据结构说明
│   └── PROMPT-DESIGN.md  # 提示词设计说明
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

---

## 许可

代码使用 MIT 许可，见 [LICENSE](LICENSE)。

图库中的图片、原始数据与名称归各自原作者所有，不在本许可范围内。使用前请确认上游素材的授权条款。
