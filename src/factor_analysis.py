"""
Factor Analysis Module
量化因子分析：验证情绪因子的有效性
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/factor_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 设置绘图样式
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']  # 支持中文
plt.rcParams['axes.unicode_minus'] = False


@dataclass
class FactorStats:
    """因子统计数据"""
    mean: float
    std: float
    min: float
    max: float
    q25: float
    q50: float
    q75: float

    @classmethod
    def from_series(cls, series: pd.Series) -> 'FactorStats':
        """从 pandas Series 创建统计数据"""
        return cls(
            mean=series.mean(),
            std=series.std(),
            min=series.min(),
            max=series.max(),
            q25=series.quantile(0.25),
            q50=series.quantile(0.50),
            q75=series.quantile(0.75)
        )


class FactorAnalyzer:
    """因子分析器"""

    def __init__(
        self,
        input_file: str = "data/processed/factor_data.parquet",
        output_dir: str = "data/analysis"
    ):
        """
        Args:
            input_file: 输入的因子数据文件
            output_dir: 输出目录（保存分析结果和图表）
        """
        self.input_file = Path(input_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 因子列表
        self.factors = ['confidence_score', 'risk_awareness', 'strategic_shift']

        logger.info(f"Initialized FactorAnalyzer: input={input_file}, output={output_dir}")

    def load_data(self) -> pd.DataFrame:
        """加载因子数据"""
        logger.info(f"Loading data from {self.input_file}")
        df = pd.read_parquet(self.input_file)
        logger.info(f"Loaded {len(df)} rows, {len(df['ticker'].unique())} unique tickers")
        return df

    def aggregate_by_company_quarter(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        按公司-季度聚合因子

        从 chunk 级别 → 公司-季度级别
        使用加权平均（按文本长度加权）
        """
        logger.info("Aggregating factors by company-quarter")

        # 计算文本长度作为权重
        df['text_length'] = df['text'].str.len()

        # 按 ticker-year-quarter 分组
        agg_dict = {
            'confidence_score': lambda x: np.average(x, weights=df.loc[x.index, 'text_length']),
            'risk_awareness': lambda x: np.average(x, weights=df.loc[x.index, 'text_length']),
            'strategic_shift': lambda x: np.average(x, weights=df.loc[x.index, 'text_length']),
            'chunk_id': 'count',  # 记录 chunk 数量
            'text_length': 'sum',  # 总文本长度
            'tokens_used': 'sum',  # 总 token 消耗
            'model_name': 'first',
            'prompt_version': 'first'
        }

        aggregated = df.groupby(['ticker', 'year', 'quarter']).agg(agg_dict).reset_index()

        # 重命名列
        aggregated.rename(columns={'chunk_id': 'num_chunks'}, inplace=True)

        logger.info(f"Aggregated to {len(aggregated)} company-quarter observations")

        return aggregated

    def compute_factor_statistics(self, df: pd.DataFrame) -> Dict[str, FactorStats]:
        """计算因子统计量"""
        logger.info("Computing factor statistics")

        stats = {}
        for factor in self.factors:
            stats[factor] = FactorStats.from_series(df[factor])
            logger.info(f"{factor}: mean={stats[factor].mean:.2f}, std={stats[factor].std:.2f}")

        return stats

    def quantile_analysis(
        self,
        df: pd.DataFrame,
        factor: str,
        n_quantiles: int = 3
    ) -> pd.DataFrame:
        """
        分位数分析

        将因子分为 n 个分位数（如 3 分位：低/中/高）
        分析不同分位数的特征
        """
        logger.info(f"Performing quantile analysis for {factor} (n={n_quantiles})")

        # 检查数据量是否足够
        if len(df) < n_quantiles:
            logger.warning(f"Insufficient data ({len(df)} rows) for {n_quantiles} quantiles, skipping")
            return df

        try:
            # 计算分位数标签
            df[f'{factor}_quantile'] = pd.qcut(
                df[factor],
                q=n_quantiles,
                labels=[f'Q{i+1}' for i in range(n_quantiles)],
                duplicates='drop'
            )

            # 按分位数分组统计
            quantile_stats = df.groupby(f'{factor}_quantile').agg({
                factor: ['mean', 'std', 'count'],
                'ticker': 'nunique'
            }).round(2)

            logger.info(f"\n{quantile_stats}")

        except ValueError as e:
            logger.warning(f"Could not create quantiles for {factor}: {e}")
            # 如果无法创建分位数，使用简单分组
            df[f'{factor}_quantile'] = 'Q1'

        return df

    def cross_factor_correlation(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算因子间相关性"""
        logger.info("Computing cross-factor correlation")

        corr_matrix = df[self.factors].corr()
        logger.info(f"\nCorrelation Matrix:\n{corr_matrix}")

        return corr_matrix

    def plot_factor_distributions(self, df: pd.DataFrame, save: bool = True):
        """绘制因子分布图"""
        logger.info("Plotting factor distributions")

        # 检查数据量
        if len(df) < 2:
            logger.warning(f"Insufficient data ({len(df)} rows) for distribution plot, skipping")
            return

        fig, axes = plt.subplots(1, 3, figsize=(15, 4))

        for i, factor in enumerate(self.factors):
            ax = axes[i]

            # 直方图
            df[factor].hist(bins=min(10, len(df)), alpha=0.6, ax=ax, edgecolor='black')

            # KDE（仅当数据足够时）
            if len(df) >= 3:
                try:
                    df[factor].plot(kind='kde', ax=ax, secondary_y=True, color='red', linewidth=2)
                except Exception as e:
                    logger.warning(f"Could not plot KDE for {factor}: {e}")

            ax.set_title(f'{factor.replace("_", " ").title()} Distribution')
            ax.set_xlabel('Score')
            ax.set_ylabel('Frequency')
            ax.grid(True, alpha=0.3)

            # 添加统计信息
            mean = df[factor].mean()
            ax.axvline(mean, color='green', linestyle='--', linewidth=2, label=f'Mean: {mean:.2f}')
            ax.legend()

        plt.tight_layout()

        if save:
            output_path = self.output_dir / 'factor_distributions.png'
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved plot to {output_path}")

        plt.close()

    def plot_factor_correlation_heatmap(self, corr_matrix: pd.DataFrame, save: bool = True):
        """绘制因子相关性热力图"""
        logger.info("Plotting correlation heatmap")

        fig, ax = plt.subplots(figsize=(8, 6))

        sns.heatmap(
            corr_matrix,
            annot=True,
            fmt='.2f',
            cmap='coolwarm',
            center=0,
            square=True,
            linewidths=1,
            cbar_kws={"shrink": 0.8},
            ax=ax
        )

        ax.set_title('Factor Correlation Matrix', fontsize=14, fontweight='bold')

        plt.tight_layout()

        if save:
            output_path = self.output_dir / 'factor_correlation.png'
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved plot to {output_path}")

        plt.close()

    def plot_quantile_comparison(
        self,
        df: pd.DataFrame,
        factor: str,
        save: bool = True
    ):
        """绘制分位数对比图"""
        logger.info(f"Plotting quantile comparison for {factor}")

        quantile_col = f'{factor}_quantile'
        if quantile_col not in df.columns:
            logger.warning(f"Quantile column {quantile_col} not found, skipping plot")
            return

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # 左图：箱线图
        ax1 = axes[0]
        df.boxplot(column=factor, by=quantile_col, ax=ax1)
        ax1.set_title(f'{factor.replace("_", " ").title()} by Quantile')
        ax1.set_xlabel('Quantile')
        ax1.set_ylabel('Score')
        plt.sca(ax1)
        plt.xticks(rotation=0)

        # 右图：均值对比
        ax2 = axes[1]
        quantile_means = df.groupby(quantile_col)[factor].mean()
        quantile_means.plot(kind='bar', ax=ax2, color='steelblue', edgecolor='black')
        ax2.set_title(f'Mean {factor.replace("_", " ").title()} by Quantile')
        ax2.set_xlabel('Quantile')
        ax2.set_ylabel('Mean Score')
        ax2.grid(True, alpha=0.3)
        plt.sca(ax2)
        plt.xticks(rotation=0)

        plt.tight_layout()

        if save:
            output_path = self.output_dir / f'{factor}_quantile_comparison.png'
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved plot to {output_path}")

        plt.close()

    def plot_time_series(self, df: pd.DataFrame, save: bool = True):
        """绘制因子时间序列（如果有多个时期）"""
        logger.info("Plotting factor time series")

        # 创建时间索引
        df['period'] = df['year'].astype(str) + df['quarter']

        if len(df['period'].unique()) < 2:
            logger.info("Only one time period, skipping time series plot")
            return

        fig, ax = plt.subplots(figsize=(12, 6))

        for factor in self.factors:
            period_means = df.groupby('period')[factor].mean()
            period_means.plot(ax=ax, marker='o', linewidth=2, label=factor.replace('_', ' ').title())

        ax.set_title('Factor Evolution Over Time', fontsize=14, fontweight='bold')
        ax.set_xlabel('Period')
        ax.set_ylabel('Average Score')
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save:
            output_path = self.output_dir / 'factor_time_series.png'
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved plot to {output_path}")

        plt.close()

    def simulate_forward_returns(
        self,
        df: pd.DataFrame,
        factor: str,
        n_quantiles: int = 3
    ) -> pd.DataFrame:
        """
        模拟 forward returns 分析

        注意：这是模拟数据，实际应用需要接入真实市场数据
        """
        logger.info(f"Simulating forward returns for {factor}")
        logger.warning("Using SIMULATED returns - replace with real market data in production")

        # 模拟收益率：高因子分数 → 略高收益（仅用于演示）
        np.random.seed(42)

        # 基础收益率：正态分布
        base_returns = np.random.normal(0.02, 0.10, len(df))

        # 因子效应：标准化因子 * 小系数
        factor_normalized = (df[factor] - df[factor].mean()) / df[factor].std()
        factor_effect = factor_normalized * 0.03  # 3% 因子效应

        # 总收益率
        df['simulated_forward_return'] = base_returns + factor_effect

        # 按分位数分析收益率
        quantile_col = f'{factor}_quantile'
        if quantile_col in df.columns:
            return_by_quantile = df.groupby(quantile_col)['simulated_forward_return'].agg([
                'mean', 'std', 'count'
            ]).round(4)

            logger.info(f"\nSimulated Returns by {factor} Quantile:\n{return_by_quantile}")

            # 计算 long-short 收益
            if len(return_by_quantile) >= 2:
                long_short = return_by_quantile.iloc[-1]['mean'] - return_by_quantile.iloc[0]['mean']
                logger.info(f"Long-Short Return (Q{len(return_by_quantile)} - Q1): {long_short:.4f}")

        return df

    def plot_factor_return_relationship(
        self,
        df: pd.DataFrame,
        factor: str,
        save: bool = True
    ):
        """绘制因子与收益率关系图"""
        if 'simulated_forward_return' not in df.columns:
            logger.warning("No forward returns found, skipping plot")
            return

        logger.info(f"Plotting factor-return relationship for {factor}")

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # 左图：散点图 + 回归线
        ax1 = axes[0]
        ax1.scatter(df[factor], df['simulated_forward_return'], alpha=0.6)

        # 添加回归线
        z = np.polyfit(df[factor], df['simulated_forward_return'], 1)
        p = np.poly1d(z)
        x_line = np.linspace(df[factor].min(), df[factor].max(), 100)
        ax1.plot(x_line, p(x_line), "r--", linewidth=2, label=f'y={z[0]:.4f}x+{z[1]:.4f}')

        ax1.set_title(f'{factor.replace("_", " ").title()} vs Forward Return')
        ax1.set_xlabel(factor.replace("_", " ").title())
        ax1.set_ylabel('Simulated Forward Return')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 右图：分位数收益率对比
        ax2 = axes[1]
        quantile_col = f'{factor}_quantile'
        if quantile_col in df.columns:
            quantile_returns = df.groupby(quantile_col)['simulated_forward_return'].mean()
            quantile_returns.plot(kind='bar', ax=ax2, color='steelblue', edgecolor='black')
            ax2.set_title(f'Mean Return by {factor.replace("_", " ").title()} Quantile')
            ax2.set_xlabel('Quantile')
            ax2.set_ylabel('Mean Simulated Return')
            ax2.axhline(0, color='red', linestyle='--', linewidth=1)
            ax2.grid(True, alpha=0.3)
            plt.sca(ax2)
            plt.xticks(rotation=0)

        plt.tight_layout()

        if save:
            output_path = self.output_dir / f'{factor}_return_relationship.png'
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved plot to {output_path}")

        plt.close()

    def generate_summary_report(
        self,
        df: pd.DataFrame,
        aggregated: pd.DataFrame,
        stats: Dict[str, FactorStats]
    ) -> str:
        """生成分析报告"""
        logger.info("Generating summary report")

        report = []
        report.append("=" * 70)
        report.append("FACTOR ANALYSIS REPORT")
        report.append("=" * 70)
        report.append("")

        # 数据概览
        report.append("## Data Overview")
        report.append(f"- Total chunks: {len(df)}")
        report.append(f"- Company-quarter observations: {len(aggregated)}")
        report.append(f"- Unique tickers: {df['ticker'].nunique()}")
        report.append(f"- Time periods: {df['year'].nunique()} years, {df['quarter'].nunique()} quarters")
        report.append("")

        # 因子统计
        report.append("## Factor Statistics")
        for factor, stat in stats.items():
            report.append(f"\n### {factor.replace('_', ' ').title()}")
            report.append(f"- Mean: {stat.mean:.2f}")
            report.append(f"- Std: {stat.std:.2f}")
            report.append(f"- Range: [{stat.min:.0f}, {stat.max:.0f}]")
            report.append(f"- Quartiles: Q1={stat.q25:.2f}, Q2={stat.q50:.2f}, Q3={stat.q75:.2f}")
        report.append("")

        # 因子相关性
        report.append("## Factor Correlations")
        corr_matrix = df[self.factors].corr()
        report.append(corr_matrix.to_string())
        report.append("")

        # 输出文件
        report.append("## Output Files")
        report.append(f"- Aggregated data: {self.output_dir / 'aggregated_factors.parquet'}")
        report.append(f"- Plots: {self.output_dir / '*.png'}")
        report.append("")

        report.append("=" * 70)

        report_text = "\n".join(report)

        # 保存报告
        report_path = self.output_dir / 'analysis_report.txt'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_text)

        logger.info(f"Saved report to {report_path}")

        return report_text

    def run_full_analysis(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """运行完整分析流程"""
        logger.info("=" * 70)
        logger.info("Starting Full Factor Analysis")
        logger.info("=" * 70)

        # 1. 加载数据
        df = self.load_data()

        # 2. 聚合到公司-季度级别
        aggregated = self.aggregate_by_company_quarter(df)

        # 保存聚合数据
        output_path = self.output_dir / 'aggregated_factors.parquet'
        aggregated.to_parquet(output_path, index=False)
        logger.info(f"Saved aggregated data to {output_path}")

        # 3. 计算统计量
        stats = self.compute_factor_statistics(aggregated)

        # 4. 因子相关性
        corr_matrix = self.cross_factor_correlation(aggregated)

        # 5. 分位数分析
        for factor in self.factors:
            aggregated = self.quantile_analysis(aggregated, factor, n_quantiles=3)

        # 6. 模拟 forward returns
        for factor in self.factors:
            aggregated = self.simulate_forward_returns(aggregated, factor, n_quantiles=3)

        # 7. 生成图表
        logger.info("Generating visualizations...")
        self.plot_factor_distributions(aggregated)
        self.plot_factor_correlation_heatmap(corr_matrix)
        self.plot_time_series(aggregated)

        for factor in self.factors:
            self.plot_quantile_comparison(aggregated, factor)
            self.plot_factor_return_relationship(aggregated, factor)

        # 8. 生成报告
        report = self.generate_summary_report(df, aggregated, stats)
        print("\n" + report)

        logger.info("=" * 70)
        logger.info("Factor Analysis Completed Successfully")
        logger.info("=" * 70)

        return df, aggregated


def main():
    """CLI 入口"""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze sentiment factors")
    parser.add_argument(
        "--input-file",
        default="data/processed/factor_data.parquet",
        help="Input factor data file"
    )
    parser.add_argument(
        "--output-dir",
        default="data/analysis",
        help="Output directory for analysis results"
    )

    args = parser.parse_args()

    # 创建分析器并运行
    analyzer = FactorAnalyzer(
        input_file=args.input_file,
        output_dir=args.output_dir
    )

    df, aggregated = analyzer.run_full_analysis()

    logger.info(f"\nAnalysis complete! Check {args.output_dir} for results.")


if __name__ == "__main__":
    main()
