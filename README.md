# stocktock
본 프로젝트는 주식 트레이딩을 통한 이윤 추구를 목적으로 하며, 주식 트레이딩을 위한 여러가지 활동을 포함한다.

## 개발 환경 구축
- Install Python 3.8
- Install dependencies: `pip install -r requirements.txt`
- Mark ./stocktock as source root

## Prerequisites
- ./stocktock/.config.json 파일 작성

## Entry points
### backtest_runner.py
DB에 적재한 과거 히스토리컬 Finance 데이터를 기반으로 백테스트 실행

### creon_api_server.py
CREON+ API 통해 수집한 데이터를 Rest API로 제공하는 서버

### update_corp.py
기업 공시 채널 KIND 통해 종목 데이터 수집 및 업데이트

### update_db.py
모든 종목 분봉, 일봉 데이터 및 재무재표 정보를 수집하여 DB에 적재