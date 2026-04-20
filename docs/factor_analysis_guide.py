"""
因子分析模块使用文档

## 功能概述

factor_analysis.py 提供完整的量化因子分析功能，用于验证情绪因子的有效性。

## 核心功能

### 1. 数据聚合
从 chunk 级别聚合到公司-季度级别：
- 使用文本长度加权平均
- 保留元数据（chunk 数量、token 消耗等）

### 2. 因子统计
计算每个因子的：
- 均值、标准差
- 最小值、最大值
- 四分位数（Q1, Q2, Q3）

### 3. 相关性分析
计算因子间的相关系数矩阵，识别：
- 因子独立性
- 潜在的多重共线性

### 4. 分位数分析
将因子分为高/中/低分组：
- 对比不同分组的特征
- 识别极端值的影响

### 5. Forward Returns 模拟
模拟因子与未来收益的关系：
- 计算分位数收益率
- Long-Short 策略回报
- **注意**：当前使用模拟数据，生产环境需接入真实市场数据

### 6. 可视化
生成 9 类图表：
- 因子分布图（直方图 + KDE）
- 相关性热力图
- 分位数对比图（箱线图 + 均值）
- 因子-收益关系图（散点图 + 回归线）
- 时间序列图（如有多期数据）

## 使用方法

### 基本用法

```python
from src.factor_analysis import FactorAnalyzer

# 创建分析器
analyzer = FactorAnalyzer(
    input_file="data/processed/factor_data.parquet",
    output_dir="data/analysis"
)

# 运行完整分析
df, aggregated = analyzer.run_full_analysis()
```

### CLI 用法

```bash
# 使用默认参数
python src/factor_analysis.py

# 自定义路径
python src/factor_analysis.py \\
    --input-file data/processed/factor_data.parquet \\
    --output-dir data/analysis
```

### 演示脚本

```bash
python demo_factor_analysis.py
```

## 输出文件

### 数据文件
- `aggregated_factors.parquet`: 聚合后的公司-季度级别数据

### 图表文件
1. `factor_distributions.png`: 三个因子的分布图
2. `factor_correlation.png`: 因子相关性热力图
3. `confidence_score_quantile_comparison.png`: 信心因子分位数对比
4. `confidence_score_return_relationship.png`: 信心因子与收益关系
5. `risk_awareness_quantile_comparison.png`: 风险意识分位数对比
6. `risk_awareness_return_relationship.png`: 风险意识与收益关系
7. `strategic_shift_quantile_comparison.png`: 战略转变分位数对比
8. `strategic_shift_return_relationship.png`: 战略转变与收益关系
9. `factor_time_series.png`: 因子时间序列（如有多期）

## 分析结果解读

### 当前数据（CLF 2026Q1）

**因子统计**：
- Confidence Score: 5.17 ± 0.41 (范围: 5-6)
- Risk Awareness: 5.17 ± 0.41 (范围: 5-6)
- Strategic Shift: 5.17 ± 0.41 (范围: 5-6)

**解读**：
- 所有因子均值接近 5-6（中性偏积极）
- 标准差较小（0.41），说明管理层语气一致
- 三个因子完全相关（r=1.0），可能因为：
  1. 数据量太少（仅 6 个 chunks）
  2. 同一公司同一季度的语气一致性高
  3. 需要更多公司和时期的数据来验证因子独立性

### 生产环境建议

1. **扩大数据集**：
   - 抓取多个公司（至少 20+）
   - 覆盖多个季度（至少 4+）
   - 增加样本多样性

2. **接入真实市场数据**：
   ```python
   # 替换模拟收益率
   import yfinance as yf

   def get_forward_returns(ticker, date, horizon=30):
       stock = yf.Ticker(ticker)
       hist = stock.history(start=date, period=f"{horizon}d")
       return (hist['Close'][-1] - hist['Close'][0]) / hist['Close'][0]
   ```

3. **因子标准化**：
   ```python
   # 横截面标准化
   df['confidence_score_z'] = (df['confidence_score'] - df['confidence_score'].mean()) / df['confidence_score'].std()

   # 或使用 rank
   df['confidence_score_rank'] = df['confidence_score'].rank(pct=True)
   ```

4. **回测框架集成**：
   - Backtrader
   - Zipline
   - QuantConnect

## 扩展功能

### 添加新因子

```python
# 在 FactorAnalyzer.__init__ 中添加
self.factors = [
    'confidence_score',
    'risk_awareness',
    'strategic_shift',
    'forward_guidance',  # 新因子
    'competitive_positioning'  # 新因子
]
```

### 自定义聚合方法

```python
def custom_aggregation(self, df):
    # 例如：使用中位数而非加权平均
    return df.groupby(['ticker', 'year', 'quarter']).median()
```

### 添加新的可视化

```python
def plot_factor_heatmap_by_sector(self, df):
    # 按行业分组的因子热力图
    pivot = df.pivot_table(
        values='confidence_score',
        index='ticker',
        columns='quarter'
    )
    sns.heatmap(pivot, annot=True)
```

## 性能指标

### 当前数据集
- 输入：6 chunks
- 聚合后：1 company-quarter
- 处理时间：< 3 秒
- 生成图表：9 个 PNG 文件（~1MB 总大小）

### 预期性能（1000 chunks）
- 聚合后：~50-100 company-quarters
- 处理时间：< 10 秒
- 内存占用：< 100MB

## 故障排查

### 问题 1: 数据量不足

**症状**：
```
WARNING - Insufficient data (1 rows) for 3 quantiles, skipping
```

**解决方案**：
- 抓取更多公司的数据
- 或使用 chunk 级别数据（不聚合）

### 问题 2: 因子完全相关

**症状**：
```
Correlation Matrix:
                  confidence_score  risk_awareness  strategic_shift
confidence_score               1.0             1.0              1.0
```

**解决方案**：
- 增加数据多样性（不同公司、不同时期）
- 检查 Prompt 设计是否导致因子趋同

### 问题 3: 无法生成 KDE

**症状**：
```
WARNING - Could not plot KDE for confidence_score
```

**解决方案**：
- 需要至少 3 个数据点
- 或禁用 KDE 绘制

## 下一步

1. **因子工程**：
   - 因子标准化（Z-score, Rank）
   - 因子组合（PCA, 加权平均）
   - 动态因子（变化率、趋势）

2. **回测验证**：
   - IC (Information Coefficient)
   - IR (Information Ratio)
   - Sharpe Ratio
   - 最大回撤

3. **策略构建**：
   - Long-Short 策略
   - 因子轮动
   - 多因子组合

4. **风险管理**：
   - 因子暴露控制
   - 行业中性化
   - 市值中性化
"""

if __name__ == "__main__":
    print(__doc__)
