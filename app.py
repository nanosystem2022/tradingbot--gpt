import ccxt
import json
from flask import Flask, request

# باز کردن فایل config.json و خواندن مقادیر
with open('config.json', 'r') as f:
    config = json.load(f)

# تنظیمات کلید API
key = config['KEY']

# ساخت لیست از صرافی‌هایی که باید از آن‌ها استفاده کنیم
exchanges = []
for exchange_id, exchange_data in config['EXCHANGES'].items():
    if exchange_data['ENABLED']:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            'apiKey': exchange_data['API_KEY'],
            'secret': exchange_data['API_SECRET'],
            'enableRateLimit': True,
            'options': {'defaultType': 'future'},
        })
        if exchange_data['TESTNET']:
            exchange.urls['api'] = exchange.urls['test']
        exchanges.append(exchange)

# ساخت وب اپلیکیشن Flask
app = Flask(__name__)

# تعریف روت برای دریافت وب هوک از TradingView
@app.route('/webhook', methods=['POST'])
def webhook():
    # دریافت داده‌های JSON ارسال شده از سمت TradingView
    data = request.get_json()

    # بررسی اینکه آیا ترید باید بسته شود یا خیر
    if data['action'] == 'closelong':
        side = 'sell'
    elif data['action'] == 'closeshort':
        side = 'buy'
    else:
        return 'Invalid action'

    # باز کردن معامله در صرافی‌های مختلف
    for exchange in exchanges:
        try:
            symbol = exchange.markets[data['ticker']]['symbol']
            order = exchange.create_market_order(symbol, 'limit', side, data['qty'])
            print(f"{exchange.id} trade opened: {order['info']['orderType']} {order['info']['symbol']} {order['info']['side']} {order['info']['orderQty']}")
        except ccxt.BaseError as e:
            print(f"{exchange.id} trade error: {str(e)}")

    return 'OK'

# اجرای وب اپلیکیشن
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
