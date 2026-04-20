"""
测试脚本：验证 transcript_scraper 功能
抓取财报电话会议文本
"""

import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from transcript_scraper import fetch_latest_transcript

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Transcript Scraper")
    print("=" * 60)

    # 使用 CLF 作为测试（网站上有最新数据）
    ticker = "CLF"
    print(f"\nFetching transcript for {ticker}...")

    result = fetch_latest_transcript(ticker)

    if result:
        print(f"\nSuccess! Transcript saved to: {result}")

        # 读取并显示前 500 个字符
        with open(result, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"\nTranscript preview (first 500 chars):")
            print("-" * 60)
            print(content[:500])
            print("-" * 60)
            print(f"\nTotal length: {len(content)} characters")
    else:
        print(f"\nFailed to fetch transcript for {ticker}")
        print("Possible reasons:")
        print("1. Network issues")
        print("2. Website structure changes")
        print("3. No recent transcripts available")
        print("\nTry testing with: CLF, TSLA, or other tickers with recent earnings")

