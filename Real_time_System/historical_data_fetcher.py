import config
from FiinQuantX import FiinSession
from datetime import datetime, timedelta
import pandas as pd
import logging


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_historical_data(ticker: str, days_back: int = 365):
    """
    Lấy dữ liệu lịch sử EOD (End-of-Day) cho một mã cổ phiếu.

    Args:
        ticker (str): Mã cổ phiếu cần lấy dữ liệu.
        days_back (int): Số ngày dữ liệu cần lấy tính từ hiện tại.

    Returns:
        pd.DataFrame: DataFrame chứa dữ liệu lịch sử hoặc None nếu có lỗi.
    """
    logging.info(f"Bắt đầu quá trình lấy dữ liệu lịch sử cho mã: {ticker}...")
    client = None
    try:
        client = FiinSession(username=config.FIINQUANT_USERNAME, password=config.FIINQUANT_PASSWORD).login()
        logging.info("Đăng nhập FiinQuantX thành công.")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        request_object = client.Fetch_Trading_Data(
            False, # realtime = False
            ticker,
            ['open', 'high', 'low', 'close', 'volume'],
            by='1d', # Dữ liệu EOD
            from_date=start_date.strftime('%Y-%m-%d'),
            to_date=end_date.strftime('%Y-%m-%d')
        )
        logging.info(f"Đã tạo 'Đối tượng yêu cầu' cho {ticker} thành công.")


        historical_df = request_object.get_data()
        logging.info(f"Lấy dữ liệu từ .get_data() thành công.")

        if historical_df is not None and not historical_df.empty:
       
            historical_df.set_index('timestamp', inplace=True)
            historical_df.index = pd.to_datetime(historical_df.index)
            logging.info(f"Đã xử lý và nhận được {len(historical_df)} dòng dữ liệu cho {ticker}.")
            return historical_df
        else:
            logging.warning(f"Không nhận được dữ liệu lịch sử cho {ticker}.")
            return None

    except Exception as e:
        logging.error(f"Lỗi nghiêm trọng khi lấy dữ liệu lịch sử cho {ticker}: {e}", exc_info=True)
        return None


if __name__ == '__main__':

    TICKER_TO_TEST = 'FPT'
    logging.info(f"--- BẮT ĐẦU KIỂM TRA MODULE historical_data_fetcher VỚI MÃ {TICKER_TO_TEST} ---")
    
    data = fetch_historical_data(TICKER_TO_TEST, days_back=90)

    if data is not None:
        print("\n--- DỮ LIỆU LỊCH SỬ NHẬN ĐƯỢC (5 DÒNG ĐẦU) ---")
        print(data.head())
        print("\n--- THÔNG TIN DỮ LIỆU ---")
        data.info()
        print(f"\n>>> Lấy dữ liệu thành công! Module 'historical_data_fetcher.py' hoạt động chính xác.")
    else:
        print(f"\n>>> Lấy dữ liệu thất bại. Vui lòng kiểm tra lại log.")
