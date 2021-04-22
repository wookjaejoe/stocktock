import os
import sys

basedir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(basedir, 'stocktock'))

import logging
from utils import log

log.init(logging.INFO)

from dateutil.parser import parse as parse_datetime
import flask_cors
import jsons
from flask import Flask, request, send_file
from werkzeug.serving import WSGIRequestHandler

from creon import stocks
from creon import charts
from creon.exceptions import CreonError
from creon.connection import connector as creon_connector
from datetime import date, timedelta
from dataclasses import dataclass
from simstock import BreakAbove5MaEventSimulator

# set protocol HTTP/1.1
WSGIRequestHandler.protocol_version = "HTTP/1.1"
app = Flask(__name__)
flask_cors.CORS(app)


class HttpError(IOError):
    def __init__(self, status_code, msg):
        self.url = request.url
        self.status_code = status_code
        self.msg = msg

    def __str__(self):
        return self.msg


class BadRequestError(HttpError):
    def __init__(self, msg):
        super(BadRequestError, self).__init__(400, msg)


def check_required(*param_names):
    for param_name in param_names:
        if param_name not in request.args:
            raise HttpError(400, f'The required parameter \'{param_name}\' not exists.')


@app.after_request
def append_common_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = '*'
    response.headers['Access-Control-Allow-Headers'] = '*'
    response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
    return response


@app.errorhandler(HttpError)
def handle_http_erorr(e: HttpError):
    return str(e), e.status_code


@app.errorhandler(CreonError)
def handle_creon_error(e: CreonError):
    creon_connector.connect()
    return str(e), 500


@app.errorhandler(Exception)
def handle_exception(e: Exception):
    logging.error(str(e), exc_info=e)
    return str(e), 500


def asjson(value):
    return jsons.dumps(value,
                       jdkwargs={'indent': 2, 'ensure_ascii': False})


@app.route('/')
def root_path():
    return 'Hello'


@app.route('/favicon.ico')
def favicon():
    return send_file('favicon.ico')


available_codes = stocks.get_availables()


@app.route('/stocks')
def get_stocks():
    def is_active(code: str):
        return code in available_codes

    return asjson([{'code': stock.code[-6:], 'name': stock.name, 'active': is_active(code=stock.code)}
                   for stock in stocks.ALL_STOCKS])


@app.route('/charts')
def get_charts():
    check_required('code', 'chart_type', 'begin', 'end')

    # 종목 코드
    code = request.args.get('code')

    # 봉 타입
    chart_type = charts.ChartType.create_by_name(request.args.get('chart_type'))
    if not chart_type:
        raise BadRequestError('Not supported chart_type: ' + request.args.get('chart_type'))

    # 기간 - 시작
    begin = parse_datetime(request.args.get('begin')).date()

    # 기간 - 종료
    end = parse_datetime(request.args.get('end')).date()

    max_period = timedelta(days=10)
    if chart_type == charts.ChartType.MINUTE and end - begin > max_period:
        raise BadRequestError(
            f'The duration of the minute chart cannot exceed {max_period.days} days.: {(end - begin).days} days')

    return asjson(charts.request_by_term(code=code,
                                         chart_type=chart_type,
                                         begin=begin,
                                         end=end))


@app.route('/metrics')
def get_metrics():
    code = request.args.get('code')
    begin: date = parse_datetime(request.args.get('begin')).date()
    end: date = parse_datetime(request.args.get('end')).date()

    candles = charts.request_by_term(
        code=code,
        chart_type=charts.ChartType.DAY,
        begin=begin - timedelta(days=300),
        end=end
    )

    def ma(at: date, length: int):
        closes = [candle.close for candle in candles if candle.date <= at][-length:]
        if len(closes) != length:
            return None

        return int(sum(closes) / length)

    result = []
    cur = begin
    while True:
        if cur > end:
            break

        result.append({
            'date': cur,
            'moving_average': {
                '120': ma(cur, 120),
                '60': ma(cur, 60),
                '20': ma(cur, 20),
                '5': ma(cur, 5)
            }
        })

        cur += timedelta(days=1)

    return asjson(result)


@dataclass
class PostSimulationsBody:
    code: str
    begin: date
    end: date
    earning_line: int
    stop_line: int
    strategy: str


@app.route('/simulations', methods=['POST'])
def post_simulations():
    body: PostSimulationsBody = jsons.loads(request.data.decode('utf-8'), PostSimulationsBody)
    simulator = BreakAbove5MaEventSimulator(
        code=body.code,
        begin=body.begin,
        end=body.end,
        earning_line=body.earning_line,
        stop_line=body.stop_line
    )
    return asjson(simulator.start())


if __name__ == '__main__':
    app.run(host='0.0.0.0',
            port=20000)
