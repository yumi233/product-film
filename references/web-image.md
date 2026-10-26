# ChatGPT / Gemini 网页出图指南

为什么用网页：同样的图，ChatGPT 网页约 1 分钟一张；Codex CLI 每张要先起一个助手、读参考图，实测 40 分钟一张都没出。用户也明确要网页。

## 一、ChatGPT 网页出关键帧：`scripts/gpt_web.py`

### 任务文件
```json
{"style": "（可选）每条提示词后面都加上的风格段",
 "jobs": [
  {"id": "1C", "out": "keyframes/v8/1C.png",
   "refs": ["refs/render_table.jpg", "keyframes/v8/T1.png"],
   "prompt": "Image 1 is ..., image 2 is ...",
   "style": ""}
 ]}
```
- 参考图按顺序上传，提示词里称为 image 1、image 2……，要逐一说明每张图的作用。
- 某条不要通用风格时，把它的 `style` 设成空字符串。
- 风格段放进 `剪辑脚本/风格_*.txt`，脚本里读进来，全片统一。

### 运行
```bash
python3 -u scripts/gpt_web.py jobs.json 1C 2A 3B > keyframes/v8/生成.log 2>&1   # 后台跑
```
- 一次一个对话、按顺序跑；已有输出自动跳过；失败自动重试一次。
- 输出约 1672×941，确认后再拿去 Gemini 洗高清。

### 它在页面上做什么（排错时对照）
1. 新开一个 Agent 窗口，打开 chatgpt.com（load 事件常超时，不影响）。
2. 点附件按钮 →「添加照片和文件 / Add photos & files」→ 上传参考图（先压到 1600px）。
3. 等「待处理」消失，用 `document.execCommand("insertText")` 把提示词写进输入框。`bsk fill` 在 ChatGPT 的编辑器里会丢焦点，不能用。
4. 按 Enter；上传刚完成时 Enter 会被吞，脚本会改点「发送」按钮。
5. 每 10 秒查一次：有 alt 为「已生成图像 / Generated image」的大图且停止按钮消失，就把图片 blob 转成 base64 存下来。

### 常见报错
| 现象 | 原因 | 处理 |
|---|---|---|
| `Not allowed`（上传时） | 扩展没开「允许访问文件网址」 | 请用户打开，见 setup.md |
| `attach menu not found` | 页面还没加载完，或多个窗口抢焦点 | 只跑一个；脚本会重试 |
| 图片单独发出去了，提示词没跟上 | Enter 在上传过程中触发 | 脚本已等上传完成；还发生就重跑这一条 |
| ChatGPT 回复文字、问要怎么处理 | 提示词开头没说「Generate ONE image now」 | 脚本自动加了；自己写的提示词别删 |
| `daemon IPC timed out` | 用户电脑太卡（通常是本机 TTS/ASR 在跑） | 等本机任务结束再跑 |

## 二、Gemini 网页洗高清：`scripts/gemini_wash.py`

```bash
python3 -u scripts/gemini_wash.py keyframes/v8/洗图 \
  "keyframes/v8/1C.png::refs/render_table.jpg" \
  "keyframes/v8/2C.png::refs/render_host.jpg,refs/render_guest.jpg"
```
- 每张：新对话 → 上传「待洗的图 + 产品渲染图」→ 切到「制作图片」→ 发用户惯用的提示词：
  「参考家具单体细节，重新渲染第一张图，提升结构和材质的清晰度……构图、机位……都与第一张完全一致」。
- 结果约 2752×1536。下载会落到 `~/Downloads/Gemini_Generated_Image_*.jpeg`，脚本自动挪到输出目录。
- 页面上看到的图只有 1024 宽的预览，必须点「下载完整尺寸的图片」。
- 洗完必须和原图对比：结构、构图有没有变。变了就不要这张。
- 超时（等「停止回答」超过 10 分钟）就重跑那一张。

## 三、规矩
- 网页上用的是用户自己的账号：不改设置、不删对话、不代输密码。
- 一次只开一个窗口；本机有 TTS/ASR 在跑时先等它跑完。
- 每批跑完 `bsk session list` 看有没有残留会话，有就 `bsk session stop`。
