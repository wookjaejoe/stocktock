import ctypes
import os
import time
from datetime import date, timedelta

import win32com.client
from pywinauto import application

from creon import stocks, charts


def _start_client(exe_path, _id, pw, cert_pw):
    """
    크레온 플러스 실행
    """
    app = application.Application()
    app.start(f'{exe_path} /prj:cp /id:{_id} /pwd:{pw} /pwdcert:{cert_pw} /autostart')


def _kill_client():
    """
    코레온 플러스 종료
    """
    os.system('taskkill /IM coStarter* /F /T')
    os.system('taskkill /IM CpStart* /F /T')
    os.system('taskkill /IM DibServer* /F /T')
    os.system('wmic process where "name like \'%coStarter%\'" call terminate')
    os.system('wmic process where "name like \'%CpStart%\'" call terminate')
    os.system('wmic process where "name like \'%DibServer%\'" call terminate')


def _disconnect():
    """
    CYBOS 연결 해제
    """
    cybos = win32com.client.Dispatch('CpUtil.CpCybos')
    if cybos.IsConnect:
        cybos.PlusDisconnect()


def connect():
    """
    CYBOS 연결(CYBOS: 크레온플러스 옛날 이름인듯)
    """
    cybos = win32com.client.Dispatch('CpUtil.CpCybos')
    if not cybos.IsConnect:
        _disconnect()
        _kill_client()
        _start_client(...)  # fixme: 인자 입력

    for _ in range(300):
        if cybos.IsConnect:
            return
        else:
            time.sleep(1)

    raise RuntimeError('Auto-startup failure')


def main():
    cybos = win32com.client.Dispatch('CpUtil.CpCybos')  # 크레온에서 씨발놈들아 'CpUtil.CpCybos' 이거다
    assert cybos.IsConnect, 'Disconnected'
    assert ctypes.windll.shell32.IsUserAnAdmin(), 'Not administrator'
    connect()

    # 모든 종목 코드 가져오기
    all_codes = [stock.code for stock in stocks.ALL_STOCKS]

    # 모든 종목에 대한 상세 정보 가져오기
    details = stocks.get_details(all_codes)

    x = []
    # 차트 데이터 가져오기
    for code in all_codes:
        chart = charts.request_by_term(
            code=code,
            chart_type=charts.ChartType.MINUTE,
            begin=date.today() - timedelta(days=1),
            end=date.today()
        )

        db.push(chart)

    print()


if __name__ == '__main__':
    main()
