<h4 align="right"><a href="./README.md">English</a> | <strong><a href="./README_CN.md">简体中文</a></strong></h4>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/kiri-wordmark-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/kiri-wordmark-light.svg">
    <img src="assets/kiri-wordmark-light.svg" alt="Kiri" height="74">
  </picture>
</p>

<h3 align="center"><nobr>🦊 Kiri Launchpad · 本地开发服务管控与极速端口中枢 (Web Dashboard & CLI)</nobr></h3>

<p align="center">
  现代化的本地开发服务启动台、可视化端口管控面板与智能防撞中枢。集服务极速拉起、重启、终止、文件夹卡片折叠、物理文件模式直通与毫秒级端口监视于一体。
</p>

---

<p align="center">
  <img alt="Platform" src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-brightgreen" />
  <img alt="Web Dashboard" src="https://img.shields.io/badge/Dashboard-Web%20GUI-blue" />
  <img alt="Core" src="https://img.shields.io/badge/Engine-Python%20%7C%20Rust-orange" />
  <img alt="License: Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-purple" />
</p>

<p align="center">
  <img src="assets/readme/launchpad-overview.png" alt="Kiri Launchpad 启动台全景预览" width="960" style="border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.12);" />
</p>

---

## ✨ 核心特性概览 (Key Features)

### 1. 🚀 启动台 · 服务管控与启动记录 (Launchpad)
- **单行四卡极简布局 (Compact View)**：信息密度与优雅并重，严格约束网格布局，杜绝屏幕横向溢出；
- **高频操作四键集成**：每个卡片配备单键极速操作：
  - `▷ 启动`：在独立控制台运行配置命令行，并在端口监听就绪后**自动调用默认浏览器秒开网页**；
  - `🔄 重启`：释放旧进程并平滑拉起新实例，自动重新打开网页；
  - `⏸ 暂停/停止`：一键精准终止服务进程（taskkill / kill）；
  - `📁 文件`：**“文件模式”**直达物理磁盘目录。
- **📁 文件夹折叠卡片 (Folder Cards)**：
  - 拖拽卡片悬停长按 400ms，即可将从属服务折叠收纳为文件夹卡片（第一排为主服务，第二排为从属服务）；
  - 第二排采用高密度**子端口胶囊 (`:3200` `:3300`) 并排呈现**，带有实时健康灯（🟢/⚪）；
  - **向外拖拽解散**：按住 `:3200` 胶囊往卡片外任意位置一拖一松手，瞬间解散移出文件夹，还原为独立卡片；亦可点击胶囊上的红色 `×` 一键移出。

### 2. 📂 物理“文件模式” (File Mode & Directory Opus 优先直通)
- **精准高亮定位**：无论是启动台卡片、进程列表还是监控表格，点击“文件”按键，系统将直接唤醒文件管理器并**精准高亮选中（Select/Focus）**目标项目目录，而非仅仅打开普通上级文件夹；
- **Directory Opus 物理屏幕穿透**：系统若安装有专业文件管理器 Directory Opus，优先调用 `dopusrt.exe` 直通并穿透 `WinSta0\Default` 物理交互桌面，确保置顶弹窗；未安装时优雅降级为 Windows Explorer 资源管理器。

### 3. 📈 服务监控与端口变动流 (Service Monitor)
- **毫秒级内核采集**：纯 Win32 内核级 PEB 读取与端口匹配，~70ms 极速扫描；
- **全方位实时指标**：监听端口、进程名称、PID、物理内存占用 (WorkingSet)、识别到的框架 (Vite/FastAPI/Python/Node等)、存活运行时长、健康状态；
- **📡 变动事件流 (Watch Stream)**：实时记录服务启动 (`STARTED`)、停止 (`STOPPED`) 与端口释放流水；
- **💻 原生 CLI 终端视图**：内置终端 ASCII 表格与控制台日志追踪。

### 4. 📋 端口防撞档案 (Port Anti-Collision Registry)
- **全生命周期端口档案簿**：自动沉淀本机曾经使用的开发端口，支持自定义备注与别名修改；
- **✨ 推荐无冲突可用端口**：结合当前监听状态与历史分配，智能动态推荐连续可用未冲突端口号。

### 5. ⚡ 批处理与日常维护任务 (Batch Tasks)
- 启动台底部集成日常批处理任务面板（如 Rust 内核构建 `cargo build`、缓存清理等），支持配置独立工作目录与执行命令，一键异步触发并实时反馈运行状态。

---

## ⚡ 极速开箱使用 (Quick Start)

### 方式一：Windows 一键双击直达（推荐）
直接双击根目录下的批处理脚本：
```bash
双击打开Kiri.bat
```
脚本将自动检测环境、启动轻量服务守护进程并在浏览器中打开控制台：
👉 **http://127.0.0.1:7788/**

### 方式二：Python 启动
```bash
# 启动控制台守护服务
python kiri_web.py

# 静默后台启动（不自动弹窗浏览器）
python kiri_web.py --no-browser
```

### 方式三：Rust 原生 CLI 命令行模式
如果您只需要在纯命令行终端下查看端口与日志：
```bash
cargo run --release -- ports
# 或者已安装全局命令
ports
ports logs <port|pid> -f
```

---

## 🏗️ 目录结构 (Repository Structure)

```text
├── web/
│   └── index.html               # 现代化 Kiri Launchpad Web 控制台纯前端（Century Gothic 标准字系）
├── kiri_web.py                  # 高性能 Win32 内核端口监控与启动台后端守护服务 (~70ms 采集引擎)
├── 双击打开Kiri.bat             # Windows 用户开箱即用一键启动脚本
├── kiri_services.template.json  # 启动台通用配置种子模板（脱敏开箱即用）
├── src/                         # Kiri 原生 Rust 命令行工具源代码 (CLI 内核)
│   ├── main.rs
│   ├── platform/                # Windows / macOS / Linux 进程 PEB 与 CWD 采集实现
│   └── render/                  # 终端表格渲染与 ANSI 着色器
├── Cargo.toml                   # Rust 工程配置
└── AGENTS.md                    # 严格工程规范、排版与“文件模式”规范守则
```

---

## 🔒 隐私与安全性规范 (Privacy & Security)

本项目在开源发布时已遵循严格的隐私脱敏红线：
- 本机实际运行的配置与端口流水（`kiri_services.json`、`port_aliases.json`）已被 `.gitignore` 彻底物理隔离，绝不上传云端；
- 开源开箱统一由 `kiri_services.template.json` 提供纯净标准示例；
- 绝无任何个人绝对磁盘路径、API Key 或密钥残留。

---

## 📄 开源许可证 (License)

Apache-2.0 License © 2026 Kekeyo & Kiri Contributors.
