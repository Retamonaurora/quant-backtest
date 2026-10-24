"""A股量化回测系统 —— CLI 入口。

子命令:
  backtest  单次回测:uv run python main.py backtest --strategy trend --stock 600519 \
              --start 2019-01-01 --end 2024-12-31 --param fast=5 --param slow=20
  validate  数据校验与清洗:uv run python main.py validate
  optimize  网格寻优(见 backtest/optimizer.py):--param-grid fast=5,10,15,20 --param-grid slow=20,30,40,60
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backtest.engine import BacktestConfig, run_backtest
from backtest.loader import BENCHMARK_CODE, BENCHMARK_NAME, STOCK_POOL, load_clean, load_raw_benchmark
from report.render import plot_nav
from strategies.base import STRATEGY_REGISTRY
import strategies.meanrev  # noqa: F401  触发注册
import strategies.multifactor  # noqa: F401  触发注册
import strategies.trend  # noqa: F401  触发注册


def parse_kv(pairs: list[str] | None) -> dict:
    """把 ["fast=5", "slow=20"] 解析成 {"fast": 5, "slow": 20},数值自动转 int/float。"""
    out: dict = {}
    for item in pairs or []:
        if "=" not in item:
            raise ValueError(f"参数格式应为 key=value,得到: {item}")
        k, v = item.split("=", 1)
        try:
            v = int(v)
        except ValueError:
            try:
                v = float(v)
            except ValueError:
                pass
        out[k] = v
    return out


def cmd_backtest(args) -> None:
    if args.strategy not in STRATEGY_REGISTRY:
        raise SystemExit(f"未知策略 {args.strategy!r},可选: {list(STRATEGY_REGISTRY)}")
    if args.stock not in STOCK_POOL:
        raise SystemExit(f"股票代码 {args.stock!r} 不在固定股票池,可选: {list(STOCK_POOL)}")

    strategy = STRATEGY_REGISTRY[args.strategy]()
    params = {**strategy.default_params, **parse_kv(args.param)}
    data = load_clean(args.stock)
    result = run_backtest(data, strategy.generate_target(data, params),
                          code=args.stock, start=args.start, end=args.end, config=BacktestConfig())

    m = result.metrics
    print(f"\n=== 回测结果 {STOCK_POOL[args.stock]} ({args.stock}) | {args.strategy} {params} ===")
    print(f"区间: {result.nav.index[0].date()} ~ {result.nav.index[-1].date()}  共 {m['days']} 个交易日")
    print(f"总收益: {m['total_return']:+.2%}   年化: {m['annual_return']:+.2%}")
    print(f"最大回撤: {m['max_drawdown']:.2%}   夏普: {m['sharpe']:.3f}")
    print(f"胜率: {m['win_rate']:.2%}   完整回合: {m['round_trips']}")

    bench = load_raw_benchmark()["close"]
    title = f"{STOCK_POOL[args.stock]} {args.strategy} {json.dumps(params, ensure_ascii=False)} 净值曲线"
    out_name = f"nav_{args.stock}_{args.strategy}_{args.start}_{args.end}.png"
    chart = plot_nav(result.nav, bench, title, out_name)
    print(f"净值图: {chart}")


def cmd_validate(_args) -> None:
    import scripts.prepare_data as prep

    prep.main()


def cmd_optimize(args) -> None:
    from backtest.optimizer import IN_SAMPLE, OUT_SAMPLE, grid_search, pretty_params

    if args.strategy not in STRATEGY_REGISTRY:
        raise SystemExit(f"未知策略 {args.strategy!r},可选: {list(STRATEGY_REGISTRY)}")
    if args.stock not in STOCK_POOL:
        raise SystemExit(f"股票代码 {args.stock!r} 不在固定股票池,可选: {list(STOCK_POOL)}")

    grid: dict[str, list] = {}
    for item in args.param_grid or []:
        if "=" not in item:
            raise SystemExit(f"--param-grid 格式应为 key=v1,v2,...,得到: {item}")
        k, vals = item.split("=", 1)
        grid[k] = [int(v) if v.isdigit() else float(v) for v in vals.split(",")]

    df, best = grid_search(args.strategy, args.stock, grid)
    print(f"\n=== 网格寻优 {STOCK_POOL[args.stock]} ({args.stock}) | {args.strategy} | {len(df)} 组合 ===")
    print(f"样本内: {IN_SAMPLE[0]} ~ {IN_SAMPLE[1]}   样本外: {OUT_SAMPLE[0]} ~ {OUT_SAMPLE[1]}")
    print(f"选优口径: 样本外年化收益最高(任务书附录),并列取夏普高者\n")
    cols = ["rank", "params", "in_annual_return", "in_max_drawdown", "out_annual_return",
            "out_max_drawdown", "out_sharpe", "out_win_rate"]
    show = df[cols].copy()
    show["params"] = show["params"].apply(pretty_params)
    for c in cols[2:]:
        show[c] = show[c].map(lambda x: f"{x:.2%}" if "return" in c or "drawdown" in c or "rate" in c else f"{x:.3f}")
    print(show.to_string(index=False))
    print(f"\n最优组合: {pretty_params(best['params'])}  "
          f"(样本外年化 {best['out_annual_return']:+.2%}, 夏普 {best['out_sharpe']:.3f})")
    print("对比结果已追加至 records/对比结果.csv;实验记录见 records/experiments.csv")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="A股量化回测系统")
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    sub = parser.add_subparsers(dest="command", required=True)

    p_bt = sub.add_parser("backtest", help="单次回测(策略/参数/起止日期)")
    p_bt.add_argument("--strategy", required=True, help=f"策略名: {list(STRATEGY_REGISTRY)}")
    p_bt.add_argument("--stock", required=True, help=f"股票代码: {list(STOCK_POOL)}")
    p_bt.add_argument("--start", default=None, help="起始日期 YYYY-MM-DD")
    p_bt.add_argument("--end", default=None, help="结束日期 YYYY-MM-DD")
    p_bt.add_argument("--param", action="append", help="策略参数 key=value,可重复")
    p_bt.set_defaults(func=cmd_backtest)

    p_val = sub.add_parser("validate", help="数据校验与清洗,产出校验报告与 cleaned 数据")
    p_val.set_defaults(func=cmd_validate)

    p_opt = sub.add_parser("optimize", help="网格寻优(样本内/外切分,输出最优参数组)")
    p_opt.add_argument("--strategy", required=True, help=f"策略名: {list(STRATEGY_REGISTRY)}")
    p_opt.add_argument("--stock", required=True, help=f"股票代码: {list(STOCK_POOL)}")
    p_opt.add_argument("--param-grid", action="append", help="参数网格 key=v1,v2,...,可重复")
    p_opt.set_defaults(func=cmd_optimize)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
