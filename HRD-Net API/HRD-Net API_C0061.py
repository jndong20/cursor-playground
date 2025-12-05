import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import xml.etree.ElementTree as ET
from openpyxl import Workbook
import datetime
import time
import os

# -----------------------------
# 1. requests 세션 + 재시도 설정
# -----------------------------
session = requests.Session()

retry_strategy = Retry(
    total=5,               # 최대 재시도 횟수
    backoff_factor=1,      # 재시도 간 대기시간 (점점 증가: 1, 2, 4, ...)
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["GET"]
)

adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "*/*",
}

# -----------------------------
# 2. 공통 함수들
# -----------------------------
def fetch_xml(url, max_tries=3, timeout=15):
    """
    SSL/네트워크 오류에 대비한 안전한 XML 요청 함수.
    - SSLError, ConnectionError 발생 시 일정 횟수 재시도 후 None 반환
    """
    for attempt in range(1, max_tries + 1):
        try:
            resp = session.get(url, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            return ET.fromstring(resp.text)

        except requests.exceptions.SSLError as e:
            print(f"[SSL 오류 {attempt}회차] {e} -> 재시도 합니다.")
        except requests.exceptions.ConnectionError as e:
            print(f"[연결 오류 {attempt}회차] {e} -> 재시도 합니다.")
        except requests.exceptions.Timeout as e:
            print(f"[타임아웃 {attempt}회차] {e} -> 재시도 합니다.")
        except requests.exceptions.RequestException as e:
            # 기타 HTTP 에러(예: 4xx)는 재시도해도 의미 없으므로 바로 포기
            print(f"[요청 실패] {e} -> 이 URL은 건너뜁니다.")
            return None

        # 재시도 사이에 약간 쉬어줌 (서버 부하 방지)
        time.sleep(2 * attempt)

    print(f"[포기] 최대 재시도 초과, URL 건너뜀: {url}")
    return None


def get_text(parent, tag):
    """
    XML 엘리먼트에서 tag 텍스트를 안전하게 가져오는 헬퍼 함수.
    태그가 없거나 text가 None이면 '' 반환.
    """
    if parent is None:
        return ""
    elem = parent.find(tag)
    return elem.text.strip() if elem is not None and elem.text is not None else ""


# -----------------------------
# 3. URL 리스트
# -----------------------------
# 시작일자와 종료일자를 입력받아 pageNum=1을 호출하고 scn_cnt 값을 읽은 후, url_list를 구성
import math

# 사용자로부터 시작일자, 종료일자 입력 (YYYYMMDD 형태)
srchTraStDt = input("시작일자(YYYYMMDD): ").strip()
srchTraEndDt = input("종료일자(YYYYMMDD): ").strip()
if not srchTraStDt:
    srchTraStDt = "20230101"
if not srchTraEndDt:
    srchTraEndDt = "20231231"

BASE_URL = (
    "https://www.work24.go.kr/cm/openApi/call/hr/callOpenApiSvcInfo310L01.do"
    "?returnType=XML"
    "&authKey=df46b09d-e741-4324-b929-69d15685de4a"
    "&pageNum={page}"
    "&pageSize=100"
    f"&srchTraStDt={srchTraStDt}"
    f"&srchTraEndDt={srchTraEndDt}"
    "&outType=1"
    "&sort=ASC"
    "&sortCol=TRNG_BGDE"
    "&crseTracseSe=C0061"
    "&srchTraArea1=00"

    # 'C0061' : 국민내일배움카드(일반) , 'C0104' : K-디지털 트레이닝
)

# pageNum=1로 첫 번째 페이지의 scn_cnt(전체 건수) 확인
first_url = BASE_URL.format(page=1)
root = fetch_xml(first_url)
if root is None:
    raise RuntimeError("첫 페이지 XML 데이터를 가져오지 못했습니다.")

# scn_cnt 읽기 (없으면 0으로)
scn_cnt_elem = root.find("scn_cnt")
try:
    total_count = int(scn_cnt_elem.text) if scn_cnt_elem is not None and scn_cnt_elem.text else 0
except Exception:
    total_count = 0

# pageSize는 100 (한 페이지에 100개)
page_size = 100
total_pages = math.ceil(total_count / page_size)

url_list = [
    BASE_URL.format(page=page_num)
    for page_num in range(1, total_pages + 1)
]

print(f"총 {total_count}개 항목, {total_pages}개 페이지 url_list 생성 완료.")

# -----------------------------
# 4. 엑셀 초기 설정
# -----------------------------
workbook = Workbook()
worksheet = workbook.active

columns = [
    'No', '훈련기관', '훈련기관 코드', '훈련기관ID', '회차', '과정명', '과정명ID',
    '시작일자', '종료일자', '수강신청 인원', '정원', '수료인원', '수강비', '실제 훈련비',
    '훈련시간', '만족도', '고용보험3개월인원수', '3개월 고용보험 취업률(%)',
    '고용보험6개월인원수', '6개월 고용보험 취업률(%)', 'NCS 코드', 'NCS코드명', '평가등급',
    '자격증여부', '콘텐츠', '등급', '부제목', '부제목 링크', '훈련대상', '훈련구분', '지역코드(중분류)', '주말/주중 구분'
]
worksheet.append(columns)

# -----------------------------
# 5. 메인 루프
# -----------------------------
i = 0
for url in url_list:
    current_time = datetime.datetime.now()
    print('time:', current_time, '요청 URL:', url)

    root = fetch_xml(url)
    if root is None:
        continue  # 이 페이지 전체 건너뜀

    # <srchList><scn_list> 구조 파싱
    for srchList in root.findall("srchList"):
        for item in srchList.findall("scn_list"):
            i += 1

            subTitle      = get_text(item, "subTitle")      # 부제목(훈련기관명)
            instCd        = get_text(item, "instCd")        # 훈련기관 코드
            trainstCstId  = get_text(item, "trainstCstId")  # 훈련기관 ID
            trprDegr      = get_text(item, "trprDegr")      # 훈련과정 순차
            title         = get_text(item, "title")         # 과정명
            trprId        = get_text(item, "trprId")        # 훈련과정ID
            traStartDate  = get_text(item, "traStartDate")  # 시작일자
            traEndDate    = get_text(item, "traEndDate")    # 종료일자
            regCourseMan  = get_text(item, "regCourseMan")  # 수강신청 인원
            yardMan       = get_text(item, "yardMan")       # 정원
            courseMan     = get_text(item, "courseMan")     # 수강비
            realMan       = get_text(item, "realMan")       # 실제 훈련비
            stdgScor      = get_text(item, "stdgScor")      # 만족도

            certificate = get_text(item, "certificate")     # 자격증
            contents = get_text(item, "contents")           # 콘텐츠
            grade = get_text(item, "grade")                 # 등급
            sub_title = get_text(item, "subTitle")         # 부제목
            sub_title_link = get_text(item, "subTitleLink") # 부제목 링크
            train_target = get_text(item, "trainTarget")   # 훈련대상
            train_target_cd = get_text(item, "trainTargetCd") # 훈련구분
            train_area_cd = get_text(item, "trainAreaCd") # 지역코드(중분류)
            wked_se = get_text(item, "wkendSe") # 주말/주중 구분


            # ---------- 세부 통계(L03) ----------
            finiCnt = eiEmplCnt3 = eiEmplRate3 = eiEmplCnt6 = eiEmplRate6 = ""

            url_finiCnt = (
                "https://www.work24.go.kr/cm/openApi/call/hr/callOpenApiSvcInfo310L03.do"
                f"?authKey=df46b09d-e741-4324-b929-69d15685de4a&returnType=XML&outType=2"
                f"&srchTrprId={trprId}&srchTrprDegr={trprDegr}&srchTorgId={trainstCstId}"
            )

            root_d = fetch_xml(url_finiCnt)
            if root_d is not None:
                for item_d in root_d.findall("scn_list"):
                    finiCnt     = get_text(item_d, "finiCnt")      # 수료인원
                    eiEmplCnt3  = get_text(item_d, "eiEmplCnt3")   # 3개월 고용보험 인원
                    eiEmplRate3 = get_text(item_d, "eiEmplRate3")  # 3개월 취업률
                    eiEmplCnt6  = get_text(item_d, "eiEmplCnt6")   # 6개월 고용보험 인원
                    eiEmplRate6 = get_text(item_d, "eiEmplRate6")  # 6개월 취업률


                    hrdEmplCnt6 = get_text(item_d, "hrdEmplCnt6") # 6개월 고용보험 미가입 취업인원
                    

            # ---------- 과정 상세(L02) ----------
            ncsCd = ncsNm = trtm = torgParGrad = ""

            url_course = (
                "https://www.work24.go.kr/cm/openApi/call/hr/callOpenApiSvcInfo310L02.do"
                f"?returnType=XML&authKey=df46b09d-e741-4324-b929-69d15685de4a"
                f"&srchTrprId={trprId}&srchTrprDegr={trprDegr}&outType=2&srchTorgId={trainstCstId}"
            )

            root_c = fetch_xml(url_course)
            if root_c is not None:
                for item_c in root_c.findall("inst_base_info"):
                    ncsCd      = get_text(item_c, "ncsCd")       # NCS 코드
                    ncsNm      = get_text(item_c, "ncsNm")       # NCS 코드명
                    trtm       = get_text(item_c, "trtm")        # 훈련시간
                    torgParGrad = get_text(item_c, "torgParGrad")  # 평가등급

                    

            # ---------- 엑셀에 추가 ----------
            data_row = [
                i, subTitle, instCd, trainstCstId, trprDegr, title, trprId,
                traStartDate, traEndDate, regCourseMan, yardMan, finiCnt,
                courseMan, realMan, trtm, stdgScor,
                eiEmplCnt3, eiEmplRate3, eiEmplCnt6, eiEmplRate6,
                ncsCd, ncsNm, torgParGrad
            ]
            worksheet.append(data_row)

            # 서버 부하/차단 방지를 위해 약간 쉬어가기 (필요시 조정)
            time.sleep(0.2)

# -----------------------------
# 6. 로컬 PC에 저장
# -----------------------------
final_filename = f"{srchTraStDt}-{srchTraEndDt}.xlsx"
workbook.save(final_filename)
print(f"최종 저장 완료: {final_filename}")
print(f"저장 경로: {os.path.abspath(final_filename)}")
