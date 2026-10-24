"""舆情三因子接口测试(合成数据)。

用例:
  A 向后兼容   :w_sent=0 默认路径在无舆情列的行情上,最优配置样本外指标与 strategy.json 逐位一致
  B 加载与对齐 :mock 舆情可加载、长度与交易日对齐、load_clean 附加 sentiment 列
  C 三因子回测 :w_sent>0 端到端跑通,状态机两态均出现
  D 错误路径   :w_sent>0 但行情无舆情列 -> 明确报错;权重和不等于 1 -> 明确报错
  E 去重键归一 :新增默认参数(None/0)不影响历史实验去重键

用法:uv run python scripts/test_sentiment.py(全部 PASS 退出码 0)
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backtest.engine import BacktestConfig, run_backtest
from backtest.loader import load_clean
from backtest.records import _params_key
from backtest.sentiment import load_sentiment
from strategies.base import STRATEGY_REGISTRY
import strategies.multifactor  # noqa: F401  触发注册

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if not ok:
        FAILURES.append(f"{name}: {detail}")
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""))


def case_a_compat() -> None:
    print("用例 A:向后兼容(w_sent=0 默认路径,无舆情列)")
    payload = json.loads((Path(__file__).resolve().parents[1] / "strategy" / "strategy.json").read_text(encoding="utf-8"))
    code = payload["stock"]
    data = load_clean(code)  # 不带舆情
    strategy = STRATEGY_REGISTRY["multifactor"]()
    target = strategy.generate_target(data, payload["params"])
    res = run_backtest(data, target, code=code, start="2023-01-01", end="2024-12-31", config=BacktestConfig())
    diff = abs(res.metrics["annual_return"] - payload["out_sample"]["annual_return"])
    check("A 样本外年化与 strategy.json 逐位一致", diff < 1e-12, f"diff={diff:.2e}")


def case_b_load() -> None:
    print("用例 B:mock 舆情加载与对齐")
    s = load_sentiment("600900", source="mock")
    check("B mock 数据存在", s is not None)
    data = load_clean("600900", sentiment="mock")
    check("B sentiment 列已并入", "sentiment" in data.columns)
    check("B 长度与交易日对齐", len(data["sentiment"]) == len(data))
    check("B 无缺失(对齐后)", bool(data["sentiment"].notna().all()))
    check("B 索引一致", bool((data["sentiment"].index == data.index).all()))


def case_c_three_factor() -> None:
    print("用例 C:三因子(w_sent=0.2)端到端回测")
    data = load_clean("600900", sentiment="mock")
    params = {"mom_window": 20, "vol_window": 20, "z_window": 60,
              "buy_th": 0.3, "sell_th": -0.3, "w_mom": 0.4, "w_vol": 0.4, "w_sent": 0.2}
    strategy = STRATEGY_REGISTRY["multifactor"]()
    target = strategy.generate_target(data, params)
    res = run_backtest(data, target, code="600900", start="2019-01-01", end="2024-12-31", config=BacktestConfig())
    window_len = len(data.loc["2019-01-01":"2024-12-31"])
    check("C 回测产出净值(=回测窗口长度)", len(res.nav) == window_len, f"{len(res.nav)} vs {window_len}")
    check("C 两态均出现", target.isin([0, 1]).all() and target.nunique() == 2)
    check("C 交易回合 > 0", res.metrics["round_trips"] > 0, f"round_trips={res.metrics['round_trips']}")


def case_d_errors() -> None:
    print("用例 D:错误路径")
    strategy = STRATEGY_REGISTRY["multifactor"]()
    data_no_sent = load_clean("600900")
    try:
        strategy.generate_target(data_no_sent, {"mom_window": 20, "vol_window": 20, "z_window": 60,
                                                "buy_th": 0.3, "sell_th": -0.3,
                                                "w_mom": 0.4, "w_vol": 0.4, "w_sent": 0.2})
        check("D 无舆情列时明确报错", False, "未抛异常")
    except ValueError as exc:
        check("D 无舆情列时明确报错", "舆情数据列" in str(exc))
    try:
        strategy.generate_target(load_clean("600900", sentiment="mock"),
                                 {"mom_window": 20, "vol_window": 20, "z_window": 60,
                                  "buy_th": 0.3, "sell_th": -0.3, "w_mom": 0.5, "w_sent": 0.2})
        check("D 权重和不等于 1 时明确报错", False, "未抛异常")
    except ValueError as exc:
        check("D 权重和不等于 1 时明确报错", "w_mom+w_vol+w_sent=1" in str(exc))


def case_e_dedup() -> None:
    print("用例 E:实验去重键归一化(新增默认参数不影响历史键)")
    old = {"mom_window": 20, "vol_window": 20, "z_window": 60, "buy_th": 0.5, "sell_th": -0.3, "w_mom": 0.5}
    new = {**old, "w_vol": None, "w_sent": 0.0}
    check("E 历史键不受新增默认参数影响", _params_key(new) == _params_key(old))
    sent = {**old, "w_vol": 0.4, "w_sent": 0.2}
    check("E 舆情实验键不同于历史键", _params_key(sent) != _params_key(old))


def main() -> None:
    case_a_compat()
    case_b_load()
    case_c_three_factor()
    case_d_errors()
    case_e_dedup()
    print()
    if FAILURES:
        print(f"共 {len(FAILURES)} 项失败:")
        for f in FAILURES:
            print("  FAIL", f)
        sys.exit(1)
    print("全部用例 PASS,舆情三因子接口验证通过。")


if __name__ == "__main__":
    main()
