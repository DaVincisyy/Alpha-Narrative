"""
演示脚本：抓取多个公司的财报文本
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from transcript_scraper import fetch_latest_transcript

def main():
    # 测试多个 ticker
    tickers = ["CLF", "TSLA", "NVDA", "MSFT"]

    print("=" * 70)
    print("Transcript Scraper Demo - Fetching Multiple Tickers")
    print("=" * 70)

    results = {}

    for ticker in tickers:
        print(f"\n[{ticker}] Fetching...")
        try:
            result = fetch_latest_transcript(ticker)
            if result:
                # 读取文件大小
                size = Path(result).stat().st_size
                results[ticker] = {"status": "success", "path": result, "size": size}
                print(f"[{ticker}] Success - {size:,} bytes saved")
            else:
                results[ticker] = {"status": "not_found"}
                print(f"[{ticker}] No transcript found")
        except Exception as e:
            results[ticker] = {"status": "error", "error": str(e)}
            print(f"[{ticker}] Error: {e}")

    # 总结
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    success_count = sum(1 for r in results.values() if r["status"] == "success")
    print(f"Successfully fetched: {success_count}/{len(tickers)}")

    for ticker, result in results.items():
        if result["status"] == "success":
            print(f"  - {ticker}: {result['path']}")

if __name__ == "__main__":
    main()
