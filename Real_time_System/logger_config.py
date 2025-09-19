import logging
from logging.handlers import RotatingFileHandler
import sys
from config import LOG_FILE

def setup_logger():
    """Thiết lập logger để ghi log ra file và console."""
    
    # Tạo logger chính
    logger = logging.getLogger('SignalLogger')
    logger.setLevel(logging.INFO)

    # Định dạng log message
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # --- Handler để ghi log ra file ---
    # RotatingFileHandler sẽ tự động xoay vòng file log khi đạt đến kích thước nhất định
    file_handler = RotatingFileHandler(
        LOG_FILE, 
        maxBytes=5*1024*1024, # 5 MB
        backupCount=2,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # --- Handler để in log ra console ---
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)

    # Thêm các handler vào logger
    # Kiểm tra để không thêm handler nhiều lần nếu hàm được gọi lại
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    return logger

# Tạo một instance logger để sử dụng trong toàn bộ dự án
signal_logger = setup_logger()
