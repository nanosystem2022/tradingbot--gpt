import json
from flask import Flask, render_template, request, jsonify
import time
import ccxt
from custom_http import HTTP

app = Flask(__name__)

# load config.json
with open('config.json') as config_file:
    config = json.load(config_file)

# Add a variable to track open orders
open_orders = {}

def is_exchange_enabled(exchange_name):
    if exchange_name in config['EXCHANGES']:
        if config['EXCHANGES'][exchange_name]['ENABLED']:
            return True
    return False

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
        return {
            "status": "success",
            "data": order.json()
        }, 200
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }, 500
    
def close_order_binance(data, exchange):
    order_id = open_orders.get(data['symbol'])
    if order_id:
        try:
            order = exchange.cancel_order(order_id, symbol=data['symbol'])
            return {"status": "success", "data": order}, 200
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500
    else:
        return {"status": "error", "message": "No open order found."}, 400

def close_order_bybit(data, session):
    order_id = open_orders.get(data['symbol'])
    if order_id:
        try:
            order = session.post('/v2/private/order/cancel', json={'order_id': order_id})
            return {"status": "success", "data": order.json()}, 200
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500
    else:
        return {"status": "error", "message": "No open order found."}, 400


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
    # ... your previous code ...

    if data['exchange'] == 'binance-futures':
        if data['action'] == 'close':
            response, status_code = close_order_binance(data, exchange)
            return jsonify(response), status_code
        elif data['action'] == 'open':
            response, status_code = create_order_binance(data, exchange)
            if status_code == 200:
                open_orders[data['symbol']] = response['data']['orderId']
            return jsonify(response), status_code
        else:
            error_message = "Unsupported action."
            return {"status": "error", "message": error_message}, 400

    # ... your previous code ...

    elif data['exchange'] == 'bybit':
        if data['action'] == 'close':
            response, status_code = close_order_bybit(data, session)
            return jsonify(response), status_code
        elif data['action'] == 'open':
            response, status_code = create_order_bybit(data, session)
            if status_code == 200:
                open_orders[data['symbol']] = response['data']['order_id']
            return jsonify(response), status_code
        else:
            error_message = "Unsupported action."
            return {"status": "error", "message": error_message}, 400

    else:
        error_message = "Unsupported exchange."
        return {
            "status": "error",
            "message": error_message
        }, 400

if __name__ == '__main__':
    app.run()
