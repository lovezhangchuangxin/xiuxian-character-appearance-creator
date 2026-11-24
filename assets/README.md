# 角色美术素材

| 目录                                                                        | 用途                                 |
| --------------------------------------------------------------------------- | ------------------------------------ |
| [references/style](./references/style/)                                     | 修仙漫画线稿、上色和服饰参考         |
| [references/masters/bodies/original](./references/masters/bodies/original/) | 原始男女身体模板                     |
| [references/masters/heads](./references/masters/heads/)                     | 男女各自的空脸、完整脸和同尺度对照   |
| [references/hair](./references/hair/)                                       | 编号发片使用的发色和线稿参照         |
| [prompts](./prompts/README.md)                                              | 可复制模板和能复现当前素材的生图记录 |
| [source/sheets](./source/sheets/)                                           | 在用素材的生图原稿                   |
| [source/fit-tests](./source/fit-tests/)                                     | 当前批次的载图、坐标和验收图         |
| [sprites](./sprites/)                                                       | 编辑器加载的透明图层                 |
| [thumbnails/outfits](./thumbnails/outfits/)                                 | 编辑器服装格的轻量缩略图             |

白内搭同时作为运行时身体和全身对位参考，直接使用 [男版白内搭](./sprites/bodies/male/white.png)或[女版白内搭](./sprites/bodies/female/white.png)。

## 目录与坐标

- 运行时图层使用 `sprites/<bodies|faces|hair|outfits>/<male|female>/`。男女分别登记素材，每个部位都按原稿顺序编号 `01.png` 至 `16.png`。白内搭和可关闭的发层设在编号网格下方。
- 身体和服装保持 1024 × 1536 原画布。编号服装保留独立的透明原稿，入库时叠入同体型母版的空手。头部和颈部用连续图层，衣领叠在颈部之前。
- 脸型在 `shapes/`，其余五官按 `brows/`、`eyes/`、`noses/`、`mouths/` 存放。头部工作图是 512 × 620，按[头部基准](./source/fit-tests/faces/README.md)换算到全身坐标。眼和眉按左右一对裁切，裁片使用 `headOffset` 原位回贴。脸型变化集中在脸颊和下颌，保留耳位、五官区与颈部接合点。
- 发型分为 `front/`、`back/`、`top/`。按整张原稿上的连通轮廓拆发片，再分别登记合成尺寸和头顶锚点。

## 从生图到入库

1. 从[提示词索引](./prompts/README.md)选择模板。一批只使用一个体型和一个部位的母版，记录完整提示词、参考图上传顺序和原稿。
2. 在 `source/fit-tests/` 保存载图、定位数据和试装结果。用近景看整脸协调和透明边缘，用缩略头像看区分度。使用差分脚本时保留 `placements.json` 作为原位回贴记录。
3. 按原稿顺序将全部 16 格放进 `sprites/`，保留各格的裁片坐标。发现遮挡或裁切缺陷时，修复对应格再复验。各部位编号、锚点和预设见[素材清单](../packages/character-assets/source/catalog.ts)。
4. 运行 `pnpm check:assets` 和 `pnpm build`。自动检查覆盖文件登记、男女路径、预设引用、PNG 透明格式和全身画布尺寸。可见光晕、遮挡和风格仍通过实际叠放检查。

完整原稿按部位和体型归档，供重新提取及扩展。重复裁片和透明回贴中间图可由脚本复现。[全量编号提示词](./prompts/numbered-parts.md)

脚本的命令示例、输入和写入位置见[素材工具使用指南](../scripts/README.md)。
