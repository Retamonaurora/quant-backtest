"""打包提交压缩包:「姓名-A股量化回测系统.zip」(根目录=项目根目录,勿多套一层)。

包含:全部源码与文档、data/、strategy/、records/、demo/、.git 提交历史(任务书要求)。
排除:.venv、output、__pycache__、PLAN.md 等本地开发文件。
产出校验:任务书要求的材料齐全、排除项未泄漏、.git 在内。

用法:uv run python scripts/package.py [--name 姓名] [--out 输出路径]
默认产出 C:/Users/<用户>/Desktop/zhb-A股量化回测系统.zip
"""

import argparse
import os
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]

EXCLUDE_DIRS = {".venv", "output", "__pycache__", ".pytest_cache", ".idea", ".vscode"}
EXCLUDE_FILES = {"PLAN.md"}
EXCLUDE_SUFFIXES = (".pyc", ".log")

REQUIRED = [
    "启动.bat", "main.py", "app.py", "requirements.txt", "README.md", "ai_log.md",
    "提交信息.txt", "strategy/strategy.json", "records/experiments.csv",
    "records/对比结果.csv", "data/report/validation_report.md",
]


def build(out: Path) -> None:
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(PROJECT):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for f in files:
                if f in EXCLUDE_FILES or f.endswith(EXCLUDE_SUFFIXES):
                    continue
                p = Path(root) / f
                zf.write(p, p.relative_to(PROJECT))
                n += 1
    print(f"打包完成: {out}")
    print(f"文件数 {n},大小 {out.stat().st_size / 1e6:.1f} MB")

    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
    missing = [f for f in REQUIRED if f not in names]
    assert not missing, f"缺失必需材料: {missing}"
    assert any(x.startswith(".git/") for x in names), "缺少 .git 提交历史"
    leaked = [f for f in names if f == "PLAN.md" or f.startswith((".venv/", "output/"))]
    assert not leaked, f"排除项泄漏: {leaked}"
    print("压缩包校验通过:必需材料齐全、.git 历史在内、本地开发文件未泄漏")


def main() -> None:
    parser = argparse.ArgumentParser(description="打包提交压缩包")
    parser.add_argument("--name", default="zhb", help="压缩包文件名中的姓名")
    parser.add_argument("--out", default=None, help="输出路径,默认桌面")
    args = parser.parse_args()
    out = Path(args.out) if args.out else Path.home() / "Desktop" / f"{args.name}-A股量化回测系统.zip"
    build(out)


if __name__ == "__main__":
    main()
