"""
Technical Indicators Calculator for VnStock Screener.

Calculates all technical indicators from price history data.
"""

from typing import List, Dict, Any, Optional, Tuple
import math
from datetime import datetime


def calculate_sma(prices: List[float], period: int) -> Optional[float]:
    """Calculate Simple Moving Average."""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def calculate_ema(prices: List[float], period: int) -> Optional[float]:
    """Calculate Exponential Moving Average."""
    if len(prices) < period:
        return None
    
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period  # Start with SMA
    
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    
    return ema


def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """
    Calculate Relative Strength Index.
    
    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss
    """
    if len(prices) < period + 1:
        return None
    
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        if change >= 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    if len(gains) < period:
        return None
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    # Smooth the averages
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return round(rsi, 2)


def calculate_macd(
    prices: List[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Dict[str, Optional[float]]:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    
    MACD = EMA(12) - EMA(26)
    Signal = EMA(9) of MACD
    Histogram = MACD - Signal
    """
    result = {
        'macd': None,
        'signal': None,
        'histogram': None
    }
    
    if len(prices) < slow_period:
        return result
    
    # Calculate EMAs
    ema_fast = calculate_ema(prices, fast_period)
    ema_slow = calculate_ema(prices, slow_period)
    
    if ema_fast is None or ema_slow is None:
        return result
    
    # Calculate MACD line
    macd = ema_fast - ema_slow
    result['macd'] = round(macd, 4)
    
    # Calculate signal line (EMA of MACD values)
    # We need historical MACD values for this
    if len(prices) >= slow_period + signal_period:
        macd_values = []
        for i in range(slow_period, len(prices) + 1):
            sub_prices = prices[:i]
            fast = calculate_ema(sub_prices, fast_period)
            slow = calculate_ema(sub_prices, slow_period)
            if fast and slow:
                macd_values.append(fast - slow)
        
        if len(macd_values) >= signal_period:
            signal = calculate_ema(macd_values, signal_period)
            if signal:
                result['signal'] = round(signal, 4)
                result['histogram'] = round(macd - signal, 4)
    
    return result


def calculate_adx(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14
) -> Optional[float]:
    """
    Calculate Average Directional Index (ADX).
    
    Measures trend strength (not direction).
    ADX > 25 indicates strong trend.
    """
    if len(closes) < period + 1:
        return None
    
    # Calculate True Range and Directional Movement
    tr_list = []
    plus_dm_list = []
    minus_dm_list = []
    
    for i in range(1, len(closes)):
        # True Range
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        tr_list.append(tr)
        
        # Directional Movement
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]
        
        plus_dm = up_move if up_move > down_move and up_move > 0 else 0
        minus_dm = down_move if down_move > up_move and down_move > 0 else 0
        
        plus_dm_list.append(plus_dm)
        minus_dm_list.append(minus_dm)
    
    if len(tr_list) < period:
        return None
    
    # Calculate smoothed averages
    smoothed_tr = sum(tr_list[:period])
    smoothed_plus_dm = sum(plus_dm_list[:period])
    smoothed_minus_dm = sum(minus_dm_list[:period])
    
    for i in range(period, len(tr_list)):
        smoothed_tr = smoothed_tr - (smoothed_tr / period) + tr_list[i]
        smoothed_plus_dm = smoothed_plus_dm - (smoothed_plus_dm / period) + plus_dm_list[i]
        smoothed_minus_dm = smoothed_minus_dm - (smoothed_minus_dm / period) + minus_dm_list[i]
    
    # Calculate +DI and -DI
    plus_di = 100 * smoothed_plus_dm / smoothed_tr if smoothed_tr != 0 else 0
    minus_di = 100 * smoothed_minus_dm / smoothed_tr if smoothed_tr != 0 else 0
    
    # Calculate DX
    di_sum = plus_di + minus_di
    dx = 100 * abs(plus_di - minus_di) / di_sum if di_sum != 0 else 0
    
    # ADX is smoothed DX
    return round(dx, 2)


def calculate_price_return(prices: List[float], days: int) -> Optional[float]:
    """Calculate price return over specified days."""
    if len(prices) < days:
        return None
    
    current = prices[-1]
    past = prices[-(days + 1)] if len(prices) > days else prices[0]
    
    if past == 0:
        return None
    
    return round(((current - past) / past) * 100, 2)


def calculate_price_fluctuation(prices: List[float], days: int = 30) -> Optional[float]:
    """Calculate price fluctuation (volatility) as percentage."""
    if len(prices) < days:
        return None
    
    recent_prices = prices[-days:]
    mean = sum(recent_prices) / len(recent_prices)
    
    if mean == 0:
        return None
    
    variance = sum((p - mean) ** 2 for p in recent_prices) / len(recent_prices)
    std_dev = math.sqrt(variance)
    
    return round((std_dev / mean) * 100, 2)


def calculate_adtv(
    volumes: List[float],
    prices: List[float],
    days: int = 30
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calculate Average Daily Trading Volume and Value.
    
    Returns: (ADTV shares, ADTV value in billion VND)
    """
    if len(volumes) < days or len(prices) < days:
        return None, None
    
    recent_volumes = volumes[-days:]
    recent_prices = prices[-days:]
    
    avg_volume = sum(recent_volumes) / days
    
    # Calculate average daily value
    daily_values = [v * p for v, p in zip(recent_volumes, recent_prices)]
    avg_value = sum(daily_values) / days / 1_000_000_000  # Convert to billions
    
    return round(avg_volume, 0), round(avg_value, 2)


def classify_trend(
    ema_20: Optional[float],
    ema_50: Optional[float],
    ema_200: Optional[float],
    rsi: Optional[float],
    current_price: Optional[float]
) -> str:
    """
    Classify stock trend based on technical indicators.
    
    Returns: 'strong_uptrend', 'uptrend', 'sideways', 'downtrend', 'strong_downtrend'
    """
    if not all([ema_20, ema_50, current_price]):
        return 'unknown'
    
    score = 0
    
    # Price vs EMAs
    if current_price > ema_20:
        score += 1
    else:
        score -= 1
    
    if current_price > ema_50:
        score += 1
    else:
        score -= 1
    
    if ema_200 and current_price > ema_200:
        score += 1
    elif ema_200:
        score -= 1
    
    # EMA alignment
    if ema_20 > ema_50:
        score += 1
    else:
        score -= 1
    
    if ema_200 and ema_50 > ema_200:
        score += 1
    elif ema_200:
        score -= 1
    
    # RSI
    if rsi:
        if rsi > 70:
            score += 1
        elif rsi < 30:
            score -= 1
    
    # Classify
    if score >= 4:
        return 'strong_uptrend'
    elif score >= 2:
        return 'uptrend'
    elif score <= -4:
        return 'strong_downtrend'
    elif score <= -2:
        return 'downtrend'
    else:
        return 'sideways'


def calculate_all_indicators(
    history: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate all technical indicators from price history.
    
    Args:
        history: List of OHLCV records (oldest first)
    
    Returns:
        Dict with all calculated indicators
    """
    if not history or len(history) < 14:
        return {}
    
    # Extract price series
    closes = [h.get('close_price', 0) for h in history]
    highs = [h.get('high_price', 0) for h in history]
    lows = [h.get('low_price', 0) for h in history]
    volumes = [h.get('volume', 0) for h in history]
    
    current_price = closes[-1] if closes else 0
    
    # Calculate EMAs
    ema_20 = calculate_ema(closes, 20)
    ema_50 = calculate_ema(closes, 50)
    ema_200 = calculate_ema(closes, 200) if len(closes) >= 200 else None
    
    # Calculate indicators
    rsi = calculate_rsi(closes, 14)
    macd_data = calculate_macd(closes)
    adx = calculate_adx(highs, lows, closes, 14)
    
    # Price metrics
    price_return_3m = calculate_price_return(closes, 60)  # ~3 months
    price_return_1m = calculate_price_return(closes, 20)  # ~1 month
    fluctuation = calculate_price_fluctuation(closes, 30)
    
    # Volume metrics
    adtv_shares, adtv_value = calculate_adtv(volumes, closes, 30)
    
    # Current volume vs ADTV
    current_volume = volumes[-1] if volumes else 0
    vol_vs_adtv = None
    if adtv_shares and adtv_shares > 0:
        vol_vs_adtv = round(((current_volume / adtv_shares) - 1) * 100, 2)
    
    # EMA relationships
    price_vs_ema20 = None
    ema20_vs_ema50 = None
    ema50_vs_ema200 = None
    
    if ema_20 and ema_20 > 0:
        price_vs_ema20 = round(((current_price / ema_20) - 1) * 100, 2)
    if ema_20 and ema_50 and ema_50 > 0:
        ema20_vs_ema50 = round(((ema_20 / ema_50) - 1) * 100, 2)
    if ema_50 and ema_200 and ema_200 > 0:
        ema50_vs_ema200 = round(((ema_50 / ema_200) - 1) * 100, 2)
    
    # Trend classification
    trend = classify_trend(ema_20, ema_50, ema_200, rsi, current_price)
    
    return {
        # EMAs
        'ema_20': round(ema_20, 2) if ema_20 else None,
        'ema_50': round(ema_50, 2) if ema_50 else None,
        'ema_200': round(ema_200, 2) if ema_200 else None,
        
        # RSI
        'rsi_14': rsi,
        
        # MACD
        'macd': macd_data.get('macd'),
        'macd_signal': macd_data.get('signal'),
        'macd_histogram': macd_data.get('histogram'),
        
        # ADX
        'adx': adx,
        
        # Price metrics
        'price_return_3m': price_return_3m,
        'price_return_1m': price_return_1m,
        'price_fluctuation': fluctuation,
        
        # EMA relationships
        'price_vs_ema20': price_vs_ema20,
        'ema20_vs_ema50': ema20_vs_ema50,
        'ema50_vs_ema200': ema50_vs_ema200,
        
        # Volume metrics
        'adtv_shares': adtv_shares,
        'adtv_value': adtv_value,
        'volume_vs_adtv': vol_vs_adtv,
        
        # Trend
        'stock_trend': trend,
    }
