"""
Sentiment Extractor 单元测试
测试 JSON 解析、重试机制、因子验证
"""

import pytest
import json
from unittest.mock import Mock, patch
from src.sentiment_extractor import (
    SentimentFactors,
    ExtractionMetadata,
    BaseLLMClient,
    build_user_prompt,
    SYSTEM_PROMPT,
    FEW_SHOT_EXAMPLES
)


class TestSentimentFactors:
    """测试情绪因子数据结构"""

    def test_valid_factors(self):
        """测试有效的因子值"""
        factors = SentimentFactors(
            confidence_score=7,
            risk_awareness=5,
            strategic_shift=3
        )
        assert factors.validate()

    def test_invalid_factors_too_low(self):
        """测试过低的因子值"""
        factors = SentimentFactors(
            confidence_score=0,
            risk_awareness=5,
            strategic_shift=3
        )
        assert not factors.validate()

    def test_invalid_factors_too_high(self):
        """测试过高的因子值"""
        factors = SentimentFactors(
            confidence_score=7,
            risk_awareness=11,
            strategic_shift=3
        )
        assert not factors.validate()

    def test_to_dict(self):
        """测试转换为字典"""
        factors = SentimentFactors(
            confidence_score=7,
            risk_awareness=5,
            strategic_shift=3
        )
        d = factors.to_dict()
        assert d['confidence_score'] == 7
        assert d['risk_awareness'] == 5
        assert d['strategic_shift'] == 3


class TestExtractionMetadata:
    """测试提取元数据"""

    def test_metadata_creation(self):
        """测试元数据创建"""
        metadata = ExtractionMetadata(
            model_name="gpt-4o-mini",
            prompt_version="v1.0",
            timestamp="2026-04-21T00:00:00",
            tokens_used=1234,
            api_latency_ms=567.8
        )
        assert metadata.model_name == "gpt-4o-mini"
        assert metadata.tokens_used == 1234

    def test_metadata_to_dict(self):
        """测试元数据转换为字典"""
        metadata = ExtractionMetadata(
            model_name="gpt-4o-mini",
            prompt_version="v1.0",
            timestamp="2026-04-21T00:00:00",
            tokens_used=1234,
            api_latency_ms=567.8
        )
        d = metadata.to_dict()
        assert 'model_name' in d
        assert 'tokens_used' in d


class TestPromptBuilding:
    """测试 Prompt 构建"""

    def test_system_prompt_exists(self):
        """测试系统 prompt 存在"""
        assert len(SYSTEM_PROMPT) > 0
        assert "sell-side" in SYSTEM_PROMPT
        assert "confidence_score" in SYSTEM_PROMPT

    def test_few_shot_examples(self):
        """测试 few-shot 示例"""
        assert len(FEW_SHOT_EXAMPLES) >= 2
        for ex in FEW_SHOT_EXAMPLES:
            assert 'text' in ex
            assert 'output' in ex
            assert 'confidence_score' in ex['output']

    def test_build_user_prompt(self):
        """测试用户 prompt 构建"""
        text = "This is a test transcript."
        prompt = build_user_prompt(text)

        assert "Example 1:" in prompt
        assert "Example 2:" in prompt
        assert text in prompt
        assert "Output:" in prompt


class MockLLMClient(BaseLLMClient):
    """Mock LLM 客户端用于测试"""

    def _get_api_key(self) -> str:
        return "mock-key"

    def _call_api(self, system_prompt: str, user_prompt: str) -> tuple[str, int, float]:
        # 返回模拟响应
        response = json.dumps({
            "confidence_score": 7,
            "risk_awareness": 5,
            "strategic_shift": 3
        })
        return response, 100, 50.0


class TestJSONParsing:
    """测试 JSON 解析（容错）"""

    def test_parse_pure_json(self):
        """测试纯 JSON 解析"""
        client = MockLLMClient(model_name="test")
        response = '{"confidence_score": 7, "risk_awareness": 5, "strategic_shift": 3}'
        result = client._parse_json_response(response)

        assert result['confidence_score'] == 7
        assert result['risk_awareness'] == 5

    def test_parse_json_with_markdown(self):
        """测试 Markdown 代码块包裹的 JSON"""
        client = MockLLMClient(model_name="test")
        response = '''```json
{"confidence_score": 7, "risk_awareness": 5, "strategic_shift": 3}
```'''
        result = client._parse_json_response(response)

        assert result['confidence_score'] == 7

    def test_parse_json_with_extra_text(self):
        """测试带额外文本的 JSON"""
        client = MockLLMClient(model_name="test")
        response = 'Here is the analysis: {"confidence_score": 7, "risk_awareness": 5, "strategic_shift": 3} Done.'
        result = client._parse_json_response(response)

        assert result['confidence_score'] == 7

    def test_parse_invalid_json(self):
        """测试无效 JSON"""
        client = MockLLMClient(model_name="test")
        response = 'This is not JSON at all'

        with pytest.raises(json.JSONDecodeError):
            client._parse_json_response(response)


class TestLLMClient:
    """测试 LLM 客户端"""

    def test_extract_sentiment(self):
        """测试情绪提取"""
        client = MockLLMClient(model_name="test")
        text = "We are confident about the future."

        factors, metadata = client.extract_sentiment(text)

        assert factors.validate()
        assert metadata.model_name == "test"
        assert metadata.tokens_used == 100

    def test_token_counting(self):
        """测试 token 统计"""
        client = MockLLMClient(model_name="test")

        assert client.total_tokens == 0
        assert client.total_requests == 0

        client.extract_sentiment("Test text 1")
        assert client.total_tokens == 100
        assert client.total_requests == 1

        client.extract_sentiment("Test text 2")
        assert client.total_tokens == 200
        assert client.total_requests == 2

    def test_get_stats(self):
        """测试统计信息"""
        client = MockLLMClient(model_name="test")
        client.extract_sentiment("Test")

        stats = client.get_stats()
        assert stats['total_requests'] == 1
        assert stats['total_tokens'] == 100
        assert stats['model_name'] == "test"


class TestRetryMechanism:
    """测试重试机制"""

    def test_retry_on_failure(self):
        """测试失败时重试"""
        client = MockLLMClient(model_name="test")

        # Mock _call_api 使其前两次失败，第三次成功
        call_count = 0

        def mock_call_api(system_prompt, user_prompt):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("API Error")
            return '{"confidence_score": 7, "risk_awareness": 5, "strategic_shift": 3}', 100, 50.0

        client._call_api = mock_call_api

        # 应该成功（经过 2 次重试）
        factors, metadata = client.extract_sentiment("Test")
        assert factors.validate()
        assert call_count == 3

    def test_max_retries_exceeded(self):
        """测试超过最大重试次数"""
        client = MockLLMClient(model_name="test")

        # Mock _call_api 使其总是失败
        def mock_call_api(system_prompt, user_prompt):
            raise Exception("Persistent API Error")

        client._call_api = mock_call_api

        # 应该在 3 次尝试后失败
        with pytest.raises(Exception):
            client.extract_sentiment("Test")


# 运行测试的说明
if __name__ == "__main__":
    print("Run tests with: pytest tests/test_sentiment_extractor.py -v")
