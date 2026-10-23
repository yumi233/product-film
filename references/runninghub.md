# RunningHub 接入

## 账号与 key
- 用户用的是**会员（消费）key**，扣 RH 币。它可以跑工作流：`/task/openapi/upload`、`/task/openapi/create`、`/task/openapi/status`、`/task/openapi/outputs`。
- **标准模型 API**（`/openapi/v2/...`，比如万相、可灵、TTS、作曲）只能用企业共享 key 调用，会员 key 会返回错误 1014。所以本技能只走工作流。
- key 存在环境变量 `RUNNINGHUB_API_KEY` 里，写在 `~/.zshrc`。运行时要用 `zsh -ic "python3 ..."` 才能读到。**不要让用户把 key 贴到聊天里，也不要打印 key。**
- 查余额：`rh_run.py --check`，返回 RH 币、钱包余额和正在运行的任务数。
- 钱包余额为 0 时，网页画布上的官方 H3 用不了（768P、6 秒一条扣 ¥2.88）。要花钱包里的钱，必须先问用户。

## 工作流：AITUDOU MiniMax H3 ReferenceToVideo（2113173574050729986）
| 节点 | 作用 | 字段 |
|---|---|---|
| 88 / 84 / 86 / 87 | 参考图 1–4（LoadImage） | image |
| 94 | 提示词（Text） | text |
| 85 | 视频时长，单位秒（Float，默认 13.5） | value |
| 63 | 最终画面大小，单位百万像素（ResolutionSelector，固定 16:9，默认 0.4） | megapixels |
| 111 | 二次采样器的首采缩放比例（SelfLiftH3Sampler，默认 0.5） | lowres_scale |

**分辨率和费用（实测）**

| megapixels / lowres | 输出 | 8 秒的费用 | 用时 |
|---|---|---|---|
| 1.0 / 0.5 | 1376×768 | 约 50 币 | 约 4 分钟 |
| **2.07 / 0.66** | **1952×1120** | **约 100 币** | **约 8 分钟** |

- 2.07 / 0.66 这一档：先在约 0.9 MP 出初版，再用潜空间放大和二次采样到约 1080p。这是用户要的档位。
- 1952×1120 的比例是 1.743，比 16:9 略窄。cut.py 会先缩放到 1920 宽，再裁成 1080 高，不会把画面压扁。
- 视频自带一轨环境声。
- **不支持真正的首尾帧**。给两张参考图时，结尾会靠近第二张，但不一定精确。

另一个工作流 Work-Fisher（2109735475824123905）是单次采样、只有两张参考图、0.8 MP，其余功能组都被禁用了，API 打不开。没有理由用它。

## 并发与报错
- 每个账号同时只能跑 1 个任务。再提交会返回 421 `TASK_QUEUE_MAXED`。rh_run.py 遇到会每 30 秒重试一次，所以批量任务只能按顺序跑。
- 状态每 20 秒查一次，一条通常 8–10 分钟。批量任务放到后台跑，等完成通知，不要守着轮询。
- 跑完会打印 `SAVED <path> coins <n>`。把每条的币数加起来，汇报给用户。

## 其他可以用 RH 币跑的应用（备用）
- `RH Suno_Single`（webappId 1972977443998928898）：作曲，但输出带人声的歌，计费方式也没确认，用之前先问用户。
- `IndexTTS2`（webappId 1965684535247650818）：声音克隆，需要一段参考录音。
- 查应用的节点：`python3 ~/.claude/skills/runninghub/scripts/runninghub_app.py --info <webappId>`。
