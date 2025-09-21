import argparse
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
import pandas_ta as ta

from historical_data_fetcher import fetch_historical_data
from ml_brain import DYNAMIC_THRESHOLDS, ATR_AVG_PERIOD, ATR_PERIOD
import logging
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'strategy_config.json')
MARKET_PROXY_TICKER = 'VNINDEX' # Sử dụng VNINDEX làm đại diện cho trạng thái thị trường


def get_historical_market_state(market_df: pd.DataFrame) -> pd.Series:
    """
    Phân tích và trả về một Series chứa trạng thái biến động của thị trường ('LOW_VOLATILITY' hoặc 'HIGH_VOLATILITY')
    cho mỗi ngày trong DataFrame đầu vào.
    """
    df = market_df.copy()
    df.ta.atr(length=ATR_PERIOD, append=True)
    atr_col = f'ATRr_{ATR_PERIOD}'
    atr_avg_col = f'ATR_AVG_{ATR_AVG_PERIOD}'

    df[atr_avg_col] = df[atr_col].rolling(window=ATR_AVG_PERIOD).mean()
    df.dropna(subset=[atr_col, atr_avg_col], inplace=True)

    df['market_state'] = 'LOW_VOLATILITY' # Mặc định là biến động thấp
    df.loc[df[atr_col] > df[atr_avg_col], 'market_state'] = 'HIGH_VOLATILITY'
    
    return df['market_state']


def load_strategy_config() -> Dict:
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)


def compute_indicators(price_df: pd.DataFrame, strategy_config: Dict) -> pd.DataFrame:
    df = price_df.copy()

    # Indicators mirroring real-time rules
    df.ta.rsi(length=strategy_config['RSI_PERIOD'], append=True)
    df.ta.macd(
        fast=strategy_config['MACD_FAST'],
        slow=strategy_config['MACD_SLOW'],
        signal=strategy_config['MACD_SIGNAL'],
        append=True,
    )
    df.ta.sma(length=strategy_config['SMA_SHORT_PERIOD'], append=True)
    df.ta.sma(length=strategy_config['SMA_LONG_PERIOD'], append=True)
    df.ta.stoch(
        k=strategy_config['STOCH_K'],
        d=strategy_config['STOCH_D'],
        smooth_k=strategy_config['STOCH_SMOOTH'],
        append=True,
    )
    df.ta.adx(length=strategy_config['ADX_PERIOD'], append=True)

    return df


def generate_signals(
    ind_df: pd.DataFrame, strategy_config: Dict, market_states: pd.Series
) -> pd.DataFrame:
    df = ind_df.copy()

    # Hợp nhất trạng thái thị trường vào dataframe chính để dễ dàng truy cập
    df = df.join(market_states, how='left')
    df['market_state'].fillna(method='ffill', inplace=True)
    # Nếu vẫn còn NaN ở đầu, điền bằng trạng thái mặc định
    df['market_state'].fillna('LOW_VOLATILITY', inplace=True)

    rsi_col = f"RSI_{strategy_config['RSI_PERIOD']}"
    macd_line = f"MACD_{strategy_config['MACD_FAST']}_{strategy_config['MACD_SLOW']}_{strategy_config['MACD_SIGNAL']}"
    macd_signal = f"MACDs_{strategy_config['MACD_FAST']}_{strategy_config['MACD_SLOW']}_{strategy_config['MACD_SIGNAL']}"
    sma20 = f"SMA_{strategy_config['SMA_SHORT_PERIOD']}"
    sma50 = f"SMA_{strategy_config['SMA_LONG_PERIOD']}"
    stoch_k = f"STOCHk_{strategy_config['STOCH_K']}_{strategy_config['STOCH_D']}_{strategy_config['STOCH_SMOOTH']}"
    stoch_d = f"STOCHd_{strategy_config['STOCH_K']}_{strategy_config['STOCH_D']}_{strategy_config['STOCH_SMOOTH']}"
    adx = f"ADX_{strategy_config['ADX_PERIOD']}"

    df['signal'] = None
    df['signal_reason'] = None

    # need previous row for cross checks
    for i in range(1, len(df)):
        last = df.iloc[i]
        prev = df.iloc[i - 1]

        # Lấy ngưỡng động cho ngày hiện tại
        current_market_state = last['market_state']
        dynamic_params = DYNAMIC_THRESHOLDS.get(current_market_state, DYNAMIC_THRESHOLDS['LOW_VOLATILITY'])
        
        rsi_oversold = dynamic_params['RSI_OVERSOLD']
        rsi_overbought = dynamic_params['RSI_OVERBOUGHT']
        adx_threshold = dynamic_params['ADX_THRESHOLD']

        # Skip until indicators are available
        if (
            pd.isna(last.get(rsi_col))
            or pd.isna(last.get(macd_line))
            or pd.isna(last.get(macd_signal))
            or pd.isna(last.get(sma20))
            or pd.isna(last.get(sma50))
            or pd.isna(last.get(stoch_k))
            or pd.isna(last.get(stoch_d))
            or pd.isna(last.get(adx))
        ):
            continue

        # Momentum conditions
        is_momentum_buy = (last[rsi_col] < rsi_oversold) or (
            (last[stoch_k] > last[stoch_d])
            and (prev[stoch_k] <= prev[stoch_d])
            and (last[stoch_k] < 20)
        )
        is_momentum_sell = (last[rsi_col] > rsi_overbought) or (
            (last[stoch_k] < last[stoch_d])
            and (prev[stoch_k] >= prev[stoch_d])
            and (last[stoch_k] > 80)
        )

        # Trend conditions
        is_trend_buy = (
            (last[macd_line] > last[macd_signal] and prev[macd_line] <= prev[macd_signal])
            or (last['close'] > last[sma20] and prev['close'] <= prev[sma20])
            or (last['close'] > last[sma50] and prev['close'] <= prev[sma50])
        )
        is_trend_sell = (
            (last[macd_line] < last[macd_signal] and prev[macd_line] >= prev[macd_signal])
            or (last['close'] < last[sma20] and prev['close'] >= prev[sma20])
            or (last['close'] < last[sma50] and prev['close'] >= prev[sma50])
        )

        # Risk conditions (informational)
        is_trend_still_strong_up = (
            (last[macd_line] > 0)
            and (last['close'] > last[sma20])
            and (last['close'] > last[sma50])
            and (last[adx] > adx_threshold)
        )
        is_trend_still_strong_down = (
            (last[macd_line] < 0)
            and (last['close'] < last[sma20])
            and (last['close'] < last[sma50])
            and (last[adx] > adx_threshold)
        )

        # Signals
        if is_momentum_buy and is_trend_buy:
            df.iat[i, df.columns.get_loc('signal')] = 'Mua mới'
            df.iat[i, df.columns.get_loc('signal_reason')] = 'Momentum và Trend xác nhận mua'
            continue

        if is_momentum_sell and is_trend_sell:
            df.iat[i, df.columns.get_loc('signal')] = 'Bán chốt lời'
            df.iat[i, df.columns.get_loc('signal_reason')] = 'Momentum và Trend xác nhận bán'
            continue

        if (last[rsi_col] > rsi_overbought) and is_trend_still_strong_up:
            df.iat[i, df.columns.get_loc('signal')] = 'Cảnh báo rủi ro (dễ điều chỉnh)'
            df.iat[i, df.columns.get_loc('signal_reason')] = 'RSI quá mua nhưng xu hướng vẫn mạnh'
            continue

        if (last[rsi_col] < rsi_oversold) and is_trend_still_strong_down:
            df.iat[i, df.columns.get_loc('signal')] = 'Cảnh báo rủi ro (bắt đáy nguy hiểm)'
            df.iat[i, df.columns.get_loc('signal_reason')] = 'RSI quá bán nhưng xu hướng giảm vẫn mạnh'
            continue

    return df


def simulate_trades(
    signal_df: pd.DataFrame,
    fee_bps_per_side: float = 5.0,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    df = signal_df.copy()
    df['next_open'] = df['open'].shift(-1)

    in_position = False
    entry_price: Optional[float] = None
    entry_time: Optional[pd.Timestamp] = None

    trades: List[Dict] = []
    equity_curve: List[Tuple[pd.Timestamp, float]] = []
    equity = 1.0
    fee_per_side = fee_bps_per_side / 10000.0

    for i in range(len(df) - 1):
        ts = df.index[i]
        sig = df['signal'].iloc[i]
        next_open = df['next_open'].iloc[i]

        # carry equity forward
        equity_curve.append((ts, equity))

        if pd.isna(next_open):
            continue

        if (sig == 'Mua mới') and (not in_position):
            in_position = True
            entry_price = float(next_open) * (1.0 + fee_per_side)
            entry_time = df.index[i + 1]
            continue

        if (sig == 'Bán chốt lời') and in_position:
            exit_price_gross = float(next_open)
            exit_price_net = exit_price_gross * (1.0 - fee_per_side)
            assert entry_price is not None and entry_time is not None

            pct_return = (exit_price_net - entry_price) / entry_price
            equity *= (1.0 + pct_return)

            trades.append(
                {
                    'entry_time': entry_time,
                    'entry_price': entry_price,
                    'exit_time': df.index[i + 1],
                    'exit_price': exit_price_net,
                    'pct_return': pct_return,
                }
            )

            in_position = False
            entry_price = None
            entry_time = None

    equity_df = pd.DataFrame(equity_curve, columns=['timestamp', 'equity']).set_index('timestamp')
    trades_df = pd.DataFrame(trades)

    metrics: Dict = {
        'num_trades': int(len(trades_df)) if not trades_df.empty else 0,
        'win_rate': float((trades_df['pct_return'] > 0).mean()) if not trades_df.empty else 0.0,
        'avg_return_per_trade': float(trades_df['pct_return'].mean()) if not trades_df.empty else 0.0,
        'total_return': float((equity - 1.0)),
        'final_equity': float(equity),
    }

    return trades_df, equity_df, metrics


def slice_date_range(df: pd.DataFrame, start: Optional[str], end: Optional[str]) -> pd.DataFrame:
    if start:
        df = df[df.index >= pd.to_datetime(start)]
    if end:
        df = df[df.index <= pd.to_datetime(end)]
    return df


def backtest_ticker(
    ticker: str,
    start: Optional[str],
    end: Optional[str],
    fee_bps: float,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict, pd.DataFrame]:
    # Compute minimal days_back from start to reduce API time, with buffer for indicators
    if start:
        start_dt = pd.to_datetime(start)
        days_span = max((pd.Timestamp.today().normalize() - start_dt).days, 1)
        days_back = max(days_span + 300, 400)  # buffer for warm-up/indicators
    else:
        days_back = 2000

    # Fetch history once then slice
    raw_df = fetch_historical_data(ticker, days_back=days_back)
    if raw_df is None or raw_df.empty:
        raise RuntimeError(f"Không lấy được dữ liệu lịch sử cho {ticker}")

    # ensure expected columns
    required_cols = {'open', 'high', 'low', 'close', 'volume'}
    missing = required_cols - set(raw_df.columns)
    if missing:
        raise RuntimeError(f"Thiếu cột dữ liệu {missing} cho {ticker}")

    raw_df = slice_date_range(raw_df, start, end)
    if raw_df.empty:
        raise RuntimeError(f"Khoảng thời gian không có dữ liệu cho {ticker}")

    # Lấy dữ liệu thị trường để xác định trạng thái biến động
    market_df = fetch_historical_data(MARKET_PROXY_TICKER, days_back=days_back)
    if market_df is None or market_df.empty:
        raise RuntimeError(f"Không lấy được dữ liệu thị trường cho {MARKET_PROXY_TICKER}")
    
    market_df = slice_date_range(market_df, start, end)
    market_states = get_historical_market_state(market_df)

    strategy_config = load_strategy_config()
    ind_df = compute_indicators(raw_df, strategy_config)
    sig_df = generate_signals(ind_df, strategy_config, market_states)

    trades_df, equity_df, metrics = simulate_trades(sig_df, fee_bps_per_side=fee_bps)
    return trades_df, equity_df, metrics, sig_df


def main():
    parser = argparse.ArgumentParser(description='Backtest hệ thống tín hiệu (EOD).')
    parser.add_argument('--tickers', type=str, required=True, help='Danh sách mã, ví dụ: FPT,MWG,VCB')
    parser.add_argument('--start', type=str, default=None, help='Ngày bắt đầu YYYY-MM-DD')
    parser.add_argument('--end', type=str, default=None, help='Ngày kết thúc YYYY-MM-DD')
    parser.add_argument('--fee_bps', type=float, default=5.0, help='Phí giao dịch mỗi chiều (basis points)')
    parser.add_argument('--outdir', type=str, default='backtest_outputs', help='Thư mục lưu kết quả')

    args = parser.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    all_metrics: List[Dict] = []

    for ticker in [t.strip() for t in args.tickers.split(',') if t.strip()]:
        print(f"\n=== Backtest {ticker} ===")
        try:
            trades_df, equity_df, metrics, sig_full_df = backtest_ticker(
                ticker=ticker,
                start=args.start,
                end=args.end,
                fee_bps=args.fee_bps,
            )

            # Save results
            trades_path = os.path.join(args.outdir, f'trades_{ticker}.csv')
            equity_path = os.path.join(args.outdir, f'equity_{ticker}.csv')
            signals_path = os.path.join(args.outdir, f'signals_{ticker}.csv')

            sig_full_df.to_csv(signals_path)
            trades_df.to_csv(trades_path, index=False)
            equity_df.to_csv(equity_path)

            print(metrics)
            all_metrics.append({'ticker': ticker, **metrics})
        except Exception as e:
            print(f"Lỗi backtest {ticker}: {e}")

    if all_metrics:
        summary_df = pd.DataFrame(all_metrics)
        summary_path = os.path.join(args.outdir, 'summary.csv')
        summary_df.to_csv(summary_path, index=False)
        print(f"\nSaved summary to {summary_path}")


if __name__ == '__main__':
    main()


