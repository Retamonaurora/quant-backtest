"""数据加载:原始行情 CSV -> 标准化 DataFrame。

数据源切换说明:
- 当前使用 data/raw/baostock/(官方数据包到位前的开发占位,来源 BaoStock)
- 官方数据包到位后放 data/raw/official/,届时仅需调整 load_raw 的文件解析,
  输出的标准化列结构不变,下游校验/清洗/回测无需改动。
"""

from pathlib import Path

import pandas as pd

# 任务书固定股票池(不得更改):代码(无交易所前缀) -> 名称
STOCK_POOL = {
    "600519": "贵州茅台",
    "601318": "中国平安",
    "601398": "工商银行",
    "600900": "长江电力",
    "000002": "万科A",
    "600276": "恒瑞医药",
    "002415": "海康威视",
    "002594": "比亚迪",
    "600111": "北方稀土",
    "601888": "中国中免",
}

BENCHMARK_CODE = "000300"
BENCHMARK_NAME = "沪深300"

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data"
CLEANED_DIR = DATA_DIR / "cleaned"

# 标准化后的列(下游统一使用)
PRICE_COLS = ["open", "high", "low", "close"]


def _baostock_path(code: str) -> Path:
    return DATA_DIR / "raw" / "baostock" / f"{code}_{STOCK_POOL[code]}.csv"


def _benchmark_path() -> Path:
    return DATA_DIR / "raw" / "baostock" / f"{BENCHMARK_CODE}_{BENCHMARK_NAME}.csv"


def load_calendar() -> pd.DatetimeIndex:
    """主交易日历:以沪深300 指数的交易日为准(指数不存在停牌)。"""
    df = pd.read_csv(_benchmark_path(), parse_dates=["date"])
    return pd.DatetimeIndex(pd.to_datetime(df["date"].sort_values()).unique())


def load_raw(code: str) -> pd.DataFrame:
    """加载单只股票原始数据并标准化。

    输出列:date(index), open, high, low, close, preclose, volume,
           amount, tradestatus(1交易/0停牌), pctchg(涨跌幅,%)
    """
    df = pd.read_csv(_baostock_path(code), parse_dates=["date"])
    df = df.rename(columns={"pctChg": "pctchg"})
    df["tradestatus"] = pd.to_numeric(df["tradestatus"], errors="coerce").astype("Int64")
    df = df.sort_values("date").set_index("date")
    return df


def load_raw_benchmark() -> pd.DataFrame:
    """加载沪深300 指数(基准),结构与个股一致但不做复权处理。"""
    df = pd.read_csv(_benchmark_path(), parse_dates=["date"])
    df = df.rename(columns={"pctChg": "pctchg"})
    df = df.sort_values("date").set_index("date")
    return df


def load_clean(code: str, sentiment: str | None = None) -> pd.DataFrame:
    """加载清洗后数据(data/cleaned/,prepare_data.py 产出),回测引擎的输入。

    sentiment: 舆情数据源("official"/"mock"),非 None 时附加 sentiment 列
    (按交易日对齐、前向填充、首日前 0 中性,见 backtest/sentiment.py);
    数据源不可用时抛 ValueError,避免静默回退到无舆情回测。
    """
    path = CLEANED_DIR / f"{code}_{STOCK_POOL[code]}.csv"
    df = pd.read_csv(path, parse_dates=["date"]).set_index("date")
    df["tradable"] = df["tradable"].astype(int)
    if sentiment is not None:
        from backtest.sentiment import align_sentiment, load_sentiment

        score = load_sentiment(code, source=sentiment)
        if score is None:
            raise ValueError(f"舆情数据源 {sentiment!r} 中没有 {code} 的可用数据")
        df["sentiment"] = align_sentiment(score, df.index)
    return df
