from .com import *
from typing import *
CATEGORIES = {
    "1": "종목뉴스",
    "2": "공시정보",
    "10": "외국계 증권사 창구 첫 매수",
    "11": "외국계 증권사 창구 첫 매도",
    "12": "외국인 순매수",
    "13": "외국인 순매도",
    "21": "전일 거래량 갱신",
    "22": "최근5일 거래량최고 갱신",
    "23": "최근5일 매물대 돌파",
    "24": "최근60일 매물대 돌파",
    "28": "최근5일 첫 상한가",
    "29": "최근5일 신고가 갱신",
    "30": "최근5일 신저가 갱신",
    "31": "상한가 직전",
    "32": "하한가 직전",
    "41": "주가 5MA 상향 돌파",
    "42": "주가 5MA 하향 돌파",
    "43": "거래량 5MA 상향 돌파",
    "44": "주가 데드크로스(5MA < 20MA)",
    "45": "주가 골든크로스(5MA > 20MA)",
    "46": "MACD 매수-Signal(9) 상향돌파",
    "47": "MACD 매도-Signal(9) 하향돌파",
    "48": "CCI 매수-기준선(-100) 상향돌파",
    "49": "CCI 매도-기준선(100) 하향돌파",
    "50": "Stochastic(10,5,5)매수- 기준선 상향돌파",
    "51": "Stochastic(10,5,5)매도- 기준선 하향돌파",
    "52": "Stochastic(10,5,5)매수- %K%D 교차",
    "53": "Stochastic(10,5,5)매도- %K%D 교차",
    "54": "Sonar 매수-Signal(9) 상향돌파",
    "55": "Sonar 매도-Signal(9) 하향돌파",
    "56": "Momentum 매수-기준선(100) 상향돌파",
    "57": "Momentum 매도-기준선(100) 하향돌파",
    "58": "RSI(14) 매수-Signal(9) 상향돌파",
    "59": "RSI(14) 매도-Signal(9) 하향돌파",
    "60": "Volume Oscillator 매수-Signal(9) 상향돌파",
    "61": "Volume Oscillator 매도-Signal(9) 하향돌파",
    "62": "Price roc 매수-Signal(9) 상향돌파",
    "63": "Price roc 매도-Signal(9) 하향돌파",
    "64": "일목균형표 매수-전환선 > 기준선 상향교차",
    "65": "일목균형표 매도-전환선 < 기준선 하향교차",
    "66": "일목균형표 매수-주가가 선행스팬 상향돌파",
    "67": "일목균형표 매도-주가가 선행스팬 하향돌파",
    "68": "삼선전환도-양전환",
    "69": "삼선전환도-음전환",
    "70": "캔들패턴-상승반전형",
    "71": "캔들패턴-하락반전형",
    "81": "단기급락 후 5MA 상향돌파",
    "82": "주가 이동평균밀집-5%이내",
    "83": "눌림목 재 상승-20MA 지지"
}


# def request(arguments: Dict[int, Any]) -> List[Dict[str, Any]]:
#     for idx, value in arguments.items():
#         stockchart.SetInputValue(idx, value)
#
#     stockchart.BlockRequest()
#
#     result = []
#     output_names = stockchart.GetHeaderValue(2)  # 데이터 필드명
#     output_length = stockchart.GetHeaderValue(2)  # 수신 개수
#     for i in range(output_length):
#         result.append({output_names[j]: stockchart.GetDataValue(j, i) for j in range(len(output_names))})
#
#     return result

def request(code='*'):
    cpmarketwatch.SetInputValue(0, '*')  # 종목코드(string): 요청하는 종목코드. Default("*") - 전종목
    """
    1 - 수신항목구분목록(string):
    구분자 ','로 나열한 수신항목의 목록
    (ex) 1,2 -> 종목뉴와와 공시정보 요청
    Default("*") - 모든항목
    """
    cpmarketwatch.SetInputValue(1, code)
    cpmarketwatch.SetInputValue(2, 0)  # 시작시간(ushort): 요청 시작시간. Default(0) - 처음부터
    cpmarketwatch.BlockRequest()

    signal_codes = cpmarketwatch.GetHeaderValue(0)  # 수신항목구분목록(string)
    signal_codes = signal_codes.split(',')
    start_time = cpmarketwatch.GetHeaderValue(1)  # 시작시간(short)
    count = cpmarketwatch.GetHeaderValue(2)  # 수신개수(short)

    for i in range(count):
        time = cpmarketwatch.GetDataValue(0, i)  # 0 - 시간(ushort)
        stock_code = cpmarketwatch.GetDataValue(1, i)  # 1 - 종목코드(string)
        stock_name = cpmarketwatch.GetDataValue(2, i)  # 2 - 종목명(string)
        category = cpmarketwatch.GetDataValue(3, i)  # 3 - 항목구분(ushort)
        contents = cpmarketwatch.GetDataValue(4, i)  # 4 - 내용(string)
        print(time, stock_code, stock_name, category, contents)

    print()
