# Cursor Playground

다양한 Python 프로젝트와 실습 코드 모음입니다.

## 프로젝트 구조

### 1. HRD-Net API
- HRD-Net API를 활용한 훈련 과정 정보 수집
- 시작/종료 날짜를 입력하여 자동으로 페이지네이션 처리
- Excel 파일로 결과 저장

### 2. Wanted 크롤링
- 원티드 채용 공고 크롤링
- Selenium을 사용한 동적 페이지 처리
- 리스트 정보와 상세 페이지 정보 수집
- Excel 파일로 결과 저장

파일:
- `wanted_crawl.py`: 기본 버전
- `wanted_crawl_1124_fast.py`: 최적화 버전 (리스트 먼저 수집 후 상세 정보 수집)
- `wanted_crawl_1124_slow.py`: 순차 처리 버전

### 3. API 테스트
- OpenAI API 테스트 도구
- 텍스트 생성 (GPT 모델)
- 이미지 생성 (DALL-E 모델)
- 환경 변수를 통한 API 키 관리

### 4. Django 프로젝트 (hello_site)
- Django 기본 프로젝트
- greetings 앱

### 5. 기타
- `calculator.py`: 계산기 예제
- `test_calculator.py`: 계산기 테스트
- `hello.py`: Hello World 예제

## 설치 및 실행

### 필요한 라이브러리
```bash
pip install requests openpyxl selenium pandas beautifulsoup4 lxml python-dotenv openai
```

### 환경 변수 설정
`config.env` 파일을 생성하고 API 키를 설정하세요:
```
OPENAI_API_KEY=your-api-key-here
```

## 주의사항
- API 키나 민감한 정보는 절대 커밋하지 마세요
- `.gitignore`에 `config.env`, `.env` 파일이 포함되어 있습니다
- 생성된 엑셀 파일과 이미지는 저장소에 포함되지 않습니다

