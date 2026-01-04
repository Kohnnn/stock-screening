"""
AI Service for Stock Analysis using Google Gemini.

Features:
- Gemini API integration with Google Search grounding
- Stock data aggregation from database
- Vietnamese analysis output with 9 sections
- Custom prompt overlay support
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import httpx
from loguru import logger

from database import Database


# ============================================
# Configuration
# ============================================

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Available models
GEMINI_MODELS = {
    "gemini-2.0-flash-exp": "Gemini 2.0 Flash (Experimental) - Best for grounding",
    "gemini-1.5-flash": "Gemini 1.5 Flash - Fast responses",
    "gemini-1.5-pro": "Gemini 1.5 Pro - Most capable",
}

DEFAULT_MODEL = "gemini-2.0-flash-exp"


# ============================================
# Vietnamese Analysis Prompt Template
# ============================================

ANALYSIS_PROMPT_TEMPLATE = """
Hãy đóng vai một chuyên gia phân tích tài chính hàng đầu tại Việt Nam (như SSI, VCSC, HSC).
Nhiệm vụ của bạn là phân tích chi tiết mã cổ phiếu {symbol} ({company_name}) để hỗ trợ nhà đầu tư ra quyết định.

**DỮ LIỆU ĐẦU VÀO:**
{stock_data}

**YÊU CẦU PHÂN TÍCH:**
Hãy viết báo cáo phân tích BẰNG TIẾNG VIỆT, sử dụng ngôn ngữ chuyên ngành tài chính nhưng dễ hiểu, với cấu trúc Markdown chuẩn như sau:

# 📊 Báo cáo Phân tích {symbol} - {company_name}

## 1. 🚦 Khuyến nghị Đầu tư (Quan trọng nhất)
*   **Đánh giá:** Mua / Nắm giữ / Bán
*   **Vùng giá mua khuyến nghị:** ...
*   **Giá mục tiêu (Target Price):** ...
*   **Thời gian nắm giữ:** Ngắn hạn / Trung hạn / Dài hạn
*   **Tóm tắt luận điểm chính:** (3 gạch đầu dòng quan trọng nhất)

## 2. 🏢 Tổng quan Doanh nghiệp & Vị thế
*   Mô tả ngắn gọn mô hình kinh doanh.
*   Vị thế trong ngành (Top mấy, thị phần).
*   Lợi thế cạnh tranh bền vững (Moat) là gì?

## 3. 💰 Sức khỏe Tài chính (Dựa trên dữ liệu)
*   **Định giá (P/E, P/B):** So sánh với trung bình ngành/lịch sử. Đắt hay rẻ?
*   **Hiệu quả (ROE, ROA):** Công ty sử dụng vốn có hiệu quả không?
*   **Rủi ro tài chính:** Nợ vay, dòng tiền như thế nào?

## 4. 📈 Phân tích Kỹ thuật (Technical Analysis)
*   Xu hướng hiện tại (Trend).
*   Các vùng hỗ trợ/kháng cự cứng.
*   Tín hiệu từ các chỉ báo (RSI, Volume,...).

## 5. ⚠️ Rủi ro & Thách thức
*   Nêu 3 rủi ro lớn nhất (Vĩ mô, Ngành, Nội tại).

## 6. 🔮 Triển vọng Tương lai
*   Động lực tăng trưởng (Catalyst) sắp tới là gì?

---
{custom_prompt}

**LƯU Ý KHI VIẾT:**
1.  **Tuyệt đối sử dụng Tiếng Việt** 100%.
2.  **Số liệu minh chứng:** Mọi nhận định phải đi kèm số liệu từ DỮ LIỆU ĐẦU VÀO hoặc Google Search.
3.  **Trình bày đẹp:** Sử dụng bold, bullet points, table để dễ đọc.
4.  **Google Grounding:** Tự động tìm kiếm tin tức mới nhất để bổ sung vào bài viết (ví dụ: kết quả kinh doanh quý gần nhất, tin đồn, v.v.).

Bắt đầu phân tích ngay:
"""


# ============================================
# Data Classes
# ============================================

@dataclass
class AIAnalysisRequest:
    """Request model for AI analysis."""
    symbol: str
    api_key: str
    model: str = DEFAULT_MODEL
    custom_prompt: Optional[str] = None
    prompt_template: Optional[str] = None
    enable_grounding: bool = True


@dataclass
class AIAnalysisResponse:
    """Response model for AI analysis."""
    analysis: str
    model: str
    symbol: str
    company_name: str
    grounding_sources: List[str]
    generated_at: str
    tokens_used: Optional[int] = None


# ============================================
# Stock Data Aggregator
# ============================================

class StockDataAggregator:
    """Aggregates all available stock data for AI analysis."""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def aggregate(self, symbol: str) -> Dict[str, Any]:
        """
        Aggregate all available data for a symbol.
        
        Returns a comprehensive data package for AI analysis.
        """
        data = {
            "symbol": symbol,
            "collected_at": datetime.now().isoformat(),
        }
        
        # Get basic stock info with prices
        stocks = await self.db.get_stocks(search=symbol, limit=1)
        if stocks:
            stock = stocks[0]
            data["basic_info"] = {
                "company_name": stock.get("company_name"),
                "exchange": stock.get("exchange"),
                "sector": stock.get("sector"),
                "industry": stock.get("industry"),
            }
            data["current_market"] = {
                "current_price": stock.get("current_price"),
                "price_change": stock.get("price_change"),
                "percent_change": stock.get("percent_change"),
                "volume": stock.get("volume"),
                "market_cap": stock.get("market_cap"),
                "pe_ratio": stock.get("pe_ratio"),
                "pb_ratio": stock.get("pb_ratio"),
                "roe": stock.get("roe"),
                "roa": stock.get("roa"),
                "eps": stock.get("eps"),
            }
        
        # Get technical metrics
        metrics = await self.db.get_stock_metrics(symbol)
        if metrics:
            data["technical_indicators"] = {
                "rsi_14": metrics.get("rsi_14"),
                "macd": metrics.get("macd"),
                "macd_signal": metrics.get("macd_signal"),
                "macd_histogram": metrics.get("macd_histogram"),
                "adx": metrics.get("adx"),
                "ema_20": metrics.get("ema_20"),
                "ema_50": metrics.get("ema_50"),
                "ema_200": metrics.get("ema_200"),
                "price_vs_ema20": metrics.get("price_vs_ema20"),
                "stock_trend": metrics.get("stock_trend"),
                "price_return_1m": metrics.get("price_return_1m"),
                "price_return_3m": metrics.get("price_return_3m"),
            }
        
        # Get screener metrics (84 columns)
        screener = await self._get_screener_metrics(symbol)
        if screener:
            data["screener_metrics"] = screener
        
        # Get price history (last 60 days for context)
        price_history = await self.db.get_price_history(symbol, days=60)
        if price_history:
            data["price_history_summary"] = {
                "days": len(price_history),
                "high_52w": max(p.get("high_price", 0) or 0 for p in price_history),
                "low_52w": min(p.get("low_price", float('inf')) or float('inf') for p in price_history),
                "recent_prices": price_history[:5],  # Last 5 days
            }
        
        # Get dividend history
        dividends = await self.db.get_dividend_history(symbol, limit=5)
        if dividends:
            data["dividend_history"] = dividends
        
        # Get company ratings
        ratings = await self.db.get_company_ratings(symbol)
        if ratings:
            data["ratings"] = ratings
        
        return data
    
    async def _get_screener_metrics(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get 84-column screener metrics."""
        query = "SELECT * FROM screener_metrics WHERE symbol = ?"
        
        async with self.db.connection() as db:
            cursor = await db.execute(query, (symbol,))
            row = await cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def format_for_prompt(self, data: Dict[str, Any]) -> str:
        """Format aggregated data as text for AI prompt."""
        lines = []
        
        # Basic info
        if "basic_info" in data:
            info = data["basic_info"]
            lines.append("### Thông tin cơ bản:")
            lines.append(f"- Tên công ty: {info.get('company_name', 'N/A')}")
            lines.append(f"- Sàn giao dịch: {info.get('exchange', 'N/A')}")
            lines.append(f"- Ngành: {info.get('sector', 'N/A')}")
            lines.append(f"- Lĩnh vực: {info.get('industry', 'N/A')}")
            lines.append("")
        
        # Current market data
        if "current_market" in data:
            market = data["current_market"]
            lines.append("### Dữ liệu thị trường hiện tại:")
            lines.append(f"- Giá hiện tại: {market.get('current_price', 'N/A'):,.0f} VND" if market.get('current_price') else "- Giá hiện tại: N/A")
            lines.append(f"- Thay đổi: {market.get('percent_change', 0):.2f}%" if market.get('percent_change') else "- Thay đổi: N/A")
            lines.append(f"- Khối lượng: {market.get('volume', 0):,.0f}" if market.get('volume') else "- Khối lượng: N/A")
            lines.append(f"- Vốn hóa: {market.get('market_cap', 0):,.0f} tỷ VND" if market.get('market_cap') else "- Vốn hóa: N/A")
            lines.append(f"- P/E: {market.get('pe_ratio', 'N/A')}")
            lines.append(f"- P/B: {market.get('pb_ratio', 'N/A')}")
            lines.append(f"- ROE: {market.get('roe', 'N/A')}%")
            lines.append(f"- ROA: {market.get('roa', 'N/A')}%")
            lines.append(f"- EPS: {market.get('eps', 'N/A')}")
            lines.append("")
        
        # Technical indicators
        if "technical_indicators" in data:
            tech = data["technical_indicators"]
            lines.append("### Chỉ báo kỹ thuật:")
            lines.append(f"- RSI (14): {tech.get('rsi_14', 'N/A')}")
            lines.append(f"- MACD: {tech.get('macd', 'N/A')}")
            lines.append(f"- MACD Histogram: {tech.get('macd_histogram', 'N/A')}")
            lines.append(f"- ADX: {tech.get('adx', 'N/A')}")
            lines.append(f"- EMA 20: {tech.get('ema_20', 'N/A')}")
            lines.append(f"- EMA 50: {tech.get('ema_50', 'N/A')}")
            lines.append(f"- EMA 200: {tech.get('ema_200', 'N/A')}")
            lines.append(f"- Xu hướng: {tech.get('stock_trend', 'N/A')}")
            lines.append(f"- Lợi nhuận 1 tháng: {tech.get('price_return_1m', 'N/A')}%")
            lines.append(f"- Lợi nhuận 3 tháng: {tech.get('price_return_3m', 'N/A')}%")
            lines.append("")
        
        # Screener metrics (selected important ones)
        if "screener_metrics" in data:
            sm = data["screener_metrics"]
            lines.append("### Chỉ số sàng lọc (Screener Metrics):")
            lines.append(f"- EV/EBITDA: {sm.get('ev_ebitda', 'N/A')}")
            lines.append(f"- Gross Margin: {sm.get('gross_margin', 'N/A')}%")
            lines.append(f"- Net Margin: {sm.get('net_margin', 'N/A')}%")
            lines.append(f"- D/E Ratio: {sm.get('doe', 'N/A')}")
            lines.append(f"- Dividend Yield: {sm.get('dividend_yield', 'N/A')}%")
            lines.append(f"- Revenue Growth 1Y: {sm.get('revenue_growth_1y', 'N/A')}%")
            lines.append(f"- Revenue Growth 5Y: {sm.get('revenue_growth_5y', 'N/A')}%")
            lines.append(f"- EPS Growth 1Y: {sm.get('eps_growth_1y', 'N/A')}%")
            lines.append(f"- EPS Growth 5Y: {sm.get('eps_growth_5y', 'N/A')}%")
            lines.append(f"- Price vs SMA50: {sm.get('price_vs_sma50', 'N/A')}%")
            lines.append(f"- Foreign Buy/Sell 20s: {sm.get('foreign_buysell_20s', 'N/A')}")
            lines.append(f"- Stock Rating: {sm.get('stock_rating', 'N/A')}")
            lines.append(f"- TCBS Recommend: {sm.get('tcbs_recommend', 'N/A')}")
            lines.append("")
        
        # Price history summary
        if "price_history_summary" in data:
            hist = data["price_history_summary"]
            lines.append("### Lịch sử giá (60 ngày):")
            lines.append(f"- Cao nhất: {hist.get('high_52w', 'N/A'):,.0f} VND" if hist.get('high_52w') and hist['high_52w'] != float('inf') else "- Cao nhất: N/A")
            lines.append(f"- Thấp nhất: {hist.get('low_52w', 'N/A'):,.0f} VND" if hist.get('low_52w') and hist['low_52w'] != float('inf') else "- Thấp nhất: N/A")
            lines.append("")
        
        # Dividends
        if "dividend_history" in data and data["dividend_history"]:
            lines.append("### Lịch sử cổ tức:")
            for div in data["dividend_history"][:3]:
                lines.append(f"- {div.get('ex_date', 'N/A')}: {div.get('cash_dividend', 0):,.0f} VND/cổ phiếu")
            lines.append("")
        
        # Ratings
        if "ratings" in data and data["ratings"]:
            lines.append("### Đánh giá:")
            for rating in data["ratings"]:
                lines.append(f"- {rating.get('rating_type', 'N/A')}: {rating.get('rating_value', 'N/A')} ({rating.get('rating_grade', 'N/A')})")
            lines.append("")
        
        return "\n".join(lines)


# ============================================
# Gemini API Client
# ============================================

class GeminiClient:
    """Client for Google Gemini API with grounding support."""
    
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self.api_key = api_key
        self.model = model
        self.base_url = GEMINI_API_BASE
    
    async def generate_content(
        self,
        prompt: str,
        enable_grounding: bool = True,
        timeout: float = 120.0
    ) -> Dict[str, Any]:
        """
        Generate content using Gemini API.
        
        Args:
            prompt: The prompt text
            enable_grounding: Enable Google Search grounding
            timeout: Request timeout in seconds
            
        Returns:
            Response dict with text and metadata
        """
        url = f"{self.base_url}/models/{self.model}:generateContent"
        
        # Build request body
        body = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "topP": 0.95,
                "topK": 40,
                "maxOutputTokens": 8192,
            }
        }
        
        # Add Google Search grounding for supported models
        if enable_grounding and "2.0" in self.model:
            body["tools"] = [{
                "google_search": {}
            }]
        
        headers = {
            "Content-Type": "application/json",
        }
        
        params = {"key": self.api_key}
        
        logger.info(f"🤖 Calling Gemini API: model={self.model}, grounding={enable_grounding}")
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url,
                json=body,
                headers=headers,
                params=params
            )
            
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"❌ Gemini API error: {response.status_code} - {error_text}")
                raise Exception(f"Gemini API error: {response.status_code} - {error_text}")
            
            return response.json()
    
    def extract_response(self, response: Dict[str, Any]) -> tuple[str, List[str], int]:
        """
        Extract text, sources, and token count from Gemini response.
        
        Returns:
            Tuple of (text, grounding_sources, token_count)
        """
        text = ""
        sources = []
        tokens = 0
        
        # Extract generated text
        if "candidates" in response and response["candidates"]:
            candidate = response["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                for part in candidate["content"]["parts"]:
                    if "text" in part:
                        text += part["text"]
        
        # Extract grounding sources
        if "candidates" in response and response["candidates"]:
            candidate = response["candidates"][0]
            if "groundingMetadata" in candidate:
                metadata = candidate["groundingMetadata"]
                if "groundingChunks" in metadata:
                    for chunk in metadata["groundingChunks"]:
                        if "web" in chunk:
                            web = chunk["web"]
                            source = f"[{web.get('title', 'Source')}]({web.get('uri', '#')})"
                            sources.append(source)
        
        # Token count
        if "usageMetadata" in response:
            tokens = response["usageMetadata"].get("totalTokenCount", 0)
        
        return text, sources, tokens
    
    async def test_connection(self) -> bool:
        """Test if the API key and model are valid."""
        try:
            response = await self.generate_content(
                prompt="Respond with only 'OK' if you receive this message.",
                enable_grounding=False,
                timeout=30.0
            )
            text, _, _ = self.extract_response(response)
            return "OK" in text.upper()
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False


# ============================================
# AI Analysis Service
# ============================================

class AIAnalysisService:
    """Main service for generating AI stock analysis."""
    
    def __init__(self, db: Database):
        self.db = db
        self.aggregator = StockDataAggregator(db)
    
    async def analyze(self, request: AIAnalysisRequest) -> AIAnalysisResponse:
        """
        Generate comprehensive AI analysis for a stock.
        
        Args:
            request: AIAnalysisRequest with symbol, api_key, model, etc.
            
        Returns:
            AIAnalysisResponse with analysis text and metadata
        """
        # Initialize Gemini client
        client = GeminiClient(api_key=request.api_key, model=request.model)
        
        # Aggregate stock data
        logger.info(f"📊 Aggregating data for {request.symbol}...")
        stock_data = await self.aggregator.aggregate(request.symbol)
        
        if not stock_data.get("basic_info"):
            raise ValueError(f"Stock {request.symbol} not found in database")
        
        company_name = stock_data["basic_info"]["company_name"] or request.symbol
        
        # Format data for prompt
        formatted_data = self.aggregator.format_for_prompt(stock_data)
        
        # Build custom prompt section
        custom_section = ""
        if request.custom_prompt:
            custom_section = f"\n\n**YÊU CẦU BỔ SUNG TỪ NGƯỜI DÙNG:**\n{request.custom_prompt}\n"
        
        # Build full prompt
        template = request.prompt_template if request.prompt_template else ANALYSIS_PROMPT_TEMPLATE
        
        prompt = template.format(
            symbol=request.symbol,
            company_name=company_name,
            stock_data=formatted_data,
            custom_prompt=custom_section
        )
        
        logger.info(f"🚀 Generating analysis for {request.symbol} with {request.model}...")
        
        # Call Gemini API
        response = await client.generate_content(
            prompt=prompt,
            enable_grounding=request.enable_grounding
        )
        
        # Extract results
        analysis_text, sources, tokens = client.extract_response(response)
        
        logger.info(f"✅ Analysis complete: {len(analysis_text)} chars, {tokens} tokens, {len(sources)} sources")
        
        return AIAnalysisResponse(
            analysis=analysis_text,
            model=request.model,
            symbol=request.symbol,
            company_name=company_name,
            grounding_sources=sources,
            generated_at=datetime.now().isoformat(),
            tokens_used=tokens
        )
    
    async def test_api(self, api_key: str, model: str = DEFAULT_MODEL) -> Dict[str, Any]:
        """Test API connection and return status."""
        client = GeminiClient(api_key=api_key, model=model)
        
        try:
            is_valid = await client.test_connection()
            return {
                "success": is_valid,
                "model": model,
                "message": "API connection successful" if is_valid else "API connection failed"
            }
        except Exception as e:
            return {
                "success": False,
                "model": model,
                "message": str(e)
            }


# ============================================
# Convenience Functions
# ============================================

def get_available_models() -> Dict[str, str]:
    """Get list of available Gemini models."""
    return GEMINI_MODELS.copy()


async def create_analysis_service() -> AIAnalysisService:
    """Create and return an AIAnalysisService instance."""
    db = Database()
    await db.initialize()
    return AIAnalysisService(db)
