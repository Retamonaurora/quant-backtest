"""批量实验:策略 × 股票 × 参数网格 逐一网格寻优,实验记录自动落盘。

用法:
  uv run python scripts/run_experiments.py                          # 全部策略 × 全部股票
  uv run python scripts/run_experiments.py --strategies meanrev     # 指定策略
  uv run python scripts/run_experiments.py --stocks 600519,000002   # 指定股票

每个 (策略, 股票) 输出最优组合;实验明细见 records/experiments.csv 与 records/对比结果.csv。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backtest.optimizer import grid_search, pretty_params
from backtest.records import count_real_experiments
from backtest.loader import STOCK_POOL
from strategies.base import STRATEGY_REGISTRY
import strategies.trend  # noqa: F401
import strategies.meanrev  # noqa: F401
try:
    import strategies.multifactor  # noqa: F401
except ImportError:  # 多因子未实现前允许缺省
    pass

# 各策略的默认寻优网格(覆盖常用档位,组合数控制在寻优可承受范围)
GRIDS = {
    "trend": {"fast": [5, 10, 15, 20], "slow": [20, 30, 40, 60]},
    "meanrev": {"window": [15, 20, 25], "num_std": [1.5, 2.0, 2.5]},
    "multifactor": {"mom_window": [10, 20], "vol_window": [10, 20], "buy_th": [0.3, 0.5]},
}


def main() -> None:
    parser = argparse.ArgumentParser(description="批量网格实验")
    parser.add_argument("--strategies", default=None, help="逗号分隔策略名,默认全部")
    parser.add_argument("--stocks", default=None, help="逗号分隔股票代码,默认全部 10 只")
    args = parser.parse_args()

    strategy_names = args.strategies.split(",") if args.strategies else list(GRIDS)
    stock_codes = args.stocks.split(",") if args.stocks else list(STOCK_POOL)
    for s in strategy_names:
        if s not in STRATEGY_REGISTRY:
            raise SystemExit(f"未知策略 {s!r},可用: {list(STRATEGY_REGISTRY)}")

    for s in strategy_names:
        for code in stock_codes:
            df, best = grid_search(s, code, GRIDS[s])
            print(f"[{s}] {STOCK_POOL[code]}({code}): {len(df)} 组合 | 最优 {pretty_params(best['params'])}"
                  f" | 样本外年化 {best['out_annual_return']:+.2%} 夏普 {best['out_sharpe']:.3f}")
        print(f"累计真实变化实验: {count_real_experiments()}")

    print(f"\n完成。实验记录: records/experiments.csv;对比结果: records/对比结果.csv")
    print(f"统计: {count_real_experiments()}")


if __name__ == "__main__":
    main()
