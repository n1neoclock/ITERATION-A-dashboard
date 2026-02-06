import streamlit as st
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
st.set_page_config(page_title="Sniper Bot HQ", layout="wide", initial_sidebar_state="collapsed")

# --- PASSWORD PROTECTION SYSTEM ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("### 🔒 Restricted Access")
    password = st.text_input("Enter Trader Password:", type="password")
    
    if st.button("Login"):
        if password == "TjRtr@d1nG?!":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("⛔ Access Denied: Incorrect Password")
    st.stop()

# --- CONNECT TO ALPACA ---
# Try to get secrets, otherwise look for local file (fallback)
try:
    API_KEY = st.secrets["API_KEY"]
    SECRET_KEY = st.secrets["SECRET_KEY"]
except:
    # If running locally without secrets.toml
    API_KEY = "PKDRKIBGXRIWT7ON2H3N7ACMXN"
    SECRET_KEY = "GWccu2BaiQ8T9vUCfDBbpC4RNrvDKST7Y3ZHHK6syvCJ"

SYMBOLS = ['SPY', 'SLV', 'GLD']

# Initialize Clients
try:
    trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
    data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
except:
    st.error("Failed to connect to Alpaca. Check API Keys.")
    st.stop()

# ==========================================
# CUSTOM CSS
# ==========================================
st.markdown("""
<style>
    .block-container {padding-top: 5rem; padding-bottom: 1rem;}
    div[data-testid="stMetricValue"] {font-size: 1.8rem;}
    .status-dot-green {
        height: 12px; width: 12px; background-color: #00ff00;
        border-radius: 50%; display: inline-block; margin-right: 8px;
        box-shadow: 0 0 0 0 rgba(0, 255, 0, 1); animation: pulse 2s infinite;
    }
    .status-dot-red {
        height: 12px; width: 12px; background-color: #ff0000;
        border-radius: 50%; display: inline-block; margin-right: 8px;
    }
    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 255, 0, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(0, 255, 0, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 255, 0, 0); }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# DATA LOADING FUNCTIONS
# ==========================================

@st.cache_data(ttl=300)
def get_ticker_performance(symbols):
    data = []
    end = datetime.now(pytz.utc)
    start = end - timedelta(days=8)
    try:
        req = StockBarsRequest(symbol_or_symbols=symbols, timeframe=TimeFrame(1, TimeFrameUnit.Day), start=start)
        bars = data_client.get_stock_bars(req).df
        for sym in symbols:
            df = bars.xs(sym)
            if len(df) > 1:
                price = df['close'].iloc[-1]
                prev = df['close'].iloc[-2]
                pct_1d = ((price - prev) / prev) * 100
                data.append({"Symbol": sym, "Price": price, "1D %": pct_1d})
    except:
        pass
    return pd.DataFrame(data)

def close_position_handler(symbol):
    try:
        trading_client.close_position(symbol)
        st.toast(f"🚫 Closed {symbol}!", icon="✅")
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

# ==========================================
# MAIN DASHBOARD LAYOUT
# ==========================================

# 1. HEADER & STATUS (Now based on Alpaca Connection, not local file)
try:
    account = trading_client.get_account()
    status_html = '<span class="status-dot-green"></span> SYSTEM ONLINE (CLOUD MODE)'
    equity = float(account.equity)
    start_equity = float(account.last_equity)
    pnl_amt = equity - start_equity
    pnl_pct = (pnl_amt / start_equity) * 100
    buying_power = float(account.buying_power)
except:
    status_html = '<span class="status-dot-red"></span> DISCONNECTED'
    equity, pnl_amt, pnl_pct, buying_power = 0, 0, 0, 0

st.markdown(f"### {status_html} <span style='color:gray; font-size:0.8em; margin-left:10px'>ITERATION-A-V1</span>", unsafe_allow_html=True)
st.divider()

# 2. METRICS
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Equity", f"${equity:,.2f}")
m2.metric("Day P&L ($)", f"${pnl_amt:,.2f}", delta=f"{pnl_amt:,.2f}")
m3.metric("Day P&L (%)", f"{pnl_pct:.2f}%", delta=f"{pnl_pct:.2f}%")
m4.metric("Buying Power", f"${buying_power:,.2f}")

st.divider()

# 3. PERFORMANCE
st.markdown("#### 📊 Market Snapshot")
perf_df = get_ticker_performance(SYMBOLS)
if not perf_df.empty:
    st.dataframe(
        perf_df.style.format({"Price": "${:.2f}", "1D %": "{:.2f}%"})
        .applymap(lambda v: 'color: green' if v > 0 else 'color: red', subset=['1D %']),
        use_container_width=True, hide_index=True
    )

# 4. ACTIVE POSITIONS
st.markdown("#### 📦 Active Positions")
try:
    positions = trading_client.get_all_positions()
    if positions:
        for pos in positions:
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1])
                pl_amt = float(pos.unrealized_pl)
                color = "green" if pl_amt > 0 else "red"
                c1.write(f"**{pos.symbol}**")
                c2.write(f"Qty: {pos.qty}")
                c3.write(f"Entry: ${float(pos.avg_entry_price):.2f}")
                c4.markdown(f"<span style='color:{color}'>**${pl_amt:+.2f}**</span>", unsafe_allow_html=True)
                if c5.button(f"🚫 CLOSE", key=f"close_{pos.symbol}"):
                    close_position_handler(pos.symbol)
                st.markdown("---")
    else:
        st.info("No active trades.")
except:
    st.write("Error fetching positions.")

# 5. CHARTS (Simple View)
st.markdown("#### 📉 Live Charts")
tabs = st.tabs(SYMBOLS)
for i, sym in enumerate(SYMBOLS):
    with tabs[i]:
        components.html(f"""
        <div class="tradingview-widget-container">
          <div id="tradingview_{sym}"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
          new TradingView.widget(
          {{ "width": "100%", "height": 400, "symbol": "{sym}", "interval": "D", "timezone": "America/New_York", "theme": "dark", "style": "1", "locale": "en", "toolbar_bg": "#f1f3f6", "enable_publishing": false, "allow_symbol_change": true, "container_id": "tradingview_{sym}" }}
          );
          </script>
        </div>
        """, height=410)

# 6. LOGS NOTICE
st.markdown("#### 📜 Activity Log")
st.warning("⚠️ **Note:** Detailed logs are only visible when running on your local computer. Since you are on the Cloud, check 'Active Positions' above for live status.")

# Auto Refresh
time.sleep(10)
st.rerun()
