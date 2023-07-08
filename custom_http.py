import hmac
import time
import os
from requests import Session

class HTTP(Session):
    def __init__(self, endpoint):
        super().__init__()
        self.endpoint = endpoint
        self.api_key = os.getenv('API_KEY')
        self.api_secret = os.getenv('API_SECRET')

    def request(self, method, path, *args, **kwargs):
        url = self.endpoint + path

        # Sign the request if needed
        if self.api_key and self.api_secret:
            timestamp = int(time.time() * 1000)
            kwargs['headers'] = kwargs.get('headers', {})
            kwargs['headers'].update({
                'api-key': self.api_key,
                'api-expires': str(timestamp + 5000),
            })

            # Create signature
            signature_payload = f"{method}\n{path}\n{timestamp}"
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                signature_payload.encode('utf-8'),
                digestmod='sha256'
            ).hexdigest()

            kwargs['headers']['api-signature'] = signature

        return super().request(method, url, *args, **kwargs)
