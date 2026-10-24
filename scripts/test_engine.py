"""回测引擎手工对账测试(SOP 验收:每笔交易可手算核对)。

用例(期望值均为人工推算,写死在断言里):
  A 基础买卖  :整手递减、双边佣金、卖出印花税、回合盈亏、净值,全部手算核对
  B 涨停禁买  :执行日开盘=涨停价 -> 买入不成交,指令作废,次日重新按信号执行
  C 停牌禁交易:tradable=0 不撮合,复牌后成交
  D 跌停禁卖  :开盘=跌停价 -> 卖出不成交,次日执行;亏损回合 -> 胜率 0
  E 信号时序  :T 日信号必须 T+1 开盘才成交(反未来函数),全量断言卖出日 > 买入日
  F 真实数据  :600519 前 10 日买入后清仓,成交价与 cleaned CSV 开盘价逐项核对

用法:uv run python scripts/test_engine.py(全部 PASS 退出码 0)
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backtest.engine import BacktestConfig, run_backtest
from backtest.loader import load_clean

FAILURES: list[str] = []


def check(name: str, actual, expected) -> None:
    ok = actual == expected
    if not ok:
        FAILURES.append(f"{name}: 期望 {expected!r}, 实际 {actual!r}")
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {actual!r}" + ("" if ok else f"  (期望 {expected!r})"))


def make_data(rows: list[dict]) -> pd.DataFrame:
    """rows: 每日 dict(date, open, high, low, close, preclose, tradable[, volume, amount])"""
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    df["volume"] = df.get("volume", 1_000_000.0)
    df["amount"] = df.get("amount", df["volume"] * df["close"])
    return df[["open", "high", "low", "close", "preclose", "volume", "amount", "tradable"]]


def target_series(dates, values: dict[str, int]) -> pd.Series:
    return pd.Series([values.get(str(d.date()), 0) for d in dates], index=dates)


def case_a_basic() -> None:
    print("用例 A:基础买卖(费用/整手/净值 手算核对)")
    data = make_data([
        dict(date="2024-01-02", open=10.00, high=10.50, low=9.80, close=10.20, preclose=9.90, tradable=1),
        dict(date="2024-01-03", open=10.00, high=10.60, low=9.95, close=10.40, preclose=10.20, tradable=1),
        dict(date="2024-01-04", open=10.55, high=10.90, low=10.30, close=10.80, preclose=10.40, tradable=1),
        dict(date="2024-01-05", open=10.90, high=11.00, low=10.70, close=10.95, preclose=10.80, tradable=1),
    ])
    tgt = target_series(data.index, {"2024-01-02": 1, "2024-01-03": 0})
    res = run_backtest(data, tgt, code="TEST")
    buy, sell = res.trades.iloc[0], res.trades.iloc[1]
    # 手算:买入 100 万 -> 1000 手超预算 -> 99900 股,成本 999000,佣金 max(249.75,5)=249.75,余 750.25
    check("A 买入日期=信号次日", str(res.trades.index[0].date()), "2024-01-03")
    check("A 买入股数", int(buy["shares"]), 99_900)
    check("A 买入佣金", float(buy["commission"]), 249.75)
    check("A 买后现金", float(buy["cash_after"]), 750.25)
    # 手算:卖出 99900x10.55=1,053,945,佣金 263.49,印花税 526.97,净得 1,053,154.54
    #      pnl = 1,053,154.54 - 999,249.75 = 53,904.79;期末现金 = 750.25 + 1,053,154.54 = 1,053,904.79
    check("A 卖出日期", str(res.trades.index[1].date()), "2024-01-04")
    check("A 卖出佣金", float(sell["commission"]), 263.49)
    check("A 印花税", float(sell["stamp_tax"]), 526.97)
    check("A 回合盈亏", float(sell["pnl"]), 53_904.79)
    check("A 期末净值(=全现金)", float(res.nav.iloc[-1]), 1_053_904.79)
    check("A 胜率", res.metrics["win_rate"], 1.0)


def case_b_limit_up() -> None:
    print("用例 B:开盘涨停禁买(前收10.00 -> 涨停价11.00)")
    data = make_data([
        dict(date="2024-01-02", open=10.00, high=10.20, low=9.90, close=10.00, preclose=9.90, tradable=1),
        dict(date="2024-01-03", open=11.00, high=11.00, low=11.00, close=11.00, preclose=10.00, tradable=1),  # 一字涨停
        dict(date="2024-01-04", open=11.10, high=11.50, low=11.00, close=11.30, preclose=11.00, tradable=1),
    ])
    tgt = target_series(data.index, {"2024-01-02": 1, "2024-01-03": 1, "2024-01-04": 1})
    res = run_backtest(data, tgt, code="TEST")
    # 涨停日不成交且指令作废;T2 收盘信号仍为 1 -> T3 开盘 11.10 成交:
    # 900 手 = 90000 股,成本 999000,佣金 249.75,余 750.25
    check("B 仅成交一次", len(res.trades), 1)
    check("B 成交日期避开涨停日", str(res.trades.index[0].date()), "2024-01-04")
    check("B 成交股数", int(res.trades.iloc[0]["shares"]), 90_000)
    check("B 成交价", float(res.trades.iloc[0]["price"]), 11.10)


def case_c_suspension() -> None:
    print("用例 C:停牌禁交易,复牌成交")
    data = make_data([
        dict(date="2024-01-02", open=10.00, high=10.10, low=9.90, close=10.00, preclose=9.90, tradable=1),
        dict(date="2024-01-03", open=10.00, high=10.00, low=10.00, close=10.00, preclose=10.00, tradable=0),  # 停牌
        dict(date="2024-01-04", open=10.20, high=10.40, low=10.10, close=10.30, preclose=10.00, tradable=1),
    ])
    tgt = target_series(data.index, {"2024-01-02": 1, "2024-01-03": 1, "2024-01-04": 1})
    res = run_backtest(data, tgt, code="TEST")
    # 复牌日开盘 10.20:980 手 = 98000 股,成本 999600,佣金 249.90,余 150.10
    check("C 仅成交一次", len(res.trades), 1)
    check("C 成交日期避开停牌日", str(res.trades.index[0].date()), "2024-01-04")
    check("C 买后现金", float(res.trades.iloc[0]["cash_after"]), 150.10)


def case_d_limit_down() -> None:
    print("用例 D:开盘跌停禁卖,次日成交(亏损回合 -> 胜率 0)")
    data = make_data([
        dict(date="2024-01-02", open=10.20, high=10.30, low=10.00, close=10.20, preclose=10.00, tradable=1),
        dict(date="2024-01-03", open=10.00, high=10.10, low=9.90, close=10.00, preclose=10.20, tradable=1),
        dict(date="2024-01-04", open=9.00, high=9.00, low=9.00, close=9.00, preclose=10.00, tradable=1),  # 一字跌停(跌停价9.00)
        dict(date="2024-01-05", open=8.95, high=9.05, low=8.80, close=8.90, preclose=9.00, tradable=1),
    ])
    tgt = target_series(data.index, {"2024-01-02": 1, "2024-01-03": 0})
    res = run_backtest(data, tgt, code="TEST")
    # 买入 T2 开盘 10.00:99900 股,成本 999000,佣金 249.75,余 750.25(同用例 A)
    # T3 跌停禁卖;T4 开盘 8.95 > 跌停价 8.10:卖出 99900x8.95=894105,
    # 佣金 223.53,印花税 447.05,净得 893434.42,pnl = 893434.42-999249.75 = -105815.33
    check("D 仅两次成交(买+卖)", len(res.trades), 2)
    check("D 卖出避开跌停日", str(res.trades.index[1].date()), "2024-01-05")
    check("D 亏损回合盈亏", float(res.trades.iloc[1]["pnl"]), -105_815.33)
    check("D 胜率", res.metrics["win_rate"], 0.0)


def case_e_timing() -> None:
    print("用例 E:信号时序(全量断言 T+1 与 T+1 持仓约束)")
    data = make_data([
        dict(date="2024-01-02", open=10.00, high=10.50, low=9.80, close=10.20, preclose=9.90, tradable=1),
        dict(date="2024-01-03", open=10.00, high=10.60, low=9.95, close=10.40, preclose=10.20, tradable=1),
        dict(date="2024-01-04", open=10.55, high=10.90, low=10.30, close=10.80, preclose=10.40, tradable=1),
        dict(date="2024-01-05", open=10.90, high=11.00, low=10.70, close=10.95, preclose=10.80, tradable=1),
    ])
    tgt = target_series(data.index, {"2024-01-02": 1, "2024-01-03": 0})
    res = run_backtest(data, tgt, code="TEST")
    buys = res.trades[res.trades["side"] == "BUY"]
    sells = res.trades[res.trades["side"] == "SELL"]
    for b_date in buys.index:
        later = sells.index[sells.index > b_date]
        check("E 卖出严格晚于买入(T+1)", len(later) > 0, True)
    check("E 买入不在信号当日", str(buys.index[0].date()) != "2024-01-02", True)


def case_f_real_data() -> None:
    print("用例 F:真实数据核对(600519 前 10 日持有后清仓)")
    data = load_clean("600519")
    window = data.loc["2019-01-01":"2019-03-31"]
    tgt = pd.Series(0, index=window.index)
    tgt.iloc[:10] = 1
    res = run_backtest(window, tgt, code="600519")
    buy = res.trades.iloc[0]
    buy_day = res.trades.index[0]
    ref = window.loc[buy_day]
    check("F 买入日期=窗口第 2 个交易日", str(buy_day.date()), str(window.index[1].date()))
    check("F 成交价=当日开盘价", float(buy["price"]), float(ref["open"]))
    # 与 CSV 独立重算佣金与现金(对账核心)
    shares = int(buy["shares"])
    cost = round(shares * ref["open"], 2)
    comm = round(max(cost * 2.5e-4, 5.0), 2)
    check("F 佣金独立重算一致", float(buy["commission"]), comm)
    check("F 现金独立重算一致", float(buy["cash_after"]), round(1_000_000 - cost - comm, 2))
    # 买入整手:股数必为 100 的倍数,且再加一手就超预算
    check("F 整手约束", shares % 100, 0)
    one_more = (shares + 100) * ref["open"]
    check("F 预算约束(加一手即超)", one_more + max(one_more * 2.5e-4, 5) > 1_000_000, True)


def main() -> None:
    case_a_basic()
    case_b_limit_up()
    case_c_suspension()
    case_d_limit_down()
    case_e_timing()
    case_f_real_data()
    print()
    if FAILURES:
        print(f"共 {len(FAILURES)} 项失败:")
        for f in FAILURES:
            print("  FAIL", f)
        sys.exit(1)
    print("全部用例 PASS,回测引擎手工对账通过。")


if __name__ == "__main__":
    main()
