"""Flask 绩效报告页(任务书成果要求:绩效报告页 / 数据可视化看板)。

启动:双击 启动.bat,或 uv run python app.py,浏览器访问 http://127.0.0.1:5000
功能:选择策略/股票/起止日期/参数 -> 运行回测 -> 展示四大指标、净值 vs 沪深300、成交明细。
每次页面回测同样自动落实验记录(records/experiments.csv)。
"""

import base64
import sys
from pathlib import Path

import pandas as pd
from flask import Flask, redirect, render_template_string, request, url_for

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backtest.engine import BacktestConfig, run_backtest
from backtest.loader import BENCHMARK_NAME, STOCK_POOL, load_clean, load_raw_benchmark
from backtest.records import log_run
from report.render import nav_figure_bytes
from strategies.base import STRATEGY_REGISTRY
import strategies.meanrev  # noqa: F401
import strategies.multifactor  # noqa: F401
import strategies.trend  # noqa: F401

app = Flask(__name__)

PAGE = """<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>A股量化回测系统 · 绩效报告</title>
<style>
 body { font-family: "Microsoft YaHei", sans-serif; margin: 24px auto; max-width: 1080px; color: #222; background: #fff; }
 h1 { font-size: 20px; border-bottom: 2px solid #c0392b; padding-bottom: 8px; }
 form { display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end; background: #f7f7f7;
        padding: 14px; border-radius: 8px; }
 label { font-size: 12px; color: #666; display: block; margin-bottom: 4px; }
 select, input { padding: 6px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; }
 button { background: #c0392b; color: #fff; border: 0; padding: 9px 22px; border-radius: 4px;
          font-size: 14px; cursor: pointer; }
 button:hover { background: #a93226; }
 .metrics { display: flex; gap: 12px; flex-wrap: wrap; margin: 18px 0; }
 .card { flex: 1; min-width: 150px; background: #fff; border: 1px solid #eee; border-radius: 8px;
         padding: 12px 16px; box-shadow: 0 1px 3px rgba(0,0,0,.06); }
 .card .k { font-size: 12px; color: #888; } .card .v { font-size: 22px; font-weight: 600; margin-top: 4px; }
 .pos { color: #c0392b; } .neg { color: #27ae60; }
 img.chart { width: 100%; border: 1px solid #eee; border-radius: 8px; }
 table { border-collapse: collapse; width: 100%; font-size: 13px; margin-top: 10px; }
 th, td { border-bottom: 1px solid #eee; padding: 6px 10px; text-align: right; }
 th { background: #fafafa; text-align: right; } th:first-child, td:first-child { text-align: left; }
 .err { background: #fdecea; color: #a93226; padding: 10px 14px; border-radius: 6px; }
 .muted { color: #888; font-size: 12px; }
</style>
</head>
<body>
<h1>A股量化回测系统 · 绩效报告页</h1>
<form method="post" action="{{ url_for('run') }}">
 <div><label>策略</label>
  <select name="strategy">
   {% for s, cls in strategies.items() %}
   <option value="{{ s }}" {% if s == sel_strategy %}selected{% endif %}>{{ s }} · {{ cls.description }}</option>
   {% endfor %}
  </select></div>
 <div><label>股票(固定池)</label>
  <select name="stock">
   {% for code, name in stocks.items() %}
   <option value="{{ code }}" {% if code == sel_stock %}selected{% endif %}>{{ code }} {{ name }}</option>
   {% endfor %}
  </select></div>
 <div><label>开始日期</label><input type="date" name="start" value="{{ start }}"></div>
 <div><label>结束日期</label><input type="date" name="end" value="{{ end }}"></div>
 <div><label>参数(可选, key=value 逗号分隔)</label>
  <input type="text" name="params" size="34" placeholder="{{ placeholder }}" value="{{ params_text }}"></div>
 <button type="submit">运行回测</button>
</form>
{% if error %}<p class="err">{{ error }}</p>{% endif %}
{% if result %}
<div class="metrics">
 <div class="card"><div class="k">总收益</div><div class="v {{ 'pos' if result.m.total_return >= 0 else 'neg' }}">{{ "%.2f%%"|format(result.m.total_return*100) }}</div></div>
 <div class="card"><div class="k">年化收益</div><div class="v {{ 'pos' if result.m.annual_return >= 0 else 'neg' }}">{{ "%.2f%%"|format(result.m.annual_return*100) }}</div></div>
 <div class="card"><div class="k">最大回撤</div><div class="v neg">{{ "%.2f%%"|format(result.m.max_drawdown*100) }}</div></div>
 <div class="card"><div class="k">夏普比率</div><div class="v">{{ "%.3f"|format(result.m.sharpe) }}</div></div>
 <div class="card"><div class="k">胜率</div><div class="v">{{ "%.1f%%"|format(result.m.win_rate*100) }}</div></div>
</div>
<p class="muted">区间 {{ result.range_ }} · {{ result.m.days }} 个交易日 · {{ result.m.round_trips }} 个完整买卖回合 ·
   初始资金 100 万 · 撮合:信号收盘计算,次日开盘成交(T+1 / 涨跌停不成交 / 停牌不可交易) ·
   费用:佣金万2.5(最低5元)+ 卖出印花税万5</p>
<img class="chart" src="data:image/png;base64,{{ result.chart }}">
<h3>成交明细({{ result.trades|length }} 笔)</h3>
<table>
 <tr><th>日期</th><th>方向</th><th>价格</th><th>股数</th><th>佣金</th><th>印花税</th><th>回合盈亏</th><th>交易后现金</th></tr>
 {% for t in result.trades %}
 <tr><td>{{ t.date }}</td><td>{{ t.side }}</td><td>{{ "%.2f"|format(t.price) }}</td><td>{{ t.shares }}</td>
     <td>{{ "%.2f"|format(t.commission) }}</td><td>{{ "%.2f"|format(t.stamp_tax) }}</td>
     <td>{{ "-" if t.pnl is none else "%.2f"|format(t.pnl) }}</td><td>{{ "%.2f"|format(t.cash_after) }}</td></tr>
 {% endfor %}
</table>
{% endif %}
</body>
</html>"""


def parse_params(text: str) -> dict:
    out = {}
    for item in filter(None, (p.strip() for p in text.split(","))):
        if "=" not in item:
            raise ValueError(f"参数格式应为 key=value: {item}")
        k, v = item.split("=", 1)
        try:
            v = int(v)
        except ValueError:
            try:
                v = float(v)
            except ValueError:
                pass
        out[k] = v
    return out


@app.route("/")
def index():
    return render_page()


def render_page(**ctx):
    sel = ctx.get("form", {})
    return render_template_string(
        PAGE,
        strategies=STRATEGY_REGISTRY,
        stocks=STOCK_POOL,
        sel_strategy=sel.get("strategy", "trend"),
        sel_stock=sel.get("stock", "600519"),
        start=sel.get("start", "2019-01-01"),
        end=sel.get("end", "2024-12-31"),
        params_text=sel.get("params", ""),
        placeholder=", ".join(f"{k}={v}" for k, v in STRATEGY_REGISTRY[sel.get("strategy", "trend")].default_params.items()),
        result=ctx.get("result"),
        error=ctx.get("error"),
    )


@app.route("/run", methods=["POST"])
def run():
    form = request.form
    strategy_name = form.get("strategy", "trend")
    code = form.get("stock", "600519")
    start, end = form.get("start") or None, form.get("end") or None
    params_text = form.get("params", "").strip()
    try:
        if strategy_name not in STRATEGY_REGISTRY:
            raise ValueError(f"未知策略 {strategy_name}")
        if code not in STOCK_POOL:
            raise ValueError(f"股票 {code} 不在固定股票池")
        strategy_cls = STRATEGY_REGISTRY[strategy_name]
        params = {**strategy_cls.default_params}
        if params_text:
            params.update(parse_params(params_text))
        strategy = strategy_cls()
        data = load_clean(code)
        target = strategy.generate_target(data, params)
        res = run_backtest(data, target, code=code, start=start, end=end, config=BacktestConfig())
        log_run(code, strategy_name, params, "page", str(res.nav.index[0].date()),
                str(res.nav.index[-1].date()), {**res.metrics, "name": STOCK_POOL[code]})
        bench = load_raw_benchmark()["close"]
        title = f"{STOCK_POOL[code]} {strategy_name} {params} vs {BENCHMARK_NAME}"
        chart = base64.b64encode(nav_figure_bytes(res.nav, bench, title)).decode()
        trades = [dict(date=str(idx.date()), **{k: row[k] for k in
                  ("side", "price", "shares", "commission", "stamp_tax", "pnl", "cash_after")})
                  for idx, row in res.trades.iterrows()]
        return render_page(form=form, result=dict(
            m=res.metrics, chart=chart, trades=trades,
            range_=f"{res.nav.index[0].date()} ~ {res.nav.index[-1].date()}"))
    except Exception as exc:  # 报告页对输入容错,展示错误而不是 500
        return render_page(form=form, error=f"回测失败:{exc}")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
