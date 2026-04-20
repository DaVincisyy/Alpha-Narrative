"""
Pipeline 使用文档

## 功能概述

数据处理 pipeline 将原始财报文本转换为结构化的 DataFrame，支持两种切分模式。

## 核心组件

### 1. TranscriptMetadata
从文件名解析元数据（ticker, year, quarter）

### 2. StandardTextCleaner
文本清洗：
- 去除非 ASCII 字符
- 标准化空格和换行
- 保留段落结构

### 3. Chunker（两种模式）

#### ParagraphChunker
按段落切分，适合保留语义完整性
- 参数：min_paragraph_length（最小段落长度）
- 自动合并过短段落

#### TokenChunker
按 token 数量切分，适合 LLM 输入
- 参数：chunk_size（每个 chunk 的 token 数）
- 参数：overlap（chunk 间重叠 token 数）

### 4. TranscriptPipeline
完整处理流程：读取 -> 清洗 -> 切分 -> 保存

## 使用方法

### 基本用法（Python）

```python
from src.pipeline import TranscriptPipeline

# 段落模式
pipeline = TranscriptPipeline(
    input_dir="data/raw_transcripts",
    output_file="data/processed/output.parquet",
    chunker_type="paragraph"
)
df = pipeline.run()

# Token 模式
pipeline = TranscriptPipeline(
    input_dir="data/raw_transcripts",
    output_file="data/processed/output_token.parquet",
    chunker_type="token",
    chunk_size=512,
    overlap=50
)
df = pipeline.run()
```

### CLI 用法

```bash
# 段落模式（默认）
python src/pipeline.py

# Token 模式
python src/pipeline.py --chunker token --chunk-size 256 --overlap 30

# 自定义路径
python src/pipeline.py \\
    --input-dir data/raw_transcripts \\
    --output-file data/processed/custom.parquet \\
    --chunker paragraph \\
    --min-paragraph-length 100
```

### CLI 参数

- `--input-dir`: 输入目录（默认：data/raw_transcripts）
- `--output-file`: 输出文件（默认：data/processed/processed_data.parquet）
- `--chunker`: 切分模式（paragraph 或 token）
- `--chunk-size`: token 模式的 chunk 大小（默认：512）
- `--overlap`: token 模式的重叠大小（默认：50）
- `--min-paragraph-length`: paragraph 模式的最小段落长度（默认：50）

## 输出格式

DataFrame 包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| ticker | str | 股票代码 |
| year | int | 年份 |
| quarter | str | 季度（Q1-Q4）|
| chunk_id | int | chunk 编号 |
| text | str | 文本内容 |
| position | int | 在原文中的位置 |

## 测试

运行单元测试：

```bash
pytest tests/test_pipeline.py -v
```

测试覆盖：
- 元数据解析
- 文本清洗
- 段落切分
- Token 切分
- 端到端 pipeline

## 扩展性

### 添加新的 Cleaner

```python
from src.pipeline import BaseTextCleaner

class CustomCleaner(BaseTextCleaner):
    def clean(self, text: str) -> str:
        # 自定义清洗逻辑
        return text
```

### 添加新的 Chunker

```python
from src.pipeline import BaseChunker

class CustomChunker(BaseChunker):
    def chunk(self, text: str, metadata: TranscriptMetadata) -> List[TextChunk]:
        # 自定义切分逻辑
        return chunks
```

## 性能

- CLF 2026Q1 (44KB)：
  - Paragraph 模式：6 chunks，平均 7.4KB/chunk
  - Token 模式 (256)：34 chunks，平均 1.5KB/chunk
- 处理时间：< 1 秒/文件

## 日志

日志保存在 `logs/pipeline.log`，包含：
- 文件处理进度
- Chunk 统计信息
- 错误和警告
"""

if __name__ == "__main__":
    print(__doc__)
