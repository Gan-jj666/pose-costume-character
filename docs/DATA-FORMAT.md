# 数据结构

图库需要 `data/` 目录下四份 JSON。

## poses.json

```json
{
  "angles": [
    {"key": "front", "names": {"zh": "正面", "en": "Front", "ja": "正面"}}
  ],
  "categories": [{"key": "standing", "names": {"zh": "站姿"}}],
  "poses": [
    {
      "id": "full_std_P019",
      "series": "full_std",
      "category": "站姿",
      "no": "P019",
      "names": {
        "zh": "站立・双臂上举伸展",
        "en": "Standing, arms reaching overhead",
        "ja": "立ち・両腕を頭上に伸ばす"
      },
      "variants": [
        {
          "angle": "front",
          "thumb": "thumbs/full_std_P019_front.jpg",
          "full": "img/full_std_P019_front.png"
        }
      ]
    }
  ]
}
```

- `variants[].full` 是生图时实际读取的图
- `variants[].thumb` 是网页列表用的缩略图
- 路径相对于图库根目录

## costumes.json

```json
{
  "categories": [{"key": "spring", "names": {"zh": "春"}, "count": 215}],
  "groups": [{"key": "dress", "names": {"zh": "连衣裙"}, "count": 191}],
  "costumes": [
    {
      "id": "SPR-0001",
      "cat": "spring",
      "group": "top",
      "color": "ivory",
      "main": "knit",
      "tags": ["ivory", "frill", "knit", "skirt"],
      "thumb": "costume/thumbs/SPR-0001.webp",
      "image": "costume/img/SPR-0001.webp"
    }
  ]
}
```

- `tags` 用英文单词，便于跨语言检索
- `image` 是生图读取的全尺寸图

## faces.json

```json
{
  "sections": [{"key": "face", "names": {"zh": "脸部"}, "count": 893}],
  "hairs": [{"key": "short", "names": {"zh": "短发"}, "count": 727}],
  "images": [
    {
      "id": "f71f980dde3",
      "sec": "face",
      "hair": "short",
      "style": "",
      "w": 1122,
      "h": 1402,
      "thumb": "portrait/thumbs/f71f980dde3.webp",
      "full": "portrait/img/f71f980dde3.png"
    }
  ]
}
```

- 程序默认读 `thumb`（体积小、足够视觉模型识别）
- 若 `full` 存在可改读原图提升精度

## tags.json（可选）

用于中文/日文搜索。没有此文件时只能按英文标签检索。

```json
{
  "tagNames": {
    "black": {"zh": "黑色", "en": "Black", "ja": "黒"},
    "lace":  {"zh": "蕾丝", "en": "Lace",  "ja": "レース"}
  },
  "colorTags": ["black", "white", "ivory"],
  "groups": []
}
```
