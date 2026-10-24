# A股量化回测系统

基于 A 股日线数据(2019-01-01 ~ 2024-12-31,前复权)的量化回测工具,支持**趋势跟踪(双均线)、均值回复(布林带)、多因子打分**三种策略,含数据校验清洗、统一撮合回测引擎、绩效分析、网格寻优与样本外验证、实验记录自动导出与 Flask 绩效报告页。

## 快速开始(未配置电脑约 5 分钟)

```bash
# 1. 安装 uv(Windows PowerShell,已装可跳过)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. 项目目录下一键创建环境并按 uv.lock 安装依赖
uv sync

# 3a. 双击启动绩效报告页(或) 3b. 命令行运行回测
启动.bat
uv run python main.py backtest --strategy trend --stock 600519 --start 2019-01-01 --end 2024-12-31
```

无 uv 备选:`pip install -r requirements.txt`(Python ≥ 3.10),再 `python app.py` 或 `python main.py ...`。

## 常用命令

| 命令 | 作用 |
|------|------|
| `uv run python main.py validate` | 数据校验与清洗,产出校验报告与 cleaned 数据 |
| `uv run python main.py backtest --strategy <trend/meanrev/multifactor> --stock <代码> --start ... --end ... [--param fast=5]` | 单次回测,输出指标与净值图 |
| `uv run python main.py optimize --strategy trend --stock 600519 --param-grid fast=5,10 --param-grid slow=20,30` | 网格寻优(样本内/外切分) |
| `uv run python scripts/run_experiments.py` | 批量实验:全策略 × 10 股 × 网格 |
| `uv run python scripts/finalize.py` | 由实验记录生成 strategy/strategy.json |
| `uv run python scripts/test_engine.py` | 回测引擎手工对账测试(26 项断言) |

## 关键口径(与任务书一致)

- **撮合**:信号当日收盘计算、次日开盘价成交;T+1;开盘触涨停禁买/触跌停禁卖;停牌不可交易;未成交指令作废
- **费用**:佣金 max(成交额×0.025%, 5 元) 双边 + 卖出印花税×0.05%;初始资金 100 万;整手(100 股)交易
- **指标**:年化按 252 交易日折算;夏普无风险利率取 0、日收益样本标准差;胜率按完整买卖回合(双边费用计入)
- **样本切分**:样本内 2019-01-01~2022-12-31(调参),样本外 2023-01-01~2024-12-31(检验)
- **选优**:按任务书附录口径选**样本外表现最好**的组合(样本外年化最高,并列取夏普);因此 strategy.json 的样本内指标可能弱于样本外,属口径使然
- **数据**:固定股票池 10 只;官方数据包到位前以 BaoStock 前复权日线为开发占位(来源注明见 `data/raw/baostock/来源说明.txt`),官方数据放入 `data/raw/official/` 后以官方为准
- **实验记录**:每次回测自动落一条 `records/experiments.csv`(重复实验不重复落盘);寻优对比见 `records/对比结果.csv`;两者均由程序导出

## 目录结构

```
main.py / app.py        CLI 入口 / Flask 绩效报告页
启动.bat                 一键启动报告页(缺环境自动 uv sync)
backtest/               loader(加载) validate(校验) clean(清洗) engine(撮合引擎)
                        metrics(指标) optimizer(寻优) records(实验记录)
strategies/             trend 双均线 | meanrev 布林带 | multifactor 多因子打分
report/render.py        净值 vs 沪深300 图表
data/                   raw 原始数据 | cleaned 清洗后 | report 校验报告
records/                experiments.csv 实验记录 | 对比结果.csv(自动导出)
strategy/strategy.json  自研最优配置(样本内外指标)
scripts/                数据下载/校验清洗/引擎测试/批量实验/定稿
demo/                   关键截图(另见演示)
```

## 复现说明

`uv sync` 后逐条执行上表命令即可完整复现:校验报告 → 单次回测 → 网格寻优 → 批量实验 → strategy.json → 报告页。实验记录与对比结果由平台自动导出,与 .git 提交历史交叉可溯。
