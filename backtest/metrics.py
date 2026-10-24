"""绩效指标:总收益、年化收益、最大回撤、夏普比率、胜率。

口径(README 同步说明):
- 年化收益:(期末净值/期初净值)^(252/交易日数) - 1
- 最大回撤:max(1 - 净值/历史最高净值)
- 夏普比率:mean(日收益) / std(日收益, 样本标准差 ddof=1) x sqrt(252),无风险利率取 0
- 胜率:盈利的完整买卖回合数 / 全部完整回合数(一买一卖为一回合,
       盈亏 = 卖出净得 - 买入总成本,双边费用计入);期末仍持仓的未完回合不计入
"""

import math

import pandas as pd

TRADING_DAYS = 252


def compute_metrics(nav: pd.Series, trades: pd.DataFrame) -> dict:
    if len(nav) == 0 or nav.iloc[0] <= 0:
        return {"days": len(nav), "total_return": float("nan"), "annual_return": float("nan"),
                "max_drawdown": float("nan"), "sharpe": float("nan"), "win_rate": float("nan"),
                "round_trips": 0}

    ret = nav.pct_change().dropna()
    n = len(nav)
    gross = nav.iloc[-1] / nav.iloc[0]
    annual = gross ** (TRADING_DAYS / n) - 1 if gross > 0 else float("nan")
    mdd = float((1 - nav / nav.cummax()).max())
    std = ret.std(ddof=1)
    sharpe = float(ret.mean() / std * math.sqrt(TRADING_DAYS)) if std and std > 0 else float("nan")

    sells = trades[trades["side"] == "SELL"] if len(trades) else pd.DataFrame()
    round_trips = len(sells)
    win_rate = float((sells["pnl"] > 0).mean()) if round_trips else float("nan")

    return {
        "days": n,
        "total_return": float(gross - 1),
        "annual_return": float(annual),
        "max_drawdown": mdd,
        "sharpe": sharpe,
        "win_rate": win_rate,
        "round_trips": round_trips,
    }
