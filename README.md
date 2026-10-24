# A股量化回测系统

基于 A 股日线数据(2019-01-01 ~ 2024-12-31,前复权)的量化回测工具,支持**趋势跟踪、均值回复、多因子打分**三种策略,含数据校验清洗、统一撮合回测引擎、绩效分析、网格寻优与样本外验证。

> 状态:骨架搭建中(2026-10-24),功能按 PLAN.md 排期开发。

## 环境配置(未配置电脑约 5 分钟)

使用 [uv](https://docs.astral.sh/uv/) 管理(推荐):

```bash
# 1. 安装 uv(Windows PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. 在项目目录下一键创建虚拟环境并按 uv.lock 安装依赖
uv sync

# 3. 验证
uv run main.py --help
```

无 uv 时的备选方案(Python ≥ 3.10):

```bash
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

## 运行(开发中)

- CLI 回测:`uv run main.py`(参数说明待实现)
- 绩效报告页:`uv run app.py`(待实现)

## 项目结构

```
main.py          CLI 入口
backtest/        引擎:数据加载/校验/清洗/撮合/指标/寻优
strategies/      三种策略:趋势跟踪 / 均值回复 / 多因子打分
data/            raw 官方原始数据 | cleaned 清洗后 | report 校验报告
records/         实验记录(自动导出)
strategy/        自研最优配置 strategy.json
```

数据说明:回测一律以官方数据包为准(data/raw/official/,到位后放入);data/raw/baostock/ 为官方包到位前的开发占位数据,来源 BaoStock(baostock.com),仅用于流程开发与交叉校验,须在提交说明中注明。本机网络下 akshare 东财接口不可用,故采用任务书列明的备选源。
