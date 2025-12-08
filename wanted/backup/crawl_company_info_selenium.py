import pandas as pd
from datetime import datetime
import time
import requests
from bs4 import BeautifulSoup
import re
from pathlib import Path
import os
import sys

# Selenium 임포트
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
except ImportError:
    print("selenium 패키지가 필요합니다. pip install selenium 를 실행해주세요.")
    sys.exit(1)

# OpenAI API 준비
try:
    from openai import OpenAI
except ImportError:
    print("openai 패키지가 필요합니다. pip install openai 를 실행해주세요.")
    sys.exit(1)

def get_openai_api_key():
    api_key = os.getenv("OPENAI_API_KEY", None)
    config_path = "../API/config.env"
    # config.env 파일에서 읽기
    if not api_key and os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPENAI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    print("✓ config.env 파일에서 OpenAI API 키를 읽었습니다.")
                    break
    if not api_key:
        print("\nOpenAI API 키가 필요합니다.")
        api_key = input("OpenAI API 키를 입력하세요: ").strip()
    if not api_key:
        print("오류: OpenAI API 키가 제공되지 않았습니다.")
        sys.exit(1)
    return api_key

api_key = get_openai_api_key()
client = OpenAI(api_key=api_key)

print("\n" + "=" * 70)
print("원티드 기업 정보 크롤링 및 회사 소개/산업분야 추출")
print("=" * 70)

# 엑셀 파일 경로
input_file = "wanted_classified_openai_20251208_105624.xlsx"

print(f"\n파일 읽기: {input_file}")
df = pd.read_excel(input_file, engine='openpyxl')
print(f"✓ 총 {len(df)}개 레코드 로드 완료")

# 테스트용: 처음 3개만 처리 (전체 처리하려면 이 줄을 주석 처리하세요)
#df = df.head(3)
#print(f"⚠ 테스트 모드: {len(df)}개만 처리합니다")

# 컬럼 확인
print(f"\n컬럼 목록: {list(df.columns)}")

# P 컬럼 확인 (인덱스로 접근)
if len(df.columns) >= 16:  # P는 16번째 컬럼 (0-based index: 15)
    company_id_col = df.columns[15]
    print(f"P 컬럼명: {company_id_col}")
else:
    print("P 컬럼을 찾을 수 없습니다. 컬럼 이름을 직접 확인하세요.")
    # company_id 컬럼이 있는지 확인
    if 'company_id' in df.columns:
        company_id_col = 'company_id'
        print(f"company_id 컬럼을 찾았습니다.")
    else:
        print("오류: company_id 컬럼을 찾을 수 없습니다.")
        exit(1)

# 회사소개 HTML 파싱 함수
def extract_company_desc_from_html(soup):
    """
    <div data-testid='company-info-description'> 회사소개 </div> 추출
    """
    desc_div = soup.find("div", attrs={"data-testid": "company-info-description"})
    if desc_div:
        # 줄바꿈 통일
        text = desc_div.get_text("\n", strip=True)
        # 링크 있을 경우 합쳐줌(따로 추출)
        links = [a['href'] for a in desc_div.find_all('a', href=True)]
        if links:
            links_text = "\n".join(links)
            text += "\n" + links_text
        return text
    return ""

# webdriver-manager로 자동 드라이버 설치
try:
    from webdriver_manager.chrome import ChromeDriverManager
    USE_WEBDRIVER_MANAGER = True
except ImportError:
    print("⚠ webdriver-manager가 없습니다. 수동으로 설치된 ChromeDriver를 사용합니다.")
    USE_WEBDRIVER_MANAGER = False

# Selenium 브라우저 설정 (속도 최적화)
def setup_driver():
    """Chrome 드라이버 설정 - 속도 최적화 버전"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 백그라운드 실행
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # 🚀 속도 최적화 옵션들
    chrome_options.add_argument('--disable-extensions')  # 확장프로그램 비활성화
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--disable-popup-blocking')
    chrome_options.add_argument('--blink-settings=imagesEnabled=false')  # 이미지 로딩 비활성화
    chrome_options.page_load_strategy = 'eager'  # DOM만 로드되면 진행 (완전 로딩 기다리지 않음)
    
    # 실험적 옵션 - 이미지, 폰트 비활성화 (CSS는 유지 - 구조 파싱에 필요)
    prefs = {
        'profile.managed_default_content_settings.images': 2,
        'profile.managed_default_content_settings.fonts': 2,
    }
    chrome_options.add_experimental_option('prefs', prefs)
    
    try:
        if USE_WEBDRIVER_MANAGER:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            driver = webdriver.Chrome(options=chrome_options)
        
        # 페이지 로드 타임아웃 설정 (10초)
        driver.set_page_load_timeout(10)
        
        return driver
    except Exception as e:
        print(f"Chrome 드라이버 초기화 실패: {e}")
        print("\n해결 방법:")
        print("1. pip install webdriver-manager 실행")
        print("2. Chrome 브라우저가 설치되어 있는지 확인")
        return None

# 기업 정보 크롤링 함수 (Selenium 사용)
def crawl_company_info(driver, company_id, retry=3):
    """원티드 기업 정보 페이지 크롤링 및 회사소개 추출 (Selenium)"""
    if pd.isna(company_id):
        return {
            '표준산업분류': '',
            '연혁': '',
            '매출액': '',
            '고용보험가입사원수': '',
            '회사소개': ''
        }
    
    url = f"https://www.wanted.co.kr/company/{company_id}"
    for attempt in range(retry):
        try:
            driver.get(url)
            # 🚀 대기 시간 단축 (5초 → 2초)
            time.sleep(2)
            
            # 특정 요소가 로드될 때까지 대기 (최대 5초)
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "section"))
                )
            except:
                pass  # 타임아웃이어도 진행
            
            # 페이지 소스 가져오기
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            result = {
                '표준산업분류': '',
                '연혁': '',
                '매출액': '',
                '고용보험가입사원수': '',
                '회사소개': ''
            }
            
            # 회사소개 추출
            desc = extract_company_desc_from_html(soup)
            result['회사소개'] = desc
            
            # 디버깅: 모든 section 태그 찾기
            all_sections = soup.find_all('section')
            print(f"    → 페이지에서 {len(all_sections)}개 section 태그 발견")
            
            # 기업 정보 섹션 찾기 - h2 태그에 "기업 정보"가 있는 section만 찾기
            company_section = None
            for section in all_sections:
                h2 = section.find('h2')
                if h2:
                    h2_text = h2.get_text(strip=True)
                    # "기업 정보" 섹션만 찾기 (채용중인 포지션, 태그, 연봉 등 제외)
                    if h2_text == '기업 정보':
                        company_section = section
                        print(f"    → '기업 정보' 섹션 발견!")
                        break
            
            if company_section:
                # 디버깅: dl 태그 찾기 (여러 방법)
                dl_tags = company_section.find_all('dl')
                print(f"    → {len(dl_tags)}개 dl 태그 발견 (class 필터 없음)")
                
                if len(dl_tags) == 0:
                    print(f"    ⚠ dl 태그를 찾을 수 없습니다")
                    # HTML 일부 출력
                    print(f"    섹션 HTML 샘플: {str(company_section)[:200]}...")
                
                # class 필터 적용
                dl_tags_filtered = company_section.find_all('dl', class_=re.compile('CompanyInfoTable'))
                print(f"    → {len(dl_tags_filtered)}개 dl 태그 (CompanyInfoTable 필터)")
                
                # 필터된 태그 사용
                dl_tags = dl_tags if len(dl_tags_filtered) == 0 else dl_tags_filtered
                
                for dl in dl_tags:
                    dt = dl.find('dt')
                    dd = dl.find('dd')
                    if dt and dd:
                        key = dt.get_text(strip=True)
                        # get_text()는 모든 하위 태그의 텍스트를 자동으로 합쳐줌
                        value = dd.get_text(strip=True)
                        
                        # 디버깅: 추출된 키-값 출력
                        if value:
                            print(f"      - {key}: {value[:30]}..." if len(value) > 30 else f"      - {key}: {value}")
                        
                        if key == '표준산업분류':
                            result['표준산업분류'] = value
                        elif key == '연혁':
                            result['연혁'] = value
                        elif key == '매출액':
                            result['매출액'] = value
                        elif key == '고용보험 가입 사원수' or key == '고용보험가입사원수':
                            result['고용보험가입사원수'] = value
            else:
                # 디버깅: 어떤 섹션들이 있는지 출력
                section_names = []
                for section in all_sections:
                    h2 = section.find('h2')
                    if h2:
                        section_names.append(h2.get_text(strip=True)[:20])
                print(f"    ⚠ '기업 정보' 섹션을 찾을 수 없습니다")
                print(f"    발견된 섹션들: {section_names}")
            
            return result
            
        except Exception as e:
            print(f"  크롤링 오류 (시도 {attempt+1}/{retry}): {e}")
            if attempt < retry - 1:
                time.sleep(2)
    
    return {
        '표준산업분류': '',
        '연혁': '',
        '매출액': '',
        '고용보험가입사원수': '',
        '회사소개': ''
    }

def get_company_summary_via_openai(desc, org_name=None):
    """OpenAI로 회사소개 요약"""
    if not desc.strip():
        return ""
    system_prompt = (
        "다음 회사 소개글을 읽고, 핵심 내용을 150자 이내로 간결하게 요약해 주세요. "
        "회사의 주요 사업, 제품/서비스, 특징을 중심으로 요약하세요."
    )
    user_prompt = f"[회사명: {org_name if org_name else ''}]\n회사소개:\n{desc}"
    try:
        completion = client.chat.completions.create(
            model='gpt-4o-mini',  # 최신 모델로 업그레이드
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=200,
            temperature=0.3
        )
        content = completion.choices[0].message.content
        return content.strip()
    except Exception as e:
        print(f"  OpenAI 요약 실패: {e}")
        return ""

def get_industry_via_openai(desc, org_name=None):
    """OpenAI로 산업분야 추출"""
    if not desc.strip():
        return ""
    system_prompt = (
        "다음 회사 소개글을 읽고, 회사의 산업분야(예시: 게임, 소프트웨어, 헬스케어, 제조, 물류, 교육, 부동산, 광고/마케팅, 금융 등)를 최대한 구체적으로 한글로 한두 단어로 요약해 주세요."
        "직군·채용업무가 아니라 해당 기업의 전반적 산업군(주로 하는 사업분야/제품군)만 한글 키워드로 알려주세요.\n"
        f"출력 예시: 게임\n"
        "만약 산업 분야를 알 수 없으면 '미상'으로 써주세요."
    )
    user_prompt = f"[회사명: {org_name if org_name else ''}]\n회사소개:\n{desc}"
    try:
        completion = client.chat.completions.create(
            model='gpt-4o-mini',  # 최신 모델로 업그레이드
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=16,
            temperature=0
        )
        content = completion.choices[0].message.content
        # 출력에서 줄 있는 것만 추출, 한 줄로
        content = content.strip().split('\n')[0].strip()
        content = content.replace("산업분야:", "").replace("산업:", "").replace("주요 산업:", "").strip()
        return content
    except Exception as e:
        print(f"  OpenAI 산업분야 분류 실패: {e}")
        return ""

print("\n기업 정보 및 회사소개/산업분야 크롤링 중...\n(시간이 걸릴 수 있습니다...)")

# Selenium 드라이버 초기화
print("\nChrome 드라이버 초기화 중...")
driver = setup_driver()
if not driver:
    print("오류: Chrome 드라이버를 초기화할 수 없습니다.")
    sys.exit(1)
print("✓ Chrome 드라이버 초기화 완료\n")

results = []
industry_results = []
summary_results = []

try:
    for idx, row in df.iterrows():
        company_id = row[company_id_col]
        company_name = row.get('company_name', '') if 'company_name' in row else ""
        print(f"[{idx+1}/{len(df)}] 크롤링 중: {company_name} (ID: {company_id})")
        
        info = crawl_company_info(driver, company_id)
        results.append(info)
        desc = info.get('회사소개', '')
        
        # 크롤링된 데이터 출력
        if info['표준산업분류'] or info['연혁'] or info['매출액'] or info['고용보험가입사원수']:
            print(f"    ✓ 기업정보: 표준산업분류={bool(info['표준산업분류'])}, 연혁={bool(info['연혁'])}, 매출액={bool(info['매출액'])}, 사원수={bool(info['고용보험가입사원수'])}")
        
        # OpenAI로 회사소개 요약 및 산업분야 분석
        if desc:
            print("  → 회사소개 OpenAI 분석 중...", end='', flush=True)
            summary = get_company_summary_via_openai(desc, org_name=company_name)
            industry = get_industry_via_openai(desc, org_name=company_name)
            print(f" 완료")
            print(f"    - 산업분야: {industry}")
            print(f"    - 요약: {summary[:50]}..." if len(summary) > 50 else f"    - 요약: {summary}")
        else:
            summary = ""
            industry = ""
            print("  → 회사소개 없음")
        
        summary_results.append(summary)
        industry_results.append(industry)
        # 🚀 대기 시간 단축 (1초 → 0.3초)
        time.sleep(0.3)

finally:
    # 드라이버 종료
    print("\n\nChrome 드라이버 종료 중...")
    driver.quit()
    print("✓ Chrome 드라이버 종료 완료")

# 결과를 DataFrame에 추가
df['표준산업분류'] = [r['표준산업분류'] for r in results]
df['연혁'] = [r['연혁'] for r in results]
df['매출액'] = [r['매출액'] for r in results]
df['고용보험가입사원수'] = [r['고용보험가입사원수'] for r in results]
df['회사소개'] = [r.get('회사소개', '') for r in results]
df['회사소개요약(OpenAI)'] = summary_results
df['산업분야(OpenAI)'] = industry_results

# 통계
filled_count = sum(
    1 for r in results 
    if r['회사소개'] or r['표준산업분류'] or r['연혁'] or r['매출액'] or r['고용보험가입사원수']
)
industry_filled = sum(1 for v in industry_results if v and v != "미상")
summary_filled = sum(1 for v in summary_results if v)

print("\n" + "=" * 70)
print("크롤링 결과")
print("=" * 70)
print(f"회사소개 수집 성공: {sum(1 for r in results if r['회사소개'])}개")
print(f"OpenAI 요약 생성 성공: {summary_filled}개")
print(f"OpenAI 산업분야 추출 성공: {industry_filled}개")
print(f"기업정보 수집 성공: {filled_count}개 ({filled_count/len(df)*100:.1f}%)")
print(f"기업정보 수집 실패: {len(df)-filled_count}개")
print(f"총: {len(df)}개")
print("=" * 70)

# 저장
now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"wanted_AI_with_company_info_{now_str}.xlsx"

print(f"\n저장 중: {output_file}")
df.to_excel(output_file, index=False, engine='openpyxl')
print(f"✓ 기업정보/회사소개/요약/산업분야 추가 완료: {output_file}")

print("\n작업 완료!")
