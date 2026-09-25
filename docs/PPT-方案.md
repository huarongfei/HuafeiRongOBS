# PPT 集成方案（本地 LibreOffice / 无 IPC 桥接）

> 目标：把 .pptx 作为**画布内容**直接播放，并支持**讲者模式**（主屏幻灯 + 讲者窗备注/下一页）。
> 约束（产品方要求）：**本地化部署 LibreOffice，不走 IPC 桥接**；**重点关注 PPT 动画与文字渲染**。

## 一、部署方式（已执行）
- 下载官方 **LibreOffice 26.2.6 Win x86-64**（主程序 MSI 356MB + SDK MSI 22MB）
- 用 `msiexec /a`（administrative install）**免管理员**解包到：
  - `D:\HuafeirongOBS\tools\LibreOffice`（运行库，含 program/、share/）
  - `D:\HuafeirongOBS\tools\LibreOfficeSDK`（含 LibreOfficeKit 头文件）
- 不做系统级安装、不写注册表（保持可移植）；路径可配置。

## 一·五、当前状态（已实现，编译零错误；运行验证待人工执行）
- 同进程 LOK 已接入工程：`frontend/widgets/HFRPpt.{hpp,cpp}`
  - `LoadLibrary(program/mergedlo.dll)` → `GetProcAddress("lok_preinit_2")` → 同进程拿到 `LibreOfficeKit*`
  - 打开文档：`documentLoad` + `initializeForRendering`；翻页：`.uno:NextPage`/`.uno:PreviousPage`；整页渲染：`setClientZoom` + `paintTile` → BGRA
  - 独立 LO 用户配置目录（`tools/LibreOffice/hfr-lok-profile`），不污染系统；可用 `HFR_LO_PATH` 覆盖安装路径
- 编译开关：`-DHFR_ENABLE_PPT=ON -DHFR_LO_SDK_DIR=.../LibreOfficeSDK/sdk/include`（默认 OFF，其他机器无 LO 也能编译）
- 控制台新增 **PPT** 行：`打开PPT` / `PPT上一页` / `PPT下一页`；渲染输出 `<profile>\hfr_ppt_preview.bmp`，状态栏给出**非白像素占比 + 页号**（用于判断内容是否真的渲染出来）
- 无人值守自检：设 `HFR_PPT_AUTOTEST=<pptx路径>` 启动，5 秒后自动渲染并写日志 `[HFR-PPT] autotest OK: 非白像素 …%`

### 已实现（本轮）：作为**正规 OBS 来源**导入
- 来源类型 id `hfr_ppt_source`，名称 **"PPT 演示文稿（LibreOffice）"**；启动时由前端注册（`HfrRegisterPptSource()`）
- 使用方式：**来源 → + → PPT 演示文稿（LibreOffice）**
- 属性：选择 pptx 文件、渲染宽度/高度、页码（从 0 起）、按钮 **上一页 / 下一页 / 重新载入文件**，并显示"共 N 页，当前第 M 页"或具体错误
- 渲染：`video_tick` 内 CPU 渲染整页 → `video_render` 内上传 `GS_BGRA` 纹理并 `obs_source_draw`，因此**投影/推流/每画布录制自动带上 PPT**（标准源管线）
- 实现文件：`frontend/widgets/HFRPptSource.{hpp,cpp}`（配合 `HFRPpt.{hpp,cpp}` 的多实例文档）

### 尚未做的（下一步）
- 渲染结果 → **画布纹理**（投影/直播直接出画面）、**讲者视图**（备注 + 下一页）
- **缺失字体报告与替换表**、2× 超采样、动画步骤预渲染（二期）

## 一·六、运行时嵌入（自包含分发）
- **查找顺序**：`obs64.exe 同目录\lo\`（嵌入式优先）→ 环境变量 `HFR_LO_PATH` → 开发机 `tools/LibreOffice`
- **构建时自动嵌入**：CMake `HFR_EMBED_LO=ON`（默认 ON）用 `copy_directory_if_different` 把运行时复制到
  `build_x64/rundir/<Config>/bin/64bit/lo/`，与 `obs64.exe` 同级 → **拷贝整个 `bin\64bit` 即可分发**，用户无需另装 LibreOffice
  （首次复制约 350MB，后续只同步变化文件；关闭：`-DHFR_EMBED_LO=OFF`）
- **一键获取运行时**（新机器/新克隆）：`scripts\fetch-libreoffice-runtime.cmd`（下载官方 MSI + `msiexec /a` 免管理员解包）

## 二、渲染接入（同进程优先）
1. **LOK（LibreOfficeKit，进程内）**：加载 `program\sofficeapp.dll` 导出的 `lok_init_2 / lok_document_load / lok_document_render` 等 C API。
   - 输出 BGRA 位图 → 上传为 `gs_texture` → 进画布/投影（与现有画布机制天然契合）
   - 验证点：解包后先确认上述符号存在（`dumpbin /exports`）
2. 若该版本 LOK 符号不可直接用：退回**本地批量转换**（同目录 soffice 转 PNG/PDF 后进画布）——仍全本地、无网络依赖，但含子进程；
3. 接入形态：新模块 `HFRPptSource`（临时 spike 起步）→ 稳定后按需上移为源类型；
   未检测到 LO 时**优雅降级**（菜单置灰/提示路径配置）。

## 三、动画处理（明确分期）
| 阶段 | 方案 | 效果 | 成本 |
|---|---|---|---|
| 一期（先做） | 每页渲染**最终状态**；页间用自建转场（淡入/推移/硬切） | 内容完整、切换流畅；**PPT 原生动画按最终态呈现** | 低 |
| 二期（可选） | 按动画步骤**预渲染多帧**，播放时逐步切帧 | 接近原生动画 | 中高（渲染量×步数） |
| 三期（可选） | 通过 LO slideshow/UNO 命令通道驱动（需验证 LOK 命令接口） | 最接近原版放映 | 高 |

> 结论：一期先保证"**内容对、字对、切得顺**"，动画保真列二期；文档与 UI 都要明示"动画按最终态"。

## 四、文字渲染问题与对策
1. **渲染分辨率**：按该画布基础分辨率渲染；提供 2× 超采样 + 缩放，避免文字发虚/锯齿。
2. **字体缺失（最关键）**：
   - pptx 里指定的字体若系统未安装，LO 会**静默替换**→ 字宽变化 → 排版位移/断行变化；
   - 对策：启动/载入时输出**缺失字体清单**（状态栏+日志），并提供**字体替换表**（如 "思源宋体→宋体"）配置项。
3. **CJK 保障**：优先系统字体（微软雅黑/宋体/黑体）；若环境残缺，随包提供 **Noto Sans CJK** 并优先挂载，保证中文不出方块。
4. **一致性**：幻灯片画布与讲者视图使用**同一渲染管线与同一字体配置**，避免两处观感不一致。
5. **版式细节**：遵循 LO 的自动换行/自动缩放结果（与 PowerPoint 渲染存在天然差异，需在验收时用真实课件比对，必要时按模板微调）。

## 五、其他已知限制（写进 UI 提示）
- pptx 内嵌**视频/音频**：LOK 静态渲染不播放 → 需转为"外部媒体源"插入画布；
- **SmartArt/复杂 3D 与部分特效**：LO 渲染可能简化；
- 宏/VBA：不执行。

## 六、验收清单（PPT 部分）
- [ ] 中文课件：标题/正文/项目符号排版无错位，无方块字
- [ ] 英文课件：字宽变化在可接受范围，不溢出文本框
- [ ] 特殊字体课件：能列出缺失字体，替换表生效后排版回正
- [ ] 20+ 页翻页：切换流畅，无闪烁/黑帧
- [ ] 投影画布 + 讲者窗同时显示，内容一致
- [ ] 动画页：按最终态呈现（一期预期），无残影