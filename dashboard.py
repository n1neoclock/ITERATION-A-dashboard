import streamlit as st
import json
import time
import pandas as pd
from datetime import datetime, timedelta
import pytz
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
import streamlit.components.v1 as components

# ==========================================
# 1. CONFIGURATION & AUTHENTICATION
# ==========================================
st.set_page_config(page_title="Sniper Bot HQ", layout="wide",
                   initial_sidebar_state="collapsed")

# --- PASSWORD PROTECTION SYSTEM ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    # This block stops the rest of the code from running until logged in
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("### 🔒 Restricted Access")
    password = st.text_input("Enter Trader Password:", type="password")

    if st.button("Login"):
        if password == "TjRtr@d1nG?!":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("⛔ Access Denied: Incorrect Password")

    # Stop execution here if not logged in
    st.stop()

# --- IF AUTHENTICATED, CODE CONTINUES BELOW ---

# RE-ENTER YOUR KEYS HERE FOR THE DASHBOARD TO HAVE ACCESS
# Access keys securely from Streamlit Cloud Secrets
API_KEY = st.secrets["API_KEY"]
SECRET_KEY = st.secrets["SECRET_KEY"]

SYMBOLS = ['SPY', 'SLV', 'GLD']

# Initialize Clients
try:
    trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
    data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
except:
    st.error("Failed to connect to Alpaca. Check API Keys.")
    st.stop()

# ==========================================
# CUSTOM CSS (PROFESSIONAL & FIXED PADDING)
# ==========================================
st.markdown("""
<style>
    /* PADDING FIX: Pushed down so "Online" light isn't cut off */
    .block-container {padding-top: 5rem; padding-bottom: 1rem;}
    
    div[data-testid="stMetricValue"] {font-size: 1.8rem;}
    .stAlert {padding: 0.5rem;}
    iframe {border-radius: 10px; border: 1px solid #333;}
    
    /* Status Dot Animation */
    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 255, 0, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(0, 255, 0, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 255, 0, 0); }
    }
    .status-dot-green {
        height: 12px; width: 12px; background-color: #00ff00;
        border-radius: 50%; display: inline-block; margin-right: 8px;
        box-shadow: 0 0 0 0 rgba(0, 255, 0, 1); animation: pulse 2s infinite;
    }
    .status-dot-red {
        height: 12px; width: 12px; background-color: #ff0000;
        border-radius: 50%; display: inline-block; margin-right: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# DATA LOADING FUNCTIONS
# ==========================================


def load_bot_data():
    try:
        with open("dashboard_data.json", "r") as f:
            return json.load(f)
    except:
        return None


@st.cache_data(ttl=300)  # Cache this for 5 minutes to avoid rate limits
def get_ticker_performance(symbols):
    data = []
    end = datetime.now(pytz.utc)
    start = end - timedelta(days=8)  # Get last week of data

    try:
        req = StockBarsRequest(symbol_or_symbols=symbols, timeframe=TimeFrame(
            1, TimeFrameUnit.Day), start=start)
        bars = data_client.get_stock_bars(req).df

        for sym in symbols:
            df = bars.xs(sym)
            if len(df) > 1:
                price = df['close'].iloc[-1]
                # 1 Day change
                prev_close = df['close'].iloc[-2]
                pct_1d = ((price - prev_close) / prev_close) * 100

                # 1 Week change (approx 5 trading days)
                week_close = df['close'].iloc[0] if len(
                    df) >= 5 else df['close'].iloc[0]
                pct_1w = ((price - week_close) / week_close) * 100

                data.append({"Symbol": sym, "Price": price,
                            "1D %": pct_1d, "1W %": pct_1w})
    except Exception as e:
        pass

    return pd.DataFrame(data)


def close_position_handler(symbol):
    try:
        trading_client.close_position(symbol)
        st.toast(f"🚫 Closed position for {symbol}", icon="✅")
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Error closing {symbol}: {e}")

# ==========================================
# MAIN DASHBOARD LAYOUT
# ==========================================


# 1. HEADER & STATUS
bot_data = load_bot_data()
status_html = '<span class="status-dot-red"></span> OFF-LINE'

if bot_data:
    # Simple check: If dashboard refreshes and data exists
    status_html = '<span class="status-dot-green"></span> ONLINE & CONNECTED'

st.markdown(f"### {status_html} <span style='color:gray; font-size:0.8em; margin-left:10px'>ITERATION-A-V1 DASHBOARD | a passion project by n1neoclocl</span>", unsafe_allow_html=True)

st.divider()

# 2. TOP METRICS (LIVE P&L)
# We fetch this directly from Alpaca for accuracy
try:
    account = trading_client.get_account()
    equity = float(account.equity)
    start_equity = float(account.last_equity)  # Start of day equity
    pnl_amt = equity - start_equity
    pnl_pct = (pnl_amt / start_equity) * 100

    m1, m2, m3, m4 = st.columns(4)

    m1.metric("Total Equity", f"${equity:,.2f}")

    # Conditional Formatting for P&L
    m2.metric("Day P&L ($)", f"${pnl_amt:,.2f}", delta=f"{pnl_amt:,.2f}")
    m3.metric("Day P&L (%)", f"{pnl_pct:.2f}%", delta=f"{pnl_pct:.2f}%")

    buying_power = float(account.buying_power)
    m4.metric("Buying Power", f"${buying_power:,.2f}")

except Exception as e:
    st.error("Could not fetch account data.")

st.divider()

# 3. TICKER PERFORMANCE (Mini Data Table)
st.markdown("#### 📊 Market Performance")
perf_df = get_ticker_performance(SYMBOLS)
if not perf_df.empty:
    # Style the dataframe
    st.dataframe(
        perf_df.style.format(
            {"Price": "${:.2f}", "1D %": "{:.2f}%", "1W %": "{:.2f}%"})
        .applymap(lambda v: 'color: green' if v > 0 else 'color: red', subset=['1D %', '1W %']),
        use_container_width=True,
        hide_index=True
    )

# 4. ACTIVE POSITIONS WITH CLOSE BUTTON
st.markdown("#### 📦 Active Positions Management")

try:
    positions = trading_client.get_all_positions()

    if positions:
        for pos in positions:
            # Create a nice card for each position
            with st.container():
                c1, c2, c3, c4, c5, c6 = st.columns([1, 1, 1, 1, 1, 1])

                pl_pct = float(pos.unrealized_plpc) * 100
                pl_amt = float(pos.unrealized_pl)
                color = "green" if pl_amt > 0 else "red"

                c1.markdown(f"**{pos.symbol}** ({pos.side.upper()})")
                c2.write(f"Qty: {pos.qty}")
                c3.write(f"Entry: ${float(pos.avg_entry_price):.2f}")
                c4.write(f"Curr: ${float(pos.current_price):.2f}")
                c5.markdown(
                    f"<span style='color:{color}'>**{pl_amt:+.2f} ({pl_pct:+.2f}%)**</span>", unsafe_allow_html=True)

                # The Kill Switch Button
                if c6.button(f"🚫 CLOSE {pos.symbol}", key=f"close_{pos.symbol}"):
                    close_position_handler(pos.symbol)

                st.markdown("---")
    else:
        st.info("💤 No positions currently open.")

except Exception as e:
    st.write("Error fetching positions.")


# 5. TRADINGVIEW CHARTS
st.markdown("#### 📉 Live Charts")
tabs = st.tabs(SYMBOLS)


def get_tv_widget(symbol):
    # Embedding TradingView Widget via HTML
    return f"""
    <div class="tradingview-widget-container">
      <div id="tradingview_{symbol}"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
        "width": "100%",
        "height": 500,
        "symbol": "{symbol}",
        "interval": "5",
        "timezone": "America/New_York",
        "theme": "dark",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "container_id": "tradingview_{symbol}"
      }}
      );
      </script>
    </div>
    """


for i, sym in enumerate(SYMBOLS):
    with tabs[i]:
        components.html(get_tv_widget(sym), height=510)


# 6. ACTIVITY LOG
st.markdown("#### 📜 Bot Activity Log")
if bot_data and 'logs' in bot_data:
    log_container = st.container(height=300)
    for log in bot_data['logs']:
        # Color coding the logs for readability
        if "PROFIT" in log or "FILLED" in log or "WIN" in log:
            icon = "✅"
            color = "#90ee90"  # Light green
        elif "LOSS" in log or "STOP" in log:
            icon = "🛑"
            color = "#ffcccb"  # Light red
        elif "SIGNAL" in log:
            icon = "⚡"
            color = "#ffffed"  # Light yellow
        else:
            icon = "ℹ️"
            color = "#ffffff"

        log_container.markdown(
            f"<span style='color:{color}'>{icon} {log}</span>", unsafe_allow_html=True)

# Footer
st.markdown("<br><br><center><small>System updates every 5 seconds</small></center>",
            unsafe_allow_html=True)

# Auto Refresh logic
time.sleep(5)
st.rerun()

