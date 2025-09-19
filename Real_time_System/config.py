# --- CÁC BIẾN CẤU HÌNH ---

# 1. Thông tin đăng nhập FiinQuantX (lấy từ file .env)
import os
from dotenv import load_dotenv

load_dotenv()
FIINQUANT_USERNAME = os.getenv('USERNAME1')
FIINQUANT_PASSWORD = os.getenv('PASSWORD1')


# 4. Cấu hình hệ thống file
CSV_FILE = 'signals.csv' # File để lưu tín hiệu cho dashboard
LOG_FILE = 'signals.log' # File để ghi log chi tiết

# 5. Danh sách mã cổ phiếu cần theo dõi
# Có thể thêm/bớt các mã khác, ví dụ: ['FPT', 'MWG', 'VCB', 'ACB', 'HPG', 'SSI', 'VND']
TICKERS_WATCHLIST = ['FPT', 'MWG', 'VCB', 'ACB', 'HPG', 'SSI', 'VND', 'VNM', 'VIC', 'MSN']