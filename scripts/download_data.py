"""开发占位数据下载(官方数据包到位前的替代方案)。

来源:BaoStock(baostock.com,任务书列明的备选数据源,须注明来源)。
说明:本机网络下 akshare 东财接口连接被断开,故改用 BaoStock;
     官方数据包到位后放入 data/raw/official/,回测一律以官方数据为准,
     本目录数据仅用于开发期跑通流程与交叉校验。

字段含 preclose(昨收)、tradestatus(1交易/0停牌)、pctChg(涨跌幅%),
供后续数据校验模块(缺失/异常/复权检查)直接使用。

用法:uv run python scripts/download_data.py
"""

from pathlib import Path

import baostock as bs
import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "baostock"
START, END = "2019-01-01", "2024-12-31"

# 任务书固定股票池(不得更改);BaoStock 代码带交易所前缀
STOCKS = {
    "sh.600519": "贵州茅台",
    "sh.601318": "中国平安",
    "sh.601398": "工商银行",
    "sh.600900": "长江电力",
    "sz.000002": "万科A",
    "sh.600276": "恒瑞医药",
    "sz.002415": "海康威视",
    "sz.002594": "比亚迪",
    "sh.600111": "北方稀土",
    "sh.601888": "中国中免",
}

# adjustflag: 1=后复权 2=前复权 3=不复权;任务书口径为前复权
FIELDS = "date,open,high,low,close,preclose,volume,amount,tradestatus,pctChg"


def fetch(code: str, is_index: bool = False) -> pd.DataFrame:
    rs = bs.query_history_k_data_plus(
        code,
        FIELDS,
        start_date=START,
        end_date=END,
        frequency="d",
        adjustflag="3" if is_index else "2",
    )
    rows = []
    while rs.error_code == "0" and rs.next():
        rows.append(rs.get_row_data())
    if rs.error_code != "0":
        raise RuntimeError(f"{code} 拉取失败: {rs.error_code} {rs.error_msg}")
    df = pd.DataFrame(rows, columns=FIELDS.split(","))
    for col in ("open", "high", "low", "close", "preclose", "volume", "amount", "pctChg"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["tradestatus"] = pd.to_numeric(df["tradestatus"], errors="coerce").astype("Int64")
    return df


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "来源说明.txt").write_text(
        "本目录数据为开发占位数据,自行补充下载,来源:BaoStock(baostock.com)。\n"
        f"下载脚本:scripts/download_data.py;区间:{START} ~ {END};个股为前复权(adjustflag=2)。\n"
        "本机网络下 akshare 东财接口不可用,故采用任务书列明的备选源 BaoStock。\n"
        "回测一律以官方数据包(data/raw/official/)为准,本目录仅用于开发与交叉校验。\n",
        encoding="utf-8",
    )

    lg = bs.login()
    if lg.error_code != "0":
        raise RuntimeError(f"baostock 登录失败: {lg.error_msg}")
    try:
        total = 0
        for code, name in STOCKS.items():
            df = fetch(code)
            out = RAW / f"{code.split('.')[-1]}_{name}.csv"
            df.to_csv(out, index=False, encoding="utf-8-sig")
            total += len(df)
            print(f"{code} {name}: {len(df)} 行 -> {out.name}")

        idx = fetch("sh.000300", is_index=True)
        idx.to_csv(RAW / "000300_沪深300.csv", index=False, encoding="utf-8-sig")
        print(f"sh.000300 沪深300: {len(idx)} 行 -> 000300_沪深300.csv")
        print(f"完成:10 只股票共 {total} 行 + 基准指数,输出目录 {RAW}")
    finally:
        bs.logout()


if __name__ == "__main__":
    main()
