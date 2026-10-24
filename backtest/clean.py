"""数据清洗:按校验口径修复/标记,输出可直接回测的标准化数据。

清洗动作(均记录到清洗日志):
  - drop_duplicate       日期重复 -> 保留首条
  - fill_missing_day     交易日历缺口 -> 按停牌口径补行(OHLC=昨收, 不可交易)
  - repair_ohlc          交易日报价异常/缺失 -> OHLC 用 preclose 替代, 该日不可交易
  - normalize_suspension 停牌日规范化:OHLC=preclose(价格冻结), volume/amount/pctchg=0
涨跌幅越界(limit_breach)只在校验报告中标记,不擅自改价。
输出列:date(index), open, high, low, close, preclose, volume, amount, tradable(1/0)
"""

import pandas as pd

from backtest.loader import DATA_DIR, PRICE_COLS, STOCK_POOL, load_calendar, load_raw

CLEANED_DIR = DATA_DIR / "cleaned"


def clean_stock(code: str, df: pd.DataFrame, calendar: pd.DatetimeIndex) -> tuple[pd.DataFrame, list[dict]]:
    actions: list[dict] = []

    def log(action: str, dates, detail: str) -> None:
        actions.append(
            {"code": code, "name": STOCK_POOL[code], "action": action, "n_days": len(list(dates)), "detail": detail}
        )

    # 1. 重复日期:保留首条
    dup = df.index[df.index.duplicated()]
    if len(dup):
        df = df[~df.index.duplicated(keep="first")]
        log("drop_duplicate", dup, "日期重复,保留首条")

    # 2. 交易日历缺口:按停牌口径补行(价格=前收, 不可交易)
    missing = calendar.difference(df.index)
    if len(missing):
        fill = pd.DataFrame(index=missing, columns=df.columns, dtype="float64")
        fill["tradestatus"] = 0
        df = pd.concat([df, fill]).sort_index()
        df[PRICE_COLS + ["preclose"]] = df[PRICE_COLS + ["preclose"]].ffill()
        df[["volume", "amount", "pctchg"]] = df[["volume", "amount", "pctchg"]].fillna(0)
        log("fill_missing_day", missing, "日历缺口,按停牌口径补行(价格=前收)")

    trading = (df["tradestatus"] == 1).fillna(False)

    # 3. 交易日报价异常:OHLC 用 preclose 替代,该日不可交易(宁可少交易,不引入脏价)
    bad = trading & (
        (df["high"] < df["low"])
        | (df["high"] < df[["open", "close"]].max(axis=1))
        | (df["low"] > df[["open", "close"]].min(axis=1))
        | (df[PRICE_COLS] <= 0).any(axis=1)
        | df[PRICE_COLS].isna().any(axis=1)
    )
    bad = bad.fillna(False)
    if bad.any():
        prec = df.loc[bad, "preclose"]
        for col in PRICE_COLS:
            df.loc[bad, col] = prec
        log("repair_ohlc", df.index[bad], "交易日报价异常,OHLC 以 preclose 替代并禁交易")

    # 4. 停牌日规范化:价格冻结在 preclose,成交清零
    suspended = ~trading
    prec = df.loc[suspended, "preclose"]
    for col in PRICE_COLS:
        df.loc[suspended, col] = prec
    df[["volume", "amount", "pctchg"]] = df[["volume", "amount", "pctchg"]].fillna(0)

    clean = pd.DataFrame(
        {
            "open": df["open"],
            "high": df["high"],
            "low": df["low"],
            "close": df["close"],
            "preclose": df["preclose"],
            "volume": df["volume"],
            "amount": df["amount"],
            "tradable": (~suspended & ~bad).astype(int),
        },
        index=df.index,
    )
    return clean, actions


def run_clean() -> tuple[pd.DataFrame, pd.DataFrame]:
    """清洗全部股票池并写出 data/cleaned/。返回 (清洗日志 actions_df, 输出清单 files_df)。"""
    calendar = load_calendar()
    all_actions: list[dict] = []
    file_rows = []
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    for code in STOCK_POOL:
        raw = load_raw(code)
        clean, actions = clean_stock(code, raw, calendar)
        all_actions.extend(actions)
        out = CLEANED_DIR / f"{code}_{STOCK_POOL[code]}.csv"
        clean.to_csv(out, encoding="utf-8-sig")
        file_rows.append(
            {
                "code": code,
                "name": STOCK_POOL[code],
                "rows": len(clean),
                "tradable_days": int(clean["tradable"].sum()),
                "output": str(out.relative_to(DATA_DIR.parent)),
            }
        )
    return pd.DataFrame(all_actions), pd.DataFrame(file_rows)
