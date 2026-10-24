"""合成舆情数据生成器:仅用于验证三因子舆情接口,无信息含量主张。

生成规则(确定性,seed=42):对每只股票,以近 5 日收益的 tanh 为基底叠加噪声,
与前一日为止的行情弱相关(不引入未来信息);输出 data/sentiment/mock/{code}_{name}.csv。

注意:本目录数据是接口测试用合成数据,不得作为舆情因子的效果结论;
官方舆情数据包到位后放入 data/sentiment/official/ 再做真实实验。

用法:uv run python scripts/make_mock_sentiment.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backtest.loader import STOCK_POOL, load_clean
from backtest.sentiment import SENTIMENT_DIR

OUT = SENTIMENT_DIR / "mock"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "来源说明.txt").write_text(
        "本目录为合成舆情数据,仅用于三因子舆情接口的链路测试,无信息含量主张。\n"
        "生成脚本 scripts/make_mock_sentiment.py(seed=42,与近 5 日收益弱相关 + 噪声)。\n"
        "官方舆情数据包到位后请放入 data/sentiment/official/,实验结论一律以官方数据为准。\n",
        encoding="utf-8",
    )
    rng = np.random.default_rng(42)
    for code, name in STOCK_POOL.items():
        df = load_clean(code)
        ret5 = df["close"].pct_change(5).fillna(0.0)
        score = (np.tanh(ret5.to_numpy() * 20) * 0.8 + rng.normal(0, 0.3, len(df))).round(4)
        out = pd.DataFrame({"date": df.index.strftime("%Y-%m-%d"), "score": score})
        path = OUT / f"{code}_{name}.csv"
        out.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"{code} {name}: {len(out)} 日合成舆情 -> {path.name}")
    print(f"完成,输出目录 {OUT}")


if __name__ == "__main__":
    main()
