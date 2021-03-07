import logging
from datetime import date

import flask_cors
import jsons
from flask import *
from werkzeug.serving import WSGIRequestHandler

from creon import stocks
from simstock import BreakAbove5MaEventSimulator

# set protocol HTTP/1.1
WSGIRequestHandler.protocol_version = "HTTP/1.1"
app = Flask(__name__)
flask_cors.CORS(app)


@app.after_request
def append_common_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = '*'
    response.headers['Access-Control-Allow-Headers'] = '*'
    response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
    return response


@app.errorhandler(Exception)
def handle_exception(e):
    logging.error('An error occurred.', e)
    return str(e), 500 if not hasattr(e, 'code') else e.code


@app.route('/')
def home():
    return 'Hello, World!'


@app.route('/stocks')
def get_stocks():
    return jsons.dumpb([{'code': stock.code[-6:], 'name': stock.name} for stock in stocks.ALL_STOCKS if
                        stocks.get_capital_type(stock.code) == 1][-10:], encoding='utf-8')


@app.route('/charts')
def get_charts():
    pass


@app.route('/simulations', methods=['GET', 'POST'])
def simulate():
    begin = date(2021, 1, 1)
    end = date(2021, 2, 28)
    result = BreakAbove5MaEventSimulator(stocks.find('005930').code,
                                         begin=begin,
                                         end=end).start()
    return jsons.dumps(result)


if __name__ == '__main__':
    app.run(host='0.0.0.0',
            port=10000,
            debug=True)
