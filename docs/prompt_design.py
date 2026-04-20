"""
Sentiment Factor Extraction - Prompt 设计文档

## 设计理念

作为量化研究员，我们需要从财报电话会议中提取**可量化、可复现、可回测**的情绪因子。

## Prompt 架构

### 1. 角色设定 (Role)

```
You are a sell-side equity analyst evaluating earnings call transcripts.
```

**为什么选择 sell-side analyst？**
- 专注于短期价格预测（符合量化交易需求）
- 训练数据中有大量 sell-side 研究报告
- 比 buy-side 更关注市场情绪和叙事

### 2. 任务定义 (Task)

提取三个量化因子（1-10 刻度）：

#### confidence_score (管理层信心)
- **1-3**: 防御性语言（"may", "might", "challenging"）
- **4-6**: 中性陈述
- **7-10**: 强烈信心（"will", "confident", "expect"）

**量化逻辑**：
- 高信心 → 未来业绩超预期概率高 → 正向因子
- 低信心 → 可能下调指引 → 负向因子

#### risk_awareness (风险意识)
- **1-3**: 忽视风险，过度乐观
- **4-6**: 平衡的风险披露
- **7-10**: 强调风险、不确定性

**量化逻辑**：
- 过低 → 可能隐藏问题 → 负向信号
- 过高 → 保守指引，易超预期 → 正向信号（反向指标）
- 适中 → 中性

#### strategic_shift (战略转变)
- **1-3**: 业务常态，无重大变化
- **4-6**: 渐进式调整
- **7-10**: 重大战略转型

**量化逻辑**：
- 高转变 → 不确定性增加 → 波动率因子
- 低转变 → 稳定性 → 低波动

### 3. Few-Shot 示例

**示例 1: 高信心 + 低风险 + 高转变**

```
Text: "We are confident that our new product line will drive significant
revenue growth in Q2. The market response has been overwhelmingly positive,
and we expect to capture 15-20% market share within the first year."

Output: {"confidence_score": 9, "risk_awareness": 2, "strategic_shift": 7}
```

**示例 2: 低信心 + 高风险 + 低转变**

```
Text: "While we face some near-term headwinds from supply chain disruptions
and rising input costs, we believe our diversified supplier base and pricing
power will help us navigate these challenges. We may need to adjust our
guidance if conditions worsen."

Output: {"confidence_score": 4, "risk_awareness": 8, "strategic_shift": 3}
```

### 4. 输出格式约束

```
Return ONLY a valid JSON object with these three numeric fields.
No explanations, no additional text.
```

**为什么强制 JSON？**
- 确保结构化输出
- 避免模型"过度解释"
- 便于自动化解析
- OpenAI 支持 `response_format={"type": "json_object"}`

## 工程实现

### 1. 重试机制 (Tenacity)

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((Exception,))
)
```

**重试策略**：
- 最多 3 次尝试
- 指数退避：2s → 4s → 8s
- 捕获所有异常（API 错误、超时、限流）

### 2. 缓存机制

```python
text_hash = hashlib.md5(text.encode()).hexdigest()
if text_hash in cache:
    return cached_result
```

**为什么需要缓存？**
- 避免重复调用（成本控制）
- 加速重新运行
- 确保一致性（相同文本 → 相同因子）

### 3. 数据追溯 (Reproducibility)

每条记录包含：

```python
{
    "model_name": "gpt-4o-mini",
    "prompt_version": "v1.0",
    "timestamp": "2026-04-21T12:34:56.789",
    "tokens_used": 1234,
    "api_latency_ms": 567.8
}
```

**量化研究的核心要求**：
- **model_name**: 不同模型 → 不同因子分布
- **prompt_version**: Prompt 迭代时可回溯
- **timestamp**: 时间序列分析
- **tokens_used**: 成本归因
- **api_latency_ms**: 性能监控

### 4. Rate Limiting

```python
time.sleep(rate_limit_delay)  # 默认 0.5s
```

**防止限流**：
- OpenAI Tier 1: 500 RPM
- 0.5s delay → 120 RPM（安全边际）

### 5. Batch 处理

```python
for i in range(0, total, batch_size):
    batch = df.iloc[i:i+batch_size]
    # 处理 batch
```

**优势**：
- 进度可视化
- 中断后可恢复
- 便于并行化（未来扩展）

## Prompt 迭代建议

### Version 1.0 (当前)
- 基础三因子
- 简单 few-shot

### Version 1.1 (建议)
- 添加 **forward_guidance** 因子（指引变化）
- 添加 **competitive_positioning** 因子（竞争地位）

### Version 2.0 (高级)
- 使用 Chain-of-Thought
- 要求模型先提取关键句，再评分
- 提高可解释性

## 成本估算

**假设**：
- 模型：gpt-4o-mini
- 输入：~1500 tokens/chunk（含 few-shot）
- 输出：~50 tokens
- 价格：$0.15/1M input tokens, $0.60/1M output tokens

**单个 chunk 成本**：
- Input: 1500 * $0.15 / 1M = $0.000225
- Output: 50 * $0.60 / 1M = $0.000030
- **Total: ~$0.00026/chunk**

**1000 chunks**：
- 成本：~$0.26
- 时间：~8 分钟（0.5s delay）

## 验证方法

### 1. 内部一致性
- 相同文本多次调用 → 因子应相近（temperature=0）

### 2. 极端案例测试
- 明显乐观文本 → confidence_score > 7
- 明显悲观文本 → risk_awareness > 7

### 3. 与人工标注对比
- 抽样 50 个 chunks
- 人工评分
- 计算相关系数（目标 > 0.7）

### 4. 回测验证
- 因子 → 股票收益率相关性
- Sharpe ratio, IC, IR

## 使用示例

### Python API

```python
from src.sentiment_extractor import SentimentExtractorPipeline

pipeline = SentimentExtractorPipeline(
    input_file="data/processed/processed_data.parquet",
    output_file="data/processed/factor_data.parquet",
    provider="openai",
    model_name="gpt-4o-mini"
)

df = pipeline.run()
```

### CLI

```bash
# 完整运行
python src/sentiment_extractor.py

# 测试模式（前 10 个）
python src/sentiment_extractor.py --limit 10

# 使用 Anthropic
python src/sentiment_extractor.py --provider anthropic --model claude-3-haiku-20240307

# 自定义参数
python src/sentiment_extractor.py \\
    --batch-size 20 \\
    --rate-limit-delay 0.3 \\
    --limit 100
```

## 输出格式

DataFrame 包含原始字段 + 因子字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| ticker | str | 股票代码 |
| year | int | 年份 |
| quarter | str | 季度 |
| chunk_id | int | Chunk 编号 |
| text | str | 原始文本 |
| position | int | 位置 |
| **confidence_score** | int | 信心因子 (1-10) |
| **risk_awareness** | int | 风险意识 (1-10) |
| **strategic_shift** | int | 战略转变 (1-10) |
| model_name | str | 模型名称 |
| prompt_version | str | Prompt 版本 |
| timestamp | str | 提取时间 |
| tokens_used | int | Token 消耗 |
| api_latency_ms | float | API 延迟 |

## 下一步

1. **因子聚合**：Chunk 级别 → 公司-季度级别
2. **因子标准化**：Z-score, rank
3. **因子组合**：多因子模型
4. **回测框架**：Backtrader, Zipline
"""

if __name__ == "__main__":
    print(__doc__)
