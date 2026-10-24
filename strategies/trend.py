"""趋势跟踪:双均线交叉(经典实现,任务书术语表口径)。

规则:短期均线上穿长期均线(金叉)持股,下穿(死叉)空仓。
参数:fast=短期均线天数, slow=长期均线天数(须 fast < slow)。
"""

import pandas as pd

from strategies.base import BaseStrategy, register


@register
class TrendFollowing(BaseStrategy):
    name = "trend"
    description = "趋势跟踪:双均线交叉,金叉持股、死叉空仓"
    default_params = {"fast": 5, "slow": 20}

    def validate_params(self, params: dict) -> None:
        if not 0 < params["fast"] < params["slow"]:
            raise ValueError(f"双均线参数须满足 0 < fast < slow,得到 fast={params['fast']}, slow={params['slow']}")

    def generate_target(self, data: pd.DataFrame, params: dict) -> pd.Series:
        self.validate_params(params)
        ma_fast = data["close"].rolling(params["fast"], min_periods=params["fast"]).mean()
        ma_slow = data["close"].rolling(params["slow"], min_periods=params["slow"]).mean()
        target = (ma_fast > ma_slow).astype(int)
        target[ma_slow.isna()] = 0  # 长均线未成形前空仓
        return target
