# 提示词设计

编译后的提示词是四段式结构，每段各管一件事。

## 骨架

```
Create one finished portrait photograph of a single real human,
not a collage, not a reference sheet, no text or watermark.

[Identity] <人物描述>. Keep this face, hairstyle and body build.
[Pose] <姿势描述>. Camera: <视角>.
  Follow this gesture, weight distribution and limb placement exactly.
  Do not draw mannequins, joint balls, guide lines or faceless heads.
[Outfit] <服饰描述>.
  Let the garment drape and wrinkle naturally with the pose. Fully clothed.
[Style] Photorealistic, natural skin texture, soft studio lighting,
  50mm lens, simple neutral background, full body visible.
```

## 每段为什么这样写

### 开头：负面约束前置

`not a collage, not a reference sheet` 必须放在最前面。模型容易把「多图输入」理解成「输出多图对照」，这句话把这条路径堵死。

### [Identity]

`Keep this face, hairstyle and body build` 是对身份的锁定。后面接 `[Pose]` 时不重复外观描述，避免模型把姿势参考里的外观也当成身份依据。

### [Pose]

两条禁令缺一不可：

- `Do not draw mannequins` —— 姿势参考常是人台，不禁的话成品会画成人偶
- `Do not draw faceless heads` —— 人台没有五官，模型会照抄成无脸

`weight distribution and limb placement exactly` 强调重心和四肢位置，这是「像不像那个姿势」的核心。

### [Outfit]

`Fully clothed` 是必须的。不提的话模型有时把「服饰参考」理解成「服装设计稿」，只画出衣服不穿在人身上。

`drape and wrinkle naturally with the pose` 解决衣服和姿势打架的问题：同一套衣服在不同动作下形态不同，让模型自己适配。

### [Style]

`simple neutral background` 避免背景喧宾夺主。`full body visible` 防止模型裁掉腿脚——姿势参考里腿的位置往往是重点。

## 视觉模型指令的设计

三份指令都用「只描述 X，不要提及 Y」的句式：

| 参考 | 只描述 | 明确排除 |
| --- | --- | --- |
| 姿势 | 躯干朝向、四肢位置、重心、手部、动作、视角 | 人偶、线稿、灰色、模特 |
| 服饰 | 单品、颜色、材质、版型、层次、鞋袜、配饰 | 模特的脸、发型、站姿 |
| 人物 | 发型发长、刘海、发色、脸型、肤色、五官、年龄 | — |

还都强制 `English only`，因为描述最终要拼进英文提示词，混入中文会干扰模型理解。

## 字数限制

姿势 60 词、服饰 50 词、人物 45 词。

太短抓不住关键细节，太长会稀释权重——提示词前 75 词权重最高，堆太多后面就失效了。
