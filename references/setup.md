# 安装、Codex 用法、环境自检

## 安装本技能

**Claude Code**
```bash
git clone https://github.com/yumi233/product-film ~/.claude/skills/product-film
```

**Codex**（技能格式相同，SKILL.md 直接可用）
```bash
ln -s ~/.claude/skills/product-film ~/.codex/skills/product-film
```
只装 Codex 时，直接 clone 到 `~/.codex/skills/product-film`。

Codex 里的注意事项：
- 脚本都是普通命令行，Codex 一样调用；关键帧用 `scripts/gpt_web.py`（需要 browser-skill，Codex 也能装）。
- Codex 自己能生图：没有浏览器控制时，退回 `scripts/keyframe.py`（它调用 `codex exec`，提示词从 stdin 传入）。在 Codex 会话里也可以直接用自带的生图工具，按 `references/prompts.md` 写提示词，产物放进 `keyframes/`。
- 后台任务：Codex 没有「后台完成通知」时，长任务（RunningHub 视频约 8–10 分钟）改成前台等待，或让用户稍后说「继续」，再用 `rh_tasks.log` + `--fetch` 取结果。

## 一键自检
```bash
python3 ~/.claude/skills/product-film/scripts/doctor.py
```
逐项给出 OK / MISSING / WARN 和补救办法。MISSING 是必需项，WARN 是可选项。

## 声音分工

环境音效优先由视频模型生成，只允许风、水、雨、杯盏、脚步等非语言声音。原音轨核听确认无旁白、对白和唱歌后，才在剪辑配置中设`source_audio: "verified_ambience"`；默认`mute`防止未检查的人声串入成片。旁白与配乐另轨后期合成。

## Python 依赖
```bash
python3 -m venv .venv && .venv/bin/pip install -r ~/.claude/skills/product-film/requirements.txt
```
系统自带的 `/usr/bin/python3` 通常没有 numpy；剪辑和音高检查用这个 venv 的 python 跑：
`.venv/bin/python scripts/cut.py act.json`。

## 其他工具
- `brew install ffmpeg imagemagick`（需要 ImageMagick 7 的 `magick` 命令）。
- 中文字体：标注总览图用 `/System/Library/Fonts/Hiragino Sans GB.ttc`；字幕用宋体（cut.py 自动找）。圆圈数字 ⑪ 以后在部分字体里缺字，编号用阿拉伯数字。

## 浏览器控制（ChatGPT / Gemini 网页出图）
1. 安装 **browser-skill**：`bsk` 命令行 + Chrome 扩展（用户自己安装；技能里没有安装包时，请用户从其发布页获取）。
2. 在 `chrome://extensions` → BrowserSkill → 详情 → 打开 **「允许访问文件网址」**。不开就传不了参考图（报错 `Not allowed`）。
3. 用户自己在 Chrome 登录 chatgpt.com 和 gemini.google.com。**不要代输密码，不要碰账号设置。**
4. 自检：`bsk browsers` 能列出浏览器；`bsk session start --json` 能拿到 session。
5. 用完 `bsk session stop <id>`。

没有 browser-skill 时的退路：Claude in Chrome 扩展也能点网页，但上传和下载要用户批准；或者退回 Codex 生图。

## RunningHub
- 需要**会员 API key**（扣 RH 币）。用户自己写进 `~/.zshrc`：`export RUNNINGHUB_API_KEY=...`。运行时用 `zsh -ic "python3 ..."` 才读得到。
- **不要让用户把 key 贴进聊天，也不要打印 key。**
- 自检：`zsh -ic "python3 scripts/rh_run.py --check"` 返回币数。

## 旁白来源：用户录音，或可选本机Qwen3

没有Qwen3时，先索要最终旁白音频（WAV/MP3/M4A/FLAC）和对应文字，通过`vo.lines[].path`在后期导入，详见`audio.md`。不要要求用户先安装模型，也不把旁白塞进视频生成提示词。

以下仅用于用户已有且选择使用的本机Qwen3环境：
- 文件夹里要有 `.venv/`（装了 mlx-audio）和 `models/`：
  - `Qwen3-TTS-12Hz-0.6B-Base-4bit`（声音克隆，推荐）
  - `Qwen3-TTS-12Hz-0.6B-CustomVoice-4bit`（预设音色）
  - `Qwen3-ASR-0.6B-8bit`（回听核对）
- 用 `QWEN3_TTS_DIR` 指定，或放在 `~/qwen3-tts`、`~/AI/qwen3-tts*`。
- 用户机器上已有常驻 TTS 服务时不要动它，直接调模型。
- **本机模型一次只跑一个**，会占满 CPU / 内存。

## 配套技能（引导用户按需安装）
| 技能 | 什么时候需要 |
|---|---|
| browser-skill | 网页出图、洗图（必需） |
| hd-image-workflow | 需要分块高清重建、PSD 交付时 |
| human-first-article | 写旁白、片头文案，去掉 AI 腔 |
| portfolio-deck-layout | 视频截图要放进作品集 PPT 时 |

用户没装、但这一步需要时：说清楚它是做什么的、装了能省什么事，请用户自己装；不装就用上表的退路，不要卡住。
