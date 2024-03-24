# Stocktock
한국 상장 종목들의 차트 데이터를 이용한 단기 매매를 통해 수익률 향상을 기대할 수 있을지 알아보자.

## Features
- 대신증권 CREON API 통한 주가 데이터 수집
- 가격 지표를 이용한 매매 시그널 분석
- 백테스트 및 실시간 트레이딩

## Getting started
- Install Python 3.8
- Install dependencies: `pip install -r requirements.txt`
- Mark ./stocktock as source root

## Entry points
- `backtest_runner.py` DB에 적재한 과거 히스토리컬 Finance 데이터를 기반으로 백테스트 실행
- `creon_api_server.py` CREON+ API 통해 수집한 데이터를 Rest API로 제공하는 서버
- `update_corp.py` 기업 공시 채널 KIND 통해 종목 데이터 수집 및 업데이트
- `update_db.py` 모든 종목 분봉, 일봉 데이터 및 재무재표 정보를 수집하여 DB에 적재