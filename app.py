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

# ... rest of the code ...
