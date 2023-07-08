import json
from flask import Flask, render_template, request, jsonify
import time
import ccxt
from custom_http import HTTP

app = Flask(__name__)

# load config.json
with open('config.json') as config_file:
    config = json.load(config_file)

active_orders = {} # to store the active orders
trade_open = False # to store the status of the trade

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
    params = {'closePosition': 'Close-All'} if side == 'closeshort' or side == 'closelong' else {}

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
            price=price,
            params=params
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
    params = {'reduce_only': True} if side == 'closeshort' or side == 'closelong' else {}

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
            'time_in_force': 'GTC',
            **params
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

use_bybit = is_exchange_enabled('bybit')
use_binance = is_exchange_enabled('binance')

if use_bybit:
    session_bybit = HTTP(config['EXCHANGES']['bybit']['API_KEY'], config['EXCHANGES']['bybit']['SECRET'])
if use_binance:
    binance = ccxt.binance({
        'apiKey': config['EXCHANGES']['binance']['API_KEY'],
        'secret': config['EXCHANGES']['binance']['SECRET']
    })

def create_order(data):
    global trade_open
    if trade_open:
        return jsonify({
            "status": "error",
            "message": "A trade is already open. Please close the current trade before opening a new one."
        }), 400

    if use_bybit:
        response, status = create_order_bybit(data, session_bybit)
        if status == 200:
            active_orders[data['symbol']] = response['data']['result']['order_id']
    if use_binance:
        response, status = create_order_binance(data, binance)
        if status == 200:
            active_orders[data['symbol']] = response['data']['id']

    if status == 200:
        trade_open = True

    return jsonify(response), status

def close_order(data):
    global trade_open
    symbol = data['symbol']

    if symbol not in active_orders:
        return jsonify({
            "status": "error",
            "message": "There's no active order for this symbol"
        }), 400

    if use_bybit:
        response, status = close_order_bybit(symbol, active_orders[symbol], session_bybit)
    if use_binance:
        response, status = close_order_binance(symbol, active_orders[symbol], binance)

    if status == 200:
        del active_orders[symbol]
        trade_open = False

    return jsonify(response), status

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.json

    side = data.get('side')
    if side is None:
        return jsonify({
            "status": "error",
            "message": "The 'side' field is missing in the input data."
        }), 400

    if side in ['buy', 'sell']:
        return create_order(data)
    elif side in ['closeshort', 'closelong']:
        return close_order(data)
    else:
        return jsonify({
            "status": "error",
            "message": "The 'side' field must be either 'buy', 'sell', 'closeshort' or 'closelong'."
        }), 400

if __name__ == '__main__':
    app.run(port=5000)
