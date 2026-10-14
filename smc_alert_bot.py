cat << 'EOF' > smc_alert_bot.py
import time
import requests
import yfinance as yf
import pandas as pd
import numpy as np

# ==========================================
# CONFIGURATION: Auto-configured via shortcut
# ==========================================
TELEGRAM_BOT_TOKEN = "8916158320:AAFmZUMqjSHTsHL_Lq4nu43RwyGd587Nqbs"
TELEGRAM_CHAT_ID = "5118953200"

def send_telegram_alert(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("[Alert Sent Successfully to Telegram]")
        else:
            print(f"[Telegram Error]: {response.text}")
    except Exception as e:
        print(f"[Network Error]: {e}")

def run_strategy_scan():
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S UTC')}] Scanning BTC-USD 5m data...")
    
    df_m5 = yf.download("BTC-USD", period="5d", interval="5m", progress=False)
    if isinstance(df_m5.columns, pd.MultiIndex):
        df_m5.columns = df_m5.columns.get_level_values(0)
    df_m5 = df_m5[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    
    if len(df_m5) < 100:
        print("Insufficient data returned. Retrying next cycle...")
        return

    df_h1 = df_m5.resample('1h').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna()
    h1_high = df_h1['High'].rolling(window=12).max().iloc[-2]
    h1_low = df_h1['Low'].rolling(window=12).min().iloc[-2]
    
    df_m15 = df_m5.resample('15min').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna()
    m15_prev = df_m15.iloc[-2]
    
    curr_time = pd.Timestamp.utcnow()
    in_killzone = (7 <= curr_time.hour < 10) or (12 <= curr_time.hour < 16)
    
    if not in_killzone:
        print("Outside active killzone hours. Monitoring market state...")
        return

    bearish_sweep = (m15_prev['High'] > h1_high) and (m15_prev['Close'] < h1_high)
    bullish_sweep = (m15_prev['Low'] < h1_low) and (m15_prev['Close'] > h1_low)
    latest_m5_close = df_m5['Close'].iloc[-1]
    
    if bearish_sweep:
        alert_msg = (
            "🚨 *BTCUSD SMC SHORT SETUP DETECTED* 🚨\n\n"
            f"• *Time:* {curr_time.strftime('%H:%M UTC')}\n"
            f"• *Trigger:* M15 swept H1 High ({h1_high:.2f})\n"
            f"• *Current Price:* ${latest_m5_close:,.2f}\n"
            "• *Action:* Look for M5 Bearish FVG limit entry!"
        )
        send_telegram_alert(alert_msg)
        print("Bearish setup triggered and alerted!")
        
    elif bullish_sweep:
        alert_msg = (
            "🚨 *BTCUSD SMC LONG SETUP DETECTED* 🚨\n\n"
            f"• *Time:* {curr_time.strftime('%H:%M UTC')}\n"
            f"• *Trigger:* M15 swept H1 Low ({h1_low:.2f})\n"
            f"• *Current Price:* ${latest_m5_close:,.2f}\n"
            "• *Action:* Look for M5 Bullish FVG limit entry!"
        )
        send_telegram_alert(alert_msg)
        print("Bullish setup triggered and alerted!")
    else:
        print("No active sweep detected on this candle close.")

if __name__ == "__main__":
    print("==================================================")
    print("   FREE BTCUSD SMC TELEGRAM ALERT BOT STARTED     ")
    print("==================================================")
    send_telegram_alert("🟢 *SMC Bot Online:* Monitoring BTC-USD 24/7.")
    
    while True:
        try:
            run_strategy_scan()
        except Exception as err:
            print(f"[Error in main loop]: {err}")
        
        time.sleep(300)
EOF
