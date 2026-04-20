"""
Transcript Scraper Module
抓取上市公司财报电话会议文本的可扩展架构
"""

import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict
import requests
from bs4 import BeautifulSoup

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TranscriptData:
    """财报电话会议数据结构"""
    def __init__(self, ticker: str, year: int, quarter: str, content: str):
        self.ticker = ticker.upper()
        self.year = year
        self.quarter = quarter
        self.content = content

    def get_filename(self) -> str:
        """生成标准化文件名"""
        return f"{self.ticker}_{self.year}{self.quarter}.txt"


class BaseTranscriptSource(ABC):
    """财报文本数据源基类 - 可扩展架构"""

    def __init__(self, output_dir: str = "data/raw_transcripts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    @abstractmethod
    def fetch(self, ticker: str) -> Optional[TranscriptData]:
        """抓取最新财报文本 - 子类必须实现"""
        pass

    def save_transcript(self, data: TranscriptData) -> Path:
        """保存文本到本地"""
        filepath = self.output_dir / data.get_filename()
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(data.content)
        logger.info(f"Saved transcript to {filepath}")
        return filepath

    def _retry_request(self, url: str, max_retries: int = 3, delay: float = 2.0) -> Optional[requests.Response]:
        """带重试机制的 HTTP 请求"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(delay)
                else:
                    logger.error(f"All retries failed for {url}")
                    return None
        return None


class MotleyFoolSource(BaseTranscriptSource):
    """Motley Fool 数据源实现"""

    BASE_URL = "https://www.fool.com"
    SEARCH_URL = f"{BASE_URL}/earnings-call-transcripts/"

    def fetch(self, ticker: str) -> Optional[TranscriptData]:
        """
        抓取 Motley Fool 最新财报文本

        流程：
        1. 访问搜索页面，查找该 ticker 的 transcript 列表
        2. 定位最新的 transcript 链接
        3. 访问详情页，提取完整文本和元数据
        """
        ticker = ticker.upper()
        logger.info(f"Fetching latest transcript for {ticker} from Motley Fool")

        # Step 1: 搜索 ticker 的 transcript 列表页
        search_url = f"{self.SEARCH_URL}?ticker={ticker}"
        response = self._retry_request(search_url)
        if not response:
            logger.error(f"Failed to access search page for {ticker}")
            return None

        soup = BeautifulSoup(response.content, 'html.parser')

        # Step 2: 查找最新 transcript 链接
        # Motley Fool 通常使用特定的 CSS 类或结构来组织 transcript 列表
        transcript_link = self._find_latest_transcript_link(soup, ticker)
        if not transcript_link:
            logger.error(f"No transcript found for {ticker}")
            return None

        # Step 3: 访问详情页
        full_url = transcript_link if transcript_link.startswith('http') else f"{self.BASE_URL}{transcript_link}"
        detail_response = self._retry_request(full_url)
        if not detail_response:
            logger.error(f"Failed to access transcript detail page: {full_url}")
            return None

        # Step 4: 解析详情页，提取数据
        return self._parse_transcript_page(detail_response.content, ticker)

    def _find_latest_transcript_link(self, soup: BeautifulSoup, ticker: str) -> Optional[str]:
        """
        从搜索结果页找到最新 transcript 链接

        策略：
        - 查找包含 '/earnings/call-transcripts/' 的链接
        - 匹配 ticker 在 URL 中
        - 优先选择日期最新的
        """
        # 策略 1: 查找新格式的 transcript 链接 (/earnings/call-transcripts/YYYY/MM/DD/...)
        links = soup.find_all('a', href=True)
        transcript_links = [
            link['href'] for link in links
            if '/earnings/call-transcripts/' in link['href'] and ticker.lower() in link['href'].lower()
        ]

        if transcript_links:
            # URL 通常按日期排序，第一个是最新的
            logger.info(f"Found {len(transcript_links)} transcript(s) for {ticker}")
            return transcript_links[0]

        # 策略 2: 旧格式兼容 (earnings-call-transcript)
        old_format_links = [
            link['href'] for link in links
            if 'earnings-call-transcript' in link['href'].lower() and ticker.lower() in link['href'].lower()
        ]

        if old_format_links:
            logger.info(f"Found {len(old_format_links)} transcript(s) via old format")
            return old_format_links[0]

        return None

    def _parse_transcript_page(self, html_content: bytes, ticker: str) -> Optional[TranscriptData]:
        """
        解析 transcript 详情页，提取元数据和正文

        提取内容：
        - year, quarter: 从标题或 URL 中解析
        - content: 主要文本内容
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # 提取标题（通常包含公司名、年份、季度）
        title = soup.find('h1')
        if not title:
            title = soup.find('title')

        title_text = title.get_text() if title else ""
        logger.info(f"Parsing transcript: {title_text}")

        # 解析年份和季度
        year, quarter = self._extract_year_quarter(title_text)
        if not year or not quarter:
            logger.warning("Could not extract year/quarter from title, using defaults")
            year = 2024  # 默认值
            quarter = "Q4"

        # 提取正文内容
        # Motley Fool 通常将 transcript 放在特定的 div 或 article 标签中
        content = self._extract_transcript_content(soup)
        if not content:
            logger.error("Failed to extract transcript content")
            return None

        logger.info(f"Successfully extracted transcript: {ticker} {year}{quarter}, {len(content)} characters")
        return TranscriptData(ticker=ticker, year=year, quarter=quarter, content=content)

    def _extract_year_quarter(self, text: str) -> tuple[Optional[int], Optional[str]]:
        """从文本中提取年份和季度"""
        import re

        # 查找年份 (2020-2030)
        year_match = re.search(r'20[2-3]\d', text)
        year = int(year_match.group()) if year_match else None

        # 查找季度 (Q1, Q2, Q3, Q4)
        quarter_match = re.search(r'Q[1-4]', text, re.IGNORECASE)
        quarter = quarter_match.group().upper() if quarter_match else None

        return year, quarter

    def _extract_transcript_content(self, soup: BeautifulSoup) -> Optional[str]:
        """
        提取 transcript 正文内容

        策略：
        - 优先查找 main 标签（Motley Fool 新版结构）
        - 备选 article 标签
        - 过滤广告、导航等无关内容
        - 保留段落结构
        """
        # 策略 1: 查找 main 标签（Motley Fool 当前使用）
        main = soup.find('main')
        if main:
            # 移除脚本、样式、导航等
            for tag in main.find_all(['script', 'style', 'nav', 'aside', 'header', 'footer']):
                tag.decompose()
            content = main.get_text(separator='\n', strip=True)
            if len(content) > 500:  # 确保内容足够长
                return content

        # 策略 2: 查找 article 标签
        article = soup.find('article')
        if article:
            for tag in article.find_all(['script', 'style', 'nav', 'aside']):
                tag.decompose()
            content = article.get_text(separator='\n', strip=True)
            if len(content) > 500:
                return content

        # 策略 3: 查找包含 'transcript' 或 'content' 的 div
        content_div = soup.find('div', class_=lambda x: x and ('transcript' in x.lower() or 'content' in x.lower()))
        if content_div:
            for tag in content_div.find_all(['script', 'style']):
                tag.decompose()
            content = content_div.get_text(separator='\n', strip=True)
            if len(content) > 500:
                return content

        # 兜底：返回 body 的文本（可能包含噪音）
        body = soup.find('body')
        if body:
            logger.warning("Using body text as fallback - may contain noise")
            return body.get_text(separator='\n', strip=True)

        return None


def fetch_latest_transcript(ticker: str, source: str = "motley_fool") -> Optional[str]:
    """
    便捷函数：抓取并保存最新财报文本

    Args:
        ticker: 股票代码
        source: 数据源类型 (默认 'motley_fool')

    Returns:
        保存的文件路径，失败返回 None
    """
    # 数据源工厂模式
    sources: Dict[str, type[BaseTranscriptSource]] = {
        "motley_fool": MotleyFoolSource,
        # 未来扩展：
        # "seeking_alpha": SeekingAlphaSource,
        # "ir_website": IRWebsiteSource,
    }

    if source not in sources:
        logger.error(f"Unknown source: {source}. Available: {list(sources.keys())}")
        return None

    scraper = sources[source]()
    data = scraper.fetch(ticker)

    if data:
        filepath = scraper.save_transcript(data)
        return str(filepath)

    return None


# 未来扩展示例（占位符）
class SeekingAlphaSource(BaseTranscriptSource):
    """Seeking Alpha 数据源 - 待实现"""
    def fetch(self, ticker: str) -> Optional[TranscriptData]:
        raise NotImplementedError("SeekingAlpha source not yet implemented")


class IRWebsiteSource(BaseTranscriptSource):
    """公司 IR 官网数据源 - 待实现"""
    def fetch(self, ticker: str) -> Optional[TranscriptData]:
        raise NotImplementedError("IR website source not yet implemented")
