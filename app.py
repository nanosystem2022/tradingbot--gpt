import json
from flask import Flask, jsonify, request
import ccxt
from custom_http import HTTP

app = Flask(__name__)

# Load config.json
with open('config.json') as config_file:
    config = json.load(config_file)

open_trade = False
open_trade_id = None


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


def close_order_binance(order_id, symbol, side, remaining, exchange):
    try:
        order = exchange.create_order(
            symbol=symbol,
            type='market',
            side=side,
            amount=remaining
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


def close_order_bybit(order_id, symbol, side, remaining, session):
    try:
        order = session.post('/v2/private/order/create', json={
            'symbol': symbol,
            'side': side,
            'order_type': 'Market',
            'qty': remaining,
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
    global open_trade, open_trade_id
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

    # Handle close trade requests
    if data.get('action') in ['closeshort', 'closelong']:
        close_trade_handlers = {
            'binance-futures': (use_binance_futures, close_order_binance),
            'bybit': (use_bybit, close_order_bybit)
        }

        if data['exchange'] in close_trade_handlers:
            enabled, handler = close_trade_handlers[data['exchange']]
            if enabled:
                if data['action'] == 'closeshort':
                    side = 'buy'
                else:
                    side = 'sell'

                order = exchange.fetch_order(id=open_trade_id, symbol=data['symbol'])
                response, status_code = handler(
                    order['id'],  # Use the 'id' from the fetched order
                    data['symbol'],
                    side,
                    order['remaining'],
                    exchange
                )
                open_trade = False
                open_trade_id = None
            else:
                error_message = f"{data['exchange']} is not enabled in the config file."
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
    # Handle open trade requests
    elif not open_trade:
        open_trade_handlers = {
            'binance-futures': (use_binance_futures, create_order_binance),
            'bybit': (use_bybit, create_order_bybit)
        }

        if data['exchange'] in open_trade_handlers:
            enabled, handler = open_trade_handlers[data['exchange']]
            if enabled:
                response, status_code = handler(data, exchange if data['exchange'] == 'binance-futures' else session)
                if status_code == 200:
                    open_trade = True
                    open_trade_id = response['data']['id']
                return jsonify(response), status_code
            else:
                error_message = f"{data['exchange']} is not enabled in the config file."
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
    else:
        # Reject new trades while a trade is open
        error_message = "A trade is already open. Please close the current trade before opening a new one."
        return {
            "status": "error",
            "message": error_message
        }, 400

if __name__ == '__main__':
    app.run()
