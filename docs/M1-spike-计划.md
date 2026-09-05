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

## 附：M0 阶段初步代码勘察（build 期间，非结论性，供 spike 参照）
- **帧循环已是多 mix 结构**：obs->video.mixes 为 obs_core_video_mix 数组；
  obs_graphics_thread_loop 每帧 = update_active_states → tick_sources → output_frames()（按 mix 出帧）→ render_displays()。
  → hfr-canvas-scheduler 的挂载点候选：output_frames 阶段或其后、render_displays 前的"画布渲染"通道（待 E1 验证）。
- **canvas ≈ mix + view + 场景集**：obs-canvas.c 内 canvas 持 mix（video 输出）与 view（channels，供 obs_canvas_set_channel/渲染取用）；
  obs_canvas_get_video() = mix->video；obs_canvas_reset_video() 仅当 !obs_video_active() 且非 MAIN 时可调。
- **obs_canvas_render(canvas)** 已实现（obs-canvas.c:589），obs.c 已有主画布纹理渲染内部函数（obs_render_canvas_texture_internal ~2170）——
  说明"画布→纹理"的原语已具备；缺的是"谁在每帧调度 N 个画布渲染 + 分档跳过"（我们新增）。
- obs-video.c 关键函数行号：output_frames(916)、render_video(539)、update_active_states(1076/1054)、obs_graphics_thread_loop(1097)。

## E1 补丁设计（定稿，待实施）
目标：菜单"工具 → HFR-E1 第二画布窗口"→ 弹出独立小窗显示"额外画布"的实时画面（内容先镜像主节目=克隆语义演示）。
依据（源码核实）：
- obs_canvas_create(name, ovi, PROGRAM) 运行期可调用；内部 obs_create_video_mix(ovi) 并把 mix 压入 obs->video.mixes、
  mix->view = &canvas->view（obs-canvas.c:138-171）。output_frames() 每帧遍历 mixes → 画布自动渲染进自身 mix->render_texture（obs-video.c:916）。
- obs_render_canvas_texture(canvas) 公开可把任意画布 mix->render_texture 画到当前 gs target（obs.c:2234；guard texture_rendered）。
- flags：enum obs_canvas_flags { MAIN, ACTIVATE, MIX_AUDIO, SCENE_REF, EPHEMERAL, PROGRAM=ACTIVATE|MIX_AUDIO|SCENE_REF, ... }（obs.h:2604）。
- 通道：obs_canvas_set_channel(canvas, 0, sceneSource)；克隆演示 = channel0 放当前主场景源。
- 窗口：仿 OBSProjector —— OBSQTDisplay 子类 + obs_display_add_draw_callback(display, OBSRender, this)；
  OBSRender 内 obs_render_canvas_texture(canvas)；Esc 关闭即 obs_canvas_remove+release（沿用 OBSCanvas RAII 语义）。
实施文件（拟）：
- 新增 frontend/widgets/HFRSpike.{hpp,cpp}（临时 spike 类，M1 结束可删）
- frontend/CMakeLists.txt 登记源文件；OBSBasic.cpp 菜单"工具"加 action
- 增量编译验证；若渲染无内容 → 查 texture_rendered/ACTIVATE 时机
验收：窗口显示与主节目一致画面（克隆1）；帧率流畅；关闭窗口无崩溃（mix 正常释放）。

## E1/E2 补丁合入状态（v2，等待人工运行验收）
- 补丁文件：frontend/widgets/HFRSpike.{hpp,cpp}；菜单 HFR(M1) 登记于 OBSBasic::OBSInit；
  env HFR_E1_AUTO=1 → 4s 后自动开 E1。
- E1（克隆）：obs_canvas_create("HFR-E1",960x540, ACTIVATE|SCENE_REF) + 通道0=当前主场景源 + 独立窗口绘制画布纹理。
- E2（独立）：同尺寸画布 + obs_canvas_scene_create("E2 Scene") + color_source_v3 色块 + OBS_BOUNDS_STRETCH 铺满。
- 日志探针一律用 blog(LOG_INFO,"[HFR-...]")（进 obs 日志），不再用 fopen 外部文件。
- 待人工验收项见 docs/晨间验收清单.md。

## 调试教训（重要，写进 ADR 思路）
1) **自动化启动曾致"伪崩溃"**：后台 Start-Process + 强杀会留下崩溃对话框/脏配置；
   用户手动双击启动正常。→ 运行期验证以"人工启动 + obs 日志"为准；自动化只做构建与静态检查。
2) **增量构建可被污染**：多次 reconfigure/编改后出现"连原始代码都早崩"；
   --clean-first（或删 build_x64 全量）可恢复。→ 涉及源码列表/头文件的改动后若异常，先 clean。
3) **obs 运行期 canvas 创建的真实性待人工确认**：源码显示 obs_canvas_create 会向 obs->video.mixes
   推入新 mix（output_frames 每帧遍历渲染），API 层面成立；是否所有时机安全由 E1/E2 运行结果判定。
