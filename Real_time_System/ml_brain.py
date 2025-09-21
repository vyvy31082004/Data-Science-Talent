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
MARKET_PROXY_TICKERS = ['VNINDEX', 'HNXINDEX', 'UPCOMINDEX'] # Phân tích cả 3 sàn chính

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
    Phân tích trạng thái biến động của thị trường dựa trên đa số các chỉ số chính.
    """
    logging.info(f"Bắt đầu phân tích trạng thái biến động thị trường từ các chỉ số: {MARKET_PROXY_TICKERS}...")
    
    volatility_states = []
    
    for ticker in MARKET_PROXY_TICKERS:
        logging.info(f"--- Đang phân tích chỉ số: {ticker} ---")
        df = fetch_historical_data(ticker, days_back=250)

        if df is None or df.empty:
            logging.error(f"Không thể lấy dữ liệu cho chỉ số {ticker}. Bỏ qua...")
            continue

        df.ta.atr(length=ATR_PERIOD, append=True)
        atr_col = f'ATRr_{ATR_PERIOD}'
        atr_avg_col = f'ATR_AVG_{ATR_AVG_PERIOD}'
        df[atr_avg_col] = df[atr_col].rolling(window=ATR_AVG_PERIOD).mean()
        
        df.dropna(subset=[atr_col, atr_avg_col], inplace=True)
        if df.empty:
            logging.error(f"Không đủ dữ liệu để tính toán ATR trung bình cho {ticker}.")
            continue

        last_atr = df[atr_col].iloc[-1]
        last_avg_atr = df[atr_avg_col].iloc[-1]

        logging.info(f"[{ticker}] ATR hiện tại: {last_atr:.2f}, Trung bình ATR {ATR_AVG_PERIOD} ngày: {last_avg_atr:.2f}")

        if last_atr > last_avg_atr:
            logging.warning(f"[{ticker}] Trạng thái: BIẾN ĐỘNG CAO (HIGH_VOLATILITY)")
            volatility_states.append("HIGH_VOLATILITY")
        else:
            logging.info(f"[{ticker}] Trạng thái: BIẾN ĐỘNG THẤP (LOW_VOLATILITY)")
            volatility_states.append("LOW_VOLATILITY")

    if not volatility_states:
        logging.error("Không phân tích được trạng thái của bất kỳ chỉ số nào. Sẽ giữ nguyên cấu hình hiện tại.")
        return None

    # Quyết định trạng thái chung dựa trên đa số
    high_vol_count = volatility_states.count("HIGH_VOLATILITY")
    low_vol_count = volatility_states.count("LOW_VOLATILITY")

    logging.info(f"Tổng kết: {high_vol_count} chỉ số biến động CAO, {low_vol_count} chỉ số biến động THẤP.")

    if high_vol_count > low_vol_count:
        final_state = "HIGH_VOLATILITY"
        logging.warning(f"==> KẾT LUẬN: Thị trường chung đang BIẾN ĐỘNG CAO.")
    else:
        final_state = "LOW_VOLATILITY"
        logging.info(f"==> KẾT LUẬN: Thị trường chung đang BIẾN ĐỘNG THẤP.")
        
    return final_state

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
