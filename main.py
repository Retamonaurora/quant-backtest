"""A股量化回测系统 —— CLI 入口(骨架)。

后续按 PLAN.md 实现 backtest / optimize / validate 子命令。
"""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="A股量化回测系统")
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    args = parser.parse_args()
    print("A股量化回测系统骨架已就绪,功能开发中(见 PLAN.md 排期)。")


if __name__ == "__main__":
    main()
