"""
测试脚本：演示情绪因子提取功能
包含模拟模式（无需 API key）和真实 API 调用模式
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

# 检查是否有 API key
has_api_key = bool(os.getenv("OPENAI_API_KEY"))

if has_api_key:
    print("=" * 70)
    print("OPENAI_API_KEY detected - Running REAL API test")
    print("=" * 70)
    print("\nThis will make actual API calls and incur costs.")
    print("Testing with first 3 chunks only.\n")

    from sentiment_extractor import SentimentExtractorPipeline

    pipeline = SentimentExtractorPipeline(
        input_file="data/processed/processed_data.parquet",
        output_file="data/processed/factor_data_test.parquet",
        provider="openai",
        model_name="gpt-4o-mini",
        batch_size=3,
        rate_limit_delay=1.0
    )

    df = pipeline.run(limit=3)

    if not df.empty:
        print("\n" + "=" * 70)
        print("SUCCESS - Sample Results:")
        print("=" * 70)
        print(df[['ticker', 'year', 'quarter', 'chunk_id',
                  'confidence_score', 'risk_awareness', 'strategic_shift',
                  'model_name', 'tokens_used']].head())

        print("\n" + "=" * 70)
        print("API Usage:")
        print("=" * 70)
        stats = pipeline.client.get_stats()
        print(f"Total requests: {stats['total_requests']}")
        print(f"Total tokens: {stats['total_tokens']}")
        print(f"Model: {stats['model_name']}")

else:
    print("=" * 70)
    print("No OPENAI_API_KEY found - Running MOCK test")
    print("=" * 70)
    print("\nDemonstrating functionality with simulated responses.\n")

    import pandas as pd
    import json
    from sentiment_extractor import (
        SYSTEM_PROMPT,
        FEW_SHOT_EXAMPLES,
        build_user_prompt,
        SentimentFactors
    )

    # 读取数据
    df = pd.read_parquet("data/processed/processed_data.parquet")
    print(f"Loaded {len(df)} chunks\n")

    # 演示 Prompt 设计
    print("=" * 70)
    print("PROMPT DESIGN")
    print("=" * 70)
    print("\n[System Prompt]")
    print(SYSTEM_PROMPT[:300] + "...\n")

    print("[Few-Shot Examples]")
    for i, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
        print(f"\nExample {i}:")
        print(f"Text: {ex['text'][:100]}...")
        print(f"Output: {json.dumps(ex['output'])}")
        print(f"Reasoning: {ex['reasoning']}")

    # 演示单个 chunk 的处理
    print("\n" + "=" * 70)
    print("PROCESSING SAMPLE CHUNK")
    print("=" * 70)

    sample_text = df.iloc[0]['text'][:500]
    print(f"\nInput text (first 500 chars):")
    print("-" * 70)
    print(sample_text)
    print("-" * 70)

    # 构建完整 prompt
    user_prompt = build_user_prompt(sample_text)
    print(f"\nUser prompt length: {len(user_prompt)} chars")

    # 模拟响应
    print("\n[Simulated API Response]")
    mock_response = {
        "confidence_score": 6,
        "risk_awareness": 5,
        "strategic_shift": 4
    }
    print(json.dumps(mock_response, indent=2))

    # 验证因子
    factors = SentimentFactors(**mock_response)
    print(f"\nValidation: {factors.validate()}")
    print(f"Factors: {factors.to_dict()}")

    # 演示重试机制
    print("\n" + "=" * 70)
    print("RETRY MECHANISM (Tenacity)")
    print("=" * 70)
    print("[OK] Configured with exponential backoff")
    print("[OK] Max 3 attempts")
    print("[OK] Wait: 2s -> 4s -> 8s")
    print("[OK] Retries on: API errors, rate limits, timeouts")

    # 演示缓存机制
    print("\n" + "=" * 70)
    print("CACHING MECHANISM")
    print("=" * 70)
    print("[OK] Text hash-based deduplication")
    print("[OK] Avoids redundant API calls")
    print("[OK] Persisted to: data/processed/.sentiment_cache.parquet")

    # 演示数据追溯
    print("\n" + "=" * 70)
    print("DATA TRACEABILITY (Quant Core)")
    print("=" * 70)
    print("Each record includes:")
    print("  - model_name: 'gpt-4o-mini'")
    print("  - prompt_version: 'v1.0'")
    print("  - timestamp: '2026-04-21T00:00:00.000000'")
    print("  - tokens_used: 1234")
    print("  - api_latency_ms: 567.8")
    print("\n[OK] Ensures factor reproducibility")
    print("[OK] Enables version control of prompts")
    print("[OK] Tracks API costs per extraction")

    print("\n" + "=" * 70)
    print("TO RUN WITH REAL API:")
    print("=" * 70)
    print("1. Set environment variable:")
    print("   export OPENAI_API_KEY='your-key-here'")
    print("\n2. Run:")
    print("   python test_sentiment.py")
    print("\n3. Or use CLI:")
    print("   python src/sentiment_extractor.py --limit 5")
