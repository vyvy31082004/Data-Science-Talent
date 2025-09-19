# --- CÁC BIẾN CẤU HÌNH ---

# 1. Thông tin đăng nhập FiinQuantX (lấy từ file .env)
import os
from dotenv import load_dotenv

load_dotenv()
FIINQUANT_USERNAME = os.getenv('USERNAME1')
FIINQUANT_PASSWORD = os.getenv('PASSWORD1')

# 2. Cấu hình Email
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = os.getenv('EMAIL_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_APP_PASSWORD') # Sử dụng App Password của Google
EMAIL_SENDER_PASSWORD = os.getenv('EMAIL_SENDER_PASSWORD')
EMAIL_RECEIVER = os.getenv('EMAIL_RECEIVER')

# 3. Cấu hình Telegram
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# 4. Cấu hình hệ thống file
CSV_FILE = 'signals.csv' # File để lưu tín hiệu cho dashboard
LOG_FILE = 'signals.log' # File để ghi log chi tiết

# 5. Danh sách mã cổ phiếu cần theo dõi
# Có thể thêm/bớt các mã khác, ví dụ: ['FPT', 'MWG', 'VCB', 'ACB', 'HPG', 'SSI', 'VND']
TICKERS_WATCHLIST = ['FPT', 'MWG', 'VCB', 'ACB', 'HPG', 'SSI', 'VND', 'VNM', 'VIC', 'MSN']