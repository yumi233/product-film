# 提示词写法

全部用英文写。每条都由四部分组成：**参考图各自的角色 + 镜头运动 + 画面里动什么 + 要保住什么、排除什么**。

## H3 视频（rh_run.py）

**声音规则适用于下方所有视频模板**：只生成与画面同步的环境声和非语言音效，不生成旁白、对白、唱歌或配乐。人物可以做事但不开口；不把旁白台词填入视频提示词。`rh_run.py`会自动追加以下要求，其他入口需明确加入：
```text
Generate only natural non-verbal location ambience and synchronized sound effects. No narration, no voice-over, no spoken dialogue, no intelligible speech, no singing and no music. People remain silent. Narration and music will be added separately in post-production.
```

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

### 单张起始帧 + 自由运镜（现在的默认写法，10–15 秒）
```
Image 1 is the FIRST frame. <其余参考图各自是什么：产品渲染图、人物定妆>. <画风或去油风格段>.
Over 15 seconds: <镜头运动，具体到方向和节奏：slow dolly in / orbit 30° to the left / crane up>, <画面里依次发生的 2–3 件事>.
Keep <产品> exactly as the render: <结构要点>. No cuts, no new people, no text.
```
- 不写「image 2 is the exact LAST frame」；结尾交给剪辑。
- 15 秒里安排「先远后近」或「先动作后细节」，方便剪成两个镜头。
- 出画镜头写：the silk texture and ink lines fade away from the <product> like a thin sheet of paper, revealing real walnut and brushed steel; the painted surroundings dissolve into a warm grey-beige space.

## 关键帧（ChatGPT 网页 gpt_web.py；备选 Codex keyframe.py）

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


---

## 写实画面「去油」（用户定稿的写法）

用户眼里「油」的东西：深蓝天 + 完美白云、饱和的绿、黄昏橙金、太阳和反光点、HDR 感、过度锐化、图库照片式的标准构图。
用户眼里「灰」的东西：雾蒙蒙的黄昏、整体发闷。
改法不是加「not oily」，而是**换成真实胶片摄影的语言**：具体时间和光、具体胶片、具体颜色、不完美的构图。用户不满意时，一次给 4–5 种思路并排挑（Portra 过曝、明亮阴天、Fuji 淡彩、午后侧光、逆光柳叶），不要只改一个形容词。

### 白天 L6（默认，用户选定）
```
LOOK (apply to the whole image): around 3 pm, soft sunlight from the side through thin high haze; the sky and the far lake are pale and bright, NOT blue-saturated; warm-neutral colours, foliage a muted yellow-green, wood a natural mid-brown (not orange), steel neutral grey, linen true off-white; gentle shadows, modest contrast, open shadows; Kodak Gold 200 colour negative, 35mm, natural fine grain. It must look like a real documentary photograph from a film roll: NOT a stock photo, NOT glossy, NOT saturated orange, no golden-hour glow, no sun glints, no lens flare, no HDR, no sharpening halos.
```

### 夜景
```
Night, lit only by the warm paper pendant lamp and a little cool blue dusk from outside; quiet, low contrast, deep but open shadows (no crushed
blacks), warm light not orange-saturated, Kodak Portra 800 35mm grain; a real documentary photograph, not a rendering, no glow halos, no lens flare.
```

### 雨天
```
Overcast rainy afternoon: soft even grey-white light, wet dark stone, fine rain visible against dark eaves, water dripping from the roof edge;
colours quiet and natural; Fuji colour negative 35mm grain, low contrast; a real documentary photograph, not glossy, no HDR.
```

## 画中（工笔）
```
Ming dynasty blue-green gongbi painting on old silk, the SAME painting style and silk as the reference painting: fine even ink outlines, flat faded
colour washes, no photographic texture, no CG shading, faint craquelure. Furniture is PAINTED in the same technique (ruled jiehua lines,
ochre-brown walnut wash, pale silver-grey steel with thin white highlight lines). No text, no seals.
```
- 画中产品：参考图 = 画中场景 + 渲染图，整张生成。写清「same horizon, legs on the floor, inside the railing」，否则椅子会飘到亭子外面。
- 「破碎感」= 老绢的裂纹、水渍、颜料剥落、断续的细线；不是画面支离破碎。

## 空间与摆放（每条含家具的提示词都加）
```
Correct perspective: one horizon and one set of vanishing points for everything; every leg on the floor with soft contact shadows; believable real
scale (table top 0.75 m, seat 0.45 m, people ~1.7 m); furniture placed where people would really put it.
```
再写清：每件在哪、朝哪、机位高度。**有产品方的平面布置图时照它写**，例（茶席）：
```
PLACEMENT (follow strictly): the host chair sits at the FAR long side of the tea table, centred behind the inset tea tray, facing the table
and pulled in under the table edge; it never stands next to or against the slab pedestal. Guest chairs at the two short ends facing inward,
the twin seat on the near long side. Knees go under the tabletop without touching any leg.
```
产品带有容易被画丢的部件时，逐项写成清单（例：`The inset stainless tray MUST stay complete: sink at the left, slatted draining grid in the
middle, induction kettle well with the electric kettle at the right.`），出图后按清单逐件对照。

## 主题白棚（产品展示、线描人）
背景元素从项目主题取，不用通用的丝带、纱帘（用户说「不符合主题」）。竹院主题例：
```
SET: pure white seamless studio, bright soft high-key daylight, crisp bamboo stalk and leaf shadows on the white backdrop and floor, two or three
slender green bamboo stalks at the frame edges, a few bamboo leaves drifting. 16:9 landscape. The bamboo never covers the product structure.
```
同一部片子里的白棚统一一种，旧的灰棚白底镜头要么重做、要么只用在不相邻的位置。

## 线描人（白棚里演示怎么用）
```
The people are NOT real: thin continuous WHITE line drawings (outline only, transparent bodies), sitting naturally on the real furniture with
correct scale. CRUCIAL: every line figure sits INSIDE its chair: hips on the seat, back against the backrest, forearms on or just above the
armrests, feet on the floor. The figures overlap the chairs exactly; never float beside or between chairs.
```
视频提示词里再加：`The people remain thin white line drawings for the whole shot; they never become real people and never leave their seats.`

## 实景真人（固定卡司）
全片用同一组人，服装写死，每条含人的提示词都带上：
```
CAST (same people across the film): a calm Chinese man in his 40s in an off-white linen stand-collar shirt (host); a woman in her 30s in a pale
grey-green linen dress, hair in a low bun (guest); a younger man in a charcoal linen shirt. Natural documentary moment, nobody looks at the camera,
no talking, correct scale.
```
在已经对照通过的场景图上用「局部修改」加人，不重画全图；加人后仍要逐件复查（常带出外来椅子、吃掉小部件）。要「只有一个人」时写 `Add ONLY ONE person ... exactly one chair; do NOT add any other chairs, guests or furniture.`

## 稳定运镜（视频提示词结尾）
```
Camera on a stabilised dolly: perfectly smooth, constant slow speed, no shake, no jitter, no sudden moves; subject motion slow and continuous.
All furniture stays perfectly rigid and unchanged: same structure, parts, proportions, materials and colours as the first frame; nothing added
or removed, no morphing.
```

## 爆炸图（暖灰棚拍，和出画画面同色）
```
Image 1 is the exploded view of OUR <product>. Re-shoot it exactly as image 1 (same parts, separation and angle, every screw and dashed guide line)
in the warm grey-beige studio of image 2. Clean warm grey-beige seamless studio (the colour of faded silk), soft even light, soft contact shadows;
photorealistic product photograph, restrained, no glossy CG look.
```

## 在用户场景图上加人
```
Image 1 is a real <space> with OUR furniture. Keep ALL furniture exactly as in image 1 (pieces, positions, every structural detail). Add <people>:
<谁坐在哪把椅子上、在做什么>. They sit properly: hips on the seat, backs near the backrest, feet on the floor, forearms at table height.
Same camera and framing as image 1.
```
加人后检查：人坐的是不是那把椅子（主人常被放到客位椅上）、有没有悬空坐、动作合不合理（注水要揭盖）、被提起的水壶下面那块电磁炉还在不在。

## 局部修改（结构错了、道具错了）
```
Edit image 1. Change ONLY these things, keep everything else exactly the same: (1) ... (2) ...
```
一次改 1–3 处，逐条写清楚，并附该部件的渲染图。

## 统一调色（已有的图换风格）
```
Re-grade image 1 so its light and colour match the photograph style of image 2. <风格段> Change only light and colour; keep people, furniture,
objects, architecture and framing exactly.
```
