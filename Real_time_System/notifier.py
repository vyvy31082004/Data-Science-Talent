import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import telegram
import asyncio

from config import (
    EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_RECEIVER,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
)
from logger_config import signal_logger

def send_email(subject, body):
    """Gửi cảnh báo qua Email."""
    if not all([EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_RECEIVER]):
        signal_logger.warning("Thông tin email chưa được cấu hình. Bỏ qua việc gửi email.")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_HOST_USER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_HOST_USER, EMAIL_RECEIVER, text)
        server.quit()
        signal_logger.info(f"Đã gửi email cảnh báo tới {EMAIL_RECEIVER}")
    except Exception as e:
        signal_logger.error(f"Lỗi khi gửi email: {e}")

async def send_telegram_message_async(message):
    """Hàm bất đồng bộ để gửi tin nhắn Telegram."""
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
        signal_logger.warning("Thông tin Telegram chưa được cấu hình. Bỏ qua việc gửi tin nhắn.")
        return
        
    try:
        bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        signal_logger.info(f"Đã gửi tin nhắn Telegram tới chat_id: {TELEGRAM_CHAT_ID}")
    except Exception as e:
        signal_logger.error(f"Lỗi khi gửi tin nhắn Telegram: {e}")

def send_telegram_message(message):
    """Gửi cảnh báo qua Telegram (wrapper cho hàm async)."""
    try:
        asyncio.run(send_telegram_message_async(message))
    except Exception as e:
        signal_logger.error(f"Lỗi khi khởi tạo event loop cho Telegram: {e}")

# --- Test functions ---
if __name__ == '__main__':
    # Test gửi email
    print("Testing email function...")
    send_email("Test Cảnh Báo Cổ Phiếu", "Đây là tin nhắn test từ hệ thống cảnh báo.")
    
    # Test gửi Telegram
    print("\nTesting Telegram function...")
    send_telegram_message("Test Cảnh Báo Cổ Phiếu: Đây là tin nhắn test từ hệ thống cảnh báo.")
    print("Test finished.")
