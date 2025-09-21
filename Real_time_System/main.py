import time
import csv
import os
from datetime import datetime
from FiinQuantX import FiinSession, RealTimeData

import config
from logger_config import signal_logger
from signal_detector import detect_signal

def write_signal_to_csv(timestamp, ticker, signal, price, details):
    """Ghi tín hiệu vào file CSV."""
    try:
        header_needed = not os.path.exists(config.CSV_FILE)
        with open(config.CSV_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if header_needed:
                writer.writerow(['timestamp', 'ticker', 'signal', 'price', 'details'])
            writer.writerow([timestamp, ticker, signal, price, details])
    except Exception as e:
        signal_logger.error(f"Lỗi khi ghi file CSV: {e}")

def on_event(data: RealTimeData):
    """
    Hàm callback được gọi mỗi khi có dữ liệu mới từ FiinQuantX.
    """
    if not hasattr(data, 'Ticker') or not hasattr(data, 'Close'):
        signal_logger.debug(f"Nhận dữ liệu không hợp lệ: {data}")
        return

    try:
        signal_logger.info(f"Nhận data: {data.Ticker}, Giá: {data.Close}, Thời gian: {getattr(data, 'Time', 'N/A')}")
        
        # Gọi hàm detect_signal mới
        signal, details = detect_signal(data)
        
        if signal:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ticker = data.Ticker
            price = data.Close
            
            message = (
                f"--- CẢNH BÁO TÍN HIỆU ---\n"
                f" Cổ phiếu: {ticker}\n"
                f" Tín hiệu: {signal}\n"
                f" Giá hiện tại: {price}\n"
                f" Chi tiết: {details}\n"
                f" Thời gian: {timestamp}"
            )
            signal_logger.warning(message)
            write_signal_to_csv(timestamp, ticker, signal, price, details)
            
    except Exception as e:
        signal_logger.error(f"Lỗi trong hàm on_event cho {getattr(data, 'Ticker', 'Unknown Ticker')}: {e}", exc_info=True)


def main():
    signal_logger.info("--- Bắt đầu hệ thống cảnh báo Real-time ---")
    
    client = None
    try:
        client = FiinSession(username=config.FIINQUANT_USERNAME, password=config.FIINQUANT_PASSWORD).login()
        signal_logger.info("Đăng nhập FiinQuantX thành công.")
    except Exception as e:
        signal_logger.error(f"Đăng nhập FiinQuantX thất bại: {e}")
        return

    ticker_events = None
    try:
        tickers_to_stream = config.TICKERS_WATCHLIST
        signal_logger.info(f"Sẽ stream dữ liệu cho {len(tickers_to_stream)} mã: {tickers_to_stream}")
        
        ticker_events = client.Trading_Data_Stream(tickers=tickers_to_stream, callback=on_event)
        ticker_events.start()
        
        signal_logger.info("Bắt đầu lắng nghe luồng dữ liệu. Nhấn Ctrl+C để dừng.")
        
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        signal_logger.info("Nhận tín hiệu dừng từ bàn phím (Ctrl+C).")
    except Exception as e:
        signal_logger.error(f"Lỗi nghiêm trọng trong quá trình stream: {e}", exc_info=True)
    finally:
        if ticker_events:
            ticker_events.stop()
        signal_logger.info("--- Hệ thống cảnh báo đã dừng ---")


if __name__ == '__main__':
    main()
