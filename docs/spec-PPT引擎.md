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
