"""
OpenClaw 测试脚本
使用 OpenClaw API 测试情绪因子提取
"""

import sys
import os
from pathlib import Path

# 设置环境变量（如果未设置）
if not os.getenv("OPENCLAW_TOKEN"):
    print("WARNING: OPENCLAW_TOKEN not found in environment")
    print("Please set it before running:")
    print("  export OPENCLAW_TOKEN='your-token-here'")
    print("\nFor testing, you can also set it in this script:")
    print("  os.environ['OPENCLAW_TOKEN'] = 'your-token-here'")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent / "src"))

from sentiment_extractor import SentimentExtractorPipeline

print("=" * 70)
print("OpenClaw Sentiment Extraction Test")
print("=" * 70)

# 配置
config = {
    "provider": "openclaw",
    "model_name": "anthropic/claude-sonnet-4-6",
    "base_url": "https://xuedingtoken.com",
    "input_file": "data/processed/processed_data.parquet",
    "output_file": "data/processed/factor_data_openclaw.parquet",
    "batch_size": 3,
    "rate_limit_delay": 1.0
}

print("\nConfiguration:")
for key, value in config.items():
    print(f"  {key}: {value}")

print("\n" + "=" * 70)
print("Starting extraction (first 3 chunks)...")
print("=" * 70)

try:
    pipeline = SentimentExtractorPipeline(**config)

    # 测试前 3 个 chunks
    df = pipeline.run(limit=3)

    if not df.empty:
        print("\n" + "=" * 70)
        print("SUCCESS - Results:")
        print("=" * 70)

        # 显示结果
        print("\nExtracted Factors:")
        print(df[['ticker', 'year', 'quarter', 'chunk_id',
                  'confidence_score', 'risk_awareness', 'strategic_shift']].to_string())

        print("\n" + "=" * 70)
        print("Metadata:")
        print("=" * 70)
        print(f"Model: {df['model_name'].iloc[0]}")
        print(f"Prompt version: {df['prompt_version'].iloc[0]}")
        print(f"Total tokens used: {df['tokens_used'].sum()}")
        print(f"Avg API latency: {df['api_latency_ms'].mean():.0f}ms")

        print("\n" + "=" * 70)
        print("Factor Statistics:")
        print("=" * 70)
        for factor in ['confidence_score', 'risk_awareness', 'strategic_shift']:
            mean = df[factor].mean()
            std = df[factor].std()
            print(f"  {factor}: mean={mean:.2f}, std={std:.2f}")

        print("\n" + "=" * 70)
        print(f"Output saved to: {config['output_file']}")
        print("=" * 70)

    else:
        print("\nERROR: No results generated")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
