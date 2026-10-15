# -*- coding: utf-8 -*-
"""
Kiri Web Dashboard 后端服务
复刻 Kiri (Rust) 的端口扫描、框架识别、开发进程过滤、实时监控与进程终止能力，并提供毫秒级响应的 Web API。
"""

import datetime
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
PORTS_EXE = BASE_DIR / "ports.exe"
ALIASES_FILE = BASE_DIR / "port_aliases.json"
HOST = "127.0.0.1"
PORT = 7788


def load_aliases() -> dict[str, dict]:
    """读取本地持久化端口别名与网页标题缓存"""
    if not ALIASES_FILE.exists():
        return {}
    try:
        return json.loads(ALIASES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_aliases(aliases: dict[str, dict]):
    """持久化保存端口别名与网页标题到本地 JSON"""
    try:
        ALIASES_FILE.write_text(json.dumps(aliases, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[Kiri Web] 保存别名失败: {e}", file=sys.stderr)


SERVICES_FILE = BASE_DIR / "kiri_services.json"


def get_default_services_seed() -> dict:
    """初始化默认启动台登记服务与批处理任务 (标准开发通用模板)"""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "services": [
            {
                "id": "srv_7788",
                "name": "Kiri Web 端口监控与启动台",
                "category": "系统管控",
                "port": 7788,
                "command": "python kiri_web.py --no-browser",
                "cwd": str(BASE_DIR),
                "framework": "Kiri Web",
                "icon": "⚡",
                "created_at": now_str,
                "updated_at": now_str,
            },
            {
                "id": "srv_3000",
                "name": "Web 前端应用 (示例)",
                "category": "Web 前端",
                "port": 3000,
                "command": "npm run dev",
                "cwd": ".",
                "framework": "Vite",
                "icon": "🌐",
                "created_at": now_str,
                "updated_at": now_str,
            },
            {
                "id": "srv_8000",
                "name": "后端 API 服务 (示例)",
                "category": "后端服务",
                "port": 8000,
                "command": "python -m uvicorn main:app --reload --port 8000",
                "cwd": ".",
                "framework": "FastAPI",
                "icon": "🚀",
                "created_at": now_str,
                "updated_at": now_str,
            },
        ],
        "tasks": [
            {
                "id": "task_build",
                "name": "构建 Rust 端口内核",
                "category": "工程构建",
                "command": "cargo build --release",
                "cwd": str(BASE_DIR),
                "icon": "🦀",
                "last_run": "-",
                "last_status": "idle",
            },
            {
                "id": "task_clean",
                "name": "清理 Python 字节码缓存",
                "category": "清理维护",
                "command": "powershell -Command \"Get-ChildItem -Recurse -Filter __pycache__ | Remove-Item -Recurse -Force\"",
                "cwd": str(BASE_DIR),
                "icon": "🧹",
                "last_run": "-",
                "last_status": "idle",
            },
        ],
    }
        "tasks": [
            {
                "id": "task_build",
                "name": "构建 Rust 端口内核",
                "category": "工程构建",
                "command": "cargo build --release",
                "cwd": str(BASE_DIR),
                "icon": "🦀",
                "last_run": "-",
                "last_status": "idle",
            },
            {
                "id": "task_clean",
                "name": "清理 Python 字节码缓存",
                "category": "清理维护",
                "command": 'powershell -Command "Get-ChildItem -Recurse -Filter __pycache__ | Remove-Item -Recurse -Force"',
                "cwd": str(BASE_DIR),
                "icon": "🧹",
                "last_run": "-",
                "last_status": "idle",
            },
        ]
    }


def load_services_registry() -> dict:
    """加载启动台登记的服务与任务"""
    if not SERVICES_FILE.exists():
        data = get_default_services_seed()
        save_services_registry(data)
        return data
    try:
        data = json.loads(SERVICES_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {"services": [], "tasks": []}
        if "services" not in data:
            data["services"] = []
        if "tasks" not in data:
            data["tasks"] = []
        return data
    except Exception:
        return get_default_services_seed()


def save_services_registry(data: dict):
    """保存启动台服务与任务至本地 JSON"""
    try:
        SERVICES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[Kiri Web] 保存启动台配置失败: {e}", file=sys.stderr)


def is_port_listening(port: int) -> bool:
    """极速探测指定端口是否已进入 LISTENING 状态"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            return s.connect_ex(("127.0.0.1", int(port))) == 0
    except Exception:
        return False


def wait_and_open_browser(port: int, max_wait: float = 30.0):
    """在后台线程中监视目标端口，一旦服务启动就绪立即自动调用系统默认浏览器打开网页"""
    def _waiter():
        t0 = time.time()
        while time.time() - t0 < max_wait:
            time.sleep(0.4)
            if is_port_listening(port):
                time.sleep(0.3)
                try:
                    webbrowser.open(f"http://127.0.0.1:{port}/")
                    print(f"[Kiri Web] 端口 :{port} 已就绪，已自动拉起系统浏览器", file=sys.stderr)
                except Exception as e:
                    print(f"[Kiri Web] 自动打开浏览器失败: {e}", file=sys.stderr)
                break
    threading.Thread(target=_waiter, daemon=True).start()


def launch_service_cmd(cmd: str, cwd: str = "", title: str = "", port: int | None = None, auto_open: bool = True) -> tuple[bool, int, str]:
    """在新独立控制台中安全拉起服务或执行任务命令，并智能打开网页"""
    if not cmd:
        return False, 0, "命令为空"

    effective_cwd = cwd if (cwd and os.path.exists(cwd)) else None
    title_label = title or (f"服务 :{port}" if port else "Kiri Service")

    if os.name == "nt":
        # 使用 cmd.exe /k 组合指令：
        # 1. 设置控制台标题；
        # 2. 切换物理工作盘符与目录；
        # 3. 打印启动看板信息（避免黑色窗口瞬间关闭导致用户看不清错误）；
        # 4. 执行真实服务启动命令（如 npm run dev 或 python main.py）。
        cmd_parts = [f'title [Kiri] {title_label}']
        if effective_cwd:
            drive = os.path.splitdrive(effective_cwd)[0]
            if drive:
                cmd_parts.append(drive)
            cmd_parts.append(f'cd /d "{effective_cwd}"')
        cmd_parts.append(f'echo [Kiri Launchpad] 正在拉起服务: {title_label}')
        if effective_cwd:
            cmd_parts.append(f'echo [工作目录] {effective_cwd}')
        cmd_parts.append(f'echo [启动命令] {cmd}')
        cmd_parts.append("echo ----------------------------------------------------")
        cmd_parts.append(cmd)

        full_cli = " & ".join(cmd_parts)
        launch_args = f'cmd.exe /k "{full_cli}"'
        creationflags = subprocess.CREATE_NEW_CONSOLE
    else:
        launch_args = cmd
        creationflags = 0

    try:
        proc = subprocess.Popen(
            launch_args,
            cwd=effective_cwd,
            shell=True if os.name != "nt" else False,
            creationflags=creationflags
        )

        if port and auto_open:
            wait_and_open_browser(port)

        msg = f"已在独立控制台启动服务 (PID {proc.pid})，端口 :{port} 就绪后将自动打开网页" if port else f"已在独立控制台启动 (PID {proc.pid})"
        return True, proc.pid, msg
    except Exception as e:
        return False, 0, f"启动异常: {e}"


def probe_web_title(port: int) -> str | None:
    """尝试通过 HTTP 访问该本地端口并嗅探 HTML <title> 作为初始网页名称"""
    for host in ("127.0.0.1", "localhost"):
        url = f"http://{host}:{port}/"
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) KiriPortMonitor/1.0"}
            )
            with urllib.request.urlopen(req, timeout=0.8) as resp:
                content = resp.read(8192).decode("utf-8", errors="ignore")
                m = re.search(r"<title[^>]*>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
                if m:
                    title = " ".join(m.group(1).split()).strip()
                    if title:
                        return title
        except Exception:
            continue
    return None


SYSTEM_PROCESS_PREFIXES = (
    "spotify", "raycast", "tableplus", "postman", "linear", "cursor",
    "controlce", "rapportd", "slack", "discord", "firefox", "chrome",
    "google", "safari", "figma", "notion", "zoom", "teams", "code",
    "iterm2", "warp", "arc", "loginwindow", "windowserver", "systemuise",
    "kernel_task", "launchd", "mdworker", "mds_stores", "cfprefsd",
    "coreaudio", "airportd", "bluetoothd", "sharingd", "systemd", "snapd",
    "networkmanager", "gdm", "sshd", "cron", "dbus-daemon", "svchost",
    "csrss", "lsass", "services", "explorer", "system", "wininit",
    "smss", "spoolsv", "searchindexer", "msedge", "webview2"
)

DEV_PROCESS_NAMES = {
    "node", "ruby", "java", "go", "cargo", "deno", "bun", "php",
    "uvicorn", "gunicorn", "flask", "rails", "npm", "npx", "yarn",
    "pnpm", "tsc", "tsx", "esbuild", "rollup", "turbo", "nx",
    "jest", "vitest", "mocha", "pytest", "cypress", "playwright",
    "rustc", "dotnet", "gradle", "mvn", "mix", "elixir", "docker",
}

COMMAND_INDICATORS = {
    "node", "next", "vite", "nuxt", "webpack", "remix", "astro",
    "gulp", "gatsby", "flask", "django", "uvicorn", "rails", "cargo",
}

PROJECT_MARKERS = (
    "package.json", "Cargo.toml", "go.mod", "pyproject.toml",
    "Gemfile", "pom.xml", "build.gradle"
)


def is_python_process_name(name: str) -> bool:
    """判断进程名称是否为 Python 解释器进程"""
    n = name.lower()
    if n.endswith(".exe"):
        n = n[:-4]
    if n == "python":
        return True
    if not n.startswith("python"):
        return False
    ver = n[6:]
    if ver.endswith("t"):
        ver = ver[:-1]
    parts = ver.split(".")
    return all(p.isdigit() and len(p) > 0 for p in parts) and 1 <= len(parts) <= 2


def is_developer_process(process_name: str, command: str, port: int = 0) -> bool:
    """复刻 Kiri 的开发进程判定规则"""
    if port == PORT:
        return True
    name = process_name.lower()
    if name.endswith(".exe"):
        name = name[:-4]
    cmd = (command or "").lower()

    if any(name.startswith(prefix) for prefix in SYSTEM_PROCESS_PREFIXES):
        return False

    if is_python_process_name(name) or name in DEV_PROCESS_NAMES:
        return True
    if name.startswith("com.docke") or name == "docker-sandbox":
        return True
    if "manage.py" in cmd or "ng serve" in cmd:
        return True

    tokens = []
    curr = []
    for ch in cmd:
        if ch.isalnum() or ch == ".":
            curr.append(ch)
        else:
            if curr:
                tokens.append("".join(curr))
                curr = []
    if curr:
        tokens.append("".join(curr))

    return any(ind in tokens for ind in COMMAND_INDICATORS)


def find_project_root(exe_or_cwd: str) -> Path | None:
    """向上查找包含项目标志文件的项目根目录"""
    if not exe_or_cwd:
        return None
    try:
        p = Path(exe_or_cwd)
        if p.is_file():
            p = p.parent
        orig = p
        curr = p
        for _ in range(15):
            if any((curr / m).exists() for m in PROJECT_MARKERS):
                return curr
            if curr.parent == curr:
                break
            curr = curr.parent
        return orig
    except Exception:
        return None


def detect_framework(command: str, process_name: str, project_root: Path | None) -> str:
    """根据启动命令、进程名与项目根目录识别开发框架"""
    cmd = (command or "").lower()
    if "kiri_web.py" in cmd:
        return "Kiri Web"
    if "next" in cmd:
        return "Next.js"
    if "vite" in cmd:
        return "Vite"
    if "nuxt" in cmd:
        return "Nuxt"
    if "angular" in cmd or "ng serve" in cmd:
        return "Angular"
    if "webpack" in cmd:
        return "Webpack"
    if "remix" in cmd:
        return "Remix"
    if "astro" in cmd:
        return "Astro"
    if "gatsby" in cmd:
        return "Gatsby"
    if "flask" in cmd:
        return "Flask"
    if "django" in cmd or "manage.py" in cmd:
        return "Django"
    if "uvicorn" in cmd or "fastapi" in cmd:
        return "FastAPI"
    if "rails" in cmd:
        return "Rails"
    if "cargo" in cmd or "rustc" in cmd:
        return "Rust"

    if project_root and project_root.exists():
        pkg_file = project_root / "package.json"
        if pkg_file.exists():
            try:
                pkg = json.loads(pkg_file.read_text(encoding="utf-8", errors="ignore"))
                deps = {}
                if isinstance(pkg.get("dependencies"), dict):
                    deps.update(pkg["dependencies"])
                if isinstance(pkg.get("devDependencies"), dict):
                    deps.update(pkg["devDependencies"])
                for key, label in [
                    ("next", "Next.js"), ("nuxt", "Nuxt"), ("nuxt3", "Nuxt"),
                    ("@sveltejs/kit", "SvelteKit"), ("svelte", "Svelte"),
                    ("astro", "Astro"), ("vite", "Vite"), ("@angular/core", "Angular"),
                    ("vue", "Vue"), ("react", "React"), ("express", "Express"),
                    ("fastify", "Fastify"), ("hono", "Hono"), ("koa", "Koa"),
                    ("@nestjs/core", "NestJS")
                ]:
                    if key in deps:
                        return label
            except Exception:
                pass

    if is_python_process_name(process_name):
        return "Python"
    n = process_name.lower().removesuffix(".exe")
    mapping = {
        "node": "Node.js",
        "ruby": "Ruby",
        "java": "Java",
        "go": "Go",
        "dotnet": ".NET",
        "php": "PHP",
        "bun": "Bun",
        "deno": "Deno",
    }
    return mapping.get(n, process_name)


def format_memory(rss_kb: int) -> str:
    """格式化内存大小"""
    if rss_kb <= 0:
        return "-"
    if rss_kb > 1_048_576:
        return f"{rss_kb / 1_048_576:.1f} GB"
    if rss_kb > 1024:
        return f"{rss_kb / 1024:.1f} MB"
    return f"{rss_kb} KB"


def format_uptime(seconds: float) -> str:
    """格式化运行时长"""
    if seconds < 0:
        return "-"
    s = int(seconds)
    m = s // 60
    h = m // 60
    d = h // 24
    if d > 0:
        return f"{d}d {h % 24}h"
    if h > 0:
        return f"{h}h {m % 60}m"
    if m > 0:
        return f"{m}m {s % 60}s"
    return f"{s}s"


if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010
    PEB_PROCESS_PARAMETERS_OFFSET = 0x20
    CURRENT_DIRECTORY_DOS_PATH_OFFSET = 0x38
    COMMAND_LINE_OFFSET = 0x70

    class PROCESS_BASIC_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("Reserved1", ctypes.c_void_p),
            ("PebBaseAddress", ctypes.c_void_p),
            ("Reserved2", ctypes.c_void_p * 2),
            ("UniqueProcessId", ctypes.c_void_p),
            ("Reserved3", ctypes.c_void_p),
        ]

    class UNICODE_STRING(ctypes.Structure):
        _fields_ = [
            ("Length", wintypes.USHORT),
            ("MaximumLength", wintypes.USHORT),
            ("_pad", wintypes.DWORD),
            ("Buffer", ctypes.c_void_p),
        ]

    _kernel32 = ctypes.windll.kernel32
    _ntdll = ctypes.windll.ntdll


def get_process_cwd(pid: int) -> str | None:
    """通过读取 Win32 进程 PEB 结构极速提取进程当前真实工作目录 (耗时 ~9 微秒)"""
    if os.name != "nt":
        try:
            return os.readlink(f"/proc/{pid}/cwd")
        except Exception:
            return None

    if pid <= 4:
        return None

    try:
        h_proc = _kernel32.OpenProcess(0x0410, False, pid)  # PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
        if not h_proc:
            return None
        try:
            pbi = PROCESS_BASIC_INFORMATION()
            ret_len = wintypes.ULONG()
            status = _ntdll.NtQueryInformationProcess(
                h_proc, 0, ctypes.byref(pbi), ctypes.sizeof(pbi), ctypes.byref(ret_len)
            )
            if status != 0 or not pbi.PebBaseAddress:
                return None

            proc_params_addr = ctypes.c_void_p()
            read_bytes = ctypes.c_size_t()
            ok = _kernel32.ReadProcessMemory(
                h_proc,
                ctypes.c_void_p(pbi.PebBaseAddress + PEB_PROCESS_PARAMETERS_OFFSET),
                ctypes.byref(proc_params_addr),
                ctypes.sizeof(proc_params_addr),
                ctypes.byref(read_bytes),
            )
            if not ok or not proc_params_addr.value:
                return None

            dos_path = UNICODE_STRING()
            ok = _kernel32.ReadProcessMemory(
                h_proc,
                ctypes.c_void_p(proc_params_addr.value + CURRENT_DIRECTORY_DOS_PATH_OFFSET),
                ctypes.byref(dos_path),
                ctypes.sizeof(dos_path),
                ctypes.byref(read_bytes),
            )
            if not ok or not dos_path.Length or not dos_path.Buffer:
                return None

            buf = ctypes.create_unicode_buffer(dos_path.Length // 2)
            ok = _kernel32.ReadProcessMemory(
                h_proc,
                ctypes.c_void_p(dos_path.Buffer),
                buf,
                dos_path.Length,
                ctypes.byref(read_bytes),
            )
            if not ok:
                return None

            raw = buf.value.rstrip("\x00").strip()
            if raw.startswith(r"\\?\\"):
                raw = raw[4:]
            raw = raw.rstrip(r"\/")
            return raw if raw else None
        finally:
            _kernel32.CloseHandle(h_proc)
    except Exception:
        return None


def get_process_cmdline(pid: int) -> str | None:
    """通过读取 Win32 进程 PEB 结构极速提取进程完整命令行 (耗时 ~9 微秒)"""
    if os.name != "nt":
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                return f.read().replace(b"\x00", b" ").decode("utf-8", errors="ignore").strip()
        except Exception:
            return None

    if pid <= 4:
        return None

    try:
        h_proc = _kernel32.OpenProcess(0x0410, False, pid)  # PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
        if not h_proc:
            return None
        try:
            pbi = PROCESS_BASIC_INFORMATION()
            ret_len = wintypes.ULONG()
            status = _ntdll.NtQueryInformationProcess(
                h_proc, 0, ctypes.byref(pbi), ctypes.sizeof(pbi), ctypes.byref(ret_len)
            )
            if status != 0 or not pbi.PebBaseAddress:
                return None

            proc_params_addr = ctypes.c_void_p()
            read_bytes = ctypes.c_size_t()
            ok = _kernel32.ReadProcessMemory(
                h_proc,
                ctypes.c_void_p(pbi.PebBaseAddress + PEB_PROCESS_PARAMETERS_OFFSET),
                ctypes.byref(proc_params_addr),
                ctypes.sizeof(proc_params_addr),
                ctypes.byref(read_bytes),
            )
            if not ok or not proc_params_addr.value:
                return None

            cmd_us = UNICODE_STRING()
            ok = _kernel32.ReadProcessMemory(
                h_proc,
                ctypes.c_void_p(proc_params_addr.value + COMMAND_LINE_OFFSET),
                ctypes.byref(cmd_us),
                ctypes.sizeof(cmd_us),
                ctypes.byref(read_bytes),
            )
            if not ok or not cmd_us.Length or not cmd_us.Buffer:
                return None

            buf = ctypes.create_unicode_buffer(cmd_us.Length // 2)
            ok = _kernel32.ReadProcessMemory(
                h_proc,
                ctypes.c_void_p(cmd_us.Buffer),
                buf,
                cmd_us.Length,
                ctypes.byref(read_bytes),
            )
            if not ok:
                return None

            raw = buf.value.rstrip("\x00").strip()
            return raw if raw else None
        finally:
            _kernel32.CloseHandle(h_proc)
    except Exception:
        return None


def resolve_process_cwd(pid: int, exe_path: str = "") -> str:
    """综合解析进程真实工作目录：PEB 内存直接读取 -> kiri-cwd.exe 回退 -> exe 父目录回退"""
    cwd = get_process_cwd(pid)
    if cwd and os.path.exists(cwd):
        return cwd

    kiri_cwd_tool = BASE_DIR / "kiri-cwd.exe"
    if kiri_cwd_tool.exists():
        try:
            res = subprocess.run(
                [str(kiri_cwd_tool), str(pid)],
                capture_output=True,
                text=True,
                timeout=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            out = res.stdout.strip()
            if out and os.path.exists(out):
                return out
        except Exception:
            pass

    if exe_path and os.path.exists(exe_path):
        p = Path(exe_path)
        return str(p.parent) if p.is_file() else str(p)
    return ""


def find_dopusrt() -> Path | None:
    """自动检测 Directory Opus 的命令行调度工具 dopusrt.exe"""
    candidates = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "GPSoftware" / "Directory Opus" / "dopusrt.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "GPSoftware" / "Directory Opus" / "dopusrt.exe",
        Path(r"C:\Program Files\GPSoftware\Directory Opus\dopusrt.exe"),
    ]
    for c in candidates:
        if c.exists():
            return c

    if os.name == "nt":
        try:
            import winreg
            for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(root, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\DOpus.exe") as key:
                        app_dir, _ = winreg.QueryValueEx(key, "Path")
                        if app_dir:
                            d = Path(app_dir) / "dopusrt.exe"
                            if d.exists():
                                return d
                except OSError:
                    pass
        except Exception:
            pass

    return None


def launch_on_user_desktop(cmd: str) -> bool:
    """在 Windows 物理交互桌面 (WinSta0\\Default) 上启动进程，确保能真实弹出窗口并置顶"""
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            class STARTUPINFOW(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("lpReserved", wintypes.LPWSTR),
                    ("lpDesktop", wintypes.LPWSTR),
                    ("lpTitle", wintypes.LPWSTR),
                    ("dwX", wintypes.DWORD),
                    ("dwY", wintypes.DWORD),
                    ("dwXSize", wintypes.DWORD),
                    ("dwYSize", wintypes.DWORD),
                    ("dwXCountChars", wintypes.DWORD),
                    ("dwYCountChars", wintypes.DWORD),
                    ("dwFillAttribute", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD),
                    ("wShowWindow", wintypes.WORD),
                    ("cbReserved2", wintypes.WORD),
                    ("lpReserved2", ctypes.c_char_p),
                    ("hStdInput", wintypes.HANDLE),
                    ("hStdOutput", wintypes.HANDLE),
                    ("hStdError", wintypes.HANDLE),
                ]

            class PROCESS_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ("hProcess", wintypes.HANDLE),
                    ("hThread", wintypes.HANDLE),
                    ("dwProcessId", wintypes.DWORD),
                    ("dwThreadId", wintypes.DWORD),
                ]

            si = STARTUPINFOW()
            si.cb = ctypes.sizeof(STARTUPINFOW)
            si.lpDesktop = r"WinSta0\Default"
            pi = PROCESS_INFORMATION()

            kernel32 = ctypes.windll.kernel32
            ok = kernel32.CreateProcessW(
                None, cmd, None, None, False, 0, None, None, ctypes.byref(si), ctypes.byref(pi)
            )
            if ok:
                kernel32.CloseHandle(pi.hProcess)
                kernel32.CloseHandle(pi.hThread)
                return True
        except Exception as e:
            print(f"[Kiri Web] CreateProcessW failed: {e}", file=sys.stderr)

    try:
        subprocess.Popen(cmd, shell=True)
        return True
    except Exception as e:
        print(f"[Kiri Web] subprocess.Popen failed: {e}", file=sys.stderr)
        return False


def open_path_in_file_manager(target_path: str, select: bool = True, force_explorer: bool = False) -> tuple[bool, str]:
    """打开文件管理器，优先使用 Directory Opus 并自动定位选中目标"""
    p = Path(target_path)
    if not p.exists():
        return False, f"目录或文件不存在: {target_path}"

    real_abs = str(p.resolve())
    dopusrt = find_dopusrt()
    is_drive_root = (p.parent == p)

    if os.name == "nt":
        # 1. 优先使用 Directory Opus (除非显式要求资源管理器)
        if not force_explorer and dopusrt and dopusrt.exists():
            try:
                if select and not is_drive_root:
                    # 使用 /cmd 唤醒 Directory Opus，OPENCONTAINER 定位父目录并选中，TOFRONT 置顶窗口
                    # NEWTAB=deflister,findexisting 确保没有 Lister 打开时自动拉起 Default Lister
                    cmd = f'"{dopusrt}" /cmd Go OPENCONTAINER PATH "{real_abs}" NEWTAB=deflister,findexisting TOFRONT'
                    action_name = "定位并选中"
                else:
                    cmd = f'"{dopusrt}" /cmd Go PATH "{real_abs}" NEWTAB=deflister,findexisting TOFRONT'
                    action_name = "打开"

                ok = launch_on_user_desktop(cmd)
                if ok:
                    return True, f"已在 Directory Opus 中{action_name}: {real_abs}"
            except Exception as e:
                print(f"[Kiri Web] Directory Opus 唤起异常: {e}", file=sys.stderr)

        # 2. 回退使用 Windows Explorer
        try:
            if select and not is_drive_root:
                cmd = f'explorer.exe /select,"{real_abs}"'
                action_name = "定位并选中"
            else:
                cmd = f'explorer.exe "{real_abs}"'
                action_name = "打开"

            ok = launch_on_user_desktop(cmd)
            if ok:
                return True, f"已在资源管理器中{action_name}: {real_abs}"
        except Exception as e:
            return False, f"打开失败: {e}"

    elif sys.platform == "darwin":
        if select and not is_drive_root:
            subprocess.Popen(["open", "-R", real_abs])
        else:
            subprocess.Popen(["open", real_abs])
        return True, f"已在访达 (Finder) 中打开: {real_abs}"

    else:
        subprocess.Popen(["xdg-open", real_abs])
        return True, f"已打开: {real_abs}"


def _collect_win32_processes() -> dict[int, dict]:
    """使用 ctypes 直接调用 Win32 内核 API 极速获取所有进程信息 (耗时 ~3ms，零子进程开销)"""
    import ctypes
    from ctypes import wintypes

    TH32CS_SNAPPROCESS = 0x00000002
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    MAX_PATH = 260

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * MAX_PATH),
        ]

    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    class FILETIME(ctypes.Structure):
        _fields_ = [
            ("dwLowDateTime", wintypes.DWORD),
            ("dwHighDateTime", wintypes.DWORD),
        ]

    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi

    h_snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if h_snap == -1 or h_snap == 0:
        return {}

    procs: dict[int, dict] = {}
    pe = PROCESSENTRY32W()
    pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)

    now_ts = int(time.time())
    try:
        ok = kernel32.Process32FirstW(h_snap, ctypes.byref(pe))
        while ok:
            pid = int(pe.th32ProcessID)
            ppid = int(pe.th32ParentProcessID)
            raw_name = pe.szExeFile
            clean_name = raw_name[:-4] if raw_name.lower().endswith(".exe") else raw_name

            exe_path = ""
            rss_kb = 0
            uptime_sec = -1
            start_time_str = "-"

            if pid > 4:
                h_proc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                if h_proc:
                    try:
                        # 1. 可执行文件完整路径
                        buf = ctypes.create_unicode_buffer(1024)
                        size = wintypes.DWORD(1024)
                        if kernel32.QueryFullProcessImageNameW(h_proc, 0, buf, ctypes.byref(size)):
                            exe_path = buf.value

                        # 2. 内存 WorkingSetSize
                        pmc = PROCESS_MEMORY_COUNTERS()
                        pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
                        if kernel32.K32GetProcessMemoryInfo(h_proc, ctypes.byref(pmc), pmc.cb) or psapi.GetProcessMemoryInfo(h_proc, ctypes.byref(pmc), pmc.cb):
                            rss_kb = int(pmc.WorkingSetSize // 1024)

                        # 3. 进程启动时间
                        ft_create = FILETIME()
                        ft_exit = FILETIME()
                        ft_kernel = FILETIME()
                        ft_user = FILETIME()
                        if kernel32.GetProcessTimes(
                            h_proc,
                            ctypes.byref(ft_create),
                            ctypes.byref(ft_exit),
                            ctypes.byref(ft_kernel),
                            ctypes.byref(ft_user),
                        ):
                            ticks = (ft_create.dwHighDateTime << 32) | ft_create.dwLowDateTime
                            if ticks > 116444736000000000:
                                create_ts = int((ticks - 116444736000000000) // 10_000_000)
                                uptime_sec = max(0, now_ts - create_ts)
                                start_time_str = datetime.datetime.fromtimestamp(create_ts).strftime("%Y-%m-%d %H:%M:%S")
                    finally:
                        kernel32.CloseHandle(h_proc)

            procs[pid] = {
                "pid": pid,
                "ppid": ppid,
                "name": clean_name or f"pid-{pid}",
                "exe": exe_path,
                "cmd": exe_path or clean_name,
                "rss_kb": rss_kb,
                "uptime_sec": uptime_sec,
                "start_time": start_time_str,
            }
            ok = kernel32.Process32NextW(h_snap, ctypes.byref(pe))
    finally:
        kernel32.CloseHandle(h_snap)

    return procs


class KiriMonitor:
    """后台端口与进程状态监控器（纯 Win32 内核调用 + netstat 毫秒级引擎）"""

    def __init__(self):
        self.lock = threading.Lock()
        self.collect_lock = threading.Lock()
        self.aliases: dict[str, dict] = load_aliases()
        self.pending_probe: set[int] = set()
        self.probed_ports: set[int] = set()
        self.state = {
            "updated_at": "",
            "scan_ms": 0,
            "dev_ports": [],
            "all_ports": [],
            "dev_processes": [],
            "history_ports": [],
            "suggested_ports": [],
            "events": [],
            "cli_output": "正在加载原生 ports.exe 输出...",
            "base_dir": str(BASE_DIR),
            "has_dopus": bool(find_dopusrt()),
        }
        self.known_ports: dict[int, dict] = {}
        self.initialized = False

    def collect_once(self):
        """使用 Win32 内核 API + netstat 实现 ~70ms 极速无阻塞扫描 (多线程安全防重入)"""
        if not self.collect_lock.acquire(blocking=False):
            return
        try:
            self._do_collect_once()
        except Exception as e:
            print(f"[Kiri Web] 扫描采集异常: {e}", file=sys.stderr)
        finally:
            self.collect_lock.release()

    def _do_collect_once(self):
        t0 = time.perf_counter()
        try:
            proc_table = _collect_win32_processes()
            ns_proc = subprocess.run(
                ["netstat", "-ano", "-p", "tcp"],
                capture_output=True,
                text=True,
                encoding="mbcs" if os.name == "nt" else "utf-8",
                errors="replace",
                timeout=4,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            listeners = []
            seen_ports = set()
            for line in ns_proc.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 5 and parts[0].upper() == "TCP" and parts[3].upper() == "LISTENING":
                    local_addr = parts[1]
                    if ":" not in local_addr:
                        continue
                    addr_part, port_str = local_addr.rsplit(":", 1)
                    try:
                        port_num = int(port_str)
                        pid_num = int(parts[4])
                    except ValueError:
                        continue
                    if port_num > 0 and port_num not in seen_ports:
                        seen_ports.add(port_num)
                        listeners.append({
                            "port": port_num,
                            "addr": addr_part,
                            "pid": pid_num,
                        })
            listeners.sort(key=lambda x: x["port"])
        except Exception as e:
            print(f"[Kiri Web] 极速扫描异常: {e}", file=sys.stderr)
            return

        all_ports = []
        dev_ports = []

        for item in listeners:
            port_num = item["port"]
            pid_num = item["pid"]
            pinfo = proc_table.get(pid_num, {})

            proc_name = pinfo.get("name") or f"pid-{pid_num}"
            rss_kb = int(pinfo.get("rss_kb") or 0)
            exe = pinfo.get("exe") or ""
            cmd = get_process_cmdline(pid_num) or pinfo.get("cmd") or proc_name
            ppid = int(pinfo.get("ppid") or 0)
            uptime_sec = int(pinfo.get("uptime_sec") or -1)
            start_time = pinfo.get("start_time") or "-"

            cwd_str = resolve_process_cwd(pid_num, exe)
            proj_root = find_project_root(cwd_str or exe)
            project_name = proj_root.name if proj_root and proj_root.name else "-"
            if port_num == PORT:
                project_name = "Kiri (port)"

            framework = detect_framework(cmd, proc_name, proj_root)
            if port_num == PORT:
                framework = "Kiri Web"
            is_dev = is_developer_process(proc_name, cmd, port=port_num)

            alias_info = self.aliases.get(str(port_num), {})
            alias_val = alias_info.get("alias") or ""
            auto_title = alias_info.get("auto_title") or ""
            is_custom = bool(alias_info.get("is_custom", False))

            if is_dev and port_num not in self.probed_ports:
                self.pending_probe.add(port_num)

            entry = {
                "port": port_num,
                "address": item["addr"],
                "pid": pid_num,
                "ppid": ppid,
                "process": proc_name,
                "alias": alias_val,
                "auto_title": auto_title,
                "is_custom": is_custom,
                "command": cmd,
                "executable": exe,
                "cwd": cwd_str or (str(proj_root) if proj_root else "-"),
                "project": project_name,
                "framework": framework,
                "rss_kb": rss_kb,
                "memory": format_memory(rss_kb),
                "uptime_sec": uptime_sec,
                "uptime": format_uptime(uptime_sec),
                "start_time": start_time,
                "status": "healthy",
                "is_dev": is_dev,
            }
            all_ports.append(entry)
            if is_dev:
                dev_ports.append(entry)

        # 组装后台开发进程列表 (对应 ports ps)
        dev_processes = []
        listening_pids = {p["pid"] for p in all_ports}
        for pid_num, pinfo in proc_table.items():
            proc_name = pinfo["name"]
            cmd = get_process_cmdline(pid_num) or pinfo["cmd"]
            if is_developer_process(proc_name, cmd):
                exe = pinfo["exe"]
                cwd_str = resolve_process_cwd(pid_num, exe)
                proj_root = find_project_root(cwd_str or exe)
                project_name = proj_root.name if proj_root and proj_root.name else "-"
                rss_kb = pinfo["rss_kb"]
                uptime_sec = pinfo["uptime_sec"]
                dev_processes.append({
                    "pid": pid_num,
                    "ppid": pinfo["ppid"],
                    "process": proc_name,
                    "command": cmd,
                    "executable": exe,
                    "cwd": cwd_str or (str(proj_root) if proj_root else "-"),
                    "project": project_name,
                    "framework": detect_framework(cmd, proc_name, proj_root),
                    "rss_kb": rss_kb,
                    "memory": format_memory(rss_kb),
                    "uptime": format_uptime(uptime_sec),
                    "listening": pid_num in listening_pids,
                })
        dev_processes.sort(key=lambda x: x["rss_kb"], reverse=True)

        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        # 构建历史端口档案簿 (防冲突一览)
        history_ports = []
        active_dev_map = {p["port"]: p for p in dev_ports}
        listening_ports_set = {p["port"] for p in all_ports}
        aliases_changed = False

        # 1. 丰富当前在线开发端口的元数据至持久化 self.aliases
        now_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for p in dev_ports:
            port_key = str(p["port"])
            cur = self.aliases.get(port_key, {})
            if p.get("project") and p["project"] != "-" and cur.get("project") != p["project"]:
                cur["project"] = p["project"]
                aliases_changed = True
            real_cwd = p.get("cwd") or ""
            if real_cwd and real_cwd != "-" and cur.get("cwd") != real_cwd:
                cur["cwd"] = real_cwd
                aliases_changed = True
            if p.get("framework") and p["framework"] != "-" and cur.get("framework") != p["framework"]:
                cur["framework"] = p["framework"]
                aliases_changed = True
            if p.get("command") and p["command"] != "-" and cur.get("command") != p["command"]:
                cur["command"] = p["command"]
                aliases_changed = True
            if not cur.get("alias") and p.get("auto_title"):
                cur["alias"] = p["auto_title"]
                aliases_changed = True
            cur["last_seen"] = now_time
            self.aliases[port_key] = cur

        if aliases_changed:
            save_aliases(self.aliases)

        # 2. 组装全量历史档案列表 (使用 safe list 快照)
        for port_str, info in list(self.aliases.items()):
            try:
                p_num = int(port_str)
            except ValueError:
                continue
            is_active = p_num in active_dev_map
            active_info = active_dev_map.get(p_num)

            history_ports.append({
                "port": p_num,
                "alias": info.get("alias") or info.get("auto_title") or "",
                "auto_title": info.get("auto_title") or "",
                "is_custom": bool(info.get("is_custom", False)),
                "project": active_info["project"] if is_active else (info.get("project") or "-"),
                "cwd": active_info["cwd"] if is_active else (info.get("cwd") or "-"),
                "framework": active_info["framework"] if is_active else (info.get("framework") or "-"),
                "command": active_info["command"] if is_active else (info.get("command") or "-"),
                "process": active_info["process"] if is_active else "offline",
                "pid": active_info["pid"] if is_active else None,
                "uptime": active_info["uptime"] if is_active else "-",
                "last_seen": info.get("last_seen") or info.get("updated_at") or "-",
                "is_active": is_active,
                "is_listening": p_num in listening_ports_set,
            })
        history_ports.sort(key=lambda x: x["port"])

        # 3. 智能计算推荐可用无冲突空闲端口
        occupied_set = set(listening_ports_set) | {int(p) for p in list(self.aliases.keys()) if p.isdigit()}
        candidates = [3000, 3001, 3002, 5173, 5174, 5175, 8000, 8080, 8081, 8082, 8090, 8091, 8890, 8990, 9000, 9001]
        suggested_ports = [c for c in candidates if c not in occupied_set][:6]

        with self.lock:
            current_dev_map = {p["port"]: p for p in dev_ports}
            if self.initialized:
                for p, info in current_dev_map.items():
                    if p not in self.known_ports:
                        self.state["events"].insert(0, {
                            "time": now_str,
                            "type": "STARTED",
                            "port": p,
                            "process": info["process"],
                            "pid": info["pid"],
                            "framework": info["framework"],
                            "project": info["project"],
                        })
                for p, old_info in list(self.known_ports.items()):
                    if p not in current_dev_map:
                        self.state["events"].insert(0, {
                            "time": now_str,
                            "type": "STOPPED",
                            "port": p,
                            "process": old_info["process"],
                            "pid": old_info["pid"],
                            "framework": old_info["framework"],
                            "project": old_info["project"],
                        })
                self.state["events"] = self.state["events"][:100]
            else:
                for p, info in current_dev_map.items():
                    self.state["events"].append({
                        "time": now_str,
                        "type": "ACTIVE",
                        "port": p,
                        "process": info["process"],
                        "pid": info["pid"],
                        "framework": info["framework"],
                        "project": info["project"],
                    })
                self.initialized = True

            self.known_ports = current_dev_map
            self.state["updated_at"] = now_str
            self.state["scan_ms"] = elapsed_ms
            self.state["dev_ports"] = dev_ports
            self.state["all_ports"] = all_ports
            self.state["dev_processes"] = dev_processes[:60]
            self.state["history_ports"] = history_ports
            self.state["suggested_ports"] = suggested_ports
            self.state["cli_output"] = self._render_ascii_table(dev_ports)

    def _render_ascii_table(self, dev_ports: list[dict]) -> str:
        """直接基于内存极速数据生成 Kiri 风格 ASCII 表格输出（无需等待慢速 WMI）"""
        cnt = len(dev_ports)
        lines = [
            "      .-~~~~-.",
            "   .-(  ●  ● )-.",
            f"  (  •   ⌣   •  )  Kiri is watching {cnt} ports, {cnt} ports active",
            "   '-.        .-'",
            "      '------'",
            "",
            f"{'Port':<7} {'Process':<10} {'PID':<8} {'Mem':<10} {'Framework':<12} {'Uptime':<10} {'Status':<10} {'Project':<14} {'Path'}",
            "-" * 105,
        ]
        for p in dev_ports:
            lines.append(
                f"{p['port']:<7} {p['process'][:10]:<10} {p['pid']:<8} {p['memory']:<10} "
                f"{p['framework'][:12]:<12} {p['uptime']:<10} {p['status']:<10} {p['project'][:14]:<14} {p['cwd']}"
            )
        return "\n".join(lines)

    def update_cli_output(self):
        pass

    def start_background_loops(self):
        """启动后台定时采集与网页标题探测线程"""
        def fast_loop():
            while True:
                time.sleep(3)
                try:
                    self.collect_once()
                except Exception as e:
                    print(f"[Kiri Web] 定时采集异常: {e}", file=sys.stderr)

        def probe_loop():
            while True:
                try:
                    if self.pending_probe:
                        batch = list(self.pending_probe)
                        self.pending_probe.clear()
                        changed = False
                        for p in batch:
                            self.probed_ports.add(p)
                            port_str = str(p)
                            cur = self.aliases.get(port_str, {})
                            t = probe_web_title(p)
                            if t:
                                if not cur.get("is_custom"):
                                    self.aliases[port_str] = {
                                        "alias": t,
                                        "auto_title": t,
                                        "is_custom": False,
                                        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    }
                                    changed = True
                                elif cur.get("auto_title") != t:
                                    cur["auto_title"] = t
                                    changed = True
                        if changed:
                            save_aliases(self.aliases)
                            self.collect_once()
                except Exception as e:
                    print(f"[Kiri Web] 网页嗅探异常: {e}", file=sys.stderr)
                time.sleep(2)

        threading.Thread(target=fast_loop, daemon=True).start()
        threading.Thread(target=probe_loop, daemon=True).start()

    def get_launchpad_state(self) -> dict:
        """获取启动台全量服务与任务状态快照 (优先解析物理真实运行路径与命令)"""
        registry = load_services_registry()
        services = registry.get("services", [])
        tasks = registry.get("tasks", [])

        with self.lock:
            dev_ports = list(self.state.get("dev_ports", []))
            all_ports = list(self.state.get("all_ports", []))
            suggested_ports = list(self.state.get("suggested_ports", []))

        active_port_map = {p["port"]: p for p in dev_ports}
        for p in all_ports:
            if p["port"] not in active_port_map:
                active_port_map[p["port"]] = p

        processed_services = []
        services_changed = False
        base_dir_lower = str(BASE_DIR).lower()

        # 检查是否还有正在运行中的活跃开发端口尚未登记到 services 中，自动动态补全
        registered_ports = {int(s.get("port") or 0) for s in services}
        for p in dev_ports:
            p_num = p["port"]
            if p_num > 0 and p_num not in registered_ports:
                new_s = {
                    "id": f"srv_{p_num}",
                    "name": p.get("alias") or p.get("auto_title") or p.get("project") or f"开发服务 :{p_num}",
                    "category": "Web 前端" if ("Vite" in p.get("framework", "") or "Node" in p.get("framework", "")) else ("Python 后端" if "Python" in p.get("framework", "") else "网络工具"),
                    "port": p_num,
                    "command": p.get("command") or "-",
                    "cwd": p.get("cwd") or "",
                    "framework": p.get("framework") or "Web",
                    "icon": "🐍" if "Python" in p.get("framework", "") else ("⚛️" if "Vite" in p.get("framework", "") else "🌐"),
                    "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                services.append(new_s)
                registered_ports.add(p_num)
                services_changed = True

        for s in services:
            p_num = int(s.get("port") or 0)
            is_active = (p_num in active_port_map) if p_num else False
            act_info = active_port_map.get(p_num, {})
            hist_info = self.aliases.get(str(p_num), {})

            # 1. 动态深度解析真实 CWD：
            # 若进程运行中，以实时抓取的真实物理工作目录为最高准则；
            # 若离线且原 CWD 为占位目录（例如误指到当前监控工程根目录 BASE_DIR），优先从历史档案中提取真实目录；
            # 否则使用登记的 cwd。
            act_cwd = act_info.get("cwd")
            hist_cwd = hist_info.get("cwd")
            reg_cwd = s.get("cwd") or ""

            is_reg_cwd_placeholder = (
                not reg_cwd
                or (reg_cwd.lower() == base_dir_lower and p_num != PORT)
                or not os.path.exists(reg_cwd)
            )

            if is_active and act_cwd and act_cwd != "-":
                effective_cwd = act_cwd
            elif is_reg_cwd_placeholder and hist_cwd and hist_cwd != "-":
                effective_cwd = hist_cwd
            else:
                effective_cwd = reg_cwd

            # 2. 动态深度解析真实启动命令行：
            # 若在运行且有真实命令行，优先采用真实命令行；
            # 若登记命令为空或为默认虚拟名字，从历史档案提取。
            act_cmd = act_info.get("command")
            hist_cmd = hist_info.get("command")
            reg_cmd = s.get("command") or ""

            is_reg_cmd_dummy = not reg_cmd or reg_cmd.strip() in ("-", "placeholder", "demo", "start")

            if is_active and act_cmd and act_cmd != "-":
                effective_cmd = act_cmd
            elif is_reg_cmd_dummy and hist_cmd and hist_cmd != "-":
                effective_cmd = hist_cmd
            else:
                effective_cmd = reg_cmd

            # 3. 动态框架与名称
            effective_fw = (
                (act_info.get("framework") if is_active else None)
                or s.get("framework")
                or hist_info.get("framework")
                or "Web"
            )
            effective_name = (
                s.get("name")
                or hist_info.get("alias")
                or hist_info.get("auto_title")
                or f"服务 :{p_num}"
            )

            # 自愈纠偏：若解析出真实有效的目录和命令，自动同步更新到 s 中并持久化
            if effective_cwd and effective_cwd != s.get("cwd"):
                s["cwd"] = effective_cwd
                services_changed = True
            is_stored_clean_script = (
                s.get("command")
                and (
                    s.get("command").startswith("npm run")
                    or s.get("command").startswith("pnpm")
                    or s.get("command").startswith("yarn")
                )
            )
            if effective_cmd and effective_cmd != s.get("command") and not is_stored_clean_script:
                s["command"] = effective_cmd
                services_changed = True
            if effective_fw and effective_fw != s.get("framework"):
                s["framework"] = effective_fw
                services_changed = True

            cwd_exists = bool(effective_cwd and os.path.exists(effective_cwd))

            processed_services.append({
                "id": s.get("id"),
                "name": effective_name,
                "category": s.get("category") or "默认",
                "port": p_num,
                "command": effective_cmd,
                "cwd": effective_cwd or "-",
                "framework": effective_fw,
                "icon": s.get("icon") or "🚀",
                "is_running": is_active,
                "pid": act_info.get("pid") if is_active else None,
                "memory": act_info.get("memory") if is_active else "-",
                "uptime": act_info.get("uptime") if is_active else "-",
                "cwd_exists": cwd_exists,
                "updated_at": s.get("updated_at") or "-",
                "parent_id": s.get("parent_id"),
            })

        if services_changed:
            save_services_registry(registry)

        categories = sorted(list(set(s["category"] for s in processed_services if s.get("category"))))
        if "全部" not in categories:
            categories.insert(0, "全部")

        running_cnt = sum(1 for s in processed_services if s["is_running"])
        stopped_cnt = len(processed_services) - running_cnt

        return {
            "services": processed_services,
            "tasks": tasks,
            "categories": categories,
            "stats": {
                "total_services": len(processed_services),
                "running_services": running_cnt,
                "stopped_services": stopped_cnt,
                "total_tasks": len(tasks),
                "suggested_ports": suggested_ports,
            }
        }


MONITOR = KiriMonitor()


class KiriRequestHandler(BaseHTTPRequestHandler):
    """处理前端页面与 RESTful API 请求"""

    def log_message(self, format, *args):
        pass

    def _send_json(self, payload: dict, status: int = 200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            html_file = WEB_DIR / "index.html"
            if html_file.exists():
                content = html_file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "index.html not found")
            return

        if parsed.path in ("/api/status", "/api/launchpad"):
            with MONITOR.lock:
                snapshot = dict(MONITOR.state)
            snapshot["has_dopus"] = bool(find_dopusrt())
            snapshot["launchpad"] = MONITOR.get_launchpad_state()
            self._send_json({"ok": True, "data": snapshot})
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8", errors="ignore") if length > 0 else "{}"
        try:
            body = json.loads(raw_body) if raw_body else {}
        except Exception:
            body = {}

        if parsed.path == "/api/refresh":
            MONITOR.collect_once()
            threading.Thread(target=MONITOR.update_cli_output, daemon=True).start()
            with MONITOR.lock:
                snapshot = dict(MONITOR.state)
            snapshot["has_dopus"] = bool(find_dopusrt())
            self._send_json({"ok": True, "data": snapshot})
            return

        if parsed.path == "/api/kill":
            target_port = body.get("port")
            target_pid = body.get("pid")
            force = bool(body.get("force", True))

            if target_pid == os.getpid() or target_port == PORT:
                self._send_json({
                    "ok": False,
                    "message": f"端口 {PORT} 是当前 Kiri 网页监控台自身进程，已保护不被误杀！"
                }, 400)
                return

            try:
                if target_pid:
                    cmd = ["taskkill", "/PID", str(int(target_pid))]
                    if force:
                        cmd.insert(1, "/F")
                    res = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    )
                    msg = (res.stdout or res.stderr or f"已终止 PID {target_pid}").strip()
                elif target_port and PORTS_EXE.exists():
                    cmd = [str(PORTS_EXE), "kill"]
                    if force:
                        cmd.append("--force")
                    cmd.append(str(int(target_port)))
                    res = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    )
                    msg = (res.stdout or res.stderr or f"已释放端口 {target_port}").strip()
                else:
                    self._send_json({"ok": False, "message": "未提供有效的 port 或 pid"}, 400)
                    return

                MONITOR.collect_once()
                with MONITOR.lock:
                    snapshot = dict(MONITOR.state)
                self._send_json({"ok": True, "message": msg, "data": snapshot})
            except Exception as e:
                self._send_json({"ok": False, "message": str(e)}, 500)
            return

        if parsed.path == "/api/restart":
            target_port = body.get("port")
            target_pid = body.get("pid")

            if target_pid == os.getpid() or (target_port and int(target_port) == PORT):
                self._send_json({
                    "ok": False,
                    "message": f"端口 {PORT} 是当前 Kiri 网页监控台自身服务，不支持自重启！"
                }, 400)
                return

            if not target_port and not target_pid:
                self._send_json({"ok": False, "message": "未提供有效的 port 或 pid"}, 400)
                return

            try:
                # 1. 查找目标进程快照
                target_entry = None
                with MONITOR.lock:
                    search_list = (
                        list(MONITOR.state.get("all_ports", []))
                        + list(MONITOR.state.get("dev_ports", []))
                        + list(MONITOR.state.get("dev_processes", []))
                    )
                for item in search_list:
                    if target_port and item.get("port") == int(target_port):
                        target_entry = item
                        break
                    if target_pid and item.get("pid") == int(target_pid):
                        target_entry = item
                        break

                pid_val = int(target_pid) if target_pid else (target_entry.get("pid") if target_entry else None)

                # 2. 提取精确命令行与运行工作目录
                cmd_to_run = ""
                cwd_to_run = ""

                if pid_val:
                    cmd_to_run = get_process_cmdline(pid_val) or ""
                    cwd_to_run = resolve_process_cwd(pid_val) or ""

                if not cmd_to_run and target_entry:
                    cmd_to_run = target_entry.get("command") or target_entry.get("executable") or ""
                if not cwd_to_run and target_entry:
                    cwd_to_run = target_entry.get("cwd") or ""

                if cwd_to_run == "-":
                    cwd_to_run = ""

                if not cmd_to_run:
                    self._send_json({
                        "ok": False,
                        "message": f"未提取到目标进程 (PID {pid_val}) 的启动命令行，无法自动重新拉起"
                    }, 400)
                    return

                # 3. 终止旧进程
                if pid_val:
                    subprocess.run(
                        ["taskkill", "/F", "/PID", str(pid_val)],
                        capture_output=True,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    )
                elif target_port and PORTS_EXE.exists():
                    subprocess.run(
                        [str(PORTS_EXE), "kill", "--force", str(int(target_port))],
                        capture_output=True,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    )

                # 4. 短暂休眠等待端口与资源完全释放
                time.sleep(0.6)

                # 5. 重新拉起新进程
                launch_kwargs = {"shell": True}
                if cwd_to_run and os.path.exists(cwd_to_run):
                    launch_kwargs["cwd"] = cwd_to_run
                if os.name == "nt":
                    launch_kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE

                proc = subprocess.Popen(cmd_to_run, **launch_kwargs)
                new_pid = proc.pid

                # 6. 等待新服务初始化并刷新监控数据
                time.sleep(0.5)
                MONITOR.collect_once()
                with MONITOR.lock:
                    snapshot = dict(MONITOR.state)

                msg = f"端口 :{target_port} 服务已成功重启 (新 PID: {new_pid})" if target_port else f"服务已成功重启 (新 PID: {new_pid})"
                self._send_json({
                    "ok": True,
                    "message": msg,
                    "new_pid": new_pid,
                    "command": cmd_to_run,
                    "cwd": cwd_to_run,
                    "data": snapshot,
                })
            except Exception as e:
                self._send_json({"ok": False, "message": f"重启异常: {e}"}, 500)
            return

        if parsed.path == "/api/alias":
            target_port = body.get("port")
            new_alias = str(body.get("alias", "")).strip()
            if not target_port:
                self._send_json({"ok": False, "message": "未提供有效端口号"}, 400)
                return
            port_str = str(target_port)
            cur = MONITOR.aliases.get(port_str, {})
            if new_alias:
                cur["alias"] = new_alias
                cur["is_custom"] = True
            else:
                cur["alias"] = cur.get("auto_title", "")
                cur["is_custom"] = False
            cur["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            MONITOR.aliases[port_str] = cur
            save_aliases(MONITOR.aliases)
            MONITOR.collect_once()
            with MONITOR.lock:
                snapshot = dict(MONITOR.state)
            self._send_json({"ok": True, "message": f"端口 :{target_port} 备注已保存", "data": snapshot})
            return

        if parsed.path == "/api/alias/probe":
            target_port = body.get("port")
            if not target_port:
                self._send_json({"ok": False, "message": "未提供有效端口号"}, 400)
                return
            port_num = int(target_port)
            t = probe_web_title(port_num)
            port_str = str(port_num)
            cur = MONITOR.aliases.get(port_str, {})
            if t:
                cur["auto_title"] = t
                if not cur.get("is_custom"):
                    cur["alias"] = t
                    cur["is_custom"] = False
                cur["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                MONITOR.aliases[port_str] = cur
                save_aliases(MONITOR.aliases)
            MONITOR.collect_once()
            with MONITOR.lock:
                snapshot = dict(MONITOR.state)
            self._send_json({"ok": True, "title": t or "未探测到标题", "data": snapshot})
            return

        if parsed.path == "/api/alias/delete":
            target_port = body.get("port")
            if target_port and str(target_port) in MONITOR.aliases:
                del MONITOR.aliases[str(target_port)]
                save_aliases(MONITOR.aliases)
                MONITOR.collect_once()
                with MONITOR.lock:
                    snapshot = dict(MONITOR.state)
                self._send_json({"ok": True, "message": f"已从历史档案中注销端口 :{target_port}", "data": snapshot})
                return
        if parsed.path == "/api/launchpad/service/save":
            service_data = body.get("service") or {}
            sid = service_data.get("id") or f"srv_{int(time.time()*1000)}"
            service_data["id"] = sid
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            service_data["updated_at"] = now_str
            if "created_at" not in service_data:
                service_data["created_at"] = now_str

            registry = load_services_registry()
            found = False
            for idx, s in enumerate(registry.get("services", [])):
                if s.get("id") == sid:
                    registry["services"][idx] = service_data
                    found = True
                    break
            if not found:
                registry["services"].append(service_data)

            save_services_registry(registry)
            MONITOR.collect_once()
            launchpad_data = MONITOR.get_launchpad_state()
            self._send_json({"ok": True, "message": f"服务「{service_data.get('name')}」登记已保存", "launchpad": launchpad_data})
            return

        if parsed.path == "/api/launchpad/service/delete":
            sid = body.get("id")
            registry = load_services_registry()
            # 释放归属于该服务的所有子服务
            for s in registry.get("services", []):
                if s.get("parent_id") == sid:
                    s["parent_id"] = None
            before_len = len(registry.get("services", []))
            registry["services"] = [s for s in registry.get("services", []) if s.get("id") != sid]
            if len(registry["services"]) < before_len:
                save_services_registry(registry)
            launchpad_data = MONITOR.get_launchpad_state()
            self._send_json({"ok": True, "message": "已删除该服务登记", "launchpad": launchpad_data})
            return

        if parsed.path == "/api/launchpad/services/reorder":
            order_ids = body.get("order") or []
            swap_pair = body.get("swap") or []
            registry = load_services_registry()
            services_list = registry.get("services", [])

            if len(swap_pair) == 2:
                id1, id2 = swap_pair[0], swap_pair[1]
                idx1 = next((i for i, s in enumerate(services_list) if s.get("id") == id1), None)
                idx2 = next((i for i, s in enumerate(services_list) if s.get("id") == id2), None)
                if idx1 is not None and idx2 is not None:
                    services_list[idx1], services_list[idx2] = services_list[idx2], services_list[idx1]
                    registry["services"] = services_list
                    save_services_registry(registry)
            elif order_ids:
                id_map = {s.get("id"): s for s in services_list}
                new_services = []
                for sid in order_ids:
                    if sid in id_map:
                        new_services.append(id_map.pop(sid))
                new_services.extend(id_map.values())
                registry["services"] = new_services
                save_services_registry(registry)

            launchpad_data = MONITOR.get_launchpad_state()
            self._send_json({"ok": True, "message": "卡片排序已持久化保存", "launchpad": launchpad_data})
            return

        if parsed.path == "/api/launchpad/services/group":
            dragged_id = body.get("dragged_id")
            target_id = body.get("target_id")
            action = body.get("action", "group")  # "group" or "ungroup"
            registry = load_services_registry()
            services_list = registry.get("services", [])

            if action == "group" and dragged_id and target_id and dragged_id != target_id:
                # 寻找 target 的最终根节点 (防止二级嵌套)
                target_srv = next((s for s in services_list if s.get("id") == target_id), None)
                real_parent_id = (target_srv.get("parent_id") or target_id) if target_srv else target_id
                for s in services_list:
                    if s.get("id") == dragged_id:
                        s["parent_id"] = real_parent_id
                        break
                save_services_registry(registry)
            elif action == "ungroup" and dragged_id:
                for s in services_list:
                    if s.get("id") == dragged_id:
                        s["parent_id"] = None
                        break
                save_services_registry(registry)

            launchpad_data = MONITOR.get_launchpad_state()
            self._send_json({"ok": True, "message": "文件夹分组已更新", "launchpad": launchpad_data})
            return

        if parsed.path == "/api/launchpad/service/start":
            target_id = body.get("id")
            target_port = body.get("port")
            cmd = body.get("command", "").strip()
            cwd = body.get("cwd", "").strip()

            registry = load_services_registry()
            target_service = None
            for s in registry.get("services", []):
                if target_id and s.get("id") == target_id:
                    target_service = s
                    break
                if target_port and int(s.get("port") or 0) == int(target_port):
                    target_service = s
                    break

            if target_service:
                if not cmd:
                    cmd = target_service.get("command", "").strip()
                if not cwd or cwd == str(BASE_DIR):
                    cwd = target_service.get("cwd", "").strip()
                if not target_port:
                    target_port = target_service.get("port")

            # 兼容纠偏：若命令仍为过时的 pnpm dev，智能更正为 npm run dev
            if cmd == "pnpm dev" and target_port and int(target_port) == 3000:
                cmd = "npm run dev"
                if target_service:
                    target_service["command"] = cmd
                    save_services_registry(registry)

            if not cmd:
                self._send_json({"ok": False, "message": "该服务尚未配置启动命令，请先编辑填写启动命令"}, 400)
                return

            p_num = int(target_port) if target_port else None

            # 若端口目前已在监听中，直接打开浏览器并返回
            if p_num and is_port_listening(p_num):
                try:
                    webbrowser.open(f"http://127.0.0.1:{p_num}/")
                except Exception:
                    pass
                self._send_json({
                    "ok": True,
                    "message": f"端口 :{p_num} 服务当前已在运行中，已为您在浏览器中打开网页！",
                    "already_running": True,
                    "url": f"http://127.0.0.1:{p_num}/"
                })
                return

            service_title = (target_service.get("name") if target_service else None) or (f"服务 :{p_num}" if p_num else "服务")
            ok, pid, msg = launch_service_cmd(cmd, cwd, title=service_title, port=p_num, auto_open=True)
            if ok:
                time.sleep(1.0)
                MONITOR.collect_once()
                with MONITOR.lock:
                    snapshot = dict(MONITOR.state)
                snapshot["launchpad"] = MONITOR.get_launchpad_state()
                self._send_json({
                    "ok": True,
                    "message": msg,
                    "pid": pid,
                    "port": p_num,
                    "url": f"http://127.0.0.1:{p_num}/" if p_num else None,
                    "data": snapshot
                })
            else:
                self._send_json({"ok": False, "message": msg}, 500)
            return

        if parsed.path == "/api/launchpad/service/stop":
            target_id = body.get("id")
            target_port = body.get("port")
            target_pid = body.get("pid")

            if not target_port and target_id:
                registry = load_services_registry()
                for s in registry.get("services", []):
                    if s.get("id") == target_id:
                        target_port = s.get("port")
                        break

            if target_port and int(target_port) == PORT:
                self._send_json({"ok": False, "message": "不能停止监控台自身进程"}, 400)
                return

            kill_pid = None
            if target_pid:
                kill_pid = int(target_pid)
            elif target_port:
                p_num = int(target_port)
                with MONITOR.lock:
                    all_p = list(MONITOR.state.get("all_ports", []))
                for item in all_p:
                    if item.get("port") == p_num:
                        kill_pid = item.get("pid")
                        break

            if kill_pid:
                res = subprocess.run(
                    ["taskkill", "/F", "/PID", str(kill_pid)],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                msg = f"已停止进程 (PID {kill_pid})"
            elif target_port and PORTS_EXE.exists():
                subprocess.run(
                    [str(PORTS_EXE), "kill", "--force", str(int(target_port))],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                msg = f"已释放端口 {target_port}"
            else:
                self._send_json({"ok": False, "message": "未找到正在运行的目标进程"}, 404)
                return

            time.sleep(0.6)
            MONITOR.collect_once()
            with MONITOR.lock:
                snapshot = dict(MONITOR.state)
            snapshot["launchpad"] = MONITOR.get_launchpad_state()
            self._send_json({"ok": True, "message": msg, "data": snapshot})
            return

        if parsed.path == "/api/launchpad/task/save":
            task_data = body.get("task") or {}
            tid = task_data.get("id") or f"task_{int(time.time()*1000)}"
            task_data["id"] = tid
            registry = load_services_registry()
            found = False
            for idx, t in enumerate(registry.get("tasks", [])):
                if t.get("id") == tid:
                    registry["tasks"][idx] = task_data
                    found = True
                    break
            if not found:
                registry["tasks"].append(task_data)
            save_services_registry(registry)
            launchpad_data = MONITOR.get_launchpad_state()
            self._send_json({"ok": True, "message": f"批处理任务「{task_data.get('name')}」已保存", "launchpad": launchpad_data})
            return

        if parsed.path == "/api/launchpad/task/delete":
            tid = body.get("id")
            registry = load_services_registry()
            registry["tasks"] = [t for t in registry.get("tasks", []) if t.get("id") != tid]
            save_services_registry(registry)
            launchpad_data = MONITOR.get_launchpad_state()
            self._send_json({"ok": True, "message": "已删除该批处理任务", "launchpad": launchpad_data})
            return

        if parsed.path == "/api/launchpad/task/run":
            task_id = body.get("id")
            registry = load_services_registry()
            target_task = None
            for t in registry.get("tasks", []):
                if t.get("id") == task_id:
                    target_task = t
                    break
            if not target_task:
                self._send_json({"ok": False, "message": "未找到指定批处理任务"}, 404)
                return

            cmd = target_task.get("command", "").strip()
            cwd = target_task.get("cwd", "").strip()
            if not cmd:
                self._send_json({"ok": False, "message": "未配置执行命令"}, 400)
                return

            ok, pid, msg = launch_service_cmd(cmd, cwd)
            target_task["last_run"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            target_task["last_status"] = "success" if ok else "failed"
            save_services_registry(registry)

            launchpad_data = MONITOR.get_launchpad_state()
            self._send_json({"ok": ok, "message": msg if ok else f"执行失败: {msg}", "launchpad": launchpad_data})
            return

        if parsed.path == "/api/launchpad/import-detected":
            registry = load_services_registry()
            existing_ports = {int(s.get("port") or 0) for s in registry.get("services", [])}
            added_count = 0
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with MONITOR.lock:
                all_candidates = list(MONITOR.state.get("dev_ports", [])) + list(MONITOR.state.get("history_ports", []))

            seen_p = set()
            for item in all_candidates:
                p_val = int(item.get("port") or 0)
                if p_val and p_val not in existing_ports and p_val not in seen_p:
                    seen_p.add(p_val)
                    name = item.get("alias") or item.get("project") or f"服务 :{p_val}"
                    category = "Python 后端" if "python" in (item.get("framework") or "").lower() else ("Web 前端" if "node" in (item.get("framework") or "").lower() or "vite" in (item.get("framework") or "").lower() else "开发服务")
                    icon = "📚" if "study" in name.lower() or "题库" in name else ("🚀" if "clash" in name.lower() or "vpn" in name.lower() else ("🤖" if "gemini" in name.lower() or "ai" in name.lower() else "⚡"))
                    registry["services"].append({
                        "id": f"srv_{p_val}_{int(time.time())}",
                        "name": name,
                        "category": category,
                        "port": p_val,
                        "command": item.get("command") or "",
                        "cwd": item.get("cwd") or "",
                        "framework": item.get("framework") or "-",
                        "icon": icon,
                        "created_at": now_str,
                        "updated_at": now_str,
                    })
                    added_count += 1

            if added_count > 0:
                save_services_registry(registry)
                MONITOR.collect_once()

            launchpad_data = MONITOR.get_launchpad_state()
            self._send_json({"ok": True, "message": f"成功导入 {added_count} 个服务", "data": MONITOR.state, "launchpad": launchpad_data})
            return

        if parsed.path in ("/api/open", "/api/open-folder", "/api/open-path"):
            target_port = body.get("port")
            target_pid = body.get("pid")
            target_path = str(body.get("path") or "").strip()
            select_target = bool(body.get("select", True))
            force_explorer = bool(body.get("force_explorer", False))

            resolved_path = ""

            # 1. 优先根据 target_port 从当前监听状态精准提取 CWD
            if target_port:
                try:
                    p_num = int(target_port)
                    with MONITOR.lock:
                        all_p = list(MONITOR.state.get("all_ports", [])) + list(MONITOR.state.get("dev_ports", []))
                    for item in all_p:
                        if item.get("port") == p_num and item.get("cwd") and item.get("cwd") != "-":
                            cand = item["cwd"]
                            if os.path.exists(cand):
                                resolved_path = cand
                                break
                except Exception:
                    pass

            # 2. 若未根据 port 解析出，或提供了 pid，则从 pid 解析
            if not resolved_path and target_pid:
                try:
                    pid_val = int(target_pid)
                    with MONITOR.lock:
                        procs = list(MONITOR.state.get("dev_processes", [])) + list(MONITOR.state.get("dev_ports", []))
                    for item in procs:
                        if item.get("pid") == pid_val and item.get("cwd") and item.get("cwd") != "-":
                            cand = item["cwd"]
                            if os.path.exists(cand):
                                resolved_path = cand
                                break
                    if not resolved_path:
                        c = resolve_process_cwd(pid_val)
                        if c and os.path.exists(c):
                            resolved_path = c
                except Exception:
                    pass

            # 3. 若前端提供了明确路径且该路径存在，使用该路径
            if not resolved_path and target_path and target_path != "-":
                if os.path.exists(target_path):
                    resolved_path = target_path
                else:
                    # 容灾：前端 JS 字符串转义可能丢失了反斜杠（如 "C:workspaceapp"），若带有 pid 则通过内核 PEB 纠正
                    if target_pid:
                        try:
                            c = resolve_process_cwd(int(target_pid))
                            if c and os.path.exists(c):
                                resolved_path = c
                        except Exception:
                            pass

            if not resolved_path:
                msg = f"目录或文件不存在: {target_path or ('PID ' + str(target_pid) if target_pid else 'Port ' + str(target_port))}"
                self._send_json({"ok": False, "message": msg}, 404)
                return

            ok, msg = open_path_in_file_manager(resolved_path, select=select_target, force_explorer=force_explorer)
            if ok:
                self._send_json({"ok": True, "message": msg, "path": resolved_path, "has_dopus": bool(find_dopusrt())})
            else:
                self._send_json({"ok": False, "message": msg}, 500)
            return

        self.send_error(404, "Not Found")


def main():
    print(f"[Kiri Web] 正在初始化首次端口扫描...")
    MONITOR.collect_once()
    MONITOR.start_background_loops()

    server = ThreadingHTTPServer((HOST, PORT), KiriRequestHandler)
    url = f"http://{HOST}:{PORT}"
    print(f"[Kiri Web] 网页监控台已启动: {url}")

    if "--no-browser" not in sys.argv:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    while True:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n[Kiri Web] 服务已停止。")
            try:
                server.server_close()
            except Exception:
                pass
            break
        except Exception as e:
            print(f"[Kiri Web] 服务请求捕获异常: {e}，正在平滑自愈恢复...", file=sys.stderr)
            time.sleep(1)


if __name__ == "__main__":
    main()
