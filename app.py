import json
import http
from flask import Flask, render_template, request, jsonify
import time
import ccxt
from custom_http import HTTP

app = Flask(__name__)

# Load config.json
with open('config.json') as config_file:
    config = json.load(config_file)

# Add a variable to track open orders
open_orders = {}

# Error messages
ERR_UNSUPPORTED_ACTION = {"status": "error", "message": "Unsupported action."}
ERR_UNSUPPORTED_EXCHANGE = {"status": "error", "message": "Unsupported exchange."}
ERR_MISSING_QUANTITY = {"status": "error", "message": "The 'quantity' field is missing in the input data."}
ERR_NO_OPEN_ORDER = {"status": "error", "message": "No open order found."}


def is_exchange_enabled(exchange_name):
    if exchange_name in config['EXCHANGES']:
        if config['EXCHANGES'][exchange_name]['ENABLED']:
            return True
    return False

def create_order_binance(data):
    symbol = data['symbol'].replace('/', '')
    order_type = data.get('type', 'market')
    side = data.get('side', None)
    quantity = data.get('quantity', None)

    if data['action'] == 'closelong':
        side = 'sell'
    elif data['action'] == 'closeshort':
        side = 'buy'

    if side is None or quantity is None:
        return {'error': 'Missing side or quantity'}, 400

    try:
        order = exchange.create_order(symbol, order_type, side, quantity)
        return {'result': order}, 200
    except Exception as e:
        return {'error': str(e)}, 400


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
    print("Hook Received!")
    data = request.json
    print(data)

    actions = {
        'binance-futures': {
            'open': create_order_binance,
            'close': close_order_binance
        },
        'bybit': {
            'open': create_order_bybit,
            'close': close_order_bybit
        }
    }

    exchange_actions = actions.get(data['exchange'])
    if exchange_actions:
        action = exchange_actions.get(data['action'])
        if action:
            response, status_code = action(data, exchange if data['exchange'] == 'binance-futures' else session)
            return jsonify(response), status_code
        else:
            return jsonify(ERR_UNSUPPORTED_ACTION), http.HTTPStatus.BAD_REQUEST
    else:
        return jsonify(ERR_UNSUPPORTED_EXCHANGE), http.HTTPStatus.BAD_REQUEST

if __name__ == '__main__':
    app.run()
