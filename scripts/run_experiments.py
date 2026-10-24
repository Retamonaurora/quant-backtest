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
    # 舆情三因子:multifactor_sent 是别名,策略仍为 multifactor,行情附加舆情列
    "multifactor_sent": {"mom_window": [20], "vol_window": [20], "buy_th": [0.3, 0.5],
                         "w_mom": [0.4], "w_vol": [0.4], "w_sent": [0.2, 0.4]},
}

# 别名 -> (真实策略名, 舆情数据源, 是否落正式实验记录)
# mock 为合成数据,实验不落正式 records(避免污染);官方数据到位后改为
# "multifactor_sent": ("multifactor", "official", True) 再跑真实舆情实验
ALIASES = {"multifactor_sent": ("multifactor", "mock", False)}


def main() -> None:
    parser = argparse.ArgumentParser(description="批量网格实验")
    parser.add_argument("--strategies", default=None, help="逗号分隔策略名,默认全部")
    parser.add_argument("--stocks", default=None, help="逗号分隔股票代码,默认全部 10 只")
    args = parser.parse_args()

    strategy_names = args.strategies.split(",") if args.strategies else list(GRIDS)
    stock_codes = args.stocks.split(",") if args.stocks else list(STOCK_POOL)
    for s in strategy_names:
        if s not in GRIDS:
            raise SystemExit(f"未知策略 {s!r},可用: {list(GRIDS)}")

    for s in strategy_names:
        real_name, sentiment, log = ALIASES.get(s, (s, None, True))
        for code in stock_codes:
            df, best = grid_search(real_name, code, GRIDS[s], log=log, sentiment=sentiment)
            tag = f"[{s}]" if sentiment is None else f"[{s} @{sentiment}]"
            print(f"{tag} {STOCK_POOL[code]}({code}): {len(df)} 组合 | 最优 {pretty_params(best['params'])}"
                  f" | 样本外年化 {best['out_annual_return']:+.2%} 夏普 {best['out_sharpe']:.3f}")
        print(f"累计真实变化实验: {count_real_experiments()}")

    print(f"\n完成。实验记录: records/experiments.csv;对比结果: records/对比结果.csv")
    print(f"统计: {count_real_experiments()}")


if __name__ == "__main__":
    main()
