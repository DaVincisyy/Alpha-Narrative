"""
因子分析演示脚本
使用 chunk 级别数据展示分析功能
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from factor_analysis import FactorAnalyzer
import pandas as pd

print("=" * 70)
print("FACTOR ANALYSIS DEMO")
print("=" * 70)

# 使用 chunk 级别数据（更多样性）
analyzer = FactorAnalyzer(
    input_file="data/processed/factor_data.parquet",
    output_dir="data/analysis"
)

# 加载数据
df = analyzer.load_data()

print(f"\nLoaded {len(df)} chunks")
print(f"\nFactor summary:")
for factor in analyzer.factors:
    print(f"  {factor}: mean={df[factor].mean():.2f}, std={df[factor].std():.2f}, range=[{df[factor].min()}, {df[factor].max()}]")

# 计算统计量
stats = analyzer.compute_factor_statistics(df)

# 因子相关性
corr_matrix = analyzer.cross_factor_correlation(df)

# 分位数分析（使用 chunk 级别数据）
for factor in analyzer.factors:
    df = analyzer.quantile_analysis(df, factor, n_quantiles=2)  # 2 分位（高/低）

# 模拟 forward returns
for factor in analyzer.factors:
    df = analyzer.simulate_forward_returns(df, factor, n_quantiles=2)

# 生成图表
print("\nGenerating visualizations...")
analyzer.plot_factor_distributions(df)
analyzer.plot_factor_correlation_heatmap(corr_matrix)

for factor in analyzer.factors:
    analyzer.plot_quantile_comparison(df, factor)
    analyzer.plot_factor_return_relationship(df, factor)

# 聚合分析
aggregated = analyzer.aggregate_by_company_quarter(df)
print(f"\nAggregated to {len(aggregated)} company-quarter observations")
print(aggregated[['ticker', 'year', 'quarter', 'confidence_score', 'risk_awareness', 'strategic_shift']])

# 保存结果
output_path = analyzer.output_dir / 'aggregated_factors.parquet'
aggregated.to_parquet(output_path, index=False)
print(f"\nSaved aggregated data to {output_path}")

print("\n" + "=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)
print(f"\nCheck {analyzer.output_dir} for:")
print("  - aggregated_factors.parquet")
print("  - factor_distributions.png")
print("  - factor_correlation.png")
print("  - *_quantile_comparison.png")
print("  - *_return_relationship.png")
