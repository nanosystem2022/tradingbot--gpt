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

class OrderManager:
    def __init__(self):
        self.current_position = 'closed'
        self.current_side = None

    def can_open_order(self):
        return self.current_position == 'closed'

    def can_close_order(self, side):
        return self.current_position == 'open' and ((self.current_side == 'buy' and side == 'closelong') or (self.current_side == 'sell' and side == 'closeshort'))

order_manager = OrderManager()

class ErrorHandler:
    @staticmethod
    def handle_error(e):
        return {"status": "error", "message": str(e)}, 400 if isinstance(e, ValueError) else 500

error_handler = ErrorHandler()

class ExchangeManager:
    def __init__(self, config):
        self.config = config
        self.use_bybit = self.is_exchange_enabled('BYBIT')
        self.use_binance_futures = self.is_exchange_enabled('BINANCE-FUTURES')
        self.use_binance_spot = self.is_exchange_enabled('BINANCE-SPOT')

        if self.use_bybit:
            print("Bybit is enabled!")
            self.session = HTTP(
                endpoint='https://api.bybit.com',
                api_key=self.config['EXCHANGES']['BYBIT']['API_KEY'],
                api_secret=self.config['EXCHANGES']['BYBIT']['API_SECRET']
            )

        if self.use_binance_futures:
            print("Binance is enabled!")
            self.exchange = ccxt.binance({
                'apiKey': self.config['EXCHANGES']['BINANCE-FUTURES']['API_KEY'],
                'secret': self.config['EXCHANGES']['BINANCE-FUTURES']['API_SECRET'],
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

            if self.config['EXCHANGES']['BINANCE-FUTURES']['TESTNET']:
                self.exchange.set_sandbox_mode(True)

        if self.use_binance_spot:
            print("Binance Spot is enabled!")
            self.exchange_spot = ccxt.binance({
                'apiKey': self.config['EXCHANGES']['BINANCE-SPOT']['API_KEY'],
                'secret': self.config['EXCHANGES']['BINANCE-SPOT']['API_SECRET'],
                'options': {
                    'defaultType': 'spot',
                }
            })

    def is_exchange_enabled(self, exchange_name):
        return exchange_name in self.config['EXCHANGES'] and self.config['EXCHANGES'][exchange_name]['ENABLED']

exchange_manager = ExchangeManager(config)

@app.route('/webhook1', methods=['POST'])
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

    try:
        if data['exchange'] == 'binance-futures':
            if exchange_manager.use_binance_futures:
                if data['side'] in ['buy', 'sell']:
                    if order_manager.can_open_order():
                        response = create_order(data, exchange_manager.exchange)
                        order_manager.current_position = 'open'
                        order_manager.current_side = data['side']
                    else:
                        raise ValueError("Cannot open a new order until the current one is closed.")
                elif data['side'] in ['closelong', 'closeshort']:
                    if order_manager.can_close_order(data['side']):
                        response = close_order(data, exchange_manager.exchange)
                        order_manager.current_position = 'closed'
                    else:
                        raise ValueError("Cannot close the order. Either there is no open order or the side of the closing order does not match the side of the open order.")
                else:
                    raise ValueError("Invalid side value. Use 'buy', 'sell', 'closelong' or 'closeshort'.")
                return {"status": "success", "data": response}, 200
            else:
                raise ValueError("Binance Futures is not enabled in the config file.")

        elif data['exchange'] == 'binance-spot':
            if exchange_manager.use_binance_spot:
                if data['side'] in ['buy', 'sell']:
                    if order_manager.can_open_order():
                        response = create_order(data, exchange_manager.exchange_spot)
                        order_manager.current_position = 'open'
                        order_manager.current_side = data['side']
                    else:
                        raise ValueError("Cannot open a new order until the current one is closed.")
                else:
                    raise ValueError("Invalid side value. Use 'buy' or 'sell'.")
                return {"status": "success", "data": response}, 200
            else:
                raise ValueError("Binance Spot is not enabled in the config file.")

        elif data['exchange'] == 'bybit':
            if exchange_manager.use_bybit:
                if data['side'] in ['buy', 'sell']:
                    if order_manager.can_open_order():
                        response = create_order_bybit(data, exchange_manager.session)
                        order_manager.current_position = 'open'
                        order_manager.current_side = data['side']
                    else:
                        raise ValueError("Cannot open a new order until the current one is closed.")
                elif data['side'] in ['closelong', 'closeshort']:
                    if order_manager.can_close_order(data['side']):
                        response = close_order_bybit(data, exchange_manager.session)
                        order_manager.current_position = 'closed'
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
        return error_handler.handle_error(e)

if __name__ == '__main__':
    app.run()
