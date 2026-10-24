"""均值回复:布林带(经典实现,任务书术语表口径)。

规则:用价格波动幅度画上下轨道(MA ± k 倍标准差),跌破下轨买入、涨破上轨卖出。
参数:window=均线窗口天数, num_std=轨道宽度(标准差倍数)。
标准差用总体口径(ddof=0),与经典布林带定义一致。
"""

import pandas as pd

from strategies.base import BaseStrategy, register


@register
class MeanReversion(BaseStrategy):
    name = "meanrev"
    description = "均值回复:布林带,跌破下轨买入、涨破上轨卖出"
    default_params = {"window": 20, "num_std": 2.0}

    def validate_params(self, params: dict) -> None:
        if params["window"] < 2 or params["num_std"] <= 0:
            raise ValueError(f"布林带参数须 window>=2 且 num_std>0,得到 {params}")

    def generate_target(self, data: pd.DataFrame, params: dict) -> pd.Series:
        self.validate_params(params)
        close = data["close"]
        ma = close.rolling(params["window"], min_periods=params["window"]).mean()
        sd = close.rolling(params["window"], min_periods=params["window"]).std(ddof=0)
        lower = ma - params["num_std"] * sd
        upper = ma + params["num_std"] * sd

        # 状态机:轨道未成形/空仓时跌破下轨 -> 持股;持股后涨破上轨 -> 空仓
        states = []
        state = 0
        for c, lo, up in zip(close.to_numpy(), lower.to_numpy(), upper.to_numpy()):
            if pd.isna(lo):
                state = 0
            elif state == 0 and c < lo:
                state = 1
            elif state == 1 and c > up:
                state = 0
            states.append(state)
        return pd.Series(states, index=data.index)
