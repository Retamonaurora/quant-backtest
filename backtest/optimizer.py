"""网格寻优:遍历参数组合,样本内/样本外分别回测,输出最优参数组。

口径(与任务书一致):
- 样本内(调参):2019-01-01 ~ 2022-12-31;样本外(检验):2023-01-01 ~ 2024-12-31
- 任务书附录定义"选样本外表现最好的组合":以样本外年化收益最高选优,
  并列时取夏普更高者。选优口径在 README 与 strategy.json 中注明。
- 信号在全量清洗数据上计算(指标均为后视滚动量,无未来函数),引擎按区间切片回测,
  保证样本内外采用一致的指标预热期。
"""

import itertools
import json
from datetime import datetime

import pandas as pd

from backtest.engine import BacktestConfig, run_backtest
from backtest.loader import STOCK_POOL, load_clean
from backtest.records import log_comparison, log_run
from strategies.base import STRATEGY_REGISTRY

IN_SAMPLE = ("2019-01-01", "2022-12-31")
OUT_SAMPLE = ("2023-01-01", "2024-12-31")


def expand_grid(param_grid: dict[str, list]) -> list[dict]:
    keys = list(param_grid)
    return [dict(zip(keys, combo)) for combo in itertools.product(*(param_grid[k] for k in keys))]


def grid_search(strategy_name: str, code: str, param_grid: dict[str, list],
                log: bool = True) -> tuple[pd.DataFrame, dict]:
    """网格寻优。返回 (对比结果 DataFrame, 最优组合 dict)。"""
    strategy = STRATEGY_REGISTRY[strategy_name]()
    data = load_clean(code)
    rows: list[dict] = []
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    for params in expand_grid(param_grid):
        full_params = {**strategy.default_params, **params}
        try:
            target = strategy.generate_target(data, full_params)
        except ValueError:
            continue  # 非法组合(如 fast>=slow)跳过
        in_m = run_backtest(data, target, code=code, start=IN_SAMPLE[0], end=IN_SAMPLE[1],
                            config=BacktestConfig()).metrics
        out_m = run_backtest(data, target, code=code, start=OUT_SAMPLE[0], end=OUT_SAMPLE[1],
                             config=BacktestConfig()).metrics
        if log:
            log_run(code, strategy_name, full_params, "in_sample", *IN_SAMPLE, in_m)
            log_run(code, strategy_name, full_params, "out_sample", *OUT_SAMPLE, out_m)
        rows.append({
            "run_id": run_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "code": code, "name": STOCK_POOL[code], "strategy": strategy_name,
            "params": full_params,
            "in_annual_return": in_m["annual_return"], "in_max_drawdown": in_m["max_drawdown"],
            "in_sharpe": in_m["sharpe"], "in_win_rate": in_m["win_rate"],
            "out_annual_return": out_m["annual_return"], "out_max_drawdown": out_m["max_drawdown"],
            "out_sharpe": out_m["sharpe"], "out_win_rate": out_m["win_rate"],
        })

    if not rows:
        raise SystemExit("网格内没有合法参数组合")

    df = pd.DataFrame(rows)
    # 任务书附录口径:选样本外表现最好的组合(样本外年化最高,并列取夏普高者)
    df = df.sort_values(["out_annual_return", "out_sharpe"], ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1
    if log:
        out = df.copy()
        out["params"] = out["params"].apply(lambda p: json.dumps(p, ensure_ascii=False))
        log_comparison(out.to_dict("records"), run_id)
    best = df.iloc[0].to_dict()
    return df, best


def pretty_params(params: dict) -> str:
    return ", ".join(f"{k}={v}" for k, v in params.items())
