# AI 使用记录

| 日期 | 工具 | 用途说明 |
|------|------|----------|
| 2026-10-24 | ZCode(CLI) | 通读任务书并制定实现计划(PLAN.md:梳理/排期/SOP/MVP) |
| 2026-10-24 | ZCode(CLI) | 项目骨架搭建:uv 环境配置(pyproject/uv.lock)、目录结构、.gitignore、README、占位数据下载脚本 |
| 2026-10-24 | ZCode(CLI) | 占位数据下载:akshare 东财接口在本机网络不可用,改用任务书备选源 BaoStock 拉取 10 股+沪深300(2019-2024,前复权,含 preclose/tradestatus/pctChg 校验字段) |
| 2026-10-24 | ZCode(CLI) | D2 数据校验与清洗模块:loader/validate/clean 三模块 + prepare_data 脚本;七项校验(重复/缺失/OHLC逻辑/涨跌幅越界/字段一致性/量异常)+ 停牌规范化与缺口补行;校验报告与清洗后 CSV 已导出,人工抽查长江电力/海康威视停牌行通过 |
| 2026-10-24 | ZCode(CLI) | D3 回测引擎与指标:engine(统一撮合:信号收盘算次日开盘成交、T+1、开盘触板不成交、停牌禁交易、佣金/印花税、整手递减)+ metrics(年化/回撤/夏普/胜率);scripts/test_engine.py 六组用例 26 项断言全部 PASS(A 费用手算对账、B 涨停禁买、C 停牌、D 跌停禁卖、E 信号时序、F 真实数据独立重算) |
| 2026-10-24 | ZCode(CLI) | D4 双均线策略与 CLI:engine 循环重构为 itertuples(26 断言复验 PASS);strategies/base 注册表 + trend 双均线;report/render 净值图 vs 沪深300(中文字体);main.py backtest/validate 子命令;600519 全区间端到端跑通(年化 +6.82%,回撤 40.39%,夏普 0.426) |
| 2026-10-24 | ZCode(CLI) | D5 网格寻优与实验记录:backtest/records(自动落盘 experiments.csv,重复实验去重;对比结果.csv 带 run_id 追加)+ backtest/optimizer(样本内 2019-2022/样本外 2023-2024 切分,任务书附录口径按样本外年化选优);main.py optimize 子命令;修复 code 列 dtype 导致的去重失效 |
| 2026-10-24 | ZCode(CLI) | D6 布林带均值回复:strategies/meanrev(跌破下轨买入/涨破上轨卖出,ddof=0 经典口径)+ scripts/run_experiments 批量实验脚本;trend+meanrev × 10 股全量寻优,累计 480 条真实变化实验(目标 ≥60 已超额);样本外结论符合直觉:趋势策略在工行/长电为正,均值回复在恒瑞/长电为正,万科/中免皆负 |
| 2026-10-24 | ZCode(CLI) | D7 多因子打分:strategies/multifactor(动量+低波动滚动 z-score 加权合成,状态机阈值交易);× 10 股寻优后累计 640 条真实变化实验、3 策略、10 股全覆盖(要求 ≥60 条/≥6 股);样本外最优:平安 +32.48%、工行 +23.34% |
| 2026-10-24 | ZCode(CLI) | D8 绩效报告页:app.py(策略/股票/日期/参数表单 → 四大指标卡 + 净值 vs 沪深300 内嵌图 + 成交明细,页面回测与 CLI 结果一致);render 增加内存图像输出;启动.bat 一键启动(自动 uv sync);demo/ 三张关键截图(三策略各一);修复模板渲染与暗色模式背景 |
| 2026-10-24 | ZCode(CLI) | D9 定稿:scripts/finalize.py 从实验记录按任务书口径(样本外年化最高,并列取夏普)选出全局最优(多因子 · 中国平安,样本外年化 +32.48%/夏普 1.350),重新回测生成 strategy/strategy.json;README 定稿(快速开始/命令表/口径说明);提交信息.txt 生成(个人信息待补);成果清单核对 12 项全齐,实验 649 条/10 股/3 策略,引擎 26 项对账复验通过 |
