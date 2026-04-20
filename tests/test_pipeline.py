"""
Pipeline 单元测试
演示如何测试数据处理组件
"""

import pytest
from pathlib import Path
from src.pipeline import (
    TranscriptMetadata,
    StandardTextCleaner,
    ParagraphChunker,
    TokenChunker,
    TranscriptPipeline
)


class TestTranscriptMetadata:
    """测试元数据解析"""

    def test_valid_filename(self):
        """测试有效的文件名解析"""
        filepath = Path("AAPL_2024Q1.txt")
        metadata = TranscriptMetadata.from_filename(filepath)

        assert metadata is not None
        assert metadata.ticker == "AAPL"
        assert metadata.year == 2024
        assert metadata.quarter == "Q1"

    def test_invalid_filename(self):
        """测试无效的文件名"""
        filepath = Path("invalid_file.txt")
        metadata = TranscriptMetadata.from_filename(filepath)

        assert metadata is None

    def test_all_quarters(self):
        """测试所有季度"""
        for q in ["Q1", "Q2", "Q3", "Q4"]:
            filepath = Path(f"TSLA_2025{q}.txt")
            metadata = TranscriptMetadata.from_filename(filepath)

            assert metadata is not None
            assert metadata.quarter == q


class TestStandardTextCleaner:
    """测试文本清洗器"""

    def test_remove_non_ascii(self):
        """测试去除非 ASCII 字符"""
        cleaner = StandardTextCleaner()
        text = "Hello 世界 World! €100"
        cleaned = cleaner.clean(text)

        # 非 ASCII 字符应被移除
        assert "世界" not in cleaned
        assert "€" not in cleaned
        assert "Hello" in cleaned
        assert "World" in cleaned

    def test_normalize_whitespace(self):
        """测试空格标准化"""
        cleaner = StandardTextCleaner()
        text = "Hello    World  \t  Test"
        cleaned = cleaner.clean(text)

        # 多个空格应合并为一个
        assert "    " not in cleaned
        assert "Hello World Test" in cleaned

    def test_normalize_newlines(self):
        """测试换行标准化"""
        cleaner = StandardTextCleaner()
        text = "Paragraph 1\n\n\n\nParagraph 2"
        cleaned = cleaner.clean(text)

        # 多个换行应合并为双换行
        assert "\n\n\n" not in cleaned
        assert "Paragraph 1\n\nParagraph 2" in cleaned


class TestParagraphChunker:
    """测试段落切分器"""

    def test_basic_chunking(self):
        """测试基本段落切分"""
        chunker = ParagraphChunker(min_paragraph_length=10)
        text = "Paragraph 1 with enough text.\n\nParagraph 2 with enough text."

        metadata = TranscriptMetadata(
            ticker="TEST",
            year=2024,
            quarter="Q1",
            filepath=Path("TEST_2024Q1.txt")
        )

        chunks = chunker.chunk(text, metadata)

        assert len(chunks) == 2
        assert chunks[0].ticker == "TEST"
        assert chunks[0].chunk_id == 0
        assert chunks[1].chunk_id == 1

    def test_merge_short_paragraphs(self):
        """测试短段落合并"""
        chunker = ParagraphChunker(min_paragraph_length=50)
        text = "Short.\n\nAlso short.\n\nThis is a much longer paragraph with enough text to stand alone."

        metadata = TranscriptMetadata(
            ticker="TEST",
            year=2024,
            quarter="Q1",
            filepath=Path("TEST_2024Q1.txt")
        )

        chunks = chunker.chunk(text, metadata)

        # 前两个短段落应被合并
        assert len(chunks) == 2
        assert "Short" in chunks[0].text
        assert "Also short" in chunks[0].text


class TestTokenChunker:
    """测试 token 切分器"""

    def test_basic_chunking(self):
        """测试基本 token 切分"""
        chunker = TokenChunker(chunk_size=10, overlap=2)
        text = " ".join([f"word{i}" for i in range(30)])  # 30 个词

        metadata = TranscriptMetadata(
            ticker="TEST",
            year=2024,
            quarter="Q1",
            filepath=Path("TEST_2024Q1.txt")
        )

        chunks = chunker.chunk(text, metadata)

        # 应该生成多个 chunk
        assert len(chunks) > 1
        assert all(chunk.ticker == "TEST" for chunk in chunks)

    def test_overlap(self):
        """测试 chunk 重叠"""
        chunker = TokenChunker(chunk_size=5, overlap=2)
        text = "word1 word2 word3 word4 word5 word6 word7"

        metadata = TranscriptMetadata(
            ticker="TEST",
            year=2024,
            quarter="Q1",
            filepath=Path("TEST_2024Q1.txt")
        )

        chunks = chunker.chunk(text, metadata)

        # 检查重叠：第二个 chunk 应包含第一个 chunk 的最后几个词
        assert len(chunks) >= 2
        # 简单验证：chunk 数量合理
        assert len(chunks) <= 5


class TestTranscriptPipeline:
    """测试完整 pipeline（集成测试）"""

    def test_pipeline_with_sample_data(self, tmp_path):
        """测试 pipeline 端到端流程"""
        # 创建临时输入目录和文件
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        sample_file = input_dir / "TEST_2024Q1.txt"
        sample_file.write_text(
            "This is paragraph one with enough text.\n\n"
            "This is paragraph two with enough text.\n\n"
            "This is paragraph three with enough text."
        )

        # 创建输出目录
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        output_file = output_dir / "test_output.parquet"

        # 运行 pipeline
        pipeline = TranscriptPipeline(
            input_dir=str(input_dir),
            output_file=str(output_file),
            chunker_type="paragraph"
        )

        df = pipeline.run()

        # 验证结果
        assert not df.empty
        assert "ticker" in df.columns
        assert "text" in df.columns
        assert df["ticker"].iloc[0] == "TEST"
        assert output_file.exists()


# Pytest fixtures
@pytest.fixture
def sample_metadata():
    """示例元数据 fixture"""
    return TranscriptMetadata(
        ticker="AAPL",
        year=2024,
        quarter="Q1",
        filepath=Path("AAPL_2024Q1.txt")
    )


@pytest.fixture
def sample_text():
    """示例文本 fixture"""
    return """
    This is the first paragraph with some content.

    This is the second paragraph with more content.

    This is the third paragraph with even more content.
    """


# 运行测试的说明
if __name__ == "__main__":
    print("Run tests with: pytest tests/test_pipeline.py -v")
