"""定稿:从实验记录中选出全局最优策略配置,生成 strategy/strategy.json。

选优口径(任务书附录):网格寻优选"样本外表现最好"的组合;
全局选优同样以样本外年化收益最高为标准,并列取夏普更高者。
选优后重新运行样本内/样本外回测,确保 JSON 中的指标与当前代码完全一致。

用法:uv run python scripts/finalize.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backtest.engine import BacktestConfig, run_backtest
from backtest.loader import STOCK_POOL, load_clean
from backtest.optimizer import IN_SAMPLE, OUT_SAMPLE
from backtest.records import COMPARISON_CSV, RECORDS_DIR, log_run
from strategies.base import STRATEGY_REGISTRY
import strategies.meanrev  # noqa: F401
import strategies.multifactor  # noqa: F401
import strategies.trend  # noqa: F401

STRATEGY_JSON = RECORDS_DIR.parent / "strategy" / "strategy.json"


def main() -> None:
    if not COMPARISON_CSV.exists():
        raise SystemExit("未找到 records/对比结果.csv,请先运行 scripts/run_experiments.py")
    cmp_df = pd.read_csv(COMPARISON_CSV, dtype={"code": str, "params": str})
    cmp_df = cmp_df.drop_duplicates(subset=["strategy", "code", "params"])  # 多轮网格去重

    top = cmp_df.sort_values(["out_annual_return", "out_sharpe"], ascending=False).head(5)
    print("=== 全局最优 TOP5(口径:样本外年化收益最高,并列取夏普)===")
    for _, r in top.iterrows():
        print(f"  {r['strategy']:11s} {r['name']}({r['code']}) {r['params']} "
              f"样本外年化 {r['out_annual_return']:+.2%} 夏普 {r['out_sharpe']:.3f}")

    best = top.iloc[0]
    strategy_name, code = best["strategy"], best["code"]
    params = json.loads(best["params"])

    strategy = STRATEGY_REGISTRY[strategy_name]()
    data = load_clean(code)
    target = strategy.generate_target(data, params)
    in_res = run_backtest(data, target, code=code, start=IN_SAMPLE[0], end=IN_SAMPLE[1], config=BacktestConfig())
    out_res = run_backtest(data, target, code=code, start=OUT_SAMPLE[0], end=OUT_SAMPLE[1], config=BacktestConfig())
    log_run(code, strategy_name, params, "in_sample", *IN_SAMPLE, in_res.metrics)
    log_run(code, strategy_name, params, "out_sample", *OUT_SAMPLE, out_res.metrics)

    def pack(m: dict, sample: str) -> dict:
        start, end = IN_SAMPLE if sample == "in" else OUT_SAMPLE
        return {"start": start, "end": end,
                **{k: m[k] for k in ("days", "total_return", "annual_return",
                                     "max_drawdown", "sharpe", "win_rate", "round_trips")}}

    payload = {
        "strategy": strategy_name,
        "strategy_description": strategy.description,
        "stock": code,
        "stock_name": STOCK_POOL[code],
        "params": params,
        "in_sample": pack(in_res.metrics, "in"),
        "out_sample": pack(out_res.metrics, "out"),
        "selection_rule": "网格寻优遍历全部参数组合,按任务书附录口径选样本外表现最好的组合"
                          "(样本外年化收益最高,并列取夏普更高者);全局选优同口径。",
        "data_source": "官方数据包未到位期间采用 BaoStock 前复权日线(2019-01-01~2024-12-31),"
                       "来源注明见 data/raw/baostock/来源说明.txt;官方数据到位后以官方数据为准并重新验证。",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "engine_rules": "信号当日收盘计算、次日开盘价成交;T+1;开盘触涨跌停不成交;停牌不可交易;"
                        "佣金万2.5(最低5元)+ 卖出印花税万5;初始资金 100 万;整手交易。",
    }
    STRATEGY_JSON.parent.mkdir(parents=True, exist_ok=True)
    STRATEGY_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n最优配置已写入 {STRATEGY_JSON}")
    print(json.dumps(payload, ensure_ascii=False, indent=2)[:600] + "\n...")


if __name__ == "__main__":
    main()
