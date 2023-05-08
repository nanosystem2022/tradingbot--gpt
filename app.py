import json
from flask import Flask, render_template, request, jsonify
import time
import ccxt
from custom_http import HTTP

app = Flask(__name__)

# load config.json
with open('config.json') as config_file:
    config = json.load(config_file)

def is_exchange_enabled(exchange_name):
    if exchange_name in config['EXCHANGES']:
        if config['EXCHANGES'][exchange_name]['ENABLED']:
            return True
    return False

user_trade_status = {}

def update_user_trade_status(data, response):
    if response['status'] == 'error':
        return
    side = data['side']
    symbol = data['symbol']
    if side.lower() == 'buy':
        user_trade_status[symbol] = 'buy'
    elif side.lower() == 'sell':
        user_trade_status[symbol] = 'sell'
    elif side.lower() == 'closelong':
        user_trade_status[symbol] = None
    elif side.lower() == 'closeshort':
        user_trade_status[symbol] = None

def create_order_binance(data, exchange):
    symbol = data['symbol']
    side = data['side']
    price = data.get('price', 0)
    quantity = data.get('quantity')

    if quantity is None:
        error_message = "The 'quantity' field is missing in the input data."
        return {
            "status": "error",
            "message": error_message
        }, 400

    try:
        order = exchange.create_order(
            symbol=symbol,
            type=data['type'],
            side=side,
            amount=float(quantity),
            price=price
        )
        user_trade_status[symbol] = side
        return {
            "status": "success",
            "data": order
        }, 200
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }, 500

def create_order_bybit(data, session):
    symbol = data['symbol']
    side = data['side']
    price = data.get('price', 0)
    quantity = data.get('quantity')

    if quantity is None:
        error_message = "The 'quantity' field is missing in the input data."
        return {
            "status": "error",
            "message": error_message
        }, 400

    try:
        order = session.post('/v2/private/order/create', json={
            'symbol': symbol,
            'side': side,
            'order_type': data['type'],
            'qty': float(quantity),
            'price': price,
            'time_in_force': 'GTC'
        })
        user_trade_status[symbol] = side
        return {
            "status": "success",
            "data": order.json()
        }, 200
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }, 500

use_bybit = is_exchange_enabled('BYBIT')
use_binance_futures = is_exchange_enabled('BINANCE-FUTURES')

if use_bybit:
    print("Bybit is enabled!")
    session = HTTP(
        endpoint='https://api.bybit.com',
        api_key=config['EXCHANGES']['BYBIT']['API_KEY'],
        api_secret=config['EXCHANGES']['BYBIT']['API_SECRET']
    )

if use_binance_futures:
    print("Binance is enabled!")
    exchange = ccxt.binance({
        'apiKey': config['EXCHANGES']['BINANCE-FUTURES']['API_KEY'],
        'secret': config['EXCHANGES']['BINANCE-FUTURES']['API_SECRET'],
        'options': {
            'defaultType': 'future',
        },
        'urls': {
            'api': {
                'public': 'https://testnet.binancefuture.com/fapi/v1',
                'private': 'https://testnet.binancefuture.com/fapi/v1',
            },
        }
    })

    if config['EXCHANGES']['BINANCE-FUTURES']['TESTNET']:
        exchange.set_sandbox_mode(True)

@app.route('/')
def index():
    return {'message': 'Server is running!'}

@app.route('/webhook', methods=['POST'])
def webhook():
    print("Hook Received!")
    data = json.loads(request.data)
    print(data)

    if int(data['key']) != config['KEY']:
        error_message = "Invalid Key, Please Try Again!"
        print(error_message)
        return {
            "status": "error",
            "message": error_message
        }, 400

    symbol = data['symbol']
    side = data['side']

    if symbol in user_trade_status:
        if side == 'closelong' and user_trade_status[symbol] != 'buy':
            return {"status": "error", "message": "Cannot close long because there is no open long position."}, 400
        if side == 'closeshort' and user_trade_status[symbol] != 'sell':
            return {"status": "error", "message": "Cannot close short because there is no open short position."}, 400

    if data['exchange'] == 'binance-futures':
        if use_binance_futures:
            response, status_code = create_order_binance(data, exchange)
            update_user_trade_status(data, response)
            return jsonify(response), status_code
        else:
            error_message = "Binance Futures is not enabled in the config file."
            return {
                "status": "error",
                "message": error_message
            }, 400

    elif data['exchange'] == 'bybit':
        if use_bybit:
            response, status_code = create_order_bybit(data, session)
            update_user_trade_status(data, response)
            return jsonify(response), status_code
        else:
            error_message = "Bybit is not enabled in the config file."
            return {
                "status": "error",
                "message": error_message
            }, 400

    else:
        error_message = "Unsupported exchange."
        return {
            "status": "error",
            "message": error_message
        }, 400

if __name__ == '__main__':
    app.run()
