import streamlit as st
import pandas as pd
import os
from datetime import datetime
import json
from config import CSV_FILE

# --- Cấu hình trang ---
st.set_page_config(
    page_title="Dashboard Tín Hiệu Giao Dịch",
    page_icon="⚡",
    layout="wide",
)

# --- CSS Tùy chỉnh cho Giao diện Hiện đại ---
st.markdown("""
<style>
    /* Tổng thể */
    .stApp {
        background-color: #f0f2f6;
    }
    /* Container chính */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 5rem;
        padding-right: 5rem;
    }
    /* Thẻ (Card) */
    div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"] {
        background-color: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.1);
        transition: 0.3s;
    }
    div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"]:hover {
        box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);
    }
    /* Metric styles */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border-left: 5px solid #1a5f7a;
        padding: 1rem;
        border-radius: 5px;
        box-shadow: 0 2px 4px 0 rgba(0,0,0,0.08);
        color: black; /* Màu chữ cho metric */
    }
    /* Tiêu đề và toàn bộ chữ mặc định */
    h1, h2, h3, p, body {
        color: black !important;
    }
    h1 {
        text-align: center;
    }

    /* --- BỔ SUNG ĐỂ SỬA MÀU CHỮ SIDEBAR --- */
    /* Ghi đè màu chữ cho tất cả các thành phần trong sidebar */
    section[data-testid="stSidebar"] * {
        color: white !important;
    }

    /* Ngoại lệ: Giữ lại màu cho trạng thái hệ thống để nó nổi bật */
    section[data-testid="stSidebar"] span[style*="color:orange"] {
        color: orange !important;
    }
    section[data-testid="stSidebar"] span[style*="color:green"] {
        color: green !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Hàm tải và cache dữ liệu ---
@st.cache_data(ttl=60)
def load_data():
    if not os.path.exists(CSV_FILE) or os.path.getsize(CSV_FILE) == 0:
        return pd.DataFrame(columns=['timestamp', 'ticker', 'signal', 'price', 'details'])
    try:
        # Đọc CSV, bỏ qua các dòng comment bắt đầu bằng '#' và chỉ định rõ tên cột
        df = pd.read_csv(
            CSV_FILE, 
            comment='#',
            names=['timestamp', 'ticker', 'signal', 'price', 'details'],
            header=None
        )
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        df.dropna(subset=['timestamp'], inplace=True)
        
        df = df.sort_values(by='timestamp', ascending=False)
        return df
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu: {e}")
        return pd.DataFrame(columns=['timestamp', 'ticker', 'signal', 'price', 'details'])

def load_system_status():
    """Đọc file trạng thái hệ thống và trả về dictionary."""
    if not os.path.exists('system_status.json'):
        return None
    try:
        with open('system_status.json', 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None


def color_signal(signal):
    if 'Mua' in signal:
        return 'background-color: #c8e6c9; color: black;' # Xanh lá cây nhạt, chữ đen
    elif 'Bán' in signal:
        return 'background-color: #ffcdd2; color: black;' # Đỏ nhạt, chữ đen
    elif 'Cảnh báo' in signal:
        return 'background-color: #fff9c4; color: black;' # Vàng nhạt cho cảnh báo, chữ đen
    return 'color: black;' # Mặc định chữ đen

# (Sidebar)
with st.sidebar:
    st.header("Bộ lọc Tín hiệu")
    
    # --- Hiển thị trạng thái hệ thống ---
    st.markdown("---")
    st.subheader(" Trạng thái Hệ thống")
    status = load_system_status()
    if status:
        state = status.get('market_state', 'Không xác định')
        last_updated = status.get('last_updated', 'Chưa có')
        thresholds = status.get('active_thresholds', {})
        
        state_color = "orange" if state == "HIGH_VOLATILITY" else "green"
        state_text = "Biến động CAO" if state == "HIGH_VOLATILITY" else "Biến động THẤP"
        
        st.markdown(f"**Trạng thái:** <span style='color:{state_color};'>**{state_text}**</span>", unsafe_allow_html=True)
        
        with st.expander("Xem các ngưỡng đang áp dụng"):
            st.metric(label="RSI Quá mua", value=thresholds.get('RSI_OVERBOUGHT', 'N/A'))
            st.metric(label="RSI Quá bán", value=thresholds.get('RSI_OVERSOLD', 'N/A'))
            st.metric(label="Ngưỡng ADX", value=thresholds.get('ADX_THRESHOLD', 'N/A'))
        
        st.caption(f"Cập nhật lần cuối: {last_updated}")
    else:
        st.info("Chưa có thông tin trạng thái từ 'Bộ não ML'.")
    st.markdown("---")


    df = load_data()
    
    # Thêm tùy chọn lọc theo ngày
    show_today_only = st.checkbox(" Chỉ hiển thị tín hiệu hôm nay", value=True)

    df_to_filter = df
    if show_today_only:
        # Chỉ lọc nếu dataframe không rỗng
        if not df.empty:
            today = datetime.now().date()
            df_to_filter = df[df['timestamp'].dt.date == today]
        else:
            df_to_filter = df # Giữ nguyên dataframe rỗng

    # Lọc theo mã cổ phiếu
    all_tickers = sorted(df_to_filter['ticker'].unique())
    # Mặc định luôn chọn tất cả các mã
    selected_tickers = st.multiselect("Mã Cổ phiếu", all_tickers, default=all_tickers)
    all_signals = sorted(df_to_filter['signal'].unique())
    # Mặc định luôn chọn tất cả các loại tín hiệu
    selected_signals = st.multiselect("Loại Tín hiệu", all_signals, default=all_signals)


df_filtered = df_to_filter[df_to_filter['ticker'].isin(selected_tickers) & df_to_filter['signal'].isin(selected_signals)]


st.title("⚡ Dashboard Tín Hiệu Giao Dịch Real-time")


st.markdown(f'<meta http-equiv="refresh" content="60">', unsafe_allow_html=True)

# --- KPIs ---
st.markdown("### Tổng quan")
col1, col2, col3 = st.columns(3)

total_signals = len(df_filtered)
unique_tickers = df_filtered['ticker'].nunique()
latest_signal_time = df_filtered['timestamp'].max().strftime('%H:%M:%S') if total_signals > 0 else "N/A"


METRIC_CARD_STYLE = """
    padding: 1rem;
    border: 1px solid #e1e1e1;
    border-radius: 7px;
    background-color: #f9f9f9;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
"""

# KPI 1: Tổng số tín hiệu
col1.markdown(f"""
<div style="{METRIC_CARD_STYLE}">
    <div style="font-size: 0.9rem; color: #555;"> Tổng số tín hiệu</div>
    <div style="font-size: 2rem; font-weight: bold; color: black;">{total_signals}</div>
</div>
""", unsafe_allow_html=True)

# KPI 2: Số mã được lọc
col2.markdown(f"""
<div style="{METRIC_CARD_STYLE}">
    <div style="font-size: 0.9rem; color: #555;"> Số mã được lọc</div>
    <div style="font-size: 2rem; font-weight: bold; color: black;">{unique_tickers}</div>
</div>
""", unsafe_allow_html=True)


col3.markdown(f"""
<div style="{METRIC_CARD_STYLE}">
    <div style="font-size: 0.9rem; color: #555;"> Tín hiệu cuối cùng</div>
    <div style="font-size: 2rem; font-weight: bold; color: black;">{latest_signal_time}</div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")
st.markdown("### Phân tích Tín hiệu")
col1_chart, col2_chart = st.columns(2)

with col1_chart:
    st.subheader("Phân bổ Tín hiệu")
    signal_counts = df_filtered['signal'].value_counts()
    st.bar_chart(signal_counts)

    st.markdown("---")
    
    # --- Bảng lịch sử tín hiệu ---
    st.subheader("Lịch sử Tín hiệu")
    styled_df = df_filtered.style.applymap(color_signal, subset=['signal'])
    st.dataframe(styled_df, use_container_width=True, height=500)
