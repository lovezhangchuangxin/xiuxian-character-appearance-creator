# 修仙角色外观

使用 Vite、Vue 3、TypeScript 和 PixiJS 的 2D 捏脸与换装样机。浏览器需支持 WebGL。开发环境使用 Node.js 20.19 以上的 20.x 版本或 Node.js 22.12 及以上，以及 `package.json` 声明的 pnpm 版本。

```sh
pnpm install --frozen-lockfile
pnpm dev
pnpm build
```

`pnpm build` 依次执行类型检查、运行时素材检查与 Vite 构建。`pnpm check:assets` 可单独检查素材登记，`pnpm preview` 查看构建产物。

编辑器可保存一个当前浏览器的外观存档。使用「外观码」可复制并导入同一套体型、九个部位编号和布料染色。外观码版本与校验由 [appearanceCode.ts](./src/character/appearanceCode.ts) 定义。

## 扩展入口

| 内容 | 入口 |
| --- | --- |
| 五官、发型和换装素材 | [目录结构、坐标和入库流程](./assets/README.md) |
| 生图与试装 | [当前编号批次提示词](./assets/prompts/numbered-parts.md) · [男女整角试装](./assets/source/fit-tests/numbered-4x4/README.md) |
| 运行时部件、预设和对位 | [素材清单](./src/character/catalog.ts) · [PixiJS 合成](./src/components/CharacterCanvas.vue) |

离线美术工具使用 Python，依赖记录在 [requirements-art.txt](./scripts/requirements-art.txt)。前端开发与构建使用 pnpm。
