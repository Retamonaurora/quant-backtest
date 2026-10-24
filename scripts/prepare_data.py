"""数据校验+清洗一键脚本:raw -> 校验报告 -> cleaned。

产出:
  data/report/validation_report.md    人读校验与清洗报告
  data/report/validation_issues.csv   问题明细(机器可读)
  data/cleaned/*.csv                  清洗后行情(含 tradable 列)

用法:uv run python scripts/prepare_data.py
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backtest.loader import BENCHMARK_NAME, DATA_DIR, STOCK_POOL, load_calendar  # noqa: E402
from backtest.clean import run_clean  # noqa: E402
from backtest.validate import run_validation  # noqa: E402

REPORT_DIR = DATA_DIR / "report"


def build_report(issues, summary, actions, files) -> str:
    lines = [
        "# 数据校验与清洗报告",
        "",
        f"- 生成时间:{datetime.now():%Y-%m-%d %H:%M}",
        f"- 数据来源:BaoStock(官方数据包到位前的开发占位,来源注明见 data/raw/baostock/来源说明.txt)",
        f"- 覆盖:股票池 {len(STOCK_POOL)} 只 + 基准{BENCHMARK_NAME}",
        f"- 交易日历:{BENCHMARK_NAME} 共 {len(load_calendar())} 个交易日(指数不停牌,作主日历)",
        "",
        "## 一、校验汇总",
        "",
        "| 代码 | 名称 | 行数 | 停牌日 | 重复日 | 缺失日 | 多余日 | OHLC异常 | 涨跌幅越界 | pctChg不一致 | 量异常 |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for _, r in summary.iterrows():
        lines.append(
            f"| {r['code']} | {r['name']} | {r['rows']} | {r['suspended_days']} | {r['duplicate_date']} "
            f"| {r['missing_day']} | {r['extra_day']} | {r['ohlc_invalid']} | {r['limit_breach']} "
            f"| {r['pctchg_mismatch']} | {r['volume_anomaly']} |"
        )
    total_issues = len(issues)
    lines += [
        "",
        f"校验结论:**{'未发现问题' if total_issues == 0 else f'共 {total_issues} 条问题'}**(停牌日属正常现象,单列不计入问题)。",
        "",
    ]
    if total_issues:
        lines += ["## 二、问题明细", "", "| 代码 | 名称 | 日期 | 检查项 | 说明 |", "|---|---|---|---|---|"]
        for _, i in issues.iterrows():
            d = i["date"].strftime("%Y-%m-%d") if hasattr(i["date"], "strftime") else i["date"]
            lines.append(f"| {i['code']} | {i['name']} | {d} | {i['check']} | {i['detail']} |")
        lines.append("")
    lines += ["## 三、清洗动作", "", "| 代码 | 名称 | 动作 | 天数 | 说明 |", "|---|---|---|---|---|"]
    if len(actions):
        for _, a in actions.iterrows():
            lines.append(f"| {a['code']} | {a['name']} | {a['action']} | {a['n_days']} | {a['detail']} |")
    else:
        lines.append("| - | - | (无需修复动作) | - | 数据无缺口/重复/报价异常,仅做停牌日规范化 |")
    lines += [
        "",
        "## 四、清洗后输出",
        "",
        "| 代码 | 名称 | 行数 | 可交易日 | 文件 |",
        "|---|---|---|---|---|",
    ]
    for _, f in files.iterrows():
        lines.append(f"| {f['code']} | {f['name']} | {f['rows']} | {f['tradable_days']} | {f['output']} |")
    lines += [
        "",
        "> 清洗口径:停牌/缺口日 OHLC 冻结为昨收、成交量 0、tradable=0;",
        "> 交易日报价异常以 preclose 替代并禁交易;涨跌幅越界仅标记不改价。",
        "> 回测引擎只允许在 tradable=1 的日子撮合成交。",
    ]
    return "\n".join(lines)


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    issues, summary = run_validation()
    actions, files = run_clean()

    issues_out = REPORT_DIR / "validation_issues.csv"
    if len(issues):
        out = issues.copy()
        out["date"] = out["date"].dt.strftime("%Y-%m-%d")
        out.to_csv(issues_out, index=False, encoding="utf-8-sig")
    report = build_report(issues, summary, actions, files)
    (REPORT_DIR / "validation_report.md").write_text(report, encoding="utf-8")

    print(report)
    print(f"\n报告: {REPORT_DIR / 'validation_report.md'}")
    print(f"问题明细: {issues_out if len(issues) else '(无问题,未生成明细文件)'}")


if __name__ == "__main__":
    main()
