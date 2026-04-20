"""
设置 OpenClaw 环境变量并运行测试

使用方法：
1. 编辑此文件，填入你的 OPENCLAW_TOKEN
2. 运行: python setup_and_test_openclaw.py
"""

import os
import sys
import subprocess

# ============================================
# 在这里设置你的 OpenClaw Token
# ============================================
OPENCLAW_TOKEN = "your-token-here"  # 替换为实际的 token
OPENCLAW_BASE_URL = "https://xuedingtoken.com"

# ============================================

if OPENCLAW_TOKEN == "your-token-here":
    print("=" * 70)
    print("ERROR: Please set your OPENCLAW_TOKEN in this file")
    print("=" * 70)
    print("\nEdit setup_and_test_openclaw.py and replace:")
    print('  OPENCLAW_TOKEN = "your-token-here"')
    print("\nWith your actual token:")
    print('  OPENCLAW_TOKEN = "sk-xxx..."')
    sys.exit(1)

# 设置环境变量
os.environ["OPENCLAW_TOKEN"] = OPENCLAW_TOKEN
os.environ["OPENCLAW_BASE_URL"] = OPENCLAW_BASE_URL

print("=" * 70)
print("Environment variables set:")
print("=" * 70)
print(f"OPENCLAW_TOKEN: {OPENCLAW_TOKEN[:20]}...")
print(f"OPENCLAW_BASE_URL: {OPENCLAW_BASE_URL}")
print()

# 运行测试
print("=" * 70)
print("Running OpenClaw test...")
print("=" * 70)
print()

# 直接导入并运行
sys.path.insert(0, "src")
from sentiment_extractor import SentimentExtractorPipeline

try:
    pipeline = SentimentExtractorPipeline(
        provider="openclaw",
        model_name="anthropic/claude-sonnet-4-6",
        base_url=OPENCLAW_BASE_URL,
        input_file="data/processed/processed_data.parquet",
        output_file="data/processed/factor_data_openclaw.parquet",
        batch_size=3,
        rate_limit_delay=1.0
    )

    print("\nProcessing first 3 chunks...\n")
    df = pipeline.run(limit=3)

    if not df.empty:
        print("\n" + "=" * 70)
        print("SUCCESS!")
        print("=" * 70)
        print(f"\nProcessed {len(df)} chunks")
        print(f"Model: {df['model_name'].iloc[0]}")
        print(f"Total tokens: {df['tokens_used'].sum()}")
        print(f"\nFactor means:")
        print(f"  confidence_score: {df['confidence_score'].mean():.2f}")
        print(f"  risk_awareness: {df['risk_awareness'].mean():.2f}")
        print(f"  strategic_shift: {df['strategic_shift'].mean():.2f}")
        print(f"\nOutput: data/processed/factor_data_openclaw.parquet")
    else:
        print("\nERROR: No results generated")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
