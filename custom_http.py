import time
import hmac
import requests
from urllib.parse import urlencode

class HTTP:
    def __init__(self, api_key, secret):
        self.api_key = api_key
        self.secret = secret

    def get_signature(self, params):
        sorted_params = sorted(params.items(), key=lambda d: d[0], reverse=False)
        encode_params = urlencode(sorted_params)
        hashed = hmac.new(self.secret.encode('utf-8'), encode_params.encode('utf-8'), digestmod='sha256')
        return hashed.hexdigest()

    def get(self, path, params=None):
        if params is None:
            params = {}
        params['api_key'] = self.api_key
        params['timestamp'] = str(int(time.time() * 1000))
        params['sign'] = self.get_signature(params)
        url = 'https://api.bybit.com' + path + '?' + urlencode(params)
        return requests.get(url)

    def post(self, path, params=None):
        if params is None:
            params = {}
        params['api_key'] = self.api_key
        params['timestamp'] = str(int(time.time() * 1000))
        params['sign'] = self.get_signature(params)
        url = 'https://api.bybit.com' + path
        return requests.post(url, json=params)
