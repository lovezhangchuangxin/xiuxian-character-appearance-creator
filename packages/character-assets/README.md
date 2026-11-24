# 修仙角色素材包

解压后从 `manifest.json` 读取体型、部位、预设和图层顺序。PNG 是带透明度的精灵图，服装的 WebP 用于选择面板。图片和示例路径均以清单所在目录为基准。Web 项目可以把解压目录放到静态资源目录，其他引擎可以直接读文件。依照 `manifest.schema.json` 校验 v1 清单。

## 合成

1. 建立 `canvas.width × canvas.height` 的透明画布。坐标以左上为原点，向右和向下递增，单位是角色画布像素。
2. 按 `slots` 显示各部位的选项。给定体型后，从 `bodies[body].parts[slot]` 按部件 `id` 查询选中项。用 `presets.calm` 或 `presets.wandering` 取得一套完整选择。选项有 `thumbnail` 时可用它展示缩略图。
3. 按 `layers` 从后往前绘制选中的图层。把完整的 `image` 缩放到 `rect` 并放在它的左上坐标，保留小数。使用线性采样和普通透明叠加。有 `clip` 时在角色画布坐标中裁剪本图层，裁剪不影响下一层。遇到 `image: null` 跳过这一层。白内搭是有图片和裁剪矩形的服装选项。
4. 自行定取景，或使用体型下的 `views` 对齐演示编辑器。取景的 `x`、`y` 表示中心点，`width` 和 `height` 是期望可见范围。按目标预览框等比缩放，以该点居中。

首版参考图以原色合成。`dyeable: true` 标记演示编辑器可染色的服装。合成原色时直接使用服装 PNG。

## 外观存档

建议保存 `packId`、`packVersion`、`body` 和 `parts`。每个部件 ID 在同一体型和部位内有效。加载时用匹配版本的素材包，并校验选项是否存在。`schemaVersion` 决定清单的解析规则，`packVersion` 用来定位素材版本。发布新版本时保留旧包，供旧存档使用。

## 示例

`examples/appearances.json` 提供男女各两组外观，覆盖跨编号混搭、无发片和白内搭。`reference` 指向以同一画布和同一套外观生成的参考图。以任意静态服务器打开解压目录里的 `examples/index.html`，可查看原生 Canvas 2D 合成和参考图。浏览器直接打开本地 HTML 时可能拦截 JSON 请求。

仓库的 `LICENSE` 适用于软件与相关文档。运行时图片的对外授权范围尚待明确。
