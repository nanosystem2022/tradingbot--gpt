import os
import json
import ccxt
from flask import Flask, request, render_template
from errors import errors_bp

app = Flask(__name__)
app.register_blueprint(errors_bp)

# خواندن تنظیمات از فایل config.json
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# ایجاد اتصال به صرافی‌ها
exchanges = {}
if config['EXCHANGES']['binanceusdm']['ENABLED']:
    exchange_config = {
        'apiKey': config['EXCHANGES']['binanceusdm']['API_KEY'],
        'secret': config['EXCHANGES']['binanceusdm']['API_SECRET'],
        'options': {'defaultType': 'future'},
        'enableRateLimit': True
    }
    if config['EXCHANGES']['binanceusdm']['TESTNET']:
        exchange_config['urls'] = {
            'api': {
                'public': 'https://testnet.binancefuture.com/fapi/v1',
                'private': 'https://testnet.binancefuture.com/fapi/v1',
                'fapiPublic': 'https://testnet.binancefuture.com/fapi/v1',
                'fapiPrivate': 'https://testnet.binancefuture.com/fapi/v1'
            }
        }
    exchanges['binanceusdm'] = ccxt.binance(exchange_config)

if config['EXCHANGES']['BYBIT']['ENABLED']:
    exchanges['bybit'] = ccxt.bybit({
        'apiKey': config['EXCHANGES']['BYBIT']['API_KEY'],
        'secret': config['EXCHANGES']['BYBIT']['API_SECRET'],
        'enableRateLimit': True
    })

open_position = False

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("دریافت سیگنال:", data)

    exchange = data['exchange'].lower()
    if exchange in exchanges:
        execute_trade(exchanges[exchange], data)
    else:
        print(f"صرافی {exchange} فعال نیست.")

    return {
        'status': 'success'
    }, 200

def execute_trade(exchange, data):
    global open_position

    symbol = data['symbol']
    side = data['side']
    if 'percentage' in data:
        percentage = float(data['percentage'])
    price = float(data['price'])

    if side == 'closelong' or side == 'closeshort':
        if open_position:
            close_position(exchange, symbol, side)
            open_position = False
        else:
            print("هیچ معامله‌ای برای بستن وجود ندارد.")
    else:
        if not open_position:
            if 'percentage' in data:
                # دریافت موجودی کاربر
                balance = exchange.fetch_balance()

                # محاسبه مقدار معامله بر اساس درصد موجودی
                base_currency = symbol.split('/')[0]
                quote_currency = symbol.split('/')[1]
                available_balance = balance[quote_currency]['free']
                amount = (percentage / 100) * available_balance / price

            # اجرای معامله
            if side == 'long':
                # خرید (long) در حالت فیوچرز
                exchange.create_market_buy_order(symbol, amount)
                open_position = True
            elif side == 'short':
                # فروش (short) در حالت فیوچرز
                exchange.create_market_sell_order(symbol, amount)
                open_position = True
            else:
                print("نوع معامله نامعتبر است.")
        else:
            print("یک معامله باز است. لطفاً ابتدا معامله فعلی را ببندید.")

def close_position(exchange, symbol, side):
    if side == 'closelong':
        position_side = 'long'
    else:
        position_side = 'short'

    if exchange == exchanges['binanceusdm']:
        exchange.private_post_position_close({
            'symbol': exchange.market_id(symbol),
            'positionSide': position_side,
            'reduceOnly': True
        })
    else:
        print("بستن معامله در این صرافی پشتیبانی نمی‌شود.")

if __name__ == '__main__':
    app.run(debug=True)
