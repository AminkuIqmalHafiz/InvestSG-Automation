import streamlit as st
import yfinance as yf
import pandas as pd
import random
import time

# 1. PAGE SETUP
st.set_page_config(page_title="SGX Terminal", layout="wide", initial_sidebar_state="expanded")

# --- SIDEBAR: TOOLS & CONTROLS ---
with st.sidebar:#sidebar
    st.title("Terminal Controls")
    
    st.markdown("### Automation")
    auto_refresh = st.toggle("Auto-Refresh (5 mins)", value=False)
    if auto_refresh:
        st.success("Auto-Refresh Active: Scanning every 5 minutes.")
    
    st.markdown("---")
    
    st.markdown("### 7x DLC Calculator")
    st.caption("Calculate leverage impact for InvestSG Tournament")
    
    capital = st.number_input("Capital Position (SGD)", min_value=100, value=1000, step=100)
    expected_move = st.slider("Expected Stock Move (%)", min_value=-10.0, max_value=10.0, value=2.0, step=0.5)
    
    dlc_move = expected_move * 7
    pnl = capital * (dlc_move / 100)
    
    st.metric(label="DLC Move (%)", value=f"{dlc_move:.1f}%")
    st.metric(label="Estimated P&L (SGD)", value=f"${pnl:+.2f}", delta=f"${pnl:+.2f}")
    
    st.markdown("---")
    manual_run = st.button("Force Manual Scan", type="primary", use_container_width=True)

# --- MAIN DASHBOARD ---
st.title("SGX Confluence Screener")
st.markdown("Live RSI & MACD Algorithmic Scanning")

# THE UPGRADE: A master dictionary mapping tickers to their Names and Sectors
sgx_master_dict = {
    "D05.SI": {"name": "DBS Group", "sector": "Banking"},
    "O39.SI": {"name": "OCBC Bank", "sector": "Banking"},
    "U11.SI": {"name": "UOB", "sector": "Banking"},
    "Z74.SI": {"name": "Singtel", "sector": "Telecommunications"},
    "BS6.SI": {"name": "Yangzijiang", "sector": "Offshore/Marine"},
    "5E2.SI": {"name": "Seatrium", "sector": "Offshore/Marine"},
    "AWX.SI": {"name": "AEM Holdings", "sector": "Tech/Semiconductors"},
    "C38U.SI": {"name": "CapitaLand Integrated", "sector": "REITs"},
    "ME8U.SI": {"name": "Mapletree Industrial", "sector": "REITs"},
    "A17U.SI": {"name": "Ascendas REIT", "sector": "REITs"},
    "BN4.SI": {"name": "Keppel", "sector": "Conglomerate/Offshore"},
    "C52.SI": {"name": "ComfortDelGro", "sector": "Transportation"},
    "S68.SI": {"name": "SGX", "sector": "Financials"},
    "U96.SI": {"name": "Sembcorp Ind", "sector": "Energy/Utilities"},
    "C09.SI": {"name": "City Developments", "sector": "Real Estate"},
    "Y92.SI": {"name": "Thai Beverage", "sector": "Food & Beverage"},
    "G13.SI": {"name": "Genting Singapore", "sector": "Hospitality/Gaming"},
    "S58.SI": {"name": "SATS Ltd", "sector": "Aviation Services"},
    "F34.SI": {"name": "Wilmar Intl", "sector": "Agriculture"},
    "D01.SI": {"name": "DFI Retail", "sector": "Retail"},
    "M44U.SI": {"name": "Mapletree Logistics", "sector": "REITs"},
    "AJBU.SI": {"name": "Keppel DC REIT", "sector": "REITs"},
    "N2IU.SI": {"name": "Mapletree Pan Asia", "sector": "REITs"},
    "RW0U.SI": {"name": "Mapletree North Asia", "sector": "REITs"},
    "J36.SI": {"name": "Jardine Matheson", "sector": "Conglomerate"},
    "J37.SI": {"name": "Jardine Strategic", "sector": "Conglomerate"},
    "S63.SI": {"name": "ST Engineering", "sector": "Aerospace/Defense"},
    "U14.SI": {"name": "UOL Group", "sector": "Real Estate"},
    "V03.SI": {"name": "Venture Corp", "sector": "Tech/Manufacturing"},
    "F99.SI": {"name": "Frencken Group", "sector": "Tech/Manufacturing"},
    "H78.SI": {"name": "Hongkong Land", "sector": "Real Estate"},
    "C31.SI": {"name": "CapitaLand Investment", "sector": "Real Estate"}
}

if manual_run or auto_refresh:
    with st.spinner('Scanning Institutional Order Flow...'):
        # Extract just the keys (tickers) to feed to yfinance
        all_tickers = list(sgx_master_dict.keys())
        sample_size = min(30, len(all_tickers))
        random_tickers = random.sample(all_tickers, sample_size)
        
        data = yf.download(random_tickers, period="3mo", progress=False)
        
        if not data.empty:
            close_prices = data['Close'].dropna(axis=1, how='all')
            
            # MATH: RSI
            def calculate_rsi(df, window=14):
                delta = df.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
                return 100 - (100 / (1 + (gain / loss)))

            # MATH: MACD
            def calculate_macd(df):
                exp1 = df.ewm(span=12, adjust=False).mean()
                exp2 = df.ewm(span=26, adjust=False).mean()
                macd = exp1 - exp2
                signal = macd.ewm(span=9, adjust=False).mean()
                return macd - signal

            rsi_data = calculate_rsi(close_prices)
            macd_hist = calculate_macd(close_prices)

            results = []
            for ticker in close_prices.columns:
                try:
                    current_price = float(close_prices[ticker].dropna().iloc[-1])
                    rsi_val = float(rsi_data[ticker].dropna().iloc[-1])
                    
                    hist_today = float(macd_hist[ticker].dropna().iloc[-1])
                    hist_yest = float(macd_hist[ticker].dropna().iloc[-2])
                    
                    macd_status = "Sideways"
                    if hist_today > 0 and hist_yest <= 0: macd_status = "BULL CROSS "
                    elif hist_today < 0 and hist_yest >= 0: macd_status = "BEAR CROSS "
                    elif hist_today > 0: macd_status = "Bullish"
                    elif hist_today < 0: macd_status = "Bearish"

                    signal = "➖"
                    if rsi_val < 35 and "BULL" in macd_status: signal = "STRONG BUY"
                    if rsi_val > 65 and "BEAR" in macd_status: signal = "STRONG SELL"

                    # THE UPGRADE: Inject the Name and Sector into our final results
                    company_name = sgx_master_dict[ticker]["name"]
                    company_sector = sgx_master_dict[ticker]["sector"]

                    results.append({
                        'Ticker': ticker, 
                        'Name': company_name,
                        'Sector': company_sector,
                        'Price': current_price, 
                        'RSI': rsi_val,
                        'MACD': macd_status,
                        'Action': signal
                    })
                except Exception:
                    pass

            df = pd.DataFrame(results).sort_values(by='RSI').reset_index(drop=True)

            col1, col2, col3 = st.columns(3)
            col1.metric("Live Tickers Tracked", len(df))
            col2.metric("Oversold (RSI < 30)", len(df[df['RSI'] < 30]))
            col3.metric("Golden Crosses (MACD)", len(df[df['MACD'] == "BULL CROSS 🚀"]))
            
            # THE UPGRADE: Added the Name and Sector columns to the Streamlit table config
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Ticker": st.column_config.TextColumn("Symbol", width="small"),
                    "Name": st.column_config.TextColumn("Company", width="medium"),
                    "Sector": st.column_config.TextColumn("Sector", width="medium"),
                    "Price": st.column_config.NumberColumn("Last Price", format="$ %.2f"),
                    "RSI": st.column_config.ProgressColumn("RSI (14)", format="%.2f", min_value=0, max_value=100),
                    "MACD": st.column_config.TextColumn("MACD Momentum"),
                    "Action": st.column_config.TextColumn("Algo Signal", width="medium")
                }
            )
            
            st.caption(f"Last updated: {time.strftime('%H:%M:%S')}")
        else:
            st.error("Failed to fetch data.")

else:
    st.info("Click 'Force Manual Scan' in the sidebar or toggle Auto-Refresh to begin.")

if auto_refresh:
    time.sleep(300)
    st.rerun()