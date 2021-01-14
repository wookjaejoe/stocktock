import win32com.client

cybos = win32com.client.Dispatch("CpUtil.CpCybos")
codemgr = win32com.client.Dispatch("CpUtil.CpCodeMgr")
stockmst = win32com.client.Dispatch("DsCbo1.StockMst")
stockchart = win32com.client.Dispatch("CpSysDib.StockChart")
cpmarketwatch = win32com.client.Dispatch("CpSysDib.CpMarketWatch")  # 특징주 포착 조회 서비스
cpmarketwatchs = win32com.client.Dispatch("CpSysDib.CpMarketWatchs")  # 실시간 차트/외국인 신호 수신
cpcodemgr = win32com.client.Dispatch('CpUtil.CpCodeMgr')
cptdutil = win32com.client.Dispatch('CpTrade.CpTdUtil')


def new_stockcur():
    return win32com.client.Dispatch("DsCbo1.StockCur")
