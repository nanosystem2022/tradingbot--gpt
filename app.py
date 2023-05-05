import json
from flask import Flask, render_template, request, jsonify
import time
import ccxt
from custom_http import HTTP

app = Flask(__name__)

# Load config.json
with open('config.json') as config_file:
    config = json.load(config_file)

def is_exchange_enabled(exchange_name):
    return config['EXCHANGES'].get(exchange_name, {}).get('ENABLED', False)

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

def close_position_binance(data, exchange):
    symbol = data['symbol']
    try:
        result = exchange.private_post_positionmargin_type(
            {"symbol": exchange.market_id(symbol), "type": "2", "amount": "0"}
        )
        return {
            "status": "success",
            "data": result
        }, 200
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }, 500

def close_order_binance(data, exchange):
    symbol = data['symbol']

    try:
        positions = exchange.fapiPrivate_get_positionrisk({"symbol": symbol})
        position_to_close = None
        for position in positions:
            if float(position["positionAmt"]) != 0:
                position_to_close = position
                break

        if position_to_close:
            side = "buy" if float(position_to_close["positionAmt"]) < 0 else "sell"
            order = exchange.create_market_order(symbol=symbol, side=side, amount=abs(float(position_to_close["positionAmt"])))
            return {
                "status": "success",
                "data": order
            }, 200
        else:
            error_message = f"No open position found for symbol {symbol}."
            return {
                "status": "error",
                "message": error_message
            }, 400
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }, 500

def close_order_bybit(data, session):
    symbol = data['symbol']

    try:
        response = session.get('/v2/private/position/list', params={"symbol": symbol})
        positions = response.json()["result"]
        position_to_close = None
        for position in positions:
            if position["size"] != 0:
                position_to_close = position
                break

        if position_to_close:
            side = "Buy" if position_to_close["side"] == "Sell" else "Sell"
            order = session.post('/v2/private/order/create', json={
                'symbol': symbol,
                'side': side,
                'order_type': 'Market',
                'qty': position_to_close["size"],
                'time_in_force': 'GTC'
            })
            return {
                "status": "success",
                "data": order.json()
            }, 200
        else:
            error_message = f"No open position found for symbol {symbol}."
            return {
                "status": "error",
                "message": error_message
            }, 400
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

    if data['exchange'] == 'binance-futures':
        if use_binance_futures:
            if data['action'] == 'close':
                response, status_code = close_order_binance(data, exchange)
            else:
                response, status_code = create_order_binance(data, exchange)
            return jsonify(response), status_code
        else:
            error_message = "Binance Futures is not enabled in the config file."
            return {
                "status": "error",
                "message": error_message
            }, 400

    elif data['exchange'] == 'bybit':
        if use_bybit:
            if data['action'] == 'close':
                response, status_code = close_order_bybit(data, session)
            else:
                response, status_code = create_order_bybit(data, session)
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
