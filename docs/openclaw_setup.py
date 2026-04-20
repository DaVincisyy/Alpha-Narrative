"""
OpenClaw 配置和使用指南

## OpenClaw 简介

OpenClaw 是一个 OpenAI 兼容的 API 代理服务，支持多种 LLM 模型。

## 配置信息

- **Base URL**: https://xuedingtoken.com
- **认证**: 使用 OPENCLAW_TOKEN 环境变量
- **推荐模型**: anthropic/claude-sonnet-4-6

## 方法 1: 使用环境变量（推荐）

### Windows (PowerShell)
```powershell
$env:OPENCLAW_TOKEN = "your-token-here"
python src/sentiment_extractor.py --provider openclaw --limit 3
```

### Windows (CMD)
```cmd
set OPENCLAW_TOKEN=your-token-here
python src/sentiment_extractor.py --provider openclaw --limit 3
```

### Linux/Mac
```bash
export OPENCLAW_TOKEN='your-token-here'
python src/sentiment_extractor.py --provider openclaw --limit 3
```

## 方法 2: 使用配置脚本

1. 编辑 `setup_and_test_openclaw.py`
2. 替换 `OPENCLAW_TOKEN = "your-token-here"` 为实际 token
3. 运行:
```bash
python setup_and_test_openclaw.py
```

## 方法 3: Python 代码

```python
import os
from src.sentiment_extractor import SentimentExtractorPipeline

# 设置环境变量
os.environ["OPENCLAW_TOKEN"] = "your-token-here"

# 创建 pipeline
pipeline = SentimentExtractorPipeline(
    provider="openclaw",
    model_name="anthropic/claude-sonnet-4-6",
    base_url="https://xuedingtoken.com",
    input_file="data/processed/processed_data.parquet",
    output_file="data/processed/factor_data.parquet"
)

# 运行（测试前 3 个 chunks）
df = pipeline.run(limit=3)
```

## CLI 参数

```bash
python src/sentiment_extractor.py \
    --provider openclaw \
    --model anthropic/claude-sonnet-4-6 \
    --base-url https://xuedingtoken.com \
    --limit 3 \
    --batch-size 5 \
    --rate-limit-delay 1.0
```

### 参数说明

- `--provider openclaw`: 使用 OpenClaw 提供商
- `--model`: 模型名称（默认: anthropic/claude-sonnet-4-6）
- `--base-url`: API 端点（默认: https://xuedingtoken.com）
- `--limit`: 限制处理的 chunks 数量（测试用）
- `--batch-size`: 批处理大小
- `--rate-limit-delay`: 请求间延迟（秒）

## 支持的模型

OpenClaw 支持多种模型，推荐使用：

- `anthropic/claude-sonnet-4-6` (推荐)
- `anthropic/claude-opus-4-7`
- `anthropic/claude-haiku-4-5`
- `openai/gpt-4o`
- `openai/gpt-4o-mini`

## 代码修改说明

### 1. OpenAIClient 增强

```python
class OpenAIClient(BaseLLMClient):
    def __init__(self, model_name, api_key=None, base_url=None):
        # 支持自定义 base_url
        if base_url:
            self.client = OpenAI(api_key=api_key, base_url=base_url)

    def _get_api_key(self):
        # 优先检查 OPENCLAW_TOKEN
        api_key = os.getenv("OPENCLAW_TOKEN")
        if api_key:
            return api_key
        # 回退到 OPENAI_API_KEY
        return os.getenv("OPENAI_API_KEY")
```

### 2. Pipeline 支持 OpenClaw

```python
class SentimentExtractorPipeline:
    def __init__(self, provider="openclaw", base_url=None, ...):
        if provider == "openclaw":
            base_url = base_url or os.getenv("OPENCLAW_BASE_URL",
                                             "https://xuedingtoken.com")
            self.client = OpenAIClient(
                model_name="anthropic/claude-sonnet-4-6",
                base_url=base_url
            )
```

### 3. CLI 默认值更新

```python
parser.add_argument(
    "--provider",
    choices=["openai", "anthropic", "openclaw"],
    default="openclaw",  # 默认使用 OpenClaw
)
```

## 测试流程

### 快速测试（3 chunks）

```bash
# 方法 1: 环境变量
export OPENCLAW_TOKEN='your-token'
python src/sentiment_extractor.py --provider openclaw --limit 3

# 方法 2: 配置脚本
python setup_and_test_openclaw.py
```

### 完整运行

```bash
export OPENCLAW_TOKEN='your-token'
python src/sentiment_extractor.py --provider openclaw
```

## 预期输出

```
2026-04-21 01:00:00,000 - __main__ - INFO - Using OPENCLAW_TOKEN for authentication
2026-04-21 01:00:00,001 - __main__ - INFO - Using custom OpenAI endpoint: https://xuedingtoken.com
2026-04-21 01:00:00,002 - __main__ - INFO - Using OpenClaw with base_url: https://xuedingtoken.com
2026-04-21 01:00:00,003 - __main__ - INFO - Initialized openclaw client with model anthropic/claude-sonnet-4-6
...
2026-04-21 01:00:10,000 - __main__ - INFO - Saved 3 rows to data/processed/factor_data.parquet
2026-04-21 01:00:10,001 - __main__ - INFO - Pipeline completed successfully!
```

## 成本估算

使用 Claude Sonnet 4.6:
- 输入: ~1500 tokens/chunk
- 输出: ~50 tokens/chunk
- 成本取决于 OpenClaw 定价

## 故障排查

### 问题 1: OPENCLAW_TOKEN not found

**解决方案**:
```bash
# 检查环境变量
echo $OPENCLAW_TOKEN

# 重新设置
export OPENCLAW_TOKEN='your-token'
```

### 问题 2: Connection error

**可能原因**:
- Base URL 错误
- 网络问题
- Token 无效

**解决方案**:
```bash
# 测试连接
curl -H "Authorization: Bearer $OPENCLAW_TOKEN" \
     https://xuedingtoken.com/v1/models

# 检查 base_url
python -c "import os; print(os.getenv('OPENCLAW_BASE_URL', 'https://xuedingtoken.com'))"
```

### 问题 3: Model not found

**解决方案**:
```bash
# 使用完整模型名称
python src/sentiment_extractor.py \
    --provider openclaw \
    --model anthropic/claude-sonnet-4-6
```

## 与其他提供商对比

| 提供商 | 默认模型 | 认证变量 | Base URL |
|--------|----------|----------|----------|
| OpenAI | gpt-4o-mini | OPENAI_API_KEY | api.openai.com |
| Anthropic | claude-3-haiku | ANTHROPIC_API_KEY | api.anthropic.com |
| OpenClaw | claude-sonnet-4-6 | OPENCLAW_TOKEN | xuedingtoken.com |

## 下一步

配置完成后，可以运行完整 pipeline:

```bash
# 1. 确保数据已处理
python src/pipeline.py

# 2. 提取因子（完整数据集）
export OPENCLAW_TOKEN='your-token'
python src/sentiment_extractor.py --provider openclaw

# 3. 查看结果
python -c "
import pandas as pd
df = pd.read_parquet('data/processed/factor_data.parquet')
print(df[['ticker', 'confidence_score', 'risk_awareness', 'strategic_shift']].describe())
"
```
"""

if __name__ == "__main__":
    print(__doc__)
