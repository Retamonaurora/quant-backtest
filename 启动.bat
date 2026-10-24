@echo off
chcp 65001 >nul
cd /d %~dp0
if not exist .venv\Scripts\python.exe (
    echo [首次运行] 未发现虚拟环境,正在安装依赖 ^(uv sync^)...
    where uv >nul 2>nul
    if errorlevel 1 (
        echo 未检测到 uv,请先阅读 README.md 安装 uv 后重试。
        pause
        exit /b 1
    )
    uv sync
)
start "" http://127.0.0.1:5000
.venv\Scripts\python.exe app.py
pause
