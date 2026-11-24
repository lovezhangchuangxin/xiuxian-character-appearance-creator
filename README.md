# 修仙角色外观

使用 Vite、Vue 3、TypeScript 和 PixiJS 的 2D 捏脸与换装样机。浏览器需支持 WebGL。开发环境使用 Node.js 20.19 以上的 20.x 版本或 Node.js 22.12 及以上，以及 `package.json` 声明的 pnpm 版本。

```sh
pnpm install --frozen-lockfile
pnpm dev
pnpm build
```

`pnpm build` 先检查运行时素材并生成清单，再执行编辑器的类型检查和 Vite 构建。编辑器产物位于 `apps/editor/dist/`。`pnpm check:assets` 可单独检查素材登记，`pnpm preview` 查看构建产物。

提交信息遵循 Conventional Commits，commit-msg 钩子用 commitlint 校验；pre-commit 钩子对暂存文件运行 oxlint 与 oxfmt（Python 美术脚本用 ruff），`pnpm install` 时自动安装。

编辑器可保存一个当前浏览器的外观存档。使用「外观码」可复制并导入同一套体型、九个部位编号和布料染色。外观码版本与校验由 [appearanceCode.ts](./apps/editor/src/character/appearanceCode.ts) 定义。

## 扩展入口

| 内容                   | 入口                                                                                                                        |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| 五官、发型和换装素材   | [目录结构、坐标和入库流程](./assets/README.md)                                                                              |
| 生图与试装             | [当前编号批次提示词](./assets/prompts/numbered-parts.md) · [男女整角试装](./assets/source/fit-tests/numbered-4x4/README.md) |
| 运行时部件、预设和对位 | [素材清单](./packages/character-assets/source/catalog.ts) · [PixiJS 合成](./apps/editor/src/components/CharacterCanvas.vue) |

离线素材的环境安装、命令示例和输出位置见[素材工具使用指南](./scripts/README.md)。前端开发与构建使用 pnpm。

## 接入其他项目

从仓库根目录运行 `pnpm pack:assets`，使用现有 uv 环境把清单、图片和示例打成 `dist/xiuxian-character-assets-<版本>.zip`。解压后将 `manifest.json` 和同级图片目录交给自己的渲染方案。清单格式和合成规则见[素材包接入说明](./packages/character-assets/README.md)。

编辑器是工作区里的 `@xiuxian/editor`，从 `@xiuxian/character-assets` 读取同一份生成清单。已有的素材制作命令仍从仓库根目录执行。在开发服务器运行期间重新入库素材后，运行 `pnpm check:assets` 并刷新页面。

更新素材、对位或示例搭配后，运行 `pnpm refs:assets` 重生成参考图和校验记录，再运行 `pnpm pack:assets`。打包时会校验参考图对应的素材和坐标，并解码全部服装缩略图。

已交付的 ZIP 版本用于复现存档。发布内容变更时，递增 `packages/character-assets/package.json` 的版本并保留旧 ZIP。对于本地已有的同版本 ZIP，打包命令会保留内容相同的存档，遇到不同内容时会报错。
