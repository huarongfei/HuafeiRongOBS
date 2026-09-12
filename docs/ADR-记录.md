# ADR 记录（Architecture Decision Records）

> 轻量决策记录：每条含 背景/决策/影响。持续追加。

## ADR-001 技术路线：扩展现有 obs_canvas（锁定 obs-studio 32.2.2）
- 背景：上游 32.2.2 已内置 Canvas API（obs_canvas_t：mix+view+场景集，save/load，MAIN 常驻，
  flags=MAIN/ACTIVATE/MIX_AUDIO/SCENE_REF/EPHEMERAL；预设 PROGRAM/PREVIEW/DEVICE），但前端无 GUI 入口、
  渲染调度/输出绑定未接（obs-video 主循环无画布级调度，仅 output_frames 遍历 mixes 自动渲染带 view 的 mix）。
- 决策：不自建多画布内核；fork 32.2.2，在其上补：画布渲染调度/活跃度档（候选挂载点 output_frames 后）、
  Sink 绑定克隆模型、音频出局路由、Console UI、PPT 桥等。
- 影响：随上游 canvas 演进需周期性评估合入；32.2.2 为基线。

## ADR-002 E1/E2 spike 实现方式（M1）
- 背景：验证"运行时第二画布→独立窗口"可行性。
- 决策：OBSQTDisplay 子类窗口 + obs_display_add_draw_callback 内 obs_render_canvas_texture(canvas)；
  画布 flags=ACTIVATE|SCENE_REF（不加 MIX_AUDIO 防音频重复）；base 960x540 独立于主画布。
  E1 克隆：canvas 通道0 = OBSBasic::GetCurrentSceneSource()；
  E2 独立：obs_canvas_scene_create + color_source_v3(1920x1080 亮青) + OBS_BOUNDS_STRETCH。
  入口：主菜单"HFR(M1)"两个 action + env HFR_E1_AUTO=1 自动演示；日志用 blog（禁止 fopen 探针）。
- 影响：临时文件 frontend/widgets/HFRSpike.*，M1 结束或转正时再决定去留。

## ADR-003 运行验证纪律（调试教训）
- 背景：自动化 Start-Process + 强杀多次制造"伪崩溃"（崩溃对话框残留/脏配置/脏增量构建），
  而用户手动双击启动正常；曾出现连原始代码都早崩，clean-first 全量重编后恢复。
- 决策：a) 运行期验收以"人工启动 + obs 日志"为准，自动化不反复启停 GUI；
  b) 头文件/源码列表变动后出现莫名崩溃先 --clean-first 或删 build_x64 重建；
  c) 探针一律 blog 进 obs 日志，不用外部 fopen。
- 影响：夜间自主开发以"编译零错误"为门槛推进；运行验证留给晨间人工清单。

## ADR-004 音频与输出语义（设计方向，M2/M3 待细化）
- 画布不带 MIX_AUDIO = 该画布声音不进总输出；为将来"每输出独立混音"保留空间（按 Sink 选混音组）。
- Sink 绑定模型：Sink.bind(canvas)=克隆（共享纹理，独立裁切/缩放/安全区）；改绑即独立接管；PGM=主画布。

## ADR-005 画布/场景销毁时序（退出崩溃 c0000005 的最终修法）
- 现象：退出时 tiny_tubular_task_thread 在 scene_destroy → obs_sceneitem_destroy → obs_source_release 崩溃，
  主线程此时在 obs_shutdown → obs_free_data → os_task_queue_wait。
- 根因：用户画布的场景/源属于"画布私有"，其销毁被延迟排队；而 obs_free_data 会先释放全局
  sources / canvases 哈希表，残留的画布场景在之后销毁时引用了已释放的源 → AV。
  仅靠 aboutToQuit 里 obs_canvas_remove/release 不够：画布对象还被 obs->data.canvases 哈希表持有，
  weak 轮询也等不到销毁（会白等超时）。
- 修法（HFRConsoleDock::CleanupForShutdown）：
  1) 关闭全部投影窗；2) 对每个用户画布：清空通道0 → 枚举并 obs_canvas_scene_remove 其场景 → obs_canvas_remove/release；
  3) 调用官方 **obs_wait_for_destroy_queue()**（obs.h:935）排空销毁队列（调两次更稳）后再让流程进入 obs_shutdown。
- 影响：运行时删除画布（RemoveSelectedCanvas）复用同一 TeardownUserCanvas 逻辑，路径一致。
