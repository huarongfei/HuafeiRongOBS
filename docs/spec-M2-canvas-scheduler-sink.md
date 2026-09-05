# M2 设计草案 v0：hfr-canvas-scheduler + hfr-sink

> 状态：草案（基于 M0/M1 结论，未实施）。落地前需 M1 E1/E2 运行验收与实测修订。
> 关联：技术文稿 §6/§8、M1-spike-计划.md、ADR-001/002/004。

## 1. 上游给我们的基础（M0/M1 源码核实）
- obs_canvas_create 运行期可把新 mix 推入 obs->video.mixes；output_frames() 每帧遍历 mixes，
  带 view 的 mix 自动渲染进自身 render_texture（obs-video.c:916）。
- obs_render_canvas_texture(canvas) 公开（obs.c:2234）：把 canvas->mix->render_texture 画到当前 gs target。
- 约束：canvas 分辨率独立（reset_video 任意 base），fps 为全局；flags 控行为（ACTIVATE/MIX_AUDIO/SCENE_REF/EPHEMERAL）。
- 缺口（我们要补）：无"画布活跃度分级调度"、无 Sink 绑定/克隆/安全区模型、无多屏布局持久化、无 GUI。

## 2. hfr-canvas-scheduler（目标：5~8 路画布在有限 GPU 上稳定运行）
职责：在图形线程每帧决定"哪些画布本次渲染"。
- 分级：
  - REAL-TIME：全帧率（默认 PGM + 用户指定，务实档 2 路 1080p60）；
  - ON_DEMAND：内容变化才渲染（PPT/静态素材屏）——由 source 事件/脏标记驱动；
  - PREVIEW：低分辨率/降频渲染（监视墙用）；
  - PAUSED：无 Sink 绑定 → 不渲染（但保留画布对象）。
- 实现候选（M2 spike 验证后定）：
  a) 在 output_frames 之后插入 hfr 调度：对非全帧率画布按帧号跳过 obs_view_render；
     风险：mix 渲染由 mix->view 统一驱动，跳过需控制而不破坏纹理一致性（保留上一帧）。
  b) 每画布维护 frameBudget；PREVIEW 复用 clone 的小尺寸取样而非重复合成。
- 验收：单机 4+ 画布（2 实时 + 2 按需/预览）CPU/GPU 占用可测、帧率达标。

## 3. hfr-sink（输出绑定/克隆模型）
概念：Sink = 一个输出目的地；任意时刻 bind 到某画布。
- 类型：SCREEN_WINDOW（真实屏独占全屏克隆窗）、PROJECTOR（窗口）、ENCODER（推流/录制）、NDI/SRT（分发）。
- 属性：绑定画布、输出分辨率/缩放模式、裁切（x/y/w/h）、安全区（标题90%/动作80% 网格开关）、LUT/色差校正、音频路由(混音组+增益+延迟)。
- 生命周期：Sink 与画布解耦——改 bind = "独立接管/克隆"切换（混合制统一表达）。
- 布局：layout = {Sink 列表 + 显示器映射 + 窗口几何}，命名保存/恢复（多屏场景关键）。
- 显示：沿用 OBSQTDisplay/OBSProjector 模式（E1 已验证 obs_display + draw canvas texture 可行）。

## 4. 落位与构建门控
- 阶段：先做"前端实验层"（类似 HFRSpike 的临时文件），稳定后按模块上移 libobs（公共 API）或保持 frontend。
- 门控：默认不改变现有行为；以单独菜单/宏打开，防止影响正常使用。
- 依赖上游 canvas API（unstable）：跟随 32.2.2 基线；每季度评估上游合入。

## 5. M2 验收映射（FR）
- FR-C1/C2 画布 CRUD/PGM：scheduler 注册表 + UI 画布管理器（M4 做 UI，M2 提供接口）。
- FR-O1/O2/O3：Sink 类型 + 克隆（裁切/缩放/安全区）+ 3+ 屏（Windows 监视器枚举+独占窗）。
- FR-O4：活跃度分级（scheduler）支撑 5~8 路目标。
- 里程碑：M2a 调度器（帧跳过/分级，含 A/B 开关）→ M2b Sink 屏幕克隆（3 屏演示）→ M2c 推流/录制绑定画布（复用上游编码器）。
