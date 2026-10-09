# spec：HFR Slides Engine（自研 PPT 实时渲染引擎）

> 本文是 **技术规格草案**，对应 `ADR-006` 的路线 C。目标：OBS 内**帧级实时**渲染 pptx，含动画与切换。

## 1. 总体结构
```
pptx(zip)
  └─ OOXML 解析层  →  文档模型(Deck)  →  场景图(SceneGraph)  →  渲染器(GPU)  →  OBS 纹理
                                          ↑
                                  时间轴(Timeline) ── OBS 帧时钟
```
- **解析层**：只做"读懂"，不做布局；输出结构化文档模型（不丢原始单位：EMU 全程保留）
- **布局层**：继承链 `slideMaster → slideLayout → slide`；主题配色/字体方案；文本框 autofit/normAutofit/spAutoFit
- **场景图**：节点 = 形状/文本/图片/表格/组/占位符；属性含 transform(EMU→px)、填充、描边、效果
- **渲染器**：批量提交到 OBS `gs_*`（纹理批 + 顶点缓冲），文本用字形图集；支持 2× 超采样
- **时间轴**：`p:timing` 的 SMIL 子集编译为关键帧序列，`t → 属性` 求值

## 2. 数据模型要点
| 概念 | 关键点 |
|---|---|
| 单位 | EMU(914400/inch) 全程保留，渲染前统一换算；避免累计误差 |
| 文本 | run 级属性（粗斜下划线、字号、字体、颜色、间距）；段落级（对齐、行距、项目符号、缩进） |
| 继承 | 母版/版式占位符按 `idx`/`type` 匹配；主题 `clrMap` 决定 accent/dk/lt 的实际取色 |
| 图片 | 关系链 `slide → rels → media`；支持裁剪(srcRect)、拉伸填充、旋转、透明度 |
| 表格 | 行高/列宽（含 span）、单元格填充/边框/边距、竖排文本 |
| 效果 | 阴影、发光、柔化、渐变填充（线性/径向）、圆角；3D/艺术字 → 兜底烘焙 |

## 3. 动画（`p:timing`）子集（M2 目标）
- 节点：`<p:par>`/`<p:seq>`/`<p:anim>`/`<p:set>`/`<p:animEffect>`/`<p:animMotion>`/`<p:cmd>`
- 行为：进入 / 退出 / 强调 / 路径运动；`dur`、`delay`、`repeatCount`、`autoRev`、`fill`
- 触发：点击（advClick）、上项后（afterEffect/afterGroup）、与上项同时（withEffect/withGroup）
- 切换：`p:transition`（淡入/推进/擦除/分割/形状/覆盖…），时长与"推进方式(click/after time)"
- 引擎接口：`Play(fragmentIdx)`、`Next()`、`Prev()`、`Seek(t)`、`Pause()`、`SetRate(x)`，**每画布一份时间轴实例**

## 4. 与 OBS 的集成
- 新增来源 `hfr_slides_source`（替代/并存 `hfr_ppt_source`）：每实例持有 Deck + Timeline
- 渲染走 `video_render`（图形线程）：只做纹理批提交；**解析/布局在 UI 线程或工作线程完成**，绝不占用图形线程（已有 ADR-005 与 LOK 崩溃教训）
- 多画布：同 deck 可被多个画布实例引用，各自独立播放状态 → "同一 PPT 不同屏播不同页"
- 录制/推流：作为普通源进入管线，无需额外处理

## 5. 兼容与兜底
- **节点级兜底**：解析或渲染失败 → 该节点标记为 `BakedImage`（导入时 soffice→PDF/pdfium 渲染该页并裁切对应区域）
- **整页兜底模式**：用户可切换"整页 PDF 模式"（当前实现），牺牲动画换取 100% 有画面
- **缺字体报告**：列出文档引用的字体族 → 与系统/随包字体比对 → 输出替换建议

## 6. M0 尖刺验收标准（下一步就做这个）
1. 解析一个真实 pptx（含中文、图片、表格各 1 个）
2. 在 OBS 内把自己的来源渲染到画布，1080p60 下 CPU/GPU 余量 ≥ 40%
3. 中文换行与 PowerPoint 对照，行数与断点一致率 ≥ 95%
4. 全流程无崩溃、退出干净（沿用 ADR-005 拆除顺序）
## 7. M0 进展记录（2026-09-25）
- ✅ **解析层可用**：自写 zip（zlib）+ 迷你 XML → 文档模型；独立验证程序 `scripts/build-deck-dump.cmd` 产出 `hfr_deck_dump.exe`
- 在 `tools/test/rich-deck.pptx`（python-pptx 生成：标题/多级项目符号/色块/PNG 图片/3×3 表格/圆角矩形+旋转/居中文本）上验证：
  - 页面尺寸、主题配色(12 项)、主字体解析正确
  - 形状位置尺寸（EMU）、纯色填充、图片字节（PNG 609B）、表格类型均正确识别
  - 文本框/占位符文本与多级段落、run 级字号解析正确
- 已修复的坑（值得记住）：
  1. **同一元素存在两个同本地名属性**（`<p:sldId id="256" r:id="rId2"/>`）→ 属性查找必须**优先 r: 引用**，否则取到数字 id
  2. 源码含中文必须加 `/utf-8`，否则按代码页 936 误读导致语法错
  3. 独立验证程序要静态链接 `zlibstatic.lib`（否则缺 zlib.dll，0xC0000135）
- 待办（进入 M1 前）：
  - 占位符/版式 **transform 继承**（当前占位符 pos/size 为 0）
  - **渐变填充**(`gradFill`)、图片裁剪、线宽/虚线、阴影
  - 渲染层：OBS 图形栈提交（形状用顶点/纹理，文本用 GDI/DirectWrite 光栅化到纹理）
## 8. M1 进展：文本样式继承 + 视觉对比工具链（2026-09-25）
### 已实现
- **母版 `p:txStyles` 解析**（titleStyle/bodyStyle/otherStyle × 9 级）：字号、粗斜体、颜色、项目符号字符(`buChar`)、左缩进(`marL`)、行距(`lnSpc/spcPct`)
- **版式/母版占位符几何继承**：按 `type|idx` → `type|*` → `idx:N` → `|idx` → `body|idx` 候选链**择优**（优先"带几何"的候选，避免空条目挡住回退）；按字段合并（后者有值才覆盖）
- **渲染层**：字号用"幻灯片高度→磅"换算（修掉原先用 EMU 比例导致文字极小的 bug）；项目符号/缩进按文档值绘制
- **对比工具链**（关键基础设施）：
  - `hfr_deck_dump.exe <pptx> --bmp out.bmp --slide N` → 我们的引擎渲染为 BMP
  - `hfr_deck_dump.exe x --pdfref out.pdf --pdfium <pdfiumlo.dll> --bmp ref.bmp --slide N` → **LibreOffice 官方渲染**作为参考
  - 同一工具、同一分辨率下逐页对比，保真回归可自动化
### 本页对比结论（rich-deck 第 1 页）
| 项目 | 修复前 | 修复后 |
|---|---|---|
| 标题字号 | 18pt（默认） | ✅ 44pt（母版 titleStyle） |
| 项目符号 | 无 | ✅ 按级别 `•` / `–` |
| 缩进 | 粗略估算 | ✅ 用文档 `marL` |
| 文本方向/大小 | 文字极小、BMP 上下颠倒 | ✅ 修正 |
### 待办
- 标题左内边距(`lIns`)与 LO 有细微差异；项目符号与正文间距需微调
- 表格单元格渲染、图片实际绘制（OBS 路径）、渐变真渲染
- OBS 来源接入（`hfr_slides_source`）与实时动画时间轴
