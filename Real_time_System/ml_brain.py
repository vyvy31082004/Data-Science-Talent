import json
import os
import pandas as pd
import pandas_ta as ta
import logging
from historical_data_fetcher import fetch_historical_data

LOGGING_LEVEL = logging.INFO
logging.basicConfig(level=LOGGING_LEVEL, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'strategy_config.json')
STATUS_FILE_PATH = os.path.join(os.path.dirname(__file__), 'system_status.json') # File mới để ghi trạng thái
MARKET_PROXY_TICKER = 'FPT' # Tạm dùng FPT làm mã đại diện cho thị trường
ATR_PERIOD = 14
ATR_AVG_PERIOD = 100 # So sánh ATR hiện tại với trung bình 100 ngày

# --- CÁC NGƯỠNG ĐỘNG ---
# Định nghĩa các bộ tham số cho từng trạng thái thị trường
DYNAMIC_THRESHOLDS = {
    "LOW_VOLATILITY": {
        "RSI_OVERBOUGHT": 70,
        "RSI_OVERSOLD": 30,
        "ADX_THRESHOLD": 22
    },
    "HIGH_VOLATILITY": {
        "RSI_OVERBOUGHT": 75,
        "RSI_OVERSOLD": 25,
        "ADX_THRESHOLD": 28
    }
}

def get_market_volatility_state():
    """
    Phân tích dữ liệu lịch sử để xác định trạng thái biến động của thị trường.
    
    Returns:
        str: "HIGH_VOLATILITY" hoặc "LOW_VOLATILITY", hoặc None nếu có lỗi.
    """
    logging.info(f"Bắt đầu phân tích trạng thái biến động thị trường (dùng mã {MARKET_PROXY_TICKER})...")
    
    # Lấy dữ liệu lịch sử đủ dài để tính toán trung bình - Tăng lên để đảm bảo đủ dữ liệu cho rolling average
    df = fetch_historical_data(MARKET_PROXY_TICKER, days_back=250)
    
    if df is None or df.empty:
        logging.error("Không thể lấy dữ liệu thị trường, không thể xác định trạng thái.")
        return None
        
    # Tính toán ATR và đường trung bình của ATR
    df.ta.atr(length=ATR_PERIOD, append=True)
    atr_col = f'ATRr_{ATR_PERIOD}'
    atr_avg_col = f'ATR_AVG_{ATR_AVG_PERIOD}'
    df[atr_avg_col] = df[atr_col].rolling(window=ATR_AVG_PERIOD).mean()
    
    # Bỏ qua các giá trị NaN ban đầu để đảm bảo tính toán chính xác
    df.dropna(subset=[atr_col, atr_avg_col], inplace=True)
    if df.empty:
        logging.error("Không đủ dữ liệu để tính toán ATR trung bình sau khi loại bỏ NaN.")
        return None

    # Lấy giá trị gần nhất
    last_atr = df[atr_col].iloc[-1]
    last_avg_atr = df[atr_avg_col].iloc[-1]
    
    logging.info(f"ATR hiện tại: {last_atr:.2f}, Trung bình ATR {ATR_AVG_PERIOD} ngày: {last_avg_atr:.2f}")
    
    # So sánh và quyết định trạng thái
    if last_atr > last_avg_atr:
        logging.warning("Trạng thái thị trường: BIẾN ĐỘNG CAO (HIGH_VOLATILITY)")
        return "HIGH_VOLATILITY"
    else:
        logging.info("Trạng thái thị trường: BIẾN ĐỘNG THẤP (LOW_VOLATILITY)")
        return "LOW_VOLATILITY"

def update_strategy_config(market_state: str):
    """
    Cập nhật file strategy_config.json dựa trên trạng thái thị trường.
    """
    if not market_state or market_state not in DYNAMIC_THRESHOLDS:
        logging.error(f"Trạng thái thị trường không hợp lệ ('{market_state}'), không cập nhật cấu hình.")
        return

    logging.info(f"Bắt đầu cập nhật file cấu hình chiến lược với trạng thái: {market_state}...")
    
    try:
        # Đọc cấu hình hiện tại
        with open(CONFIG_PATH, 'r') as f:
            current_config = json.load(f)
        
        # Lấy bộ tham số mới
        new_thresholds = DYNAMIC_THRESHOLDS[market_state]
        
        # Cập nhật các giá trị
        current_config.update(new_thresholds)
        
        # Ghi lại vào file
        with open(CONFIG_PATH, 'w') as f:
            json.dump(current_config, f, indent=4)
            
        logging.info("Cập nhật file strategy_config.json thành công!")
        logging.info(f"Giá trị mới: RSI Overbought={new_thresholds['RSI_OVERBOUGHT']}, RSI Oversold={new_thresholds['RSI_OVERSOLD']}, ADX Threshold={new_thresholds['ADX_THRESHOLD']}")

        # Ghi lại trạng thái vào file system_status.json
        status_payload = {
            "last_updated": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            "market_state": market_state,
            "active_thresholds": new_thresholds
        }
        with open(STATUS_FILE_PATH, 'w') as f:
            json.dump(status_payload, f, indent=4)
        logging.info(f"Đã ghi trạng thái hệ thống vào file {os.path.basename(STATUS_FILE_PATH)}")

    except Exception as e:
        logging.error(f"Lỗi khi cập nhật file cấu hình: {e}", exc_info=True)


if __name__ == '__main__':
    logging.info("--- ẬP NHẬT NGƯỠNG CHIẾN LƯỢC ---")
    state = get_market_volatility_state()
    if state:
        update_strategy_config(state)
        
    logging.info("--- HOÀN TẤT ---")
