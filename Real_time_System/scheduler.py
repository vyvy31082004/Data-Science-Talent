import schedule
import time
import logging
from ml_brain import get_market_volatility_state, update_strategy_config

# --- CẤU HÌNH ---
LOGGING_LEVEL = logging.INFO
logging.basicConfig(level=LOGGING_LEVEL, format='%(asctime)s - %(levelname)s - %(message)s')

def run_ml_brain_job():
    """
    Công việc được lên lịch: Chạy toàn bộ quy trình của "Bộ não ML".
    """
    try:
        logging.info("--- [SCHEDULER] Bắt đầu công việc cập nhật ngưỡng tự động ---")
        
        # 1. Xác định trạng thái thị trường
        state = get_market_volatility_state()
        
        # 2. Cập nhật file cấu hình
        if state:
            update_strategy_config(state)
            
        logging.info("--- [SCHEDULER] Hoàn tất công việc. Chờ lần chạy tiếp theo... ---")
    except Exception as e:
        logging.error(f"--- [SCHEDULER] Gặp lỗi trong quá trình chạy job tự động: {e} ---", exc_info=True)

# Lên lịch chạy công việc vào 08:00 sáng mỗi ngày
schedule.every().day.at("08:00").do(run_ml_brain_job)
if __name__ == "__main__":
    logging.info("Nó sẽ kích hoạt 'Bộ não ML' vào 08:00 sáng mỗi ngày.")
    # Chạy công việc ngay lần đầu tiên khởi động
    run_ml_brain_job()

    while True:
        schedule.run_pending()
        time.sleep(1)
