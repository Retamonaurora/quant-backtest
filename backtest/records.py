"""实验记录自动导出(任务书要求:每次回测自动落一条记录,形成对比结果)。

- records/experiments.csv:每次回测一行(策略、参数、样本内外指标)。
  完全相同的实验(code+strategy+params+sample+start+end)不重复落盘,
  即文件中每一行都是"策略或参数有实际变化"的实验。
- records/对比结果.csv:每次寻优运行的全部参数组合及样本内外指标,带 run_id 可追溯。
两者均由程序导出,不得手写(任务书规定)。
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from backtest.loader import PROJECT_DIR

RECORDS_DIR = PROJECT_DIR / "records"
EXPERIMENTS_CSV = RECORDS_DIR / "experiments.csv"
COMPARISON_CSV = RECORDS_DIR / "对比结果.csv"

EXPERIMENT_COLUMNS = [
    "timestamp", "code", "name", "strategy", "params", "sample", "start", "end",
    "days", "total_return", "annual_return", "max_drawdown", "sharpe", "win_rate", "round_trips",
]
COMPARISON_COLUMNS = [
    "run_id", "timestamp", "code", "name", "strategy", "params",
    "in_annual_return", "in_max_drawdown", "in_sharpe", "in_win_rate",
    "out_annual_return", "out_max_drawdown", "out_sharpe", "out_win_rate", "rank",
]


def _params_key(params: dict) -> str:
    return json.dumps(params, ensure_ascii=False, sort_keys=True)


def log_run(code: str, strategy: str, params: dict, sample: str,
            start: str, end: str, metrics: dict) -> bool:
    """落一条实验记录;若为完全相同的重复实验则跳过。返回是否实际写入。"""
    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "code": code,
        "name": metrics.get("name", ""),
        "strategy": strategy,
        "params": _params_key(params),
        "sample": sample,
        "start": str(start),
        "end": str(end),
        "days": metrics.get("days"),
        "total_return": metrics.get("total_return"),
        "annual_return": metrics.get("annual_return"),
        "max_drawdown": metrics.get("max_drawdown"),
        "sharpe": metrics.get("sharpe"),
        "win_rate": metrics.get("win_rate"),
        "round_trips": metrics.get("round_trips"),
    }
    RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    if EXPERIMENTS_CSV.exists():
        existing = pd.read_csv(EXPERIMENTS_CSV, dtype={"code": str, "params": str})
        dup = existing[
            (existing["code"] == code) & (existing["strategy"] == strategy)
            & (existing["params"] == row["params"]) & (existing["sample"] == sample)
            & (existing["start"] == row["start"]) & (existing["end"] == row["end"])
        ]
        if len(dup):
            return False
    pd.DataFrame([row]).to_csv(EXPERIMENTS_CSV, mode="a",
                               header=not EXPERIMENTS_CSV.exists(), index=False)
    return True


def log_comparison(rows: list[dict], run_id: str) -> Path:
    """寻优结束后导出全部参数组合的对比结果(带 run_id 追加)。"""
    df = pd.DataFrame(rows, columns=COMPARISON_COLUMNS)
    RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(COMPARISON_CSV, mode="a", header=not COMPARISON_CSV.exists(), index=False)
    return COMPARISON_CSV


def count_real_experiments() -> dict:
    """统计真实变化实验数(去重后)与覆盖股票数,供验收核对。"""
    if not EXPERIMENTS_CSV.exists():
        return {"experiments": 0, "stocks": 0, "strategies": 0}
    df = pd.read_csv(EXPERIMENTS_CSV, dtype={"code": str, "params": str})
    dedup = df.drop_duplicates(subset=["code", "strategy", "params", "sample", "start", "end"])
    return {
        "experiments": int(len(dedup)),
        "stocks": int(dedup["code"].nunique()),
        "strategies": int(dedup["strategy"].nunique()),
    }
