"""
Sentiment Factor Extractor
基于 LLM 的量化情绪因子提取系统
"""

import json
import logging
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Literal, Optional, Any
from abc import ABC, abstractmethod

import pandas as pd
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/sentiment_extractor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# Prompt 设计
# ============================================================================

PROMPT_VERSION = "v1.0"

SYSTEM_PROMPT = """You are a sell-side equity analyst evaluating earnings call transcripts.

Your task is to analyze text segments and extract quantitative sentiment factors that predict stock performance.

Rate each segment on three dimensions (1-10 scale):

1. **confidence_score** (1-10):
   - 1-3: Defensive, uncertain, hedging language ("may", "might", "challenging")
   - 4-6: Neutral, factual statements
   - 7-10: Strong conviction, assertive language ("will", "confident", "expect")

2. **risk_awareness** (1-10):
   - 1-3: Minimal risk discussion, overly optimistic
   - 4-6: Balanced risk acknowledgment
   - 7-10: Heavy emphasis on risks, headwinds, uncertainties

3. **strategic_shift** (1-10):
   - 1-3: Business as usual, no major changes
   - 4-6: Incremental adjustments
   - 7-10: Major pivots, new initiatives, significant strategic changes

**Output Format:**
Return ONLY a valid JSON object with these three numeric fields. No explanations, no additional text.

Example output:
{"confidence_score": 7, "risk_awareness": 4, "strategic_shift": 3}"""


FEW_SHOT_EXAMPLES = [
    {
        "text": """We are confident that our new product line will drive significant revenue growth in Q2.
        The market response has been overwhelmingly positive, and we expect to capture 15-20% market share
        within the first year. Our pipeline is robust and we're accelerating production.""",
        "output": {
            "confidence_score": 9,
            "risk_awareness": 2,
            "strategic_shift": 7
        },
        "reasoning": "High confidence (assertive language, specific targets), low risk awareness (no hedging), high strategic shift (new product line)"
    },
    {
        "text": """While we face some near-term headwinds from supply chain disruptions and rising input costs,
        we believe our diversified supplier base and pricing power will help us navigate these challenges.
        We're monitoring the situation closely and may need to adjust our guidance if conditions worsen.""",
        "output": {
            "confidence_score": 4,
            "risk_awareness": 8,
            "strategic_shift": 3
        },
        "reasoning": "Moderate confidence (hedging with 'may'), high risk awareness (multiple risks mentioned), low strategic shift (reactive adjustments)"
    }
]


def build_user_prompt(text: str) -> str:
    """构建用户 prompt"""
    # 包含 few-shot 示例
    examples_text = "\n\n".join([
        f"Example {i+1}:\nText: {ex['text']}\nOutput: {json.dumps(ex['output'])}"
        for i, ex in enumerate(FEW_SHOT_EXAMPLES)
    ])

    return f"""{examples_text}

Now analyze this text:

Text: {text}

Output:"""


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class SentimentFactors:
    """情绪因子数据结构"""
    confidence_score: int
    risk_awareness: int
    strategic_shift: int

    def validate(self) -> bool:
        """验证因子值在有效范围内"""
        return all(
            1 <= getattr(self, field) <= 10
            for field in ['confidence_score', 'risk_awareness', 'strategic_shift']
        )

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


@dataclass
class ExtractionMetadata:
    """提取元数据（用于可复现性）"""
    model_name: str
    prompt_version: str
    timestamp: str
    tokens_used: int
    api_latency_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# LLM 客户端抽象
# ============================================================================

class BaseLLMClient(ABC):
    """LLM 客户端基类"""

    def __init__(self, model_name: str, api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key or self._get_api_key()
        self.total_tokens = 0
        self.total_requests = 0

    @abstractmethod
    def _get_api_key(self) -> str:
        """从环境变量获取 API key"""
        pass

    @abstractmethod
    def _call_api(self, system_prompt: str, user_prompt: str) -> tuple[str, int, float]:
        """
        调用 API

        Returns:
            (response_text, tokens_used, latency_ms)
        """
        pass

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        before_sleep=lambda retry_state: logger.warning(
            f"Retry attempt {retry_state.attempt_number} after error: {retry_state.outcome.exception()}"
        )
    )
    def extract_sentiment(self, text: str) -> tuple[SentimentFactors, ExtractionMetadata]:
        """
        提取情绪因子（带重试机制）

        Returns:
            (SentimentFactors, ExtractionMetadata)
        """
        start_time = time.time()

        # 构建 prompt
        user_prompt = build_user_prompt(text)

        # 调用 API
        response_text, tokens_used, api_latency = self._call_api(SYSTEM_PROMPT, user_prompt)

        # 解析 JSON
        try:
            factors_dict = self._parse_json_response(response_text)
            factors = SentimentFactors(**factors_dict)

            if not factors.validate():
                raise ValueError(f"Invalid factor values: {factors}")

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse response: {response_text[:200]}")
            raise ValueError(f"Invalid API response format: {e}")

        # 创建元数据
        metadata = ExtractionMetadata(
            model_name=self.model_name,
            prompt_version=PROMPT_VERSION,
            timestamp=datetime.utcnow().isoformat(),
            tokens_used=tokens_used,
            api_latency_ms=api_latency
        )

        # 更新统计
        self.total_tokens += tokens_used
        self.total_requests += 1

        total_latency = (time.time() - start_time) * 1000
        logger.debug(f"Extracted factors in {total_latency:.0f}ms (API: {api_latency:.0f}ms)")

        return factors, metadata

    def _parse_json_response(self, response: str) -> Dict[str, int]:
        """
        解析 JSON 响应（容错处理）

        支持：
        - 纯 JSON
        - Markdown 代码块包裹的 JSON
        - 带额外文本的 JSON
        """
        # 去除前后空白
        response = response.strip()

        # 尝试直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 尝试提取 JSON 代码块
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            json_str = response[start:end].strip()
            return json.loads(json_str)

        # 尝试提取 {} 包裹的内容
        if "{" in response and "}" in response:
            start = response.find("{")
            end = response.rfind("}") + 1
            json_str = response[start:end]
            return json.loads(json_str)

        raise json.JSONDecodeError(f"Cannot extract JSON from response", response, 0)

    def get_stats(self) -> Dict[str, Any]:
        """获取使用统计"""
        return {
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "model_name": self.model_name
        }


class OpenAIClient(BaseLLMClient):
    """OpenAI API 客户端（支持 OpenAI 和 OpenClaw）"""

    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        super().__init__(model_name, api_key)
        self.base_url = base_url
        try:
            from openai import OpenAI
            # 如果提供了 base_url，使用自定义端点
            if self.base_url:
                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
                logger.info(f"Using custom OpenAI endpoint: {self.base_url}")
            else:
                self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("Please install openai: pip install openai")

    def _get_api_key(self) -> str:
        # 优先检查 ANTHROPIC_AUTH_TOKEN（用于 OpenClaw/Anthropic）
        api_key = os.getenv("ANTHROPIC_AUTH_TOKEN")
        if api_key:
            logger.info("Using ANTHROPIC_AUTH_TOKEN for authentication")
            return api_key

        # 检查 OPENCLAW_TOKEN
        api_key = os.getenv("OPENCLAW_TOKEN")
        if api_key:
            logger.info("Using OPENCLAW_TOKEN for authentication")
            return api_key

        # 回退到 OPENAI_API_KEY
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            logger.info("Using OPENAI_API_KEY for authentication")
            return api_key

        raise ValueError("No API key found. Set ANTHROPIC_AUTH_TOKEN, OPENCLAW_TOKEN, or OPENAI_API_KEY")

    def _call_api(self, system_prompt: str, user_prompt: str) -> tuple[str, int, float]:
        """调用 OpenAI API"""
        start_time = time.time()

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,  # 确保一致性
            max_tokens=150,
            response_format={"type": "json_object"}  # 强制 JSON 输出
        )

        latency_ms = (time.time() - start_time) * 1000

        content = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        return content, tokens_used, latency_ms


class AnthropicClient(BaseLLMClient):
    """Anthropic API 客户端"""

    def __init__(self, model_name: str = "claude-3-haiku-20240307", api_key: Optional[str] = None):
        super().__init__(model_name, api_key)
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("Please install anthropic: pip install anthropic")

    def _get_api_key(self) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        return api_key

    def _call_api(self, system_prompt: str, user_prompt: str) -> tuple[str, int, float]:
        """调用 Anthropic API"""
        start_time = time.time()

        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=150,
            temperature=0.0,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        latency_ms = (time.time() - start_time) * 1000

        content = response.content[0].text
        tokens_used = response.usage.input_tokens + response.usage.output_tokens

        return content, tokens_used, latency_ms


# ============================================================================
# 批量处理 Pipeline
# ============================================================================

class SentimentExtractorPipeline:
    """情绪因子提取 Pipeline"""

    def __init__(
        self,
        input_file: str = "data/processed/processed_data.parquet",
        output_file: str = "data/processed/factor_data.parquet",
        cache_file: str = "data/processed/.sentiment_cache.parquet",
        provider: Literal["openai", "anthropic", "openclaw"] = "openai",
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        batch_size: int = 10,
        rate_limit_delay: float = 0.5
    ):
        """
        Args:
            input_file: 输入 parquet 文件
            output_file: 输出 parquet 文件
            cache_file: 缓存文件（避免重复调用）
            provider: LLM 提供商 ('openai', 'anthropic', 'openclaw')
            model_name: 模型名称（None 使用默认）
            base_url: API base URL（用于 OpenClaw 等自定义端点）
            batch_size: 批处理大小
            rate_limit_delay: 请求间延迟（秒）
        """
        self.input_file = Path(input_file)
        self.output_file = Path(output_file)
        self.cache_file = Path(cache_file)
        self.batch_size = batch_size
        self.rate_limit_delay = rate_limit_delay

        # 初始化 LLM 客户端
        if provider == "openai":
            self.client = OpenAIClient(
                model_name=model_name or "gpt-4o-mini",
                base_url=base_url
            )
        elif provider == "openclaw":
            # OpenClaw 使用 OpenAI 兼容接口
            # 从环境变量读取 base_url（优先级：参数 > ANTHROPIC_BASE_URL > 默认值）
            if not base_url:
                base_url = os.getenv("ANTHROPIC_BASE_URL")
                if base_url and not base_url.endswith('/v1'):
                    base_url = base_url.rstrip('/') + '/v1'
                else:
                    base_url = os.getenv("OPENCLAW_BASE_URL", "https://xuedingtoken.com/v1")

            self.client = OpenAIClient(
                model_name=model_name or "claude-sonnet-4-6",
                base_url=base_url
            )
            logger.info(f"Using OpenClaw with base_url: {base_url}")
        elif provider == "anthropic":
            self.client = AnthropicClient(model_name or "claude-3-haiku-20240307")
        else:
            raise ValueError(f"Unknown provider: {provider}")

        logger.info(f"Initialized {provider} client with model {self.client.model_name}")

        # 加载缓存
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Dict]:
        """加载缓存（基于文本哈希）"""
        if self.cache_file.exists():
            try:
                cache_df = pd.read_parquet(self.cache_file)
                cache = cache_df.set_index('text_hash').to_dict('index')
                logger.info(f"Loaded {len(cache)} cached results")
                return cache
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
        return {}

    def _save_cache(self, df: pd.DataFrame):
        """保存缓存"""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(self.cache_file, index=False)
            logger.info(f"Saved cache with {len(df)} entries")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def _get_text_hash(self, text: str) -> str:
        """计算文本哈希（用于缓存键）"""
        import hashlib
        return hashlib.md5(text.encode()).hexdigest()

    def process_chunk(self, text: str) -> Optional[Dict[str, Any]]:
        """
        处理单个 chunk

        Returns:
            包含因子和元数据的字典，失败返回 None
        """
        text_hash = self._get_text_hash(text)

        # 检查缓存
        if text_hash in self.cache:
            logger.debug(f"Cache hit for text hash {text_hash[:8]}")
            return self.cache[text_hash]

        # 调用 API
        try:
            factors, metadata = self.client.extract_sentiment(text)

            result = {
                'text_hash': text_hash,
                **factors.to_dict(),
                **metadata.to_dict()
            }

            # 更新缓存
            self.cache[text_hash] = result

            return result

        except Exception as e:
            logger.error(f"Failed to process chunk: {e}")
            return None

    def run(self, limit: Optional[int] = None) -> pd.DataFrame:
        """
        运行完整 pipeline

        Args:
            limit: 限制处理的行数（用于测试）

        Returns:
            包含因子的 DataFrame
        """
        logger.info("=" * 60)
        logger.info("Starting Sentiment Extraction Pipeline")
        logger.info("=" * 60)

        # 读取输入数据
        df = pd.read_parquet(self.input_file)
        logger.info(f"Loaded {len(df)} chunks from {self.input_file}")

        if limit:
            df = df.head(limit)
            logger.info(f"Limited to first {limit} chunks for testing")

        # 批量处理
        results = []
        total = len(df)

        for i in range(0, total, self.batch_size):
            batch = df.iloc[i:i+self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (total + self.batch_size - 1) // self.batch_size

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)")

            for idx, row in batch.iterrows():
                result = self.process_chunk(row['text'])

                if result:
                    # 合并原始数据和因子
                    combined = {**row.to_dict(), **result}
                    results.append(combined)
                else:
                    logger.warning(f"Skipping chunk {idx} due to extraction failure")

                # Rate limiting
                time.sleep(self.rate_limit_delay)

            logger.info(f"Batch {batch_num} completed. Total tokens: {self.client.total_tokens}")

        # 创建结果 DataFrame
        if not results:
            logger.error("No results generated")
            return pd.DataFrame()

        result_df = pd.DataFrame(results)

        # 保存结果
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        result_df.to_parquet(self.output_file, index=False)
        logger.info(f"Saved {len(result_df)} rows to {self.output_file}")

        # 保存缓存
        cache_df = result_df[['text_hash', 'confidence_score', 'risk_awareness',
                               'strategic_shift', 'model_name', 'prompt_version',
                               'timestamp', 'tokens_used', 'api_latency_ms']]
        self._save_cache(cache_df)

        # 打印统计
        self._print_statistics(result_df)

        return result_df

    def _print_statistics(self, df: pd.DataFrame):
        """打印统计信息"""
        logger.info("=" * 60)
        logger.info("Extraction Statistics")
        logger.info("=" * 60)
        logger.info(f"Total chunks processed: {len(df)}")
        logger.info(f"Model: {df['model_name'].iloc[0]}")
        logger.info(f"Prompt version: {df['prompt_version'].iloc[0]}")
        logger.info(f"Total tokens used: {self.client.total_tokens}")
        logger.info(f"Total API requests: {self.client.total_requests}")
        logger.info(f"Avg API latency: {df['api_latency_ms'].mean():.0f}ms")

        logger.info("\nFactor Statistics:")
        for factor in ['confidence_score', 'risk_awareness', 'strategic_shift']:
            logger.info(f"  {factor}: mean={df[factor].mean():.2f}, std={df[factor].std():.2f}")


def main():
    """CLI 入口"""
    import argparse

    parser = argparse.ArgumentParser(description="Extract sentiment factors from transcripts")
    parser.add_argument(
        "--input-file",
        default="data/processed/processed_data.parquet",
        help="Input parquet file"
    )
    parser.add_argument(
        "--output-file",
        default="data/processed/factor_data.parquet",
        help="Output parquet file"
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic", "openclaw"],
        default="openclaw",
        help="LLM provider (default: openclaw)"
    )
    parser.add_argument(
        "--model",
        help="Model name (default: claude-sonnet-4-6 for openclaw, gpt-4o-mini for openai)"
    )
    parser.add_argument(
        "--base-url",
        help="API base URL (for OpenClaw or custom endpoints)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of chunks to process (for testing)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Batch size for processing"
    )
    parser.add_argument(
        "--rate-limit-delay",
        type=float,
        default=0.5,
        help="Delay between API calls (seconds)"
    )

    args = parser.parse_args()

    # 创建并运行 pipeline
    pipeline = SentimentExtractorPipeline(
        input_file=args.input_file,
        output_file=args.output_file,
        provider=args.provider,
        model_name=args.model,
        base_url=args.base_url,
        batch_size=args.batch_size,
        rate_limit_delay=args.rate_limit_delay
    )

    df = pipeline.run(limit=args.limit)

    if not df.empty:
        logger.info("Pipeline completed successfully!")
    else:
        logger.error("Pipeline failed to generate results")


if __name__ == "__main__":
    main()
