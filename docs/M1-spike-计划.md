# M1 Spike 计划：核实上游 obs_canvas 渲染/绑定/音频现状

> 前置：M0 完成（32.2.2 在本机编译通过）。目标：用两周内的最小实验回答影响 M2~M4 设计的问题，
> 每项实验给出结论并写入本文档（或 ADR）。执行者可边做边改本文档。

## 目标问题（Q 列表）
- Q1 多画布渲染：额外创建的画布如何进入每帧渲染？上游谁调用 obs_canvas_render / obs_render_canvas_texture？
  我们应把"画布调度器"挂在哪个环节（obs-video 主循环 vs obs.c 输出纹理阶段）？
- Q2 显示：能否把某画布渲染结果输出到一个 Qt 窗口/全屏（对应克隆屏）？现有 OBSDisplay/预览机制如何复用？
- Q3 编码绑定：encoder/output 能否直接绑定某画布 video_t（obs_canvas_get_video）？现有推流/录制与 program
  纹理的耦合点在哪（需要改哪些函数）？
- Q4 场景作用域：obs_canvas_scene_create/频道(channel)与切换：每画布独立切场景是否已可用？
- Q5 来源跨画布：同一 obs_source 能否同时进两个画布的活跃场景？ACTIVATE/SCENE_REF/EPHEMERAL 的运行时行为；
  若不能 → 需要"扇出/复制"策略的确切接缝。
- Q6 音频：MIX_AUDIO 的实际行为（多画布音频如何混入输出）；"按 Sink 选混音"应落在哪一层。
- Q7 分辨率/降帧：canvas reset_video 的 base 分辨率自由、fps=全局 的实测含义；"活跃度档"跳过渲染是否安全
  （纹理内容保持最后一帧？）。
- Q8 持久化：obs_save_canvas/load_canvas 与 profile 的整合路径（前端 OBSCanvas Save/Load 已存在，缺 UI 与多画布布局）。

## 阅读清单（obs-src @ 32.2.2）
- libobs/obs-canvas.c（462 行）— 画布对象实现
- libobs/obs.c 2160~2260 — 主画布纹理渲染（obs_render_canvas_texture_internal 等）
- libobs/obs-video.c — 主渲染循环与输出纹理帧推进（找 canvas 应插入的钩子）
- libobs/obs.h 2604~2694 — canvas API 声明
- libobs/obs-internal.h — obs->data.main_canvas、画布列表等内部结构
- frontend/utility/OBSCanvas.cpp/hpp、frontend/widgets/OBSBasic_Canvases.cpp — 前端存取壳
- frontend/OBSBasic.cpp — 现 UI 如何用 program 纹理/预览（OBSDisplay、预监切换）
- docs/sphinx/reference-canvases.rst — 官方 API 文档（302 行）
- plugins/obs-outputs、libobs/obs-output.c — encoder/output 与 video 绑定点

## 实验清单（每项：做法 → 通过标准 → 结论）
E1 第二画布最小演示：启动后额外创建 PROGRAM 画布（720p），每帧 obs_canvas_render 到纹理，
   用一个 Qt 子窗口显示 —— 验证渲染入口与纹理获取。
E2 独立场景切换：两画布各自场景集，分别切换当前场景互不影响 —— 验证 Q4。
E3 双画布引用同一摄像头源：观察是否双路激活/重复采集/异常 —— 验证 Q5（决定扇出设计）。
E4 画布视频接编码器：把 E1 画布 video_t 接入一个输出（FFmpeg mux / RTMP 测试服务器）—— 验证 Q3 接缝。
E5 音频行为：给两画布不同源，开/关 MIX_AUDIO 观察总输出混音 —— 验证 Q6。
E6 帧率/降帧：改 base 分辨率；人为跳过渲染帧，观察输出是否保持最后一帧 —— 验证 Q7。
E7 保存/加载：建画布→保存 profile→重启→还原（名称/场景/尺寸） —— 验证 Q8 与前端缺口。

## 产出
- 本文档内填完 Q1~Q8 结论 + E1~E7 结果与截图说明；
- 形成"hfr-canvas-scheduler / hfr-sink 模块设计（v0）"页（M2 输入）；
- 若发现上游 blocking bug → 记录最小复现，评估修复 vs 规避。

## 已知风险
- canvas API unstable：实验代码只做验证用途，不沉淀进主分支设计依赖。
- 本机 Vega8：E1/E3 性能只做定性，不做基准。
