# noinspection SpellCheckingInspection
__author__ = 'wookjae.jo'

import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

from indexes import InterestIndexes
from .backtest import *
from .common import *


class XlsxExporter:

    def __init__(self, backtest: Backtest, target_path):
        self.backtest = backtest
        self.workbook = openpyxl.Workbook()
        self.target_path = target_path

    @classmethod
    def load_from(cls, pickle_or_json: str):
        if pickle_or_json.endswith('.pickle'):
            with open(pickle_or_json, 'rb') as f:
                backteset = pickle.load(f)
        elif pickle_or_json.endswith('.json'):
            with open(pickle_or_json, 'r', encoding='utf-8') as f:
                backteset = pickle.load(f)
        else:
            raise RuntimeError(f'Not supported file extension: {pickle_or_json}')

        target_dir = os.path.abspath(os.path.join(os.path.abspath(pickle_or_json), os.path.pardir))
        return XlsxExporter(
            backtest=backteset,
            target_path=os.path.join(target_dir, f'Result-{os.path.basename(target_dir)}.xlsx')
        )

    def create_table_sheet(self, title, headers: List, rows: List[List], index=None):
        sheet = self.workbook.create_sheet(title=title, index=index)
        font_header = Font(name='맑은 고딕', bold=True, color='ffffad')
        align_header = Alignment(horizontal='center')
        fill_header = PatternFill('solid', '4a4a4a')

        row_pos = 1
        for i in range(len(headers)):
            cell = sheet.cell(row_pos, i + 1, headers[i])
            cell.font = font_header
            cell.alignment = align_header
            cell.fill = fill_header

        row_pos += 1
        font_row = Font(name='맑은 고딕')
        for i in range(len(rows)):
            for j in range(len(rows[i])):
                cell = sheet.cell(row_pos + i, j + 1, rows[i][j])
                cell.font = font_row

        column_widths = []
        for row in sheet.rows:
            for i, cell in enumerate(row):
                width = 0
                for c in str(cell.value):
                    if ord(c) > 255:
                        width += 2.5
                    else:
                        width += 1.5

                if len(column_widths) > i:
                    if width > column_widths[i]:
                        column_widths[i] = width
                else:
                    column_widths.append(width)

        for i, column_width in enumerate(column_widths):
            sheet.column_dimensions[get_column_letter(i + 1)].width = column_width

    def export(self):
        for sheet_name in self.workbook.sheetnames:
            self.workbook.remove(self.workbook[sheet_name])

        indexes = InterestIndexes.load(fromdate=self.backtest.begin, todate=self.backtest.end)

        def total_eval(_daily_log: DailyLog):
            return _daily_log.deposit + _daily_log.holding_eval

        ########## ranking ##########
        events_by_code: [str, List[BacktestEvent]] = {}
        for event in self.backtest.events:
            if event.code not in events_by_code:
                events_by_code.update({event.code: []})

            events_by_code.get(event.code).append(event)

        revenues_by_code = {}
        for code in events_by_code:
            events: List[BacktestEvent] = events_by_code.get(code)
            revenue = 0
            for event in events:
                if event.type == BacktestEventType.BUY:
                    revenue -= event.price * event.count
                elif event.type == BacktestEventType.SELL:
                    revenue += event.price * event.count
                else:
                    RuntimeError('WTF')

            revenues_by_code.update({code: revenue})

        rows = []
        fl_map = get_fl_map(list(revenues_by_code.keys()), self.backtest.begin, self.backtest.end)
        for code in revenues_by_code:
            revenue = revenues_by_code.get(code)
            first, last = fl_map.get(code)
            revenue_rate = round(revenue / self.backtest.limit_buy_amount * 100, 2)
            margin_rate = round((last - first) / first * 100, 2)
            row = [
                code, get_name(code),
                revenue_rate,
                first,
                last,
                margin_rate,
                revenue_rate - margin_rate
            ]
            rows.append(row)

        # 수익금으로 정렬
        rows.sort(key=lambda x: x[-1], reverse=True)
        self.create_table_sheet('ranking', headers=['종목코드', '종목명', '수익율(%)', '시작가', '종료가', '변동율(%)', '수익율-변동율(%)'],
                                rows=rows, index=2)

        ########## events ##########
        headers = [
            '일시', '구분', '종목코드', '종목명', '가격',
            '수량', '주문총액', '비고',
            '수익율(%)'
        ]
        rows = [[
            evt.when, evt.type.name, evt.code, get_name(evt.code), evt.price,
            evt.count, evt.price * evt.count, evt.description,
            round((evt.price - evt.bought_event.price) / evt.bought_event.price * 100, 2)
            if isinstance(evt, BacktestSellEvent) else ''
        ] for evt in self.backtest.events]
        self.create_table_sheet('events', headers=headers, rows=rows, index=2)

        ########## daily ##########
        headers = [
            '날짜', '예수금', '보유 종목 평가금액', '총 평가금액',
            '전일대비(%)', '비고',
            '코스피', '코스피 전일대비(%)',
            '코스닥', '코스피 전일대비(%)',
            'KRX 300', 'KRX 300(%)'
        ]

        rows = []
        for i in range(len(self.backtest.daily_logs)):
            dl = self.backtest.daily_logs[i]
            if i > 0:
                dl_prv = self.backtest.daily_logs[i - 1]
                margin = (total_eval(dl) - total_eval(dl_prv)) / total_eval(dl_prv) * 100
            else:
                margin = (total_eval(dl) - self.backtest.initial_deposit) / self.backtest.initial_deposit * 100

            try:
                kospi = indexes.kospi.data.get(dl.date).close
                kosdaq = indexes.kosdaq.data.get(dl.date).close
                krx_300 = indexes.krx_300.data.get(dl.date).close

                kospi_bf = indexes.kospi.data.get(dl.date - timedelta(days=1)).close
                kosdaq_bf = indexes.kosdaq.data.get(dl.date - timedelta(days=1)).close
                krx_300_bf = indexes.krx_300.data.get(dl.date - timedelta(days=1)).close

                rows.append([
                    dl.date, round(dl.deposit), round(dl.holding_eval), round(total_eval(dl)),
                    round(margin, 2), dl.description,
                    kospi, round((kospi - kospi_bf) / kospi_bf * 100, 2),
                    kosdaq, round((kosdaq - kosdaq_bf) / kosdaq_bf * 100, 2),
                    krx_300, round((krx_300 - krx_300_bf) / krx_300_bf * 100, 1)
                ])
            except:
                pass

        self.create_table_sheet('daily', headers=headers, rows=rows, index=1)

        fl_map = get_fl_map(
            codes=[stock.code for stock in stocks],
            begin=self.backtest.begin,
            end=self.backtest.end
        )

        ########## summary ##########
        headers = [
            '시작일', '종료일', '구동시간(sec)', '최초 예수금',
            '익절라인(%)', '손절라인(%)', '매매 수수료(%)', '매도 세금(%)',
            '수익금',
            '수익율(%)',
            '취급 종목 평균 변동율(%)',
            '코스피 증감율(%)', '코스닥 증감율(%)', 'KRX 300 증감율(%)'
        ]

        margin_percentage_list = []
        for code in fl_map:
            first, last = fl_map.get(code)
            margin_percentage_list.append(((last - first) / first) * 100)

        kospi_f = list(indexes.kospi.data.values())[0].close
        kospi_l = list(indexes.kospi.data.values())[-1].close
        kospi_margin = (kospi_l - kospi_f) / kospi_f * 100

        kosdaq_f = list(indexes.kosdaq.data.values())[0].close
        kosdaq_l = list(indexes.kosdaq.data.values())[-1].close
        kosdaq_margin = (kosdaq_l - kosdaq_f) / kospi_f * 100

        krx_300_f = list(indexes.krx_300.data.values())[0].close
        krx_300_l = list(indexes.krx_300.data.values())[-1].close
        krx_300_margin = (krx_300_l - krx_300_f) / krx_300_f * 100

        final_eval = total_eval(self.backtest.daily_logs[-1])
        rows = [[
            self.backtest.begin, self.backtest.end, (self.backtest.finish_time - self.backtest.start_time).seconds,
            self.backtest.initial_deposit,
            self.backtest.earn_line, self.backtest.stop_line, self.backtest.fee_percent, self.backtest.tax_percent,
            round(final_eval - self.backtest.initial_deposit),
            round((final_eval - self.backtest.initial_deposit) / self.backtest.initial_deposit * 100, 2),
            round(sum(margin_percentage_list) / len(margin_percentage_list), 2),
            round(kospi_margin, 2), round(kosdaq_margin, 2), round(krx_300_margin, 2)
        ]]
        self.create_table_sheet('summary', headers=headers, rows=rows, index=0)
        logging.info(f'Saving workbook in {self.target_path}')
        self.workbook.save(self.target_path)
