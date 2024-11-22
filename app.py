from flask import Flask, render_template, jsonify
import requests
import pandas as pd
from datetime import datetime

app = Flask(__name__)

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"

def get_btcusdt_daily_klines():
    params = {
        'symbol': 'BTCUSDT',
        'interval': '1d',
        'limit': 500  # Number of data points
    }
    response = requests.get(BINANCE_KLINES_URL, params=params)
    data = response.json()
    
    # Parse data into DataFrame
    df = pd.DataFrame(data, columns=[
        'Open Time', 'Open', 'High', 'Low', 'Close', 'Volume',
        'Close Time', 'Quote Asset Volume', 'Number of Trades',
        'Taker Buy Base Asset Volume', 'Taker Buy Quote Asset Volume', 'Ignore'
    ])
    
    # Convert columns to appropriate data types
    df['Open Time'] = pd.to_datetime(df['Open Time'], unit='ms')
    df['Close Time'] = pd.to_datetime(df['Close Time'], unit='ms')
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        df[col] = df[col].astype(float)
    
    return df

def calculate_sma(df, window=20):
    df[f'SMA_{window}'] = df['Close'].rolling(window=window).mean()
    return df

def calculate_rsi(df, window=14):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def calculate_macd(df, short_window=12, long_window=26, signal_window=9):
    ema_short = df['Close'].ewm(span=short_window, adjust=False).mean()
    ema_long = df['Close'].ewm(span=long_window, adjust=False).mean()
    macd = ema_short - ema_long
    signal = macd.ewm(span=signal_window, adjust=False).mean()
    histogram = macd - signal
    df['MACD'] = macd
    df['Signal'] = signal
    df['Histogram'] = histogram
    return df

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def data():
    df = get_btcusdt_daily_klines()
    df = calculate_macd(df)
    df = calculate_sma(df, window=20)
    df = calculate_rsi(df, window=14)  # Calculate a 14-day RSI

    # Prepare data for frontend
    chart_data = []
    for _, row in df.iterrows():
        chart_data.append({
            'time': int(row['Open Time'].timestamp()),
            'open': row['Open'],
            'high': row['High'],
            'low': row['Low'],
            'close': row['Close'],
            'macd': row['MACD'],
            'signal': row['Signal'],
            'histogram': row['Histogram'],
            'sma': row[f'SMA_20'] if pd.notna(row[f'SMA_20']) else None,
            'rsi': row['RSI'] if pd.notna(row['RSI']) else None
        })
    
    return jsonify(chart_data)


if __name__ == '__main__':
    app.run(debug=True)
