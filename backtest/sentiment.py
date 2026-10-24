"""舆情情感打分加载(任务书附加创新项资料,官方附带日度 CSV)。

目录约定:data/sentiment/<source>/*.csv
  - official/ 官方舆情打分数据(数据包到位后放入)
  - mock/     合成数据(仅用于三因子接口测试,无信息含量主张,来源说明见目录内 txt)

CSV 格式(容错解析):
  - 日期列:date / trade_date / 日期
  - 分数列:score / sentiment / 情感分 / 情感打分 / 情绪分
  - 允许单文件单股票(文件名含 6 位代码)或单文件全股票(含 code / 股票代码 列)

数据不可用(目录/文件缺失)时返回 None,调用方据此跳过舆情因子,
保证未接入舆情前的回测行为与结果完全不变。
对齐口径:按交易日 reindex 后前向填充(舆情日更,缺日沿用最近一日分值),
首个分值之前填 0(中性)。
"""

from pathlib import Path

import pandas as pd

from backtest.loader import DATA_DIR

SENTIMENT_DIR = DATA_DIR / "sentiment"

DATE_COLS = ["date", "trade_date", "日期"]
SCORE_COLS = ["score", "sentiment", "情感分", "情感打分", "情绪分"]
CODE_COLS = ["code", "stock_code", "股票代码", "代码"]


def _pick(cols: list[str], candidates: list[str]) -> str | None:
    lower = {c.lower().strip(): c for c in cols}
    for cand in candidates:
        if cand in lower:
            return lower[cand]
    return None


def _parse_score_csv(path: Path) -> pd.DataFrame | None:
    df = pd.read_csv(path, dtype={"code": str})
    date_col = _pick(list(df.columns), DATE_COLS)
    score_col = _pick(list(df.columns), SCORE_COLS)
    if date_col is None or score_col is None:
        return None
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df[score_col] = pd.to_numeric(df[score_col], errors="coerce")
    df = df.dropna(subset=[date_col]).sort_values(date_col)
    return df.rename(columns={date_col: "date", score_col: "score"})[["date", "score"]]


def load_sentiment(code: str, source: str = "mock") -> pd.Series | None:
    """加载单只股票的日度舆情分值序列(索引为日期)。不可用时返回 None。"""
    folder = SENTIMENT_DIR / source
    if not folder.exists():
        return None

    df = None
    # 形态一:单文件单股票(文件名含 6 位代码)
    for f in sorted(folder.glob("*.csv")):
        if code in f.stem:
            df = _parse_score_csv(f)
            break
    # 形态二:单文件全股票(含代码列)
    if df is None:
        for f in sorted(folder.glob("*.csv")):
            parsed = _parse_score_csv(f)
            if parsed is None:
                continue
            raw = pd.read_csv(f, dtype={c: str for c in CODE_COLS if c in pd.read_csv(f, nrows=0).columns})
            code_col = _pick(list(raw.columns), CODE_COLS)
            if code_col and code in raw[code_col].astype(str).str.zfill(6).values:
                mask = raw[code_col].astype(str).str.zfill(6) == code
                df = parsed[mask.values].reset_index(drop=True)
                break
    if df is None or df.empty:
        return None

    s = df.drop_duplicates("date").set_index("date")["score"].astype(float)
    return s.sort_index()


def align_sentiment(score: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    """把舆情序列对齐到回测交易日:缺失日沿用最近分值,首日前填 0(中性)。"""
    aligned = score.reindex(index).ffill()
    return aligned.fillna(0.0)
