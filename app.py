import json
import os
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import time
import ccxt
from custom_http import HTTP

app = Flask(__name__)
CORS(app) 

# load config.json
with open('config.json') as config_file:
    config = json.load(config_file)

current_position = 'closed'
current_side = None

def is_exchange_enabled(exchange_name):
    return exchange_name in config['EXCHANGES'] and config['EXCHANGES'][exchange_name]['ENABLED']

def create_order_binance(data, exchange):
    symbol = data['symbol']
    order_type = data['type']
    side = data['side']
    quantity = data['quantity']

    if side == "closelong":
        side = "sell"
    elif side == "closeshort":
        side = "buy"

    if order_type == "market":
        order = exchange.create_market_order(symbol, side, quantity)
    elif order_type == "limit":
        price = data['price']
        order = exchange.create_limit_order(symbol, side, quantity, price)
    else:
        raise ValueError("Invalid order type")

    return order

def create_order_bybit(data, session):
    symbol = data['symbol']
    side = data['side']
    price = data.get('price', 0)
    quantity = data.get('quantity')

    if quantity is None:
        raise ValueError("The 'quantity' field is missing in the input data.")

    order = session.post('/v2/private/order/create', json={
        'symbol': symbol,
        'side': side,
        'order_type': data['type'],
        'qty': float(quantity),
        'price': price,
        'time_in_force': 'GTC'
    })
    return order.json()

def close_order_binance(data, exchange):
    symbol = data['symbol']
    side = data['side']
    price = data.get('price', 0)
    quantity = data.get('quantity')

    if side not in ['closelong', 'closeshort']:
        raise ValueError("Invalid side value for closing order. Use 'closelong' or 'closeshort'.")

    if quantity is None:
        raise ValueError("The 'quantity' field is missing in the input data.")

    order = exchange.create_order(
        symbol=symbol,
        type=data['type'],
        side='sell' if side == 'closelong' else 'buy',
        amount=float(quantity),
        price=price
    )
    return order

def close_order_bybit(data, session):
    symbol = data['symbol']
    side = data['side']
    price = data.get('price', 0)
    quantity = data.get('quantity')

    if side not in ['closelong', 'closeshort']:
        raise ValueError("Invalid side value for closing order. Use 'closelong' or 'closeshort'.")

    if quantity is None:
        raise ValueError("The 'quantity' field is missing in the input data.")

    order = session.post('/v2/private/order/create', json={
        'symbol': symbol,
        'side': 'sell' if side == 'closelong' else 'buy',
        'order_type': data['type'],
        'qty': float(quantity),
        'price': price,
        'time_in_force': 'GTC'
    })
    return order.json()

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

@app.route('/webhook', methods=['POST'])
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
                    if current_position == 'closed':
                        response = create_order_binance(data, exchange)
                        current_position = 'open'
                        current_side = data['side']
                    else:
                        raise ValueError("Cannot open a new order until the current one is closed.")
                elif data['side'] in ['closelong', 'closeshort']:
                    if current_position == 'open' and ((current_side == 'buy' and data['side'] == 'closelong') or (current_side == 'sell' and data['side'] == 'closeshort')):
                        response = close_order_binance(data, exchange)
                        current_position = 'closed'
                    else:
                        raise ValueError("Cannot close the order. Either there is no open order or the side of the closing order does not match the side of the open order.")
                else:
                    raise ValueError("Invalid side value. Use 'buy', 'sell', 'closelong' or 'closeshort'.")
                return {"status": "success", "data": response}, 200
            else:
                raise ValueError("Binance Futures is not enabled in the config file.")

        elif data['exchange'] == 'bybit':
            if use_bybit:
                if data['side'] in ['buy', 'sell']:
                    if current_position == 'closed':
                        response = create_order_bybit(data, session)
                        current_position = 'open'
                        current_side = data['side']
                    else:
                        raise ValueError("Cannot open a new order until the current one is closed.")
                elif data['side'] in ['closelong', 'closeshort']:
                    if current_position == 'open' and ((current_side == 'buy' and data['side'] == 'closelong') or (current_side == 'sell' and data['side'] == 'closeshort')):
                        response = close_order_bybit(data, session)
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

    except ValueError as e:
        return {"status": "error", "message": str(e)}, 400
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@socketio.on('request_balance_update')
def update_balance():
    # Get the balance from the exchanges
    balances = {}
    if use_bybit:
        bybit_balance = session.get('/v2/private/wallet/balance').json()
        balances['bybit'] = bybit_balance['result']
    if use_binance_futures:
        binance_balance = exchange.fetch_balance()
        balances['binance'] = binance_balance['total']
    emit('balance_update', balances, broadcast=True)


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    socketio.run(app)
