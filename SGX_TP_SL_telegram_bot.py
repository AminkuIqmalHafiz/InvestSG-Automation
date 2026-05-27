import streamlit as st
import yfinance as yf
import requests
import time
from datetime import datetime
import pandas as pd

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Risk Desk OS", layout="wide")

#PUT YOUR TELEGRAM KEYS RIGHT HERE 
TELEGRAM_TOKEN = "Telegram bot token here"
TELEGRAM_CHAT_ID = "Telegram chat ID here"
# ==========================================

# --- INITIALIZE SESSION STATE ---
# This keeps data alive while the app refreshes
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
if 'scanner_active' not in st.session_state:
    st.session_state.scanner_active = False
if 'triggered_alerts' not in st.session_state:
    st.session_state.triggered_alerts = set()

# --- TELEGRAM FUNCTION ---
def trigger_telegram_alert(ticker, live_price, trigger_price, alert_type, token, chat_id):
    if alert_type == "KILL":
        emoji = "🚨"
        header = "LIQUIDATION ALERT"
        action = "⚠️ ACTION REQUIRED: Execute Market Sell to CUT LOSS."
    else:
        emoji = "💰"
        header = "TAKE PROFIT ALERT"
        action = "✅ ACTION REQUIRED: Execute Market Sell to SECURE BAG."

    alert_text = (
        f"{emoji} **{header}** {emoji}\n\n"
        f"**Ticker:** {ticker}\n"
        f"**Live Price:** ${live_price:.3f}\n"
        f"**Trigger Level:** ${trigger_price:.3f}\n\n"
        f"{action}"
    )
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {'chat_id': chat_id, 'text': alert_text, 'parse_mode': 'Markdown'}
    
    try:
        requests.post(url, data=payload)
        return True
    except Exception as e:
        return False

# --- SIDEBAR: SETTINGS ---
with st.sidebar:
    st.header("Server Configuration")
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "INSERT_YOUR_BOT_TOKEN_HERE":
        st.error("⚠️ Telegram Token missing at the top of the script!")
    else:
        st.success("Telegram Token Loaded")
        
    st.divider()
    st.header("Risk Parameters")
    st.markdown("Auto-calculates your floors and ceilings.")
    stop_loss_pct = st.number_input("Stop Loss (%)", value=-2.0, step=0.5)
    take_profit_pct = st.number_input("Take Profit (%)", value=4.5, step=0.5)

# --- MAIN DASHBOARD ---
st.title("Automated Risk Desk")
st.markdown("Enter your live positions. The engine will auto-calculate risk brackets and guard the exits.")

# 1. INPUT SECTION
with st.container():
    col1, col2, col3 = st.columns(3)
    with col1:
        new_ticker = st.text_input("Ticker (e.g., Z74.SI)").upper()
    with col2:
        entry_price = st.number_input("Average Entry Price", min_value=0.000, value=1.000, format="%.3f")
    with col3:
        st.markdown("<br>", unsafe_allow_html=True) # Spacing alignment
        if st.button("➕ Add Position to Radar", use_container_width=True):
            if new_ticker:
                # The Auto-Math Engine
                kill_switch = entry_price * (1 + (stop_loss_pct / 100))
                tp_target = entry_price * (1 + (take_profit_pct / 100))
                
                st.session_state.portfolio[new_ticker] = {
                    'Entry': entry_price,
                    'Kill Switch': round(kill_switch, 3),
                    'Take Profit': round(tp_target, 3)
                }
                st.success(f"{new_ticker} locked into the matrix.")
            else:
                st.error("Please enter a valid ticker.")

# 2. PORTFOLIO DISPLAY
if st.session_state.portfolio:
    st.subheader("Active Radar")
    
    # Convert dictionary to a clean Pandas DataFrame for Streamlit
    df = pd.DataFrame.from_dict(st.session_state.portfolio, orient='index')
    
    # Add a button to clear the board
    if st.button("Clear Radar"):
        st.session_state.portfolio = {}
        st.session_state.triggered_alerts = set()
        st.rerun()
        
    st.dataframe(df, use_container_width=True)

st.divider()

# 3. THE EXECUTION ENGINE
st.subheader("Live Market Scanner")

# Toggle Switch for the Engine
button_text = "STOP ENGINE" if st.session_state.scanner_active else "START ENGINE"
if st.button(button_text, type="primary", use_container_width=True):
    if TELEGRAM_TOKEN == "INSERT_YOUR_BOT_TOKEN_HERE" or TELEGRAM_CHAT_ID == "INSERT_YOUR_CHAT_ID_HERE":
        st.error("Please insert your Telegram credentials at the top of the script first!")
    elif not st.session_state.portfolio:
        st.error("Add at least one stock to the radar first!")
    else:
        st.session_state.scanner_active = not st.session_state.scanner_active
        st.rerun()

# The continuous scanning loop
if st.session_state.scanner_active:
    st.warning("⚠️ ENGINE IS LIVE. The app is actively scanning the market. Click 'Stop Engine' before adding new stocks.")
    
    # We use st.empty() to create a terminal-like window that overwrites itself
    log_window = st.empty() 
    
    while st.session_state.scanner_active:
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_text = f"**Last Scan:** {timestamp}\n\n"
        
        for ticker, levels in st.session_state.portfolio.items():
            if ticker in st.session_state.triggered_alerts:
                log_text += f"✔️ {ticker} | Alert Already Fired.\n"
                continue
                
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1d")
                
                if not hist.empty:
                    live_price = hist['Close'].iloc[-1]
                    kill_switch = levels['Kill Switch']
                    tp_target = levels['Take Profit']
                    
                    # Floor Breach
                    if live_price <= kill_switch:
                        trigger_telegram_alert(ticker, live_price, kill_switch, "KILL", TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
                        st.session_state.triggered_alerts.add(ticker)
                        st.toast(f"🚨 {ticker} HIT STOP LOSS!", icon="🚨")
                        
                    # Ceiling Breach
                    elif live_price >= tp_target:
                        trigger_telegram_alert(ticker, live_price, tp_target, "PROFIT", TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
                        st.session_state.triggered_alerts.add(ticker)
                        st.toast(f"💰 {ticker} HIT TAKE PROFIT!", icon="💰")
                        
                    else:
                        log_text += f"🟢 **{ticker}** | Live: ${live_price:.3f} (Floor: ${kill_switch:.2f} | Ceil: ${tp_target:.2f})\n"
                        
            except Exception as e:
                log_text += f"🔴 **{ticker}** | Error fetching data.\n"
        
        # Update the web UI with the new logs
        log_window.markdown(log_text)
        
        # Throttle the scanner
        time.sleep(30)