"""
Streamlit Dashboard 使用指南

## 功能概览

一个交互式的量化因子分析面板，提供：
- 实时数据筛选和可视化
- KPI 监控和 QoQ 变化
- Alpha 分析和文本回溯
- 简单回测模拟
- 数据导出功能

## 启动方法

### 方法 1: 直接运行
```bash
streamlit run app.py
```

### 方法 2: 指定端口
```bash
streamlit run app.py --server.port 8501
```

### 方法 3: 后台运行
```bash
nohup streamlit run app.py &
```

## 界面功能

### 1. Sidebar（侧边栏）

**Ticker 选择**
- 选择特定公司或查看所有公司
- 默认：All

**Time Range（时间范围）**
- 多选：选择要分析的季度
- 默认：所有可用时期

**Factors（因子选择）**
- Confidence Score: 管理层信心
- Risk Awareness: 风险意识
- Strategic Shift: 战略转变
- 默认：全选

**Data Stats（数据统计）**
- 实时显示筛选后的数据量
- Unique tickers 和 time periods

### 2. KPI Cards（关键指标卡片）

显示最新季度的：
- 平均 Confidence Score
- 平均 Risk Awareness
- 平均 Strategic Shift
- 总 Token 消耗

**QoQ Changes（环比变化）**
- 仅在有多个时期且选择单个 ticker 时显示
- 绿色 ↑ = 增长
- 红色 ↓ = 下降

### 3. Tab 1: Time Series（时间序列）

**Factor Evolution Over Time**
- 多因子折线图
- 交互式悬停显示数值
- 支持缩放和平移

**Factor Correlation Matrix**
- 热力图显示因子间相关性
- 颜色：蓝色（正相关）↔ 红色（负相关）
- 数值标注

### 4. Tab 2: Distribution（分布）

**Factor Distributions**
- 每个因子的直方图
- 红色虚线：均值
- 并排显示便于对比

### 5. Tab 3: Alpha Analysis（Alpha 分析）

**Top & Bottom Performers**
- 选择分析的因子
- 滑块调整显示数量（3-10）
- 绿色：Top chunks（高分）
- 红色：Bottom chunks（低分）

**Text Preview**
- 点击展开查看完整文本
- 显示前 500 字符
- 包含 ticker、quarter、chunk_id

### 6. Tab 4: Text Explorer（文本探索）

**Interactive Scatter Plot**
- 选择 X 轴和 Y 轴因子
- 点的大小：文本长度
- 颜色：ticker
- 红色虚线：趋势线

**Text Search**
- 输入关键词搜索
- 实时匹配显示
- 展开查看完整文本和因子分数

### 7. Data Export（数据导出）

**三种下载选项**：
1. **Filtered Data**: 当前筛选后的完整数据（CSV）
2. **Aggregated Data**: 公司-季度聚合数据（CSV）
3. **Summary Stats**: 因子统计摘要（CSV）

文件名自动包含日期戳

### 8. Simple Backtest（简单回测）

**功能**：
- 选择回测因子
- 模拟收益率分布
- 按分位数分组（Low/Medium/High）
- 计算 Long-Short 收益

**注意**：
⚠️ 当前使用模拟数据
生产环境需接入真实市场数据（yfinance, Alpha Vantage）

## 性能优化

### 缓存机制
```python
@st.cache_data
def load_factor_data():
    # 数据加载自动缓存
    # 仅在数据文件变化时重新加载
```

### 数据筛选
- 所有筛选在内存中完成
- 无需重新加载数据
- 响应时间 < 100ms

### 图表渲染
- Plotly 交互式图表
- 硬件加速
- 支持大数据集（1000+ 点）

## 使用场景

### 场景 1: 单公司深度分析
1. Sidebar 选择特定 ticker（如 CLF）
2. 查看 KPI 和 QoQ 变化
3. Time Series 观察因子演变
4. Alpha Analysis 找到极端 chunks
5. Text Explorer 阅读原文

### 场景 2: 多公司对比
1. Sidebar 选择 "All"
2. Distribution 对比因子分布
3. Scatter Plot 识别异常值
4. Backtest 验证因子有效性

### 场景 3: 时间序列分析
1. 选择多个时期
2. Time Series 观察趋势
3. QoQ Changes 识别拐点
4. 导出数据进行深度分析

### 场景 4: 文本挖掘
1. Text Search 搜索关键词（如 "risk", "growth"）
2. 查看匹配 chunks 的因子分数
3. 识别高/低分文本的语言特征

## 扩展建议

### 1. 接入真实市场数据

```python
import yfinance as yf

@st.cache_data
def get_stock_returns(ticker, start_date, end_date):
    stock = yf.Ticker(ticker)
    hist = stock.history(start=start_date, end=end_date)
    return hist['Close'].pct_change()

# 在回测中使用
df['actual_return'] = df.apply(
    lambda row: get_stock_returns(row['ticker'], row['date'], ...),
    axis=1
)
```

### 2. 添加更多图表

```python
# 行业对比
def plot_sector_comparison(df):
    # 按行业分组的因子对比
    pass

# 因子热力图
def plot_factor_heatmap(df):
    # ticker x quarter 热力图
    pass
```

### 3. 高级回测

```python
# IC (Information Coefficient)
def calculate_ic(df):
    return df['factor'].corr(df['forward_return'])

# Sharpe Ratio
def calculate_sharpe(returns):
    return returns.mean() / returns.std() * np.sqrt(252)
```

### 4. 实时更新

```python
# 自动刷新数据
if st.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# 或定时刷新
import time
placeholder = st.empty()
while True:
    with placeholder.container():
        # 更新图表
        pass
    time.sleep(60)  # 每分钟刷新
```

## 故障排查

### 问题 1: 数据文件未找到

**错误**：
```
❌ 数据文件未找到: data/processed/factor_data.parquet
```

**解决方案**：
```bash
# 先运行因子提取
python src/sentiment_extractor.py
```

### 问题 2: 端口被占用

**错误**：
```
OSError: [Errno 98] Address already in use
```

**解决方案**：
```bash
# 使用不同端口
streamlit run app.py --server.port 8502

# 或杀死占用进程
lsof -ti:8501 | xargs kill -9
```

### 问题 3: 图表不显示

**可能原因**：
- 数据为空
- 因子未选择
- 浏览器缓存

**解决方案**：
1. 检查 sidebar 筛选条件
2. 确保至少选择一个因子
3. 清除浏览器缓存或使用无痕模式

### 问题 4: 性能慢

**优化方法**：
1. 减少数据量（筛选特定 ticker 或时期）
2. 关闭不需要的 tab
3. 使用更少的 chunks 在 Alpha Analysis

## 快速开始

```bash
# 1. 确保数据已生成
python src/sentiment_extractor.py

# 2. 启动 dashboard
streamlit run app.py

# 3. 浏览器自动打开
# 默认地址: http://localhost:8501

# 4. 开始探索！
```

## 键盘快捷键

- `R`: 重新运行应用
- `C`: 清除缓存
- `Ctrl + /`: 显示快捷键帮助

## 部署

### 本地部署
```bash
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

### Streamlit Cloud
1. 推送代码到 GitHub
2. 访问 share.streamlit.io
3. 连接 GitHub repo
4. 自动部署

### Docker
```dockerfile
FROM python:3.12
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## 最佳实践

1. **定期更新数据**：每季度运行 scraper 和 extractor
2. **监控 token 消耗**：KPI card 显示总消耗
3. **导出关键发现**：使用 Download 功能保存分析结果
4. **结合原文分析**：不要只看数字，要读文本
5. **验证因子有效性**：使用 Backtest 功能

## 支持

遇到问题？
1. 检查日志：`logs/sentiment_extractor.log`
2. 查看文档：`docs/` 目录
3. 运行测试：`pytest tests/`
"""

if __name__ == "__main__":
    print(__doc__)
