"""绩效图表:净值曲线 vs 沪深300(含回撤子图)。

- plot_nav: 输出 PNG 到 output/(gitignore,可随时重新生成),CLI 使用
- nav_figure_bytes: 返回 PNG 字节流,Flask 报告页内嵌使用
"""

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from backtest.loader import PROJECT_DIR  # noqa: E402

OUTPUT_DIR = PROJECT_DIR / "output"

# 图内中文:Windows 优先微软雅黑,退回黑体
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

STRAT_COLOR = "#c0392b"
BENCH_COLOR = "#7f8c8d"


def _nav_figure(nav: pd.Series, benchmark_close: pd.Series, title: str):
    bench = benchmark_close.reindex(nav.index).ffill()
    strat = nav / nav.iloc[0]
    bench = bench / bench.iloc[0]
    dd = 1 - nav / nav.cummax()

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(10, 6), sharex=True, height_ratios=[3, 1], gridspec_kw={"hspace": 0.08}
    )
    ax1.plot(strat.index, strat.values, label="策略净值", color=STRAT_COLOR, lw=1.4)
    ax1.plot(bench.index, bench.values, label="沪深300", color=BENCH_COLOR, lw=1.1)
    ax1.set_title(title, fontsize=12)
    ax1.legend(loc="upper left", fontsize=9)
    ax1.grid(alpha=0.3)
    ax1.set_ylabel("净值(期初=1)")

    ax2.fill_between(dd.index, dd.values, 0, color=STRAT_COLOR, alpha=0.35)
    ax2.set_ylabel("回撤")
    ax2.grid(alpha=0.3)
    return fig


def plot_nav(nav: pd.Series, benchmark_close: pd.Series, title: str, out_name: str) -> str:
    """绘制并保存净值对比图,返回输出文件相对路径。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / out_name
    fig = _nav_figure(nav, benchmark_close, title)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(out_path.relative_to(PROJECT_DIR))


def nav_figure_bytes(nav: pd.Series, benchmark_close: pd.Series, title: str) -> bytes:
    """绘制净值对比图并返回 PNG 字节(报告页内嵌)。"""
    fig = _nav_figure(nav, benchmark_close, title)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()
