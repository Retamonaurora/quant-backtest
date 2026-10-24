# A股量化回测系统

基于 A 股日线数据的量化回测工具(瑞翼工坊 · 量化交易方向招新二轮):数据校验清洗 → 统一撮合回测 → 绩效分析 → 网格寻优 → 样本外验证,全程 Git 留痕、实验自动落盘。

覆盖任务书固定股票池 10 只 · 三种策略 · **649 条真实变化实验**(要求 ≥60)· 引擎 26 项手工对账断言全通过。

## 快速开始(未配置电脑约 5 分钟)

```bash
# 1. 安装 uv(Windows PowerShell;已装可跳过)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. 项目根目录下一键建环境并按 uv.lock 装依赖
uv sync

# 3. 双击 启动.bat 打开绩效报告页,或命令行回测:
uv run python main.py backtest --strategy trend --stock 600519 --start 2019-01-01 --end 2024-12-31
```

无 uv 备选:`pip install -r requirements.txt`(Python ≥ 3.10),再 `python app.py` 或 `python main.py ...`。

## 成果与任务书要求对照

| 任务书要求 | 实现 | 自验方式 |
|---|---|---|
| 三种策略,类型与参数可配置 | `strategies/`:trend 双均线、meanrev 布林带、multifactor 多因子打分,注册表统一管理 | CLI `--strategy` 任意切换 |
| 数据校验与清洗,输出报告 | `backtest/validate.py` 七项校验、`clean.py` 停牌规范化/缺口补行/异常修复 | `data/report/validation_report.md` |
| 回测引擎(撮合规则不得更改) | `backtest/engine.py`:信号收盘算→次日开盘成交,T+1,开盘触涨跌停不成交,停牌禁交易,佣金万2.5(最低5元)+卖出印花税万5,整手交易,初始 100 万 | `scripts/test_engine.py` 六组用例 26 项断言(手算对账) |
| 绩效分析 + 净值 vs 沪深300 | `backtest/metrics.py` 年化/最大回撤/夏普/胜率;`report/render.py` 净值与回撤图;`app.py` 报告页 | CLI 输出 + `output/*.png` + 报告页 |
| 网格寻优,样本内外切分 | `backtest/optimizer.py`:样本内 2019~2022 / 样本外 2023~2024,选**样本外最优**(任务书附录口径) | `uv run python main.py optimize ...` |
| 实验记录自动导出,≥60 条覆盖 ≥6 股 | `backtest/records.py`:每次回测自动落 `records/experiments.csv`(重复实验去重),寻优对比写 `records/对比结果.csv` | `uv run python scripts/run_experiments.py` 一键复现全部实验 |
| 一键启动 / 10 分钟复现 | `启动.bat`(缺环境自动 `uv sync`)、本 README、uv.lock 锁定依赖 | 换机按"快速开始"实测 |

## 三种策略

| 策略 | 规则 | 默认参数 |
|---|---|---|
| `trend` 趋势跟踪 | 短期均线上穿长期均线(金叉)持股,死叉空仓 | fast=5, slow=20 |
| `meanrev` 均值回复 | 布林带:收盘跌破下轨买入,涨破上轨卖出 | window=20, num_std=2.0 |
| `multifactor` 多因子打分 | 动量 + 低波动两因子滚动 z-score 加权合成,总分>买入阈值持股、<卖出阈值清仓 | mom=20, vol=20, z=60, buy=0.5, sell=-0.3 |

## 自研最优配置(`strategy/strategy.json`,由 `scripts/finalize.py` 自动生成)

**多因子打分 · 中国平安(601318)**,参数 mom_window=20 / vol_window=20 / buy_th=0.3:

- 样本内(2019~2022):年化 -1.55%,最大回撤 40.49%,夏普 0.012
- 样本外(2023~2024):**年化 +32.48%,最大回撤 22.29%,夏普 1.350,胜率 70%**

> 样本内弱、样本外强是任务书附录"选样本外表现最好的组合"口径下的真实结果(该策略恰在样本外区间有效),全部组合的样本内外指标见 `records/对比结果.csv` 可复核;这一反差也提示样本外选择隐含的过拟合风险。

## 关键口径

- **撮合**:信号当日收盘计算、次日开盘价成交;T+1;开盘触涨停禁买/触跌停禁卖;停牌不可交易;未成交指令作废
- **费用**:佣金 max(成交额×0.025%, 5 元) 双边 + 卖出印花税×0.05%;金额按分取整;100 股整手
- **指标**:年化按 252 交易日折算;夏普无风险利率取 0、日收益样本标准差(ddof=1);胜率按完整买卖回合(双边费用计入)
- **实验真实性**:同一(策略, 参数, 股票, 窗口)组合只落盘一次,文件中每行均为真实变化实验

## 数据

- 固定股票池 10 只(600519/601318/601398/600900/000002/600276/002415/002594/600111/601888),基准沪深300
- 任务书实验区间 **2019-01-01 ~ 2024-12-31**(前复权);官方数据包到位前以 BaoStock 为开发占位(来源注明见 `data/raw/baostock/来源说明.txt`),官方数据放入 `data/raw/official/` 后以官方为准(切换仅需改 `backtest/loader.py` 解析部分)
- 已扩充下载至最新交易日(2026-10-23,共 1892 个交易日)供延展分析;寻优/实验/strategy.json 固定在任务书区间,经逐位复验不受扩充影响

## 目录结构

```
main.py / app.py        CLI 入口 / Flask 绩效报告页(启动.bat 一键启动)
backtest/               loader 加载 | validate 校验 | clean 清洗 | engine 撮合引擎
                        metrics 指标 | optimizer 寻优 | records 实验记录
strategies/             trend | meanrev | multifactor(+ base 注册表)
report/render.py        净值 vs 沪深300 图表
data/                   raw 原始 | cleaned 清洗后 | report 校验报告
records/                experiments.csv 实验记录 | 对比结果.csv(均自动导出)
strategy/strategy.json  自研最优配置(含样本内外指标)
scripts/                download_data | prepare_data | test_engine | run_experiments | finalize
demo/                   关键截图(三策略回测各一)
```

## 常见问题

- **报告页打不开**:确认 5000 端口未被占用(`netstat -ano | findstr :5000`),或重跑 `启动.bat`
- **pip 装包失败**:本项目默认阿里云镜像;手动安装时加 `-i https://mirrors.aliyun.com/pypi/simple/`
- **图表中文乱码**:已内置微软雅黑/黑体配置;若系统无中文字体请先安装
- **想重跑全部实验**:`uv run python scripts/run_experiments.py`(约 1~2 分钟,自动去重落盘)

## 复现与追溯

`uv sync` 后按"快速开始"与上表命令可完整复现:校验报告 → 单次回测 → 网格寻优 → 批量实验 → strategy.json → 报告页。数据、实验记录、.git 提交历史三方交叉可溯;除 ai_log.md / README.md / 提交信息.txt 外,全部材料由程序自动导出。
