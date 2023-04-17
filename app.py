import json
from flask import Flask, request
import ccxt
from binanceFutures import handle_binance_request
from bybit_handler import handle_bybit_request

app = Flask(__name__)

# load config.json
with open('config.json') as config_file:
    config = json.load(config_file)

use_bybit = config['EXCHANGES']['BYBIT']['ENABLED']
if use_bybit:
    session = HTTP(
        endpoint='https://api.bybit.com',
        api_key=config['EXCHANGES']['BYBIT']['API_KEY'],
        api_secret=config['EXCHANGES']['BYBIT']['API_SECRET']
    )

use_binance_futures = config['EXCHANGES']['BINANCE-FUTURES']['ENABLED']
if use_binance_futures:
    exchange = ccxt.binance({
        'apiKey': config['EXCHANGES']['BINANCE-FUTURES']['API_KEY'],
        'secret': config['EXCHANGES']['BINANCE-FUTURES']['API_SECRET'],
        'options': {
            'defaultType': 'future',
        },
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
        print("Invalid Key, Please Try Again!")
        return {
            "status": "error",
            "message": "Invalid Key, Please Try Again!"
        }

    if data['exchange'] == 'bybit':
        if use_bybit:
            handle_bybit_request(session, data)
            return {
                "status": "success",
                "message": "Bybit Webhook Received!"
            }
        else:
            return {
                "status": "error",
                "message": "Bybit is not enabled in the configuration."
            }

    if data['exchange'] == 'binance-futures':
        if use_binance_futures:
            handle_binance_request(exchange, data)
            return {
                "status": "success",
                "message": "Binance Futures Webhook Received!"
            }
        else:
            return {
                "status": "error",
                "message": "Binance Futures is not enabled in the configuration."
            }

    else:
        print("Invalid Exchange, Please Try Again!")
        return {
            "status": "error",
            "message": "Invalid Exchange, Please Try Again!"
        }

if __name__ == '__main__':
    app.run(debug=False)
