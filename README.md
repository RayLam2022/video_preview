# 视频预览工具 — Video Preview GUI

基于 PySide6 + OpenCV 的视频文件批量预览工具，将视频片段自动生成动画 GIF 缩略图，支持网格浏览、分页、搜索筛选。

## 功能特性

- 🎬 **动画 GIF 预览** — 自动截取视频片段生成 5fps 循环动画，直观浏览视频内容
- 📂 **文件夹扫描** — 支持 mp4 / avi / mkv / mov / webm / flv / wmv / m4v / ts / 3gp
- 🖼️ **网格布局** — 可配置每页行×列，自动分页
- ⚙️ **灵活配置** — 预览起始时间、时长、网格行列数均可调节
- 🗂️ **目录树导航** — 左侧目录树快速切换文件夹
- 🧠 **智能缓存** — GIF 缩略图缓存到临时目录，二次访问秒开
- 🔄 **编码兼容** — OpenCV 解码失败时自动回退到系统 ffmpeg 提取帧
- ⏱️ **短视频适配** — 视频时长不足时自动调整采样窗口，不会黑屏
- 🌙 **深色主题** — 护眼暗色界面

## 截图

> 动画 GIF 缩略图 + 网格分页 + 目录树导航

## 环境要求

- **Python** ≥ 3.10
- **PySide6** — Qt for Python GUI
- **opencv-python** — 视频帧读取（部分编码需系统 ffmpeg 回退）
- **Pillow** — GIF 合成与缩略图处理
- **numpy** — 帧数据计算

### 可选依赖

- **ffmpeg**（系统安装）— 当 OpenCV 内置解码器无法处理某些编码格式时自动回退使用

## 安装

```bash
# 克隆项目
git clone <repo-url> preview_gui
cd preview_gui

# 创建虚拟环境并安装依赖
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install PySide6 opencv-python Pillow numpy
```

## 使用

```bash
# 激活虚拟环境后运行
python main.py
```

### 操作说明

| 操作 | 说明 |
|------|------|
| 打开文件夹 | 菜单 → 文件 → 打开文件夹，或地址栏直接输入路径 |
| 切换页码 | 底部翻页栏选择页码 |
| 调整每页数量 | 翻页栏下拉框「每页 N 项」，自动适配网格 |
| 修改预览参数 | 菜单 → 设置 → 预览参数 |
| 查看视频信息 | 鼠标悬停卡片显示时长/分辨率/编码/大小 |
| 打开视频 | 双击卡片用系统默认播放器打开 |
| 复制路径 | 右键点击卡片 → 复制路径 |

### 预览参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 起始时间 | 0 秒 | 从视频的哪个位置开始截取 |
| 预览时长 | 3 秒 | 动画 GIF 的时长，约 15 帧（3×5fps） |
| 行数 | 2 | 每页网格行数 |
| 列数 | 3 | 每页网格列数（每页共 6 个视频） |

## 项目结构

```
preview_gui/
├── main.py                          # 入口，环境初始化
├── debug.log                        # 调试日志（自动生成）
├── src/
│   ├── config.py                    # AppConfig — QSettings 持久化配置
│   ├── app.py                       # MainWindow — 主窗口，组装所有组件
│   ├── core/
│   │   ├── scanner.py               # 视频文件扫描 & 元数据提取
│   │   ├── previewer.py             # 帧提取 & GIF 生成（cv2 + ffmpeg 回退）
│   │   └── thumbnail_worker.py      # 后台缩略图生成 Worker
│   └── widgets/
│       ├── folder_bar.py            # 顶部地址栏
│       ├── folder_tree.py           # 左侧目录树
│       ├── video_card.py            # 单个视频卡片（GIF + 信息）
│       ├── video_grid.py            # 网格布局容器
│       ├── pagination_bar.py        # 底部翻页控件
│       └── settings_dialog.py       # 预览参数设置对话框
```

## 技术要点

### 预览生成流程

```
1. 扫描目录 → 收集 VideoInfo（帧率/分辨率/时长/编码）
2. 后台 Worker 逐个处理:
   a. OpenCV 打开视频 → 截取 start_sec ~ start_sec+duration_sec
   b. 按 5fps 采样 → 缩放到 240×180 → PIL 合成 GIF
   c. 全黑帧检测 → 自动回退到系统 ffmpeg 提取
3. GIF 缓存到 %TEMP%\preview_gui_cache\
4. QMovie 播放 GIF → 显示在卡片网格中
```

### 短视频 / 黑屏处理

- 视频 < 起始时间：自动取最后 duration_sec
- 视频 < 预览时长：取全部可用帧
- OpenCV 帧 seek 失败：四级回退（seek → 前1帧 → 逐帧读取 → 跳过黑帧）
- 所有帧全黑：回退到系统 ffmpeg，单次 `fps` filter 提取

### GIF 缓存

缓存路径为 `%TEMP%\preview_gui_cache\`，以 `{video_path}|{start}|{duration}|{frame_count}` 的 MD5 命名，相同参数不会重复生成。可通过设置对话框清除缓存。

## License

MIT
