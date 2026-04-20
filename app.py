"""
Quantitative Factor Analysis Dashboard
量化因子分析面板 - Streamlit + Plotly
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# 页面配置
st.set_page_config(
    page_title="Sentiment Factor Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .kpi-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .kpi-label {
        font-size: 1rem;
        color: #666;
        margin-top: 0.5rem;
    }
    .kpi-change-positive {
        color: #28a745;
        font-size: 1.2rem;
    }
    .kpi-change-negative {
        color: #dc3545;
        font-size: 1.2rem;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# 数据加载和缓存
# ============================================================================

@st.cache_data
def load_factor_data() -> pd.DataFrame:
    """加载因子数据（带缓存）"""
    try:
        df = pd.read_parquet("data/processed/factor_data.parquet")
        # 创建时间索引
        df['period'] = df['year'].astype(str) + df['quarter']
        df['date'] = pd.to_datetime(df['year'].astype(str) + '-' + df['quarter'].str.replace('Q', ''), format='%Y-%m')
        return df
    except FileNotFoundError:
        st.error("❌ 数据文件未找到: data/processed/factor_data.parquet")
        st.info("请先运行: python src/sentiment_extractor.py")
        st.stop()


@st.cache_data
def load_aggregated_data() -> Optional[pd.DataFrame]:
    """加载聚合数据（可选）"""
    try:
        df = pd.read_parquet("data/analysis/aggregated_factors.parquet")
        df['period'] = df['year'].astype(str) + df['quarter']
        df['date'] = pd.to_datetime(df['year'].astype(str) + '-' + df['quarter'].str.replace('Q', ''), format='%Y-%m')
        return df
    except FileNotFoundError:
        return None


@st.cache_data
def compute_qoq_changes(df: pd.DataFrame, ticker: str) -> dict:
    """计算 QoQ 变化"""
    ticker_data = df[df['ticker'] == ticker].sort_values('date')

    if len(ticker_data) < 2:
        return {
            'confidence_change': 0,
            'risk_change': 0,
            'shift_change': 0
        }

    latest = ticker_data.iloc[-1]
    previous = ticker_data.iloc[-2]

    return {
        'confidence_change': latest['confidence_score'] - previous['confidence_score'],
        'risk_change': latest['risk_awareness'] - previous['risk_awareness'],
        'shift_change': latest['strategic_shift'] - previous['strategic_shift']
    }


# ============================================================================
# 可视化函数
# ============================================================================

def plot_factor_time_series(df: pd.DataFrame, factors: List[str], ticker: Optional[str] = None):
    """绘制因子时间序列"""
    if ticker:
        df = df[df['ticker'] == ticker]

    # 按时间聚合
    time_series = df.groupby('date')[factors].mean().reset_index()

    fig = go.Figure()

    colors = {'confidence_score': '#1f77b4', 'risk_awareness': '#ff7f0e', 'strategic_shift': '#2ca02c'}

    for factor in factors:
        fig.add_trace(go.Scatter(
            x=time_series['date'],
            y=time_series[factor],
            mode='lines+markers',
            name=factor.replace('_', ' ').title(),
            line=dict(width=3, color=colors.get(factor, '#333')),
            marker=dict(size=8)
        ))

    fig.update_layout(
        title="Factor Evolution Over Time",
        xaxis_title="Date",
        yaxis_title="Score",
        hovermode='x unified',
        height=400,
        template='plotly_white',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig


def plot_factor_distribution(df: pd.DataFrame, factor: str):
    """绘制因子分布"""
    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=df[factor],
        nbinsx=20,
        name=factor.replace('_', ' ').title(),
        marker_color='#1f77b4',
        opacity=0.7
    ))

    # 添加均值线
    mean_val = df[factor].mean()
    fig.add_vline(x=mean_val, line_dash="dash", line_color="red",
                  annotation_text=f"Mean: {mean_val:.2f}")

    fig.update_layout(
        title=f"{factor.replace('_', ' ').title()} Distribution",
        xaxis_title="Score",
        yaxis_title="Frequency",
        height=350,
        template='plotly_white'
    )

    return fig


def plot_factor_correlation(df: pd.DataFrame):
    """绘制因子相关性热力图"""
    factors = ['confidence_score', 'risk_awareness', 'strategic_shift']
    corr_matrix = df[factors].corr()

    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=[f.replace('_', ' ').title() for f in corr_matrix.columns],
        y=[f.replace('_', ' ').title() for f in corr_matrix.index],
        colorscale='RdBu',
        zmid=0,
        text=corr_matrix.values.round(2),
        texttemplate='%{text}',
        textfont={"size": 14},
        colorbar=dict(title="Correlation")
    ))

    fig.update_layout(
        title="Factor Correlation Matrix",
        height=400,
        template='plotly_white'
    )

    return fig


def plot_top_bottom_chunks(df: pd.DataFrame, factor: str, n: int = 5):
    """绘制 Top/Bottom chunks"""
    top_chunks = df.nlargest(n, factor)[['ticker', 'quarter', 'chunk_id', factor, 'text']]
    bottom_chunks = df.nsmallest(n, factor)[['ticker', 'quarter', 'chunk_id', factor, 'text']]

    fig = go.Figure()

    # Top chunks
    fig.add_trace(go.Bar(
        x=top_chunks[factor],
        y=[f"{row['ticker']} {row['quarter']} C{row['chunk_id']}" for _, row in top_chunks.iterrows()],
        orientation='h',
        name='Top Chunks',
        marker_color='#2ca02c',
        text=top_chunks[factor].round(1),
        textposition='outside'
    ))

    # Bottom chunks
    fig.add_trace(go.Bar(
        x=bottom_chunks[factor],
        y=[f"{row['ticker']} {row['quarter']} C{row['chunk_id']}" for _, row in bottom_chunks.iterrows()],
        orientation='h',
        name='Bottom Chunks',
        marker_color='#d62728',
        text=bottom_chunks[factor].round(1),
        textposition='outside'
    ))

    fig.update_layout(
        title=f"Top & Bottom {n} Chunks by {factor.replace('_', ' ').title()}",
        xaxis_title="Score",
        height=400,
        template='plotly_white',
        barmode='group'
    )

    return fig, top_chunks, bottom_chunks


def plot_scatter_with_text(df: pd.DataFrame, x_factor: str, y_factor: str):
    """绘制散点图（可点击查看文本）"""
    fig = px.scatter(
        df,
        x=x_factor,
        y=y_factor,
        color='ticker',
        size='text_length' if 'text_length' in df.columns else None,
        hover_data=['ticker', 'quarter', 'chunk_id'],
        title=f"{x_factor.replace('_', ' ').title()} vs {y_factor.replace('_', ' ').title()}",
        template='plotly_white',
        height=450
    )

    # 添加回归线
    z = np.polyfit(df[x_factor], df[y_factor], 1)
    p = np.poly1d(z)
    x_line = np.linspace(df[x_factor].min(), df[x_factor].max(), 100)

    fig.add_trace(go.Scatter(
        x=x_line,
        y=p(x_line),
        mode='lines',
        name='Trend',
        line=dict(color='red', dash='dash')
    ))

    return fig


# ============================================================================
# 主应用
# ============================================================================

def main():
    # 标题
    st.markdown('<div class="main-header">📊 Sentiment Factor Analysis Dashboard</div>', unsafe_allow_html=True)
    st.markdown("---")

    # 加载数据
    with st.spinner("Loading data..."):
        df = load_factor_data()
        aggregated_df = load_aggregated_data()

    # 添加文本长度列（如果不存在）
    if 'text_length' not in df.columns:
        df['text_length'] = df['text'].str.len()

    # ============================================================================
    # Sidebar
    # ============================================================================

    st.sidebar.header("🎛️ Controls")

    # Ticker 选择
    tickers = sorted(df['ticker'].unique())
    selected_ticker = st.sidebar.selectbox(
        "Select Ticker",
        options=['All'] + tickers,
        index=0
    )

    # 时间范围筛选
    st.sidebar.subheader("Time Range")
    periods = sorted(df['period'].unique())

    if len(periods) > 1:
        selected_periods = st.sidebar.multiselect(
            "Select Periods",
            options=periods,
            default=periods
        )
    else:
        selected_periods = periods
        st.sidebar.info(f"Only one period available: {periods[0]}")

    # 因子选择
    st.sidebar.subheader("Factors")
    all_factors = ['confidence_score', 'risk_awareness', 'strategic_shift']
    selected_factors = st.sidebar.multiselect(
        "Select Factors",
        options=all_factors,
        default=all_factors,
        format_func=lambda x: x.replace('_', ' ').title()
    )

    # 数据筛选
    filtered_df = df.copy()
    if selected_ticker != 'All':
        filtered_df = filtered_df[filtered_df['ticker'] == selected_ticker]
    if selected_periods:
        filtered_df = filtered_df[filtered_df['period'].isin(selected_periods)]

    # 显示数据统计
    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 Data Stats")
    st.sidebar.metric("Total Chunks", len(filtered_df))
    st.sidebar.metric("Unique Tickers", filtered_df['ticker'].nunique())
    st.sidebar.metric("Time Periods", filtered_df['period'].nunique())

    # ============================================================================
    # KPI Cards
    # ============================================================================

    st.subheader("📊 Key Performance Indicators")

    # 计算最新季度的平均值
    latest_period = filtered_df['period'].max()
    latest_data = filtered_df[filtered_df['period'] == latest_period]

    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

    with kpi_col1:
        avg_confidence = latest_data['confidence_score'].mean()
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{avg_confidence:.2f}</div>
            <div class="kpi-label">Avg Confidence</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col2:
        avg_risk = latest_data['risk_awareness'].mean()
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{avg_risk:.2f}</div>
            <div class="kpi-label">Avg Risk Awareness</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col3:
        avg_shift = latest_data['strategic_shift'].mean()
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{avg_shift:.2f}</div>
            <div class="kpi-label">Avg Strategic Shift</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col4:
        total_tokens = latest_data['tokens_used'].sum() if 'tokens_used' in latest_data.columns else 0
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{total_tokens:,}</div>
            <div class="kpi-label">Total Tokens Used</div>
        </div>
        """, unsafe_allow_html=True)

    # QoQ 变化（如果有多个时期）
    if len(filtered_df['period'].unique()) > 1 and selected_ticker != 'All':
        st.markdown("### 📈 Quarter-over-Quarter Changes")
        qoq_changes = compute_qoq_changes(filtered_df, selected_ticker)

        qoq_col1, qoq_col2, qoq_col3 = st.columns(3)

        with qoq_col1:
            change = qoq_changes['confidence_change']
            color_class = "kpi-change-positive" if change >= 0 else "kpi-change-negative"
            arrow = "↑" if change >= 0 else "↓"
            st.markdown(f"""
            <div style="text-align: center;">
                <span class="{color_class}">{arrow} {abs(change):.2f}</span>
                <div style="color: #666; font-size: 0.9rem;">Confidence QoQ</div>
            </div>
            """, unsafe_allow_html=True)

        with qoq_col2:
            change = qoq_changes['risk_change']
            color_class = "kpi-change-positive" if change >= 0 else "kpi-change-negative"
            arrow = "↑" if change >= 0 else "↓"
            st.markdown(f"""
            <div style="text-align: center;">
                <span class="{color_class}">{arrow} {abs(change):.2f}</span>
                <div style="color: #666; font-size: 0.9rem;">Risk QoQ</div>
            </div>
            """, unsafe_allow_html=True)

        with qoq_col3:
            change = qoq_changes['shift_change']
            color_class = "kpi-change-positive" if change >= 0 else "kpi-change-negative"
            arrow = "↑" if change >= 0 else "↓"
            st.markdown(f"""
            <div style="text-align: center;">
                <span class="{color_class}">{arrow} {abs(change):.2f}</span>
                <div style="color: #666; font-size: 0.9rem;">Shift QoQ</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ============================================================================
    # 主要图表
    # ============================================================================

    # Tab 布局
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Time Series", "📊 Distribution", "🔍 Alpha Analysis", "📝 Text Explorer"])

    with tab1:
        st.subheader("Factor Time Series")

        if selected_factors:
            fig = plot_factor_time_series(
                filtered_df,
                selected_factors,
                ticker=None if selected_ticker == 'All' else selected_ticker
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Please select at least one factor")

        # 相关性矩阵
        if len(selected_factors) > 1:
            st.subheader("Factor Correlation")
            fig_corr = plot_factor_correlation(filtered_df)
            st.plotly_chart(fig_corr, use_container_width=True)

    with tab2:
        st.subheader("Factor Distributions")

        if selected_factors:
            cols = st.columns(len(selected_factors))
            for i, factor in enumerate(selected_factors):
                with cols[i]:
                    fig = plot_factor_distribution(filtered_df, factor)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Please select at least one factor")

    with tab3:
        st.subheader("Alpha Analysis: Top & Bottom Performers")

        # 选择分析的因子
        alpha_factor = st.selectbox(
            "Select Factor for Analysis",
            options=all_factors,
            format_func=lambda x: x.replace('_', ' ').title()
        )

        n_chunks = st.slider("Number of chunks to show", 3, 10, 5)

        fig, top_chunks, bottom_chunks = plot_top_bottom_chunks(filtered_df, alpha_factor, n=n_chunks)
        st.plotly_chart(fig, use_container_width=True)

        # 显示详细信息
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**🟢 Top {n_chunks} Chunks**")
            for idx, row in top_chunks.iterrows():
                with st.expander(f"{row['ticker']} {row['quarter']} Chunk {row['chunk_id']} - Score: {row[alpha_factor]:.1f}"):
                    st.text(row['text'][:500] + "..." if len(row['text']) > 500 else row['text'])

        with col2:
            st.markdown(f"**🔴 Bottom {n_chunks} Chunks**")
            for idx, row in bottom_chunks.iterrows():
                with st.expander(f"{row['ticker']} {row['quarter']} Chunk {row['chunk_id']} - Score: {row[alpha_factor]:.1f}"):
                    st.text(row['text'][:500] + "..." if len(row['text']) > 500 else row['text'])

    with tab4:
        st.subheader("Interactive Text Explorer")

        # 散点图：选择两个因子
        col1, col2 = st.columns(2)
        with col1:
            x_factor = st.selectbox("X-axis Factor", options=all_factors, index=0,
                                   format_func=lambda x: x.replace('_', ' ').title())
        with col2:
            y_factor = st.selectbox("Y-axis Factor", options=all_factors, index=1,
                                   format_func=lambda x: x.replace('_', ' ').title())

        fig = plot_scatter_with_text(filtered_df, x_factor, y_factor)
        st.plotly_chart(fig, use_container_width=True)

        # 文本搜索
        st.markdown("### 🔍 Search Text")
        search_term = st.text_input("Enter search term")

        if search_term:
            matching_chunks = filtered_df[filtered_df['text'].str.contains(search_term, case=False, na=False)]
            st.write(f"Found {len(matching_chunks)} matching chunks")

            for idx, row in matching_chunks.iterrows():
                with st.expander(f"{row['ticker']} {row['quarter']} Chunk {row['chunk_id']}"):
                    st.markdown(f"**Factors:** Confidence={row['confidence_score']:.1f}, Risk={row['risk_awareness']:.1f}, Shift={row['strategic_shift']:.1f}")
                    st.text(row['text'])

    # ============================================================================
    # 数据下载
    # ============================================================================

    st.markdown("---")
    st.subheader("💾 Data Export")

    col1, col2, col3 = st.columns(3)

    with col1:
        # 下载筛选后的数据
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Filtered Data (CSV)",
            data=csv,
            file_name=f"factor_data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

    with col2:
        # 下载聚合数据
        if aggregated_df is not None:
            agg_csv = aggregated_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Aggregated Data (CSV)",
                data=agg_csv,
                file_name=f"aggregated_factors_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

    with col3:
        # 下载统计摘要
        summary = filtered_df[all_factors].describe().to_csv().encode('utf-8')
        st.download_button(
            label="📥 Download Summary Stats (CSV)",
            data=summary,
            file_name=f"factor_summary_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

    # ============================================================================
    # 简单回测
    # ============================================================================

    st.markdown("---")
    st.subheader("🎯 Simple Backtest Simulation")

    st.info("⚠️ Note: Using simulated returns. Replace with real market data in production.")

    backtest_factor = st.selectbox(
        "Select Factor for Backtest",
        options=all_factors,
        format_func=lambda x: x.replace('_', ' ').title(),
        key='backtest_factor'
    )

    # 模拟收益率
    np.random.seed(42)
    filtered_df['simulated_return'] = np.random.normal(0.02, 0.10, len(filtered_df))

    # 添加因子效应
    factor_normalized = (filtered_df[backtest_factor] - filtered_df[backtest_factor].mean()) / filtered_df[backtest_factor].std()
    filtered_df['simulated_return'] += factor_normalized * 0.03

    # 分位数分组
    try:
        filtered_df['quantile'] = pd.qcut(
            filtered_df[backtest_factor],
            q=3,
            labels=['Low', 'Medium', 'High'],
            duplicates='drop'
        )
    except ValueError:
        # 如果数据太少或值重复太多，使用简单分组
        filtered_df['quantile'] = 'All'
        st.warning("⚠️ Insufficient data variation for quantile grouping. Showing all data together.")

    # 计算分位数收益
    if 'quantile' in filtered_df.columns and filtered_df['quantile'].nunique() > 1:
        quantile_returns = filtered_df.groupby('quantile')['simulated_return'].agg(['mean', 'std', 'count'])
    else:
        # 如果没有分位数，显示整体统计
        quantile_returns = pd.DataFrame({
            'mean': [filtered_df['simulated_return'].mean()],
            'std': [filtered_df['simulated_return'].std()],
            'count': [len(filtered_df)]
        }, index=['All'])

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Returns by Factor Quantile**")
        st.dataframe(quantile_returns.style.format({'mean': '{:.2%}', 'std': '{:.2%}'}))

        if len(quantile_returns) >= 2 and 'High' in quantile_returns.index and 'Low' in quantile_returns.index:
            long_short = quantile_returns.loc['High', 'mean'] - quantile_returns.loc['Low', 'mean']
            st.metric("Long-Short Return", f"{long_short:.2%}")
        else:
            st.info("Need at least 2 quantiles for Long-Short calculation")

    with col2:
        # 绘制收益分布
        if filtered_df['quantile'].nunique() > 1:
            fig = go.Figure()
            for q in ['Low', 'Medium', 'High']:
                if q in filtered_df['quantile'].values:
                    data = filtered_df[filtered_df['quantile'] == q]['simulated_return']
                    fig.add_trace(go.Box(y=data, name=q))

            fig.update_layout(
                title="Return Distribution by Quantile",
                yaxis_title="Simulated Return",
                template='plotly_white',
                height=350
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Quantile grouping not available with current data")

    # ============================================================================
    # Footer
    # ============================================================================

    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        <p>📊 Sentiment Factor Analysis Dashboard | Built with Streamlit + Plotly</p>
        <p>Data Source: Earnings Call Transcripts | Model: Claude Sonnet 4.6</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
