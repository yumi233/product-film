# product-film

一个 Claude Code / Codex 技能，用 AI 给**家具或产品**做 1–3 分钟的介绍短片。从创意、完整脚本、关键帧，到视频生成、旁白、配乐，一直做到粗剪。带新用户引导和环境自检；流程是一幕一审：每一步先给用户看，确认后再花钱生成。视频模型只生成无说话声的环境音效；旁白由用户提供录音，或用已有Qwen3单独制作，统一在后期合成。

- 入口：[`SKILL.md`](SKILL.md)
- 审核交付：每个镜号的脚本与对应分镜图同处展示，包含时长、动作、转场和声音；新图、旧候选与待修图标清。图文分镜通过后才生成新视频，既有视频可先重剪供比较。
- 规则：[`references/`](references/)
  - 三种结构：分幕写实、一镜到底、画卷（出画入真）
  - 分镜模板
  - 提示词写法
  - 声音与字幕
  - RunningHub 接入
  - 踩坑清单
- 脚本：[`scripts/`](scripts/)

  | 脚本 | 作用 |
  |---|---|
  | `gpt_web.py` | 在已登录的 ChatGPT 网页一张张生成关键帧（经 browser-skill） |
  | `gemini_wash.py` | 在 Gemini 网页把关键帧洗成高清（约 2752×1536） |
  | `rh_run.py` | 调 RunningHub 上的 MiniMax H3 工作流生成视频（任务编号落盘，可 `--fetch` 取回） |
  | `keyframe.py` | 备选：用 Codex CLI 生成关键帧 |
  | `scroll.py` | 画卷外扩与拼接 |
  | `doctor.py` | 环境自检：缺什么、怎么补 |
  | `contact.py` | 把视频抽帧拼成总览，用来检查 |
  | `vo.py` | 可选：用已有Qwen3-TTS单独配旁白，并用ASR辅助核对；没有模型时索要用户录音 |
  | `audio_policy.py` | 限定视频仅生成环境音效，核听后保留源音轨，支持用户旁白文件导入 |
  | `voicestat.py` | 测每句旁白的音高，检查音色是否一致 |
  | `score.py` | 按剪辑点合成配乐 |
  | `cut.py` | 读一份 JSON 配置，直接出粗剪 |

- 示例：[`examples/nodes-tea-furniture/`](examples/nodes-tea-furniture/)

## 需要的环境
- macOS，Python 3.9+（`pip install -r requirements.txt`：numpy、scipy、Pillow），ffmpeg，ImageMagick 7。
- Chrome + **browser-skill**（`bsk` 命令行和扩展，扩展要开「允许访问文件网址」），并在 Chrome 里登录 ChatGPT 和 Gemini。
- RunningHub 会员 API key，写在环境变量 `RUNNINGHUB_API_KEY` 里。视频走工作流接口，扣 RH 币。
- 旁白可以直接使用用户提供的WAV/MP3/M4A/FLAC和对应文稿，不依赖本地语音模型。Qwen3-TTS/ASR是已有环境下的可选路径，用`QWEN3_TTS_DIR`指定。
- 可选：[Codex CLI](https://github.com/openai/codex)（备选生图）；配套技能 hd-image-workflow、human-first-article。

详细的安装、自检和排错见 [`references/setup.md`](references/setup.md)。第一次使用时，技能会先帮你逐项自检，缺什么会告诉你怎么补。

## 安装
- Claude Code：把整个目录放到 `~/.claude/skills/product-film/`。
- Codex：放到 `~/.codex/skills/product-film/`，或者 `ln -s ~/.claude/skills/product-film ~/.codex/skills/product-film`。

## 示例效果
以下是示例项目「节序 Nodes in Order」茶家具系列视频的制作过程。

**第一幕用的长卷**：以仇英《竹院品古》为中段，向左右两侧外扩，拼成 9600×1350。
![scroll](docs/showcase/scroll.jpg)

**第一幕粗剪抽帧**：引首题字，长卷一路向左展开，最后停在空亭。
![act 1](docs/showcase/act1-frames.jpg)

**第二幕关键帧**：人物定妆，以及在作者设计的茶台、客位椅上进行的茶事。
![keyframes](docs/showcase/keyframes.jpg)

## 版权说明
- **家具设计**：示例中的茶台、主位椅、客位椅等家具及其渲染图，均为作者 **yumi233 原创设计**，版权归作者所有。未经许可，不得使用、复制或用于商业用途。`docs/showcase/` 中的图片均已标注。
- **古画**：仇英《竹院品古》属于公有领域。长卷的外扩部分和画中动态由 AI 生成，仅作示例。
- **人物**：示例中的人物均为 AI 生成，不对应真实的人。
- **代码与文档**（`scripts/`、`references/`、`SKILL.md`）可以自由使用。
