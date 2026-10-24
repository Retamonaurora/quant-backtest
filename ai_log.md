# AI 使用记录

| 日期 | 工具 | 用途说明 |
|------|------|----------|
| 2026-10-24 | ZCode(CLI) | 通读任务书并制定实现计划(PLAN.md:梳理/排期/SOP/MVP) |
| 2026-10-24 | ZCode(CLI) | 项目骨架搭建:uv 环境配置(pyproject/uv.lock)、目录结构、.gitignore、README、占位数据下载脚本 |
| 2026-10-24 | ZCode(CLI) | 占位数据下载:akshare 东财接口在本机网络不可用,改用任务书备选源 BaoStock 拉取 10 股+沪深300(2019-2024,前复权,含 preclose/tradestatus/pctChg 校验字段) |
| 2026-10-24 | ZCode(CLI) | D2 数据校验与清洗模块:loader/validate/clean 三模块 + prepare_data 脚本;七项校验(重复/缺失/OHLC逻辑/涨跌幅越界/字段一致性/量异常)+ 停牌规范化与缺口补行;校验报告与清洗后 CSV 已导出,人工抽查长江电力/海康威视停牌行通过 |
| 2026-10-24 | ZCode(CLI) | D3 回测引擎与指标:engine(统一撮合:信号收盘算次日开盘成交、T+1、开盘触板不成交、停牌禁交易、佣金/印花税、整手递减)+ metrics(年化/回撤/夏普/胜率);scripts/test_engine.py 六组用例 26 项断言全部 PASS(A 费用手算对账、B 涨停禁买、C 停牌、D 跌停禁卖、E 信号时序、F 真实数据独立重算) |
| 2026-10-24 | ZCode(CLI) | D4 双均线策略与 CLI:engine 循环重构为 itertuples(26 断言复验 PASS);strategies/base 注册表 + trend 双均线;report/render 净值图 vs 沪深300(中文字体);main.py backtest/validate 子命令;600519 全区间端到端跑通(年化 +6.82%,回撤 40.39%,夏普 0.426) |
