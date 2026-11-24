# 离线素材工具

前端开发、构建与运行使用现成的透明图层，只需要项目的 Node.js 和 pnpm。重新制作或对齐素材时才需要 Python。以下命令在仓库根目录执行；Python 版本与环境用 [uv](https://docs.astral.sh/uv/) 管理，`.python-version` 固定为 3.10。

首次使用安装 uv，然后在仓库根目录执行一次：

```sh
uv sync
art_work="$(mktemp -d)"
```

`uv sync` 按 `uv.lock` 精确重建 `.venv`，uv 会自动准备所需的 Python 3.10（无需预装）。后续命令用 `uv run python` 前缀，无需激活环境，`art_work` 沿用同一终端。无法使用 uv 时可用传统 pip 兜底：`python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements-art.txt`，命令前缀换成 `.venv/bin/python`（Windows 为 `.venv\Scripts\python.exe`）；兜底方式需要系统 Python 在 3.10–3.13 范围内（依赖包 wheel 的覆盖范围）。Python 侧的检查与格式化用 ruff：`uv run ruff check scripts/`、`uv run ruff format scripts/`。本机启用 RTK 时，按项目约定为命令加 `rtk` 前缀。

| 脚本                                                   | 用途                                                 | 写入位置                                                                          |
| ------------------------------------------------------ | ---------------------------------------------------- | --------------------------------------------------------------------------------- |
| [feature_sheet.py](./feature_sheet.py)                 | 制作五官留空载图，从编辑后的网格提取透明裁片并回贴   | `--output`                                                                        |
| [install-feature-batch.py](./install-feature-batch.py) | 校验并按原稿顺序安装一组或多组完整 4 × 4 五官裁片    | `assets/sprites/faces/` 和 `packages/character-assets/source/numbered-faces.json` |
| [shape-sheet.py](./shape-sheet.py)                     | 对齐 16 个脸型，保留耳位和五官锚点，延伸连续颈部     | 正式脸型 PNG、脸型缩略图，以及 `--output` 中的定位和验收图                        |
| [hair-sheet.py](./hair-sheet.py)                       | 按透明轮廓拆成 16 张前发、后发或发髻，计算摆放参数   | `assets/sprites/hair/` 和 `packages/character-assets/source/numbered-hair.json`   |
| [outfit-sheet.py](./outfit-sheet.py)                   | 合并四张服装原稿，匹配领口和袖口，生成套装与缩略图   | 正式服装 PNG、WebP 缩略图，以及 `--output` 中的试装和定位数据                     |
| [standard_face.py](./standard_face.py)                 | 从同体型完整脸和空脸拆出一张标准脸的四个部件         | `--output` 中的各部件、坐标和对照图                                               |
| [eye_sheet.py](./eye_sheet.py)                         | 提供对位、差分和透明处理函数，也保留独立眼睛试样命令 | 独立运行时只写 `--output`                                                         |

会写入正式素材的脚本基于脚本文件所在的仓库定位输出。`--output` 只控制试装或中间文件位置。试跑入库、脸型、发型和服装时可用独立工作树，方便比较生成前后的差异。

## 五官

`prepare` 会复制同体型的完整脸，并只留空当前部位。常用参数为 `--body male|female`、`--part brows|eyes|noses|mouths` 和 `--grid 4`。眉眼新试样可加 `--guide` 导出基础示意。复现已入库批次时使用仓库保存的载图、轮廓示意和生图原稿。[实际提示词与参考图顺序](../assets/prompts/numbered-parts.md)

```sh
uv run python scripts/feature_sheet.py prepare --body male --part eyes --grid 4 \
  --blank assets/references/masters/heads/male/blank.png \
  --complete assets/references/masters/heads/male/complete.png \
  --output "$art_work/carrier.png" --guide "$art_work/guide.png"

uv run python scripts/feature_sheet.py extract --body male --part eyes --grid 4 \
  --carrier assets/source/fit-tests/faces/numbered-4x4/male/eyes/carrier.png \
  --edited assets/source/sheets/faces/male/eyes-numbered-4x4.png \
  --output "$art_work/eyes"
```

检查 `reassembled.png` 的整脸效果与 `reassembled-transparent.png` 的边缘，再看 `placements.json` 是否有 16 格及拒绝原因。入库命令可接收多个提取目录。它会先校验所有批次，写入失败时回滚。入库会覆盖对应体型与部位的 `01.png` 至 `16.png`，同时更新各格坐标。

```sh
uv run python scripts/install-feature-batch.py "$art_work/eyes"
```

## 脸型、发型和服装

以下以男修为例。女修用自己的原稿及 `--body female`。发型的 `--part` 可以是 `front`、`back` 或 `top`。先生成脸型，再重新生成需要更新试装图的服装。服装脚本使用同体型的白内搭母版和 `01` 脸型生成试装。

```sh
uv run python scripts/shape-sheet.py --body male \
  --edited assets/source/sheets/faces/male/shapes-numbered-4x4.png \
  --output "$art_work/shapes"

uv run python scripts/hair-sheet.py --body male --part front \
  --sheet assets/source/sheets/hair/male/front-numbered-4x4.png

uv run python scripts/outfit-sheet.py --body male --sheets \
  assets/source/sheets/outfits/male/numbered-01-04.png \
  assets/source/sheets/outfits/male/numbered-05-08.png \
  assets/source/sheets/outfits/male/numbered-09-12.png \
  assets/source/sheets/outfits/male/numbered-13-16.png \
  --output "$art_work/outfits"
```

服装四张原稿各 2 × 2，按参数顺序连续编号。袖口对位需要手调时，可加 `--wrists path/to/wrists.json`。格式见下方，`left` 与 `right` 按画面左右，坐标以 1024 × 1536 画布为基准。可从试装输出的 `placements.json` 读取自动结果作为起点。

```json
{ "01": { "left": [320, 725], "right": [705, 725] } }
```

## 参考与局部试制

```sh
uv run python scripts/standard_face.py --body male \
  --blank assets/references/masters/heads/male/blank.png \
  --complete assets/references/masters/heads/male/complete.png \
  --output "$art_work/standard"

uv run python scripts/eye_sheet.py prepare --body male --columns 2 --rows 2 \
  --blank assets/references/masters/heads/male/blank.png \
  --complete assets/references/masters/heads/male/complete.png \
  --output "$art_work/eye-trial.png"
```

旧版眼睛试样可用 `eye_sheet.py extract --body male --columns 2 --rows 2 --carrier <载图> --edited <原稿> --output <目录>` 单独分析。正式 4 × 4 入库使用上文的五官流程。各脚本可加 `--help` 查看参数。

修改正式素材后运行 `pnpm check:assets` 和 `pnpm build`。在编辑器逐体型看近景与全身，重点确认透明边缘、眉眼位置、颈部与领口、袖口与手。[固定混搭与整角试装](../assets/source/fit-tests/numbered-4x4/README.md)
