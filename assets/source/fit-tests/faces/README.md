# 头部基准与脸部试装

从 [男版白内搭](../../../sprites/bodies/male/white.png)和[女版白内搭](../../../sprites/bodies/female/white.png)裁出头部，按同一尺度生成[空脸对照](../../../references/masters/heads/aligned/blank.png)和[完整脸对照](../../../references/masters/heads/aligned/complete.png)。

| 体型 | 对照图左瞳  | 对照图右瞳  | 全身双瞳中点约值 |
| ---- | ----------- | ----------- | ---------------- |
| 男   | (293, 406)  | (467, 406)  | (511, 129)       |
| 女   | (1063, 417) | (1242, 416) | (512, 242)       |

1536 × 1024 对照图的头部裁片以全身原画布为起点放大三倍。男性全身裁片原点为 (384, 24)，女性为 (384, 134)，在各自 768 像素宽单元内下移 92 像素。独立的 512 × 620 头部工作图从对照图裁切，左上角为男 (128, 115) 和女 (896, 115)。

同体型五官的透明提取与原位回贴见[原稿和参考图](../../../prompts/numbered-parts.md)，整脸与袖口检查见[男女整角试装](../numbered-4x4/README.md)。

## 标准脸参考

标准对照通过[标准脸导出脚本](../../../../scripts/standard_face.py)从男女完整脸分别拆成眉、眼、鼻、嘴。下方对照图左侧是完整脸原稿，右侧是四个裁片从空脸重组的效果。

| 体型 | 重组与坐标                                                                                   |
| ---- | -------------------------------------------------------------------------------------------- |
| 男   | [重组对照](./standard/male/comparison.png) · [裁片坐标](./standard/male/placements.json)     |
| 女   | [重组对照](./standard/female/comparison.png) · [裁片坐标](./standard/female/placements.json) |

运行时以 `headOrigin + headOffset / 3` 把裁片放回 1024 × 1536 全身画布。现在男女脸型、眉眼、鼻嘴各保留完整的 16 个编号。[编号试装](../numbered-4x4/README.md)

## 复现一个五官批次

从项目根目录运行，输出到临时目录。其余批次用各自的体型、部位和原稿替换参数。提交保留原稿、载图、运行时裁片和定位数据。

```sh
art_work="$(mktemp -d)"
python3 scripts/feature_sheet.py extract --body male --part eyes --grid 4 \
  --carrier assets/source/fit-tests/faces/numbered-4x4/male/eyes/carrier.png \
  --edited assets/source/sheets/faces/male/eyes-numbered-4x4.png \
  --output "$art_work"
```
