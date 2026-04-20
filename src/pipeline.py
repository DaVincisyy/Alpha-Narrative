"""
Data Processing Pipeline
可扩展的财报文本数据处理管道
"""

import logging
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Literal, Optional
from abc import ABC, abstractmethod

import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class TranscriptMetadata:
    """财报文本元数据"""
    ticker: str
    year: int
    quarter: str
    filepath: Path

    @classmethod
    def from_filename(cls, filepath: Path) -> Optional['TranscriptMetadata']:
        """
        从文件名解析元数据
        格式: TICKER_YYYYQX.txt
        例如: AAPL_2024Q1.txt
        """
        try:
            stem = filepath.stem  # 去除 .txt
            # 匹配模式: TICKER_YYYYQX
            match = re.match(r'^([A-Z]+)_(\d{4})(Q[1-4])$', stem)
            if not match:
                logger.warning(f"Filename does not match pattern: {filepath.name}")
                return None

            ticker, year, quarter = match.groups()
            return cls(
                ticker=ticker,
                year=int(year),
                quarter=quarter,
                filepath=filepath
            )
        except Exception as e:
            logger.error(f"Failed to parse filename {filepath.name}: {e}")
            return None


@dataclass
class TextChunk:
    """文本块数据结构"""
    ticker: str
    year: int
    quarter: str
    chunk_id: int
    text: str
    position: int  # 在原文中的起始位置

    def to_dict(self) -> dict:
        """转换为字典（用于 DataFrame）"""
        return asdict(self)


class BaseTextCleaner(ABC):
    """文本清洗基类"""

    @abstractmethod
    def clean(self, text: str) -> str:
        """清洗文本"""
        pass


class StandardTextCleaner(BaseTextCleaner):
    """标准文本清洗器"""

    def clean(self, text: str) -> str:
        """
        清洗文本：
        1. 去除非 ASCII 字符（保留基本标点）
        2. 标准化空格
        3. 标准化换行
        """
        # 去除非 ASCII（保留常见标点和换行）
        text = self._remove_non_ascii(text)

        # 标准化空格：多个空格 -> 单个空格
        text = re.sub(r'[ \t]+', ' ', text)

        # 标准化换行：多个换行 -> 双换行（保留段落结构）
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

        # 去除行首行尾空格
        text = '\n'.join(line.strip() for line in text.split('\n'))

        return text.strip()

    def _remove_non_ascii(self, text: str) -> str:
        """
        去除非 ASCII 字符
        保留: 字母、数字、基本标点、换行
        """
        # 保留 ASCII 可打印字符 + 换行符
        return ''.join(char for char in text if ord(char) < 128)


class BaseChunker(ABC):
    """文本切分基类"""

    @abstractmethod
    def chunk(self, text: str, metadata: TranscriptMetadata) -> List[TextChunk]:
        """切分文本为多个 chunk"""
        pass


class ParagraphChunker(BaseChunker):
    """按段落切分"""

    def __init__(self, min_paragraph_length: int = 50):
        """
        Args:
            min_paragraph_length: 最小段落长度（字符数），过短的段落会被合并
        """
        self.min_paragraph_length = min_paragraph_length

    def chunk(self, text: str, metadata: TranscriptMetadata) -> List[TextChunk]:
        """
        按段落切分文本
        段落定义：由双换行分隔
        """
        paragraphs = text.split('\n\n')
        chunks = []
        chunk_id = 0
        position = 0

        current_text = ""
        current_position = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                position += 2  # 跳过空段落的换行符
                continue

            # 如果当前累积文本为空，开始新的 chunk
            if not current_text:
                current_text = para
                current_position = position
            else:
                # 如果当前累积文本太短，继续合并
                if len(current_text) < self.min_paragraph_length:
                    current_text += "\n\n" + para
                else:
                    # 保存当前 chunk，开始新的
                    chunks.append(TextChunk(
                        ticker=metadata.ticker,
                        year=metadata.year,
                        quarter=metadata.quarter,
                        chunk_id=chunk_id,
                        text=current_text,
                        position=current_position
                    ))
                    chunk_id += 1
                    current_text = para
                    current_position = position

            position += len(para) + 2  # +2 for \n\n

        # 保存最后一个 chunk
        if current_text:
            chunks.append(TextChunk(
                ticker=metadata.ticker,
                year=metadata.year,
                quarter=metadata.quarter,
                chunk_id=chunk_id,
                text=current_text,
                position=current_position
            ))

        logger.info(f"Split {metadata.ticker}_{metadata.year}{metadata.quarter} into {len(chunks)} paragraph chunks")
        return chunks


class TokenChunker(BaseChunker):
    """按 token 长度切分（适用于 LLM）"""

    def __init__(self, chunk_size: int = 512, overlap: int = 50):
        """
        Args:
            chunk_size: 每个 chunk 的 token 数量（近似）
            overlap: chunk 之间的重叠 token 数
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str, metadata: TranscriptMetadata) -> List[TextChunk]:
        """
        按 token 长度切分文本
        使用简单的空格分词（近似 token）
        """
        # 简单分词：按空格分割
        tokens = text.split()
        chunks = []
        chunk_id = 0

        start_idx = 0
        while start_idx < len(tokens):
            # 提取当前 chunk 的 tokens
            end_idx = min(start_idx + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start_idx:end_idx]
            chunk_text = ' '.join(chunk_tokens)

            # 计算在原文中的位置（近似）
            position = len(' '.join(tokens[:start_idx]))

            chunks.append(TextChunk(
                ticker=metadata.ticker,
                year=metadata.year,
                quarter=metadata.quarter,
                chunk_id=chunk_id,
                text=chunk_text,
                position=position
            ))

            chunk_id += 1

            # 移动到下一个 chunk（考虑 overlap）
            start_idx += self.chunk_size - self.overlap

            # 避免无限循环
            if self.chunk_size <= self.overlap:
                break

        logger.info(f"Split {metadata.ticker}_{metadata.year}{metadata.quarter} into {len(chunks)} token chunks (size={self.chunk_size}, overlap={self.overlap})")
        return chunks


class TranscriptPipeline:
    """财报文本处理管道"""

    def __init__(
        self,
        input_dir: str = "data/raw_transcripts",
        output_file: str = "data/processed/processed_data.parquet",
        chunker_type: Literal["paragraph", "token"] = "paragraph",
        chunk_size: int = 512,
        overlap: int = 50,
        min_paragraph_length: int = 50
    ):
        """
        Args:
            input_dir: 输入目录（包含 .txt 文件）
            output_file: 输出文件路径（.parquet）
            chunker_type: 切分模式 ('paragraph' 或 'token')
            chunk_size: token 模式下的 chunk 大小
            overlap: token 模式下的重叠大小
            min_paragraph_length: paragraph 模式下的最小段落长度
        """
        self.input_dir = Path(input_dir)
        self.output_file = Path(output_file)
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

        # 初始化组件
        self.cleaner = StandardTextCleaner()

        if chunker_type == "paragraph":
            self.chunker = ParagraphChunker(min_paragraph_length=min_paragraph_length)
        elif chunker_type == "token":
            self.chunker = TokenChunker(chunk_size=chunk_size, overlap=overlap)
        else:
            raise ValueError(f"Unknown chunker_type: {chunker_type}")

        logger.info(f"Pipeline initialized: {chunker_type} chunker, input={input_dir}, output={output_file}")

    def process_file(self, filepath: Path) -> List[TextChunk]:
        """
        处理单个文件

        流程：
        1. 解析文件名获取元数据
        2. 读取文件内容
        3. 清洗文本
        4. 切分为 chunks
        """
        # 解析元数据
        metadata = TranscriptMetadata.from_filename(filepath)
        if not metadata:
            logger.warning(f"Skipping file with invalid name: {filepath.name}")
            return []

        # 读取文件
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                raw_text = f.read()
        except Exception as e:
            logger.error(f"Failed to read {filepath}: {e}")
            return []

        logger.info(f"Processing {filepath.name} ({len(raw_text)} chars)")

        # 清洗文本
        cleaned_text = self.cleaner.clean(raw_text)
        logger.debug(f"Cleaned text: {len(cleaned_text)} chars")

        # 切分为 chunks
        chunks = self.chunker.chunk(cleaned_text, metadata)

        return chunks

    def run(self) -> pd.DataFrame:
        """
        运行完整 pipeline

        Returns:
            处理后的 DataFrame
        """
        logger.info("=" * 60)
        logger.info("Starting Pipeline Execution")
        logger.info("=" * 60)

        # 查找所有 .txt 文件
        txt_files = list(self.input_dir.glob("*.txt"))
        logger.info(f"Found {len(txt_files)} transcript files")

        if not txt_files:
            logger.warning(f"No .txt files found in {self.input_dir}")
            return pd.DataFrame()

        # 处理所有文件
        all_chunks = []
        for filepath in txt_files:
            chunks = self.process_file(filepath)
            all_chunks.extend(chunks)

        logger.info(f"Total chunks generated: {len(all_chunks)}")

        # 转换为 DataFrame
        if not all_chunks:
            logger.warning("No chunks generated")
            return pd.DataFrame()

        df = pd.DataFrame([chunk.to_dict() for chunk in all_chunks])

        # 保存为 parquet
        df.to_parquet(self.output_file, index=False, engine='pyarrow')
        logger.info(f"Saved {len(df)} rows to {self.output_file}")

        # 显示统计信息
        self._print_statistics(df)

        return df

    def _print_statistics(self, df: pd.DataFrame):
        """打印数据统计信息"""
        logger.info("=" * 60)
        logger.info("Pipeline Statistics")
        logger.info("=" * 60)
        logger.info(f"Total rows: {len(df)}")
        logger.info(f"Unique tickers: {df['ticker'].nunique()}")
        logger.info(f"Date range: {df['year'].min()}-{df['year'].max()}")
        logger.info(f"Quarters: {sorted(df['quarter'].unique())}")
        logger.info(f"Avg chunk length: {df['text'].str.len().mean():.0f} chars")
        logger.info(f"Chunks per transcript: {df.groupby(['ticker', 'year', 'quarter']).size().mean():.1f}")


def main():
    """CLI 入口"""
    import argparse

    parser = argparse.ArgumentParser(description="Process earnings call transcripts")
    parser.add_argument(
        "--input-dir",
        default="data/raw_transcripts",
        help="Input directory containing .txt files"
    )
    parser.add_argument(
        "--output-file",
        default="data/processed/processed_data.parquet",
        help="Output parquet file path"
    )
    parser.add_argument(
        "--chunker",
        choices=["paragraph", "token"],
        default="paragraph",
        help="Chunking strategy"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=512,
        help="Chunk size for token chunker"
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=50,
        help="Overlap size for token chunker"
    )
    parser.add_argument(
        "--min-paragraph-length",
        type=int,
        default=50,
        help="Minimum paragraph length for paragraph chunker"
    )

    args = parser.parse_args()

    # 创建并运行 pipeline
    pipeline = TranscriptPipeline(
        input_dir=args.input_dir,
        output_file=args.output_file,
        chunker_type=args.chunker,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        min_paragraph_length=args.min_paragraph_length
    )

    df = pipeline.run()

    if not df.empty:
        logger.info("Pipeline completed successfully!")
    else:
        logger.warning("Pipeline completed but no data was generated")


if __name__ == "__main__":
    main()
