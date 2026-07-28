# GeneTrader 项目战略分析报告

> 日期: 2026-02-26
> 分析范围: 全项目代码审查 + 策略优化建议
>
> **注意**：这是一份时点报告。原第 4 节（实盘部署）和第 5 节（Agent 集成）
> 描述的自适应/部署/API 子系统已于 2026-07 移除——它从未在生产运行过，
> 而实盘由人工维护。这两节已删除；其余关于选币、参数与验证的建议仍然适用。

---

## 1. 选什么策略优化

### 当前策略: GeneStrategy

项目核心策略文件 `strategies/GeneStrategy.py` 是一个综合性多信号入场策略，包含以下子模块：

| 子策略模块 | 技术指标 | 特点 |
|-----------|---------|------|
| **NFINext44** | EMA offset + EWO + CTI + Williams%R 1h | 趋势回调入场 |
| **NFINext37** | EMA offset + EWO + RSI + CTI | 动量确认入场 |
| **NFINext7** | EMA open mult + CTI | 开盘价偏差入场 |
| **ClucHA** | BB delta + Heikin-Ashi | 波动率收窄入场 |
| **Local Uptrend** | EMA diff + BB factor | 局部上升趋势入场 |
| **SMAOffset** | SMA + low/high offset | 均线偏移入场/出场 |
| **Deadfish** | BB width + volume factor | 低活跃度止损退出 |

### 优化建议

- 可优化参数约 **30+ 个**（IntParameter + DecimalParameter），搜索空间很大
- **建议优先用 Optuna** (`optimizer_type: "optuna"`) — 对 30+ 参数的高维搜索空间，TPE 比 GA 收敛更快
- 不建议从零写新策略，应在 GeneStrategy 基础上优化
- 通过 `fix_pairs: false` 同时优化交易对选择

---

## 2. 选什么代币

### 当前选币机制

`scripts/get_pairs.py` 支持两种模式：
- `--mode all`: 所有 Binance USDT 交易对
- `--mode volume`: 按交易量排名前 N 个（默认 100）

### 推荐选币策略

**初始优化阶段用 30 个高流动性代币：**
```bash
python scripts/get_pairs.py --mode volume --top-n 30
```

**让 GA 自动选择最优子集：**
```json
{
  "fix_pairs": false,
  "num_pairs": 8
}
```

**币种类型建议：**
- 大盘币：BTC, ETH, SOL（稳定性好）
- 中盘高波动：DOGE, PEPE, AVAX, LINK, SUI, NEAR（机会多）
- 避免山寨小币（流动性差，退市风险）

**维护黑名单：**
- 定期更新 `data/delisted_coins.json`
- 运行 `--check-delistings` 检查退市公告

---

## 3. 如何更好的优化

### 推荐配置

```json
{
  "enable_walk_forward": true,
  "walk_forward_method": "rolling",
  "walk_forward_train_weeks": 26,
  "walk_forward_test_weeks": 4,
  "total_data_weeks": 52,
  "max_drawdown_limit": 0.25,
  "min_profit_factor": 1.2,
  "min_win_rate": 0.40,
  "enable_diversity_selection": true,
  "diversity_selection_weight": 0.3
}
```

### Fitness 函数权重调优建议

当前 (`strategy/evaluation.py`):
- 利润 25% + 风险调整 25% + 回撤 15% + 胜率 10% + 频率 10% + 统计 10% + 时间 5%

建议:
- 增大 **风险调整收益** 到 30%（Sharpe/Sortino 对实盘最重要）
- 增大 **回撤惩罚** 到 20%
- 降低 **利润** 到 20%（过分追求利润易过拟合）

### 优化流程

1. Optuna 粗搜索（500 trials）
2. GA 精细搜索（在 Optuna 最优解附近）
3. Walk-Forward 验证
4. Monte Carlo robustness 测试
5. robustness_score >= 0.7 才考虑上线

---

## 总结

GeneTrader 的核心竞争力是参数搜索本身：
- GA + Optuna 双优化引擎
- 防过拟合体系（淘汰阈值、walk-forward、选择门槛）

最大改进空间在实践层面：选好币、调好权重、充分验证。
