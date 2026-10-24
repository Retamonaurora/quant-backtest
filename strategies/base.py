"""策略基类与注册表。

约定:
- 策略只允许用 T 日及以前的数据计算,T 日收盘后给出目标仓位 target[T] ∈ {0, 1}
  (1=持股, 0=空仓);由回测引擎统一推迟到 T+1 开盘执行,策略侧不做 shift。
- 参数以 dict 传入,取值范围由寻优模块的网格定义。
"""

import pandas as pd

STRATEGY_REGISTRY: dict[str, type["BaseStrategy"]] = {}


def register(cls: type["BaseStrategy"]) -> type["BaseStrategy"]:
    STRATEGY_REGISTRY[cls.name] = cls
    return cls


class BaseStrategy:
    name: str = "base"
    description: str = ""
    default_params: dict = {}

    def generate_target(self, data: pd.DataFrame, params: dict) -> pd.Series:
        raise NotImplementedError

    def validate_params(self, params: dict) -> None:
        """参数合法性校验,不合法抛 ValueError。"""
