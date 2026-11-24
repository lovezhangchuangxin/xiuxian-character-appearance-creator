# AGENTS.md

## 开发与验证

- 本项目是 2D 修仙角色捏脸与换装编辑器，使用 Vite、Vue 3、TypeScript 和 PixiJS。Node.js 与 pnpm 版本以 `package.json` 为准，依赖使用 `pnpm install --frozen-lockfile`。
- 用 `pnpm dev` 启动编辑器。改动交付前运行 `pnpm build`，覆盖类型检查、素材检查和生产构建。运行 `pnpm check:assets` 可检查素材登记并重新生成编辑器和发布包共用的清单。运行 `pnpm pack:assets` 可用 uv 打包运行时素材和接入示例。
- `pnpm install` 会通过 `prepare` 脚本自动安装 git hooks：commit-msg 用 commitlint 校验 Conventional Commits，pre-commit 用 lint-staged 对暂存文件跑 `oxlint --fix` 和 `oxfmt`。提交前可用 `pnpm lint`、`pnpm fmt` 预检，设置 `SKIP_SIMPLE_GIT_HOOKS=1` 可临时跳过 hooks。
- Python 美术工具位于 `scripts/`，安装方法、命令和写入位置见[素材工具指南](./scripts/README.md)。中间输出使用临时目录，提交保留正式素材、复现输入和有用的验收图。构建产物、依赖目录和缓存由 `.gitignore` 排除。

## 代码入口

| 内容                    | 文件                                                                    |
| ----------------------- | ----------------------------------------------------------------------- |
| 体型、部件、坐标与预设  | [catalog.ts](./packages/character-assets/source/catalog.ts)             |
| 捏脸操作与存档面板      | [App.vue](./apps/editor/src/App.vue)                                    |
| PixiJS 合成、近景和染色 | [CharacterCanvas.vue](./apps/editor/src/components/CharacterCanvas.vue) |
| 版本化外观码与校验      | [appearanceCode.ts](./apps/editor/src/character/appearanceCode.ts)      |

当前外观码记录体型、九个部位的 ID 和染色。改动素材时保持现有 ID 与原稿格号对应。界面标签可以独立调整。涉及外观码格式的改动须保留已有版本的读取能力，并在浏览器确认保存、刷新、读档及导入。

## 素材规范

- 男女各用自己的母版、素材和锚点。当前九个部位为脸型、眉毛、眼睛、鼻子、嘴巴、前发、后发、发髻和服装。每个部位按原稿从左到右、从上到下保留全部 16 格，文件名和界面编号用 `01` 到 `16`。无发片与白内搭是独立选项。
- 画风以项目参考图为准，使用简约的中国修仙漫画线条和克制上色。保持空手站姿。当前部件范围只涵盖这九个部位。
- 参考图进 `assets/references/`，实际提示词和参考图顺序进 `assets/prompts/`，原稿进 `assets/source/sheets/`，载图、定位数据和试装进 `assets/source/fit-tests/`。运行时透明 PNG 进 `assets/sprites/`，服装缩略图进 `assets/thumbnails/outfits/`。
- 五官在同体型 512 × 620 工作图上原位提取，左右眉和左右眼各成一对，以 `headOffset` 回贴。脸型只微调脸颊和下颌，耳位和五官锚点沿用母版。脸与颈部使用连续图层，服装领口叠在皮肤前。
- 发片沿透明轮廓拆分并逐件检查边缘。服装按 1024 × 1536 全身画布对位，必要时用多张精灵图覆盖 16 款。检查露肤区域的透明度、空手的袖口接合和鞋底位置。

## 试装验收

素材或合成顺序有改动时，在编辑器分别检查男女的近景和全身。用跨编号组合复核颈部与衣领接缝、长鬓发对眉眼的遮挡、发髻与头顶、宽袖和手。发现问题时记录体型、部件编号和预览范围，修复后用同一组合复验。素材检查脚本负责登记和格式，搭配效果以实际渲染为准。

[素材目录与制作流程](./assets/README.md) · [实际生图提示词](./assets/prompts/numbered-parts.md) · [固定混搭与整角试装](./assets/source/fit-tests/numbered-4x4/README.md)
