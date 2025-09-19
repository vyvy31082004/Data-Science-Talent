import pandas as pd
import pandas_ta as ta
from collections import deque
from FiinQuantX import RealTimeData
import json
import os

# --- Tải cấu hình chiến lược từ file JSON ---
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'strategy_config.json')
with open(CONFIG_PATH, 'r') as f:
    strategy_config = json.load(f)

# --- Bộ nhớ đệm cho dữ liệu lịch sử ---
MAX_HISTORY_LENGTH = 200
price_history = {}

def detect_signal(data: RealTimeData):
    """
    Phát hiện tín hiệu dựa trên ma trận quy tắc Momentum và Trend.
    """
    ticker = data.Ticker
    
    # --- Bước 1: Cập nhật bộ nhớ đệm ---
    if ticker not in price_history:
        price_history[ticker] = deque(maxlen=MAX_HISTORY_LENGTH)
    
    new_candle = { 'timestamp': getattr(data, 'Time', pd.Timestamp.now()), 'open': getattr(data, 'Open', data.Close), 'high': getattr(data, 'High', data.Close), 'low': getattr(data, 'Low', data.Close), 'close': data.Close, 'volume': getattr(data, 'Volume', 0) }
    price_history[ticker].append(new_candle)

    if len(price_history[ticker]) < 50:
        return None, "Đang thu thập đủ dữ liệu lịch sử..."

    # --- Bước 2: Tính toán các chỉ báo ---
    df = pd.DataFrame(list(price_history[ticker]))
    
    df.ta.rsi(length=strategy_config['RSI_PERIOD'], append=True)
    df.ta.macd(fast=strategy_config['MACD_FAST'], slow=strategy_config['MACD_SLOW'], signal=strategy_config['MACD_SIGNAL'], append=True)
    df.ta.sma(length=strategy_config['SMA_SHORT_PERIOD'], append=True)
    df.ta.sma(length=strategy_config['SMA_LONG_PERIOD'], append=True)
    df.ta.stoch(k=strategy_config['STOCH_K'], d=strategy_config['STOCH_D'], smooth_k=strategy_config['STOCH_SMOOTH'], append=True)
    df.ta.adx(length=strategy_config['ADX_PERIOD'], append=True)
    
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # --- Bước 3: Đặt tên cột và định nghĩa các điều kiện cơ bản ---
    rsi_col = f"RSI_{strategy_config['RSI_PERIOD']}"
    macd_line = f"MACD_{strategy_config['MACD_FAST']}_{strategy_config['MACD_SLOW']}_{strategy_config['MACD_SIGNAL']}"
    macd_signal = f"MACDs_{strategy_config['MACD_FAST']}_{strategy_config['MACD_SLOW']}_{strategy_config['MACD_SIGNAL']}"
    sma20 = f"SMA_{strategy_config['SMA_SHORT_PERIOD']}"
    sma50 = f"SMA_{strategy_config['SMA_LONG_PERIOD']}"
    stoch_k = f"STOCHk_{strategy_config['STOCH_K']}_{strategy_config['STOCH_D']}_{strategy_config['STOCH_SMOOTH']}"
    stoch_d = f"STOCHd_{strategy_config['STOCH_K']}_{strategy_config['STOCH_D']}_{strategy_config['STOCH_SMOOTH']}"
    adx = f"ADX_{strategy_config['ADX_PERIOD']}"

    # -- Điều kiện Momentum --
    is_momentum_buy = (last[rsi_col] < strategy_config['RSI_OVERSOLD']) or \
                      (last[stoch_k] > last[stoch_d] and prev[stoch_k] <= prev[stoch_d] and last[stoch_k] < 20)
    
    is_momentum_sell = (last[rsi_col] > strategy_config['RSI_OVERBOUGHT']) or \
                       (last[stoch_k] < last[stoch_d] and prev[stoch_k] >= prev[stoch_d] and last[stoch_k] > 80)

    # -- Điều kiện Trend --
    is_trend_buy = (last[macd_line] > last[macd_signal] and prev[macd_line] <= prev[macd_signal]) or \
                   (last['close'] > last[sma20] and prev['close'] <= prev[sma20]) or \
                   (last['close'] > last[sma50] and prev['close'] <= prev[sma50])

    is_trend_sell = (last[macd_line] < last[macd_signal] and prev[macd_line] >= prev[macd_signal]) or \
                    (last['close'] < last[sma20] and prev['close'] >= prev[sma20]) or \
                    (last['close'] < last[sma50] and prev['close'] >= prev[sma50])

    # -- Điều kiện Cảnh báo Rủi ro --
    is_trend_still_strong_up = (last[macd_line] > 0) and (last['close'] > last[sma20]) and (last['close'] > last[sma50]) and (last[adx] > strategy_config['ADX_THRESHOLD'])
    is_trend_still_strong_down = (last[macd_line] < 0) and (last['close'] < last[sma20]) and (last['close'] < last[sma50]) and (last[adx] > strategy_config['ADX_THRESHOLD'])

    # --- Bước 4: Áp dụng ma trận quy tắc ---
    
    # 1. Tín hiệu Mua mới
    if is_momentum_buy and is_trend_buy:
        return 'Mua mới', f"Momentum ({'RSI' if last[rsi_col] < strategy_config['RSI_OVERSOLD'] else 'Stoch'}) và Trend ({'MACD' if last[macd_line] > last[macd_signal] else 'SMA'}) đều xác nhận mua."
        
    # 2. Tín hiệu Bán chốt lời
    if is_momentum_sell and is_trend_sell:
        return 'Bán chốt lời', f"Momentum ({'RSI' if last[rsi_col] > strategy_config['RSI_OVERBOUGHT'] else 'Stoch'}) và Trend ({'MACD' if last[macd_line] < last[macd_signal] else 'SMA'}) đều xác nhận bán."

    # 3. Cảnh báo rủi ro (dễ điều chỉnh)
    if last[rsi_col] > strategy_config['RSI_OVERBOUGHT'] and is_trend_still_strong_up:
        return 'Cảnh báo rủi ro (dễ điều chỉnh)', f"RSI({last[rsi_col]:.2f}) quá mua nhưng xu hướng tăng vẫn còn rất mạnh (ADX={last[adx]:.2f})."
        
    # 4. Cảnh báo rủi ro (bắt đáy nguy hiểm)
    if last[rsi_col] < strategy_config['RSI_OVERSOLD'] and is_trend_still_strong_down:
        return 'Cảnh báo rủi ro (bắt đáy nguy hiểm)', f"RSI({last[rsi_col]:.2f}) quá bán nhưng xu hướng giảm vẫn còn rất mạnh (ADX={last[adx]:.2f})."
        
    # 5. Không tín hiệu / Quan sát (không cần trả về)
    
    return None, None
