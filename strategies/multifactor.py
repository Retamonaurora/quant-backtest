"""多因子打分(任务书术语表口径:多个指标分别打分后加权合成,总分决定买卖)。

因子(均为后视量,无未来函数):
- 动量(涨势强弱):mom_window 日涨幅
- 波动(波动大小):vol_window 日收益标准差,按低波动为优反向计入
打分:各因子在 z_window 滚动窗口内做 z-score,加权合成总分(权重 w_mom / 1-w_mom)。
交易规则:总分 > buy_th 持股;< sell_th 清仓;两者之间维持原状态。
"""

import pandas as pd

from strategies.base import BaseStrategy, register


@register
class MultiFactor(BaseStrategy):
    name = "multifactor"
    description = "多因子打分:动量+低波动加权合成,高分持股、低分清仓"
    default_params = {"mom_window": 20, "vol_window": 20, "z_window": 60,
                      "buy_th": 0.5, "sell_th": -0.3, "w_mom": 0.5}

    def validate_params(self, params: dict) -> None:
        if min(params["mom_window"], params["vol_window"], params["z_window"]) < 2:
            raise ValueError(f"各窗口参数须 >= 2,得到 {params}")
        if not params["sell_th"] < params["buy_th"]:
            raise ValueError(f"须 sell_th < buy_th,得到 {params}")

    def generate_target(self, data: pd.DataFrame, params: dict) -> pd.Series:
        self.validate_params(params)
        close = data["close"]
        mom = close.pct_change(params["mom_window"])
        vol = close.pct_change().rolling(params["vol_window"],
                                         min_periods=params["vol_window"]).std(ddof=0)

        def zscore(x: pd.Series) -> pd.Series:
            m = x.rolling(params["z_window"], min_periods=params["z_window"]).mean()
            s = x.rolling(params["z_window"], min_periods=params["z_window"]).std(ddof=0)
            return (x - m) / s

        w = params["w_mom"]
        score = w * zscore(mom) + (1 - w) * zscore(-vol)

        states = []
        state = 0
        for s in score.to_numpy():
            if pd.isna(s):
                pass  # 打分未成形,维持原状态(期初为空仓)
            elif state == 0 and s > params["buy_th"]:
                state = 1
            elif state == 1 and s < params["sell_th"]:
                state = 0
            states.append(state)
        return pd.Series(states, index=data.index)
