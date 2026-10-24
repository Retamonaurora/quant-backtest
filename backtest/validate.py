"""数据校验:对标准化行情做缺失/异常/复权错误检查,产出问题清单。

任务书要求:自动检查缺失、异常与复权错误,输出校验报告(核心工作,不得跳过)。
检查项与判定口径:
  1. duplicate_date    日期重复
  2. missing_day       交易日历中存在但数据缺失(疑似数据缺口,区别于停牌)
  3. extra_day         数据中存在但不在交易日历中(疑似日历外脏数据)
  4. ohlc_invalid      OHLC 逻辑错误(高低点矛盾、价格<=0、交易日报价缺失)
  5. limit_breach      交易日 |pctChg| > 10.5%(疑似复权错误)。主板涨跌停 10%,因前收盘价
                       按分取整,涨停日 |pctChg| 合理上限约 10.1%(实测 ≤10.07%),阈值取 10.5%
                       既不误报真实涨跌停,又能捕获复权错误造成的异常跳变
  6. pctchg_mismatch   pctchg 字段与 close/preclose 推算值偏差 > 0.05 个百分点
                       (字段内部不一致,疑似复权口径混乱)
  7. volume_anomaly    交易日报量为 0/负,或任意日报量为负(停牌标志与行情矛盾)
停牌日(tradestatus=0)单列为 info,不算问题。
"""

import pandas as pd

from backtest.loader import PRICE_COLS, STOCK_POOL, load_calendar, load_raw

# 涨跌幅越界阈值:涨停日经前收取整放大后实测可达 ~10.07%,取 10.5% 为疑似复权错误判定线
LIMIT_BREACH_PCT = 10.5
PCTCHG_TOL = 0.05


def validate_stock(code: str, df: pd.DataFrame, calendar: pd.DatetimeIndex) -> list[dict]:
    issues: list[dict] = []

    def add(date, check: str, detail: str) -> None:
        issues.append({"code": code, "name": STOCK_POOL[code], "date": date, "check": check, "detail": detail})

    # 1. 重复日期
    dup = df.index[df.index.duplicated()]
    for d in dup:
        add(d, "duplicate_date", "日期重复出现")

    # 2/3. 日历对齐:缺失日与多余日
    have = df.index.unique()
    missing = calendar.difference(have)
    for d in missing:
        add(d, "missing_day", "在交易日历中但数据缺失(数据缺口,非停牌行)")
    extra = have.difference(calendar)
    for d in extra:
        add(d, "extra_day", "不在交易日历中(疑似脏数据)")

    trading = df["tradestatus"] == 1

    # 4. OHLC 逻辑
    bad_ohlc = (
        (df["high"] < df["low"])
        | (df["high"] < df[["open", "close"]].max(axis=1))
        | (df["low"] > df[["open", "close"]].min(axis=1))
        | (df[PRICE_COLS] <= 0).any(axis=1)
        | (df[PRICE_COLS].isna().any(axis=1) & trading)
    )
    for d, row in df[bad_ohlc.fillna(False)].iterrows():
        add(d, "ohlc_invalid", f"OHLC 异常: O={row['open']} H={row['high']} L={row['low']} C={row['close']}")

    # 5. 涨跌幅越界(疑似复权错误)。注意:前复权价格是缩放后的浮点值,不再是 0.01 元
    #    对齐的真实报价,不能用取整涨跌停价直接比对;以 pctChg 超阈值判定(见模块文档)。
    breach = trading & df["pctchg"].abs().gt(LIMIT_BREACH_PCT)
    for d, pct in df.loc[breach, "pctchg"].items():
        add(d, "limit_breach", f"涨跌幅 {pct:.2f}% 超过 ±{LIMIT_BREACH_PCT}%,疑似复权错误")

    # 6. pctchg 与价格推算不一致
    calc = 100 * (df["close"] / df["preclose"] - 1)
    mismatch = trading & (df["pctchg"] - calc).abs().gt(PCTCHG_TOL)
    for d in df.index[mismatch.fillna(False)]:
        add(d, "pctchg_mismatch", f"pctchg={df.loc[d, 'pctchg']} 与 close/preclose 推算 {calc.loc[d]:.4f} 不一致")

    # 7. 成交量异常
    vol_bad = (trading & (df["volume"] <= 0)) | (df["volume"] < 0)
    for d, v in df.loc[vol_bad.fillna(False), "volume"].items():
        add(d, "volume_anomaly", f"成交量 {v} 与交易日状态矛盾")

    return issues


def run_validation() -> tuple[pd.DataFrame, pd.DataFrame]:
    """对全部股票池执行校验。返回 (问题明细 issues_df, 汇总 summary_df)。"""
    calendar = load_calendar()
    all_issues: list[dict] = []
    summary_rows = []
    for code in STOCK_POOL:
        df = load_raw(code)
        issues = validate_stock(code, df, calendar)
        all_issues.extend(issues)
        counts = pd.Series([i["check"] for i in issues]).value_counts()
        summary_rows.append(
            {
                "code": code,
                "name": STOCK_POOL[code],
                "rows": len(df),
                "suspended_days": int((df["tradestatus"] == 0).sum()),
                **{c: int(counts.get(c, 0)) for c in (
                    "duplicate_date", "missing_day", "extra_day", "ohlc_invalid",
                    "limit_breach", "pctchg_mismatch", "volume_anomaly")},
            }
        )
    issues_df = pd.DataFrame(all_issues)
    summary_df = pd.DataFrame(summary_rows)
    return issues_df, summary_df
