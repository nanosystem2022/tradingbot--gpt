import json
import os
from flask import Flask, render_template, request, jsonify
import time
import ccxt
from custom_http import HTTP

app = Flask(__name__)

# load config.json
with open('config.json') as config_file:
    config = json.load(config_file)

current_position = 'closed'
current_side = None

def is_exchange_enabled(exchange_name):
    return exchange_name in config['EXCHANGES'] and config['EXCHANGES'][exchange_name]['ENABLED']

def get_balance(exchange, symbol):
    balance = exchange.fetch_balance()
    return balance['total'][symbol.split('/')[1]]

def create_order_with_percentage(exchange, symbol, side, percentage, order_type='market', price=None):
    total_balance = get_balance(exchange, symbol.split('/')[1])
    quantity = total_balance * percentage / 100

    if order_type == 'market':
        order = exchange.create_market_order(symbol, side, quantity)
    elif order_type == 'limit' and price is not None:
        order = exchange.create_limit_order(symbol, side, quantity, price)
    else:
        raise ValueError("Invalid order type or price for limit order is missing")

    return order

def handle_error(e):
    return {"status": "error", "message": str(e)}, 400 if isinstance(e, ValueError) else 500

def can_open_order(current_position):
    return current_position == 'closed'

def can_close_order(current_position, current_side, side):
    return current_position == 'open' and ((current_side == 'buy' and side == 'closelong') or (current_side == 'sell' and side == 'closeshort'))

use_bybit = is_exchange_enabled('BYBIT')
use_binance_futures = is_exchange_enabled('BINANCE-FUTURES')
use_binance_spot = is_exchange_enabled('BINANCE-SPOT')

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

if use_binance_spot:
    print("Binance Spot is enabled!")
    exchange_spot = ccxt.binance({
        'apiKey': config['EXCHANGES']['BINANCE-SPOT']['API_KEY'],
        'secret': config['EXCHANGES']['BINANCE-SPOT']['API_SECRET'],
        'options': {
            'defaultType': 'spot',
        }
    })

@app.route('/webhook1', methods=['POST'])
def webhook():
    global current_position, current_side
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

    try:
        if data['exchange'] == 'binance-futures':
            if use_binance_futures:
                if data['side'] in ['buy', 'sell']:
                    if can_open_order(current_position):
                        # Here we use the new function and specify 50% of the balance
                        response = create_order_with_percentage(exchange, data['symbol'], data['side'], 50)
                        current_position = 'open'
                        current_side = data['side']
                    else:
                        raise ValueError("Cannot open a new order until the current one is closed.")
                elif data['side'] in ['closelong', 'closeshort']:
                    if can_close_order(current_position, current_side, data['side']):
                        # Here we use the new function and specify 100% of the balance to close the entire position
                        response = create_order_with_percentage(exchange, data['symbol'], 'sell' if data['side'] == 'closelong' else 'buy', 100)
                        current_position = 'closed'
                    else:
                        raise ValueError("Cannot close the order. Either there is no open order or the side of the closing order does not match the side of the open order.")
                else:
                    raise ValueError("Invalid side value. Use 'buy', 'sell', 'closelong' or 'closeshort'.")
                return {"status": "success", "data": response}, 200
            else:
                raise ValueError("Binance Futures is not enabled in the config file.")

        elif data['exchange'] == 'binance-spot':
            if use_binance_spot:
                if data['side'] in ['buy', 'sell']:
                    if can_open_order(current_position):
                        response = create_order_with_percentage(exchange_spot, data['symbol'], data['side'], 50)
                        current_position = 'open'
                        current_side = data['side']
                    else:
                        raise ValueError("Cannot open a new order until the current one is closed.")
                else:
                    raise ValueError("Invalid side value. Use 'buy' or 'sell'.")
                return {"status": "success", "data": response}, 200
            else:
                raise ValueError("Binance Spot is not enabled in the config file.")

        elif data['exchange'] == 'bybit':
            if use_bybit:
                if data['side'] in ['buy', 'sell']:
                    if can_open_order(current_position):
                        response = create_order_with_percentage(session, data['symbol'], data['side'], 50)
                        current_position = 'open'
                        current_side = data['side']
                    else:
                        raise ValueError("Cannot open a new order until the current one is closed.")
                elif data['side'] in ['closelong', 'closeshort']:
                    if can_close_order(current_position, current_side, data['side']):
                        response = create_order_with_percentage(session, data['symbol'], 'sell' if data['side'] == 'closelong' else 'buy', 100)
                        current_position = 'closed'
                    else:
                        raise ValueError("Cannot close the order. Either there is no open order or the side of the closing order does not match the side of the open order.")
                else:
                    raise ValueError("Invalid side value. Use 'buy', 'sell', 'closelong' or 'closeshort'.")
                return {"status": "success", "data": response}, 200
            else:
                raise ValueError("Bybit is not enabled in the config file.")

        else:
            raise ValueError("Unsupported exchange.")

    except Exception as e:
        return handle_error(e)


if __name__ == '__main__':
    app.run()
