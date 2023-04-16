This is a tradingview webhook  designed to be free & open source.  This bot is written using Python & Flask and is designed to run a free heroku server. It will allow you to create custom alerts in tradingview and send them to your own private webhook server that can place trades on your account via the api.

    در ابتدای کد، کتابخانه‌های لازم برای پروژه (ccxt, Flask, json) وارد شده‌اند.
    اطلاعات از فایل config.json خوانده می‌شوند که شامل API کلیدها و تنظیمات برای صرافی‌های مورد استفاده است.
    برای هر صرافی فعال در تنظیمات config.json، یک نمونه ccxt ایجاد می‌شود که برای ارسال درخواست‌ها به صرافی استفاده می‌شود.
    تابع execute_trade ساخته شده است که مسئول انجام معاملات بر اساس اطلاعات دریافتی از وب‌هوک است.
    یک برنامه Flask ایجاد شده است با یک مسیر (route) به نام /webhook که به روش POST پاسخ می‌دهد.
    در مسیر /webhook، داده‌های JSON دریافت شده از وب‌هوک تجزیه می‌شوند و عملیات مربوط به باز/بستن معاملات انجام می‌شود.
    بسته به دستورات دریافتی از وب‌هوک، تابع execute_trade با پارامترهای مورد نیاز فراخوانی می‌شود و معاملات انجام می‌پذیرند.

کد نهایی یک ربات معاملاتی است که بر اساس اطلاعات دریافتی از وب‌هوک TradingView، معاملات باز و بسته می‌کند. این ربات قادر است برای صرافی‌های مختلف کار کند (مانند Binance Futures و Bybit)، به شرطی که آن‌ها در تنظیمات config.json فعال شوند.

برای اجرای برنامه در محیط محلی، از دستور python app.py استفاده می‌کنید و برای استفاده از آن در سرویس‌های میزبانی مانند Heroku و Render، از Gunicorn به عنوان سرور WSGI استفاده می‌شود.



# TradingView Alerts Format 

```
{
	"key": "678777",
	"exchange": "bybit",
	"symbol": "ETHUSD",
	"type": "Market",
	"side": "Buy",
	"qty": "1",
	"price": "1120",
	"close_position": "False",
	"cancel_orders": "True",
	"order_mode": "Both",
	"take_profit_percent": "1",
	"stop_loss_percent": "0.5"
}
```

برای بستن معاملات باز با استفاده از دستورهای close-long یا close-short، باید هشدارهای (alerts) TradingView را به شکل زیر تنظیم کنید:

برای بستن یک معامله‌ی long:

json

{
  "type": "close-long",
  "symbol": "{{ticker}}",
  "exchange": "BINANCE-FUTURES",
  "market": "{{strategy.market}}",
  "price": "{{strategy.order.price}}"
}

برای بستن یک معامله‌ی short:

json

{
  "type": "close-short",
  "symbol": "{{ticker}}",
  "exchange": "BINANCE-FUTURES",
  "market": "{{strategy.market}}",
  "price": "{{strategy.order.price}}"
}

در هر دو مورد، تغییرات عمده‌ای نسبت به قالب اصلی ایجاد نشده است. تنها تفاوت در فیلد type است که به close-long یا close-short تغییر کرده است. با استفاده از این الگوها، می‌توانید هشدارهایی ایجاد کنید که به ربات اطلاع دهند تا معاملات باز را ببندند.

مطمئن شوید که آدرس وب‌هوک ربات را در تنظیمات هشدارهای TradingView وارد کرده‌اید (مانند http://127.0.0.1:5000/webhook برای اجرای محلی یا آدرسی که در سرویس میزبانی مانند Heroku یا Render برای شما ایجاد شده است).


---
| Constant |Settings Keys  |
|--|--|
|key| unique key that protects your webhook server|
|exchange | bybit, binacne-futures |
|symbol | Exchange Specific ** See Below for more |
|side|Buy or Sell		|
|type | Market or Limit		|
|order_mode| Both(Stop Loss & Take Profit Orders Used), Profit ( Omly Take Profit Orders), Stop (Only Stop Loss orders)|
|qty| amount of base currency to buy 		|
|price|  ticker in quote currency		|
|close_position| True or False 		|
|cancel_orders|True or False 		|
|take_profit_percent| any float	 (0.5)	|
|stop_loss_Percent	 |and float (0.5)		|


#### ** SYMBOLS
| EXCHANGE | SYMBOL EXAMPLE |
|--|--|
|BYBIT INVERSE| BTCUSD|
|BYBIT PERP | BTCUSDT|
|Binance Futures | BTC/USDT|
