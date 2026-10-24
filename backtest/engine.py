"""回测引擎:统一撮合规则(任务书不得更改项)。

撮合口径(与任务书一致,README 同步说明):
- 信号 T 日收盘计算:策略只输出"当日收盘后的目标仓位(1持股/0空仓)",只允许用 T 日及以前的数据;
  引擎负责把 T 日信号推迟到 T+1 开盘执行,策略侧不 shift,反未来函数规则集中在引擎一处。
- T+1 持仓约束:当日买入的股票次一交易日方可卖出(日常信号流下天然满足,引擎内再做防御性校验)。
- 涨跌停不成交:执行日开盘价触板(开盘 >= 涨停价 或 <= 跌停价)则该日不成交。
  以开盘价判定,避免用盘中/收盘信息决定开盘成交(未来函数)。
  涨停价 = 前收 x 1.10、跌停价 = 前收 x 0.90,按分(0.01 元)四舍五入。
- 停牌不可交易:tradable=0 的日期不撮合;未成交指令作废(次日按当日收盘信号重算)。
- 费用:佣金 max(成交额 x 0.025%, 5 元) 双边;卖出另计印花税(成交额 x 0.05%),金额按分取整。
- A 股整手交易:买入数量为 100 股整数倍,资金连佣金不足时逐手递减直至可负担。
- 初始资金 100 万元,单标的、全仓进出。
"""

import math
from dataclasses import dataclass, field

import pandas as pd

from backtest.metrics import compute_metrics

EPS = 1e-9


@dataclass
class BacktestConfig:
    initial_cash: float = 1_000_000.0
    commission_rate: float = 2.5e-4   # 佣金万 2.5
    min_commission: float = 5.0       # 最低 5 元
    stamp_tax_rate: float = 5.0e-4    # 卖出印花税万 5
    lot_size: int = 100               # A 股一手 100 股


@dataclass
class BacktestResult:
    code: str
    nav: pd.Series          # 每日收盘净值(现金+持仓市值)
    trades: pd.DataFrame    # 成交记录:BUY/SELL、价格、股数、费用、pnl(卖出时为该轮交易盈亏)
    metrics: dict = field(default_factory=dict)


def limit_up_down(preclose: float) -> tuple[float, float]:
    """按前收计算涨停/跌停价(±10%,四舍五入到分;+epsilon 防 Python 浮点截断)。"""
    up = round(preclose * 1.10 + EPS, 2)
    down = round(preclose * 0.90 + EPS, 2)
    return up, down


def run_backtest(
    data: pd.DataFrame,
    target: pd.Series,
    code: str = "",
    start: str | None = None,
    end: str | None = None,
    config: BacktestConfig | None = None,
) -> BacktestResult:
    """执行单标的回测。

    data:   清洗后行情(load_clean 输出),索引为交易日
    target: 策略目标仓位序列(1=持股, 0=空仓),索引与 data 对齐;
            target.loc[T] 表示"T 日收盘后希望的目标仓位",引擎在 T+1 开盘执行
    start/end: 回测区间(闭区间,含两端),默认全区间
    """
    cfg = config or BacktestConfig()
    df = data.loc[start:end] if (start or end) else data
    target = target.reindex(df.index).fillna(0).astype(int)

    cash = cfg.initial_cash
    shares = 0
    last_buy_date = None
    open_cost = 0.0  # 本轮持仓的买入总成本(含佣金),卖出时结算 pnl
    pending = None   # 昨日收盘信号,今日开盘执行
    nav_rows: list[tuple[pd.Timestamp, float]] = []
    trade_rows: list[dict] = []

    for date, row in df.iterrows():
        # ---- 1. 开盘撮合昨日信号 ----
        if pending is not None:
            desired, pending = pending, None
            if row["tradable"] == 1:
                up, down = limit_up_down(row["preclose"])
                at_limit = (row["open"] >= up - EPS) or (row["open"] <= down + EPS)
                if not at_limit:
                    if desired == 1 and shares == 0:
                        lots = math.floor(cash / (row["open"] * cfg.lot_size) + EPS)
                        n = lots * cfg.lot_size
                        while n > 0:
                            cost = n * row["open"]
                            comm = max(cost * cfg.commission_rate, cfg.min_commission)
                            if cost + comm <= cash + EPS:
                                break
                            n -= cfg.lot_size
                        if n > 0:
                            cost = round(n * row["open"], 2)
                            comm = round(max(n * row["open"] * cfg.commission_rate, cfg.min_commission), 2)
                            cash = round(cash - cost - comm, 2)
                            shares, last_buy_date, open_cost = n, date, cost + comm
                            trade_rows.append(dict(date=date, side="BUY", price=row["open"], shares=n,
                                                   commission=comm, stamp_tax=0.0, cash_after=cash, pnl=None))
                    elif desired == 0 and shares > 0:
                        # T+1 防御性校验:买入当日不允许卖出
                        if last_buy_date is None or date > last_buy_date:
                            proceeds = shares * row["open"]
                            comm = round(max(proceeds * cfg.commission_rate, cfg.min_commission), 2)
                            stamp = round(proceeds * cfg.stamp_tax_rate, 2)
                            net = round(proceeds - comm - stamp, 2)
                            pnl = round(net - open_cost, 2)
                            cash = round(cash + net, 2)
                            trade_rows.append(dict(date=date, side="SELL", price=row["open"], shares=shares,
                                                   commission=comm, stamp_tax=stamp, cash_after=cash, pnl=pnl))
                            shares, last_buy_date, open_cost = 0, None, 0.0
                    # desired 与持仓一致时不动作(持有/空仓)

        # ---- 2. 收盘:记净值,读今日信号(明日开盘执行) ----
        nav_rows.append((date, round(cash + shares * row["close"], 2)))
        pending = int(target.loc[date])

    nav = pd.Series({d: v for d, v in nav_rows}, name="nav")
    trades = pd.DataFrame(trade_rows)
    if len(trades):
        trades = trades.set_index("date")
    result = BacktestResult(code=code, nav=nav, trades=trades)
    result.metrics = compute_metrics(nav, trades)
    return result
