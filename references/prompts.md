# 提示词写法

全部用英文写。每条都由四部分组成：**参考图各自的角色 + 镜头运动 + 画面里动什么 + 要保住什么、排除什么**。

## H3 视频（rh_run.py）

### 参考图的角色
- 只给一张图：H3 基本把它当首帧，画面会很接近原图。适合「让这张图动起来」。
- 给两张图：在提示词里写明 `Image 1 is the exact FIRST frame and image 2 is the exact LAST frame`。结尾会靠近第二张，但不一定完全一样，剪辑时由 cut.py 自动找帧对齐。
- 产品镜头：放一张爆炸图，再放渲染图和细节图，写 `keep the design exactly as the references`。
- 最多 4 张。不够 4 张时脚本会重复填满，所以重要的图放在第 1 张。

### 例句

**画卷平移**（首尾帧都从长卷上裁出来）
```
This is an ancient Chinese handscroll painting (Ming blue-green gongbi on aged silk). Image 1 is the exact FIRST
frame and image 2 is the exact LAST frame. The camera glides smoothly to the LEFT along the flat painted scroll at a
steady constant speed, travelling from image 1 to image 2, like a viewer unrolling a handscroll. The painting stays a
flat painted silk surface with the same brushwork, colours and silk texture; only gentle painted-world life moves
inside it. <这一段的动态：小童扇炉，白汽向左飘向屏风…> No text, no new objects, no 3D camera rotation, no zoom, no style change.
```

**爆炸图组装**（先完整展示）
```
Studio shot on seamless white. Start on the COMPLETE exploded view exactly as reference image 1, all parts floating
apart, hold it for 1.5 seconds. Then the parts fly together and click into the assembled <product> exactly as
reference image 2, with a soft light sweep. Finally push in slowly on <joint/detail> as reference image 3.
Keep the design exactly as the references: <腿数、节点、材质要点>. Only one pair of armrests. No extra parts.
```

**一镜到底接续**（参考图 1 是上一条的尾帧）
```
Continue seamlessly from reference image 1 as the exact first frame, same camera direction and speed (<方向>).
<这一段的内容>. End when <遮挡物> fills the frame.
```

**人物戏**（参考图 1 是关键帧）
```
Animate reference image 1. <人物的动作，一两个就够>. Subtle natural motion, faces stay consistent, the <product>
keeps its exact design. Slow <推/环绕> camera.
```

**提高动感**：写清楚镜头运动，比如 `dolly forward`、`orbit`、`crane up`、`pan left`；加上前景遮挡（`foreground leaves sweep past the lens`）；画面里要有具体的动作（倒、举、落、扇）。光写 `slow camera movement` 只会让画面「动一下下」。

## Codex 关键帧（keyframe.py）

### 定妆图
```
Character reference sheet on a plain warm light-grey studio background, 16:9, four views in a row: (1) HOST front,
(2) HOST profile, (3) GUEST front, (4) GUEST profile. HOST: <年龄、发型、衣着、材质与颜色>. GUEST: <…>.
Natural relaxed postures, consistent lighting, documentary realism.
```

### 产品使用场景
- 参考图依次放：定妆图（裁出单个人）、产品渲染图、场景图。
- 在提示词里逐件描述产品的结构要点，并点名排除常见的错误替代：
```
The GUEST sits in OUR guest armchair exactly as in the chair reference: a slim brushed stainless-steel tube frame
with cylindrical collar joints, walnut armrests, a walnut-brown leather sling back, a cream woven webbing seat.
NOT a rattan or cane chair, no woven wicker.
```
- 道具也要和产品配套：
```
white plain porcelain gaiwan, brushed stainless-steel gooseneck kettle. No clay teapot, no cast-iron kettle.
```

### 画卷外扩（`--painting`）
```
OUTPAINT: the LEFT quarter of this image is an existing painted strip of a handscroll (<条里有什么>). The flat beige
area to its right is EMPTY and must be painted so the scene continues seamlessly to the right from that strip.
Content of the new area: <新的景>. Keep the left strip unchanged.
Style must match the reference exactly: Ming dynasty blue-green gongbi painting on aged silk in the manner of
Qiu Ying, fine even ink outlines, mineral azurite blue and malachite green, warm yellowed silk ground with the same
silk texture. One continuous horizontal handscroll; horizon line, ground level and scale of figures must match.
```

### 界画产品（画卷里的家具）
```
Paint <product> into the scene in jiehua (ruled-line architectural painting) technique matching the scroll: fine
even ink outlines, flat mineral colours, same silk ground. The object's structure must follow reference image 2
exactly (<结构要点>); only the rendering style changes.
```

## 通用的排除词
`no text, no watermark, no logos, no extra legs, no melting metal, no style change`。按镜头补充具体会出错的东西，比如 `rattan`、`brush instead of whisk`、`second armrest`。
