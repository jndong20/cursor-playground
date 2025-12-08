from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException, StaleElementReferenceException

import pandas as pd
import time
import datetime
import warnings
import requests
import json
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

warnings.filterwarnings('ignore')

# ============================================
# 설정
# ============================================
URL = "https://www.wanted.co.kr/wdlist/518/10110"   # 소프트웨어 엔지니어
#URL = "https://www.wanted.co.kr/wdlist/518/899"      # 파이썬 개발자 
DEFAULT_JOB_CATEGORY = '소프트웨어 엔지니어'

MAX_WORKERS = 10  # 병렬 처리 워커 수

# ============================================
# 1단계: Selenium으로 리스트 페이지 스크롤 및 공고 목록 수집
# ============================================
print("=" * 70)
print("원티드 채용공고 크롤링 (병렬 처리 버전) 🚀")
print("=" * 70)

chrome_options = webdriver.ChromeOptions()
chrome_options.add_experimental_option("detach", True)
chrome_options.add_argument('--start-maximized')

driver = webdriver.Chrome(options=chrome_options)
driver.get(URL)
time.sleep(3)

# XPath 선택자
element_xpath = "//div[@data-cy='job-card']/a"
alternative_xpaths = [
    "//div[@data-cy='job-card']/a",
    "//a[contains(@href, '/wd/')]",
    "//div[contains(@class, 'JobCard_JobCard')]/a",
]

wait = WebDriverWait(driver, 20)

# 요소 찾기
element_found = False
for xpath in alternative_xpaths:
    try:
        print(f"요소 찾기 시도 중: {xpath}")
        wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        element_xpath = xpath
        element_found = True
        print(f"✓ 요소를 찾았습니다: {xpath}")
        break
    except Exception as e:
        print(f"✗ 타임아웃: {xpath}")
        continue

if not element_found:
    print("경고: 요소를 찾지 못했습니다. 기본 XPath로 진행...")
    element_xpath = alternative_xpaths[0]

# 스크롤 다운
SCROLL_PAUSE_TIME = 1.5
try:
    last_height = driver.execute_script("return document.body.scrollHeight")
except InvalidSessionIdException:
    print("세션이 끊어졌습니다.")
    driver.quit()
    raise

same_count = 0
print("\n[1단계] 리스트 페이지 스크롤 중...")

while True:
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE_TIME)
        new_height = driver.execute_script("return document.body.scrollHeight")
    except (InvalidSessionIdException, WebDriverException) as e:
        print("브라우저 세션이 끊겼습니다.")
        break

    if new_height == last_height:
        same_count += 1
    else:
        same_count = 0

    if same_count >= 2:
        print("✓ 스크롤 완료 - 더 이상 새 공고 없음")
        break

    last_height = new_height

# 요소 수집
elements = []
try:
    elements = driver.find_elements(By.XPATH, element_xpath)
    print(f"✓ {len(elements)}개 공고 발견")
except Exception as e:
    print(f"요소 수집 실패: {e}")
    elements = []

# 리스트 정보 수집
list_data = []
for idx, e in enumerate(elements):
    try:
        max_retries = 3
        retry_count = 0
        href = None
        job_category_id = ''
        company_id = ''
        company_name = ''
        position_name = ''
        position_id = ''
        
        while retry_count < max_retries:
            try:
                href = e.get_attribute('href')
                if href and href.startswith('/'):
                    href = f"https://www.wanted.co.kr{href}"
                
                parent_div = e.find_element(By.XPATH, "./..")
                try:
                    button = parent_div.find_element(By.XPATH, ".//button[@data-attribute-id='position__bookmark__click']")
                    job_category_id = button.get_attribute('data-job-category-id') or ''
                    company_id = button.get_attribute('data-company-id') or ''
                    company_name = button.get_attribute('data-company-name') or ''
                    position_name = button.get_attribute('data-position-name') or ''
                    position_id = button.get_attribute('data-position-id') or ''
                except:
                    pass
                break
            except StaleElementReferenceException:
                retry_count += 1
                if retry_count < max_retries:
                    elements = driver.find_elements(By.XPATH, element_xpath)
                    if idx < len(elements):
                        e = elements[idx]
                    time.sleep(0.5)
                else:
                    raise
        
        if href is None:
            continue
        
        list_data.append({
            'job_category_id': job_category_id,
            'job_category': DEFAULT_JOB_CATEGORY,
            'company_id': company_id,
            'company_name': company_name,
            'position_name': position_name,
            'position_id': position_id,
            'link': href or '',
        })
        
        if (idx + 1) % 50 == 0:
            print(f"  [{idx+1}/{len(elements)}] 리스트 정보 수집 중...")
    
    except Exception as ex:
        continue

print(f"✓ 리스트 정보 수집 완료: {len(list_data)}개")

# 1단계 엑셀 저장
df_list = pd.DataFrame(list_data)
now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
list_save_path = f"C://Users//MULTICAMPUS//Desktop//curosr-playground//wanted//1.{DEFAULT_JOB_CATEGORY}_wanted_{now_str}.xlsx"
df_list.to_excel(list_save_path, index=False, engine='openpyxl')
print(f"✓ 리스트 엑셀 저장: {list_save_path}")

# Selenium 브라우저 종료 (2단계는 requests 사용)
print("\n브라우저 종료 중... (2단계는 requests 사용)")
driver.quit()

# ============================================
# 2단계: requests + 병렬 처리로 상세 페이지 크롤링
# ============================================
print(f"\n[2단계] 상세 페이지 병렬 크롤링 시작 ({MAX_WORKERS}개 동시 처리) 🚀")

# 진행 상황 추적
progress_lock = threading.Lock()
completed_count = 0

def crawl_detail_page(row_data):
    """상세 페이지 크롤링 (requests + __NEXT_DATA__ JSON)"""
    global completed_count
    
    idx = row_data['idx']
    href = row_data['link']
    company_name = row_data.get('company_name', '')
    
    result = {
        'idx': idx,
        'position': '',
        'content1': '',
        'content2': '',
        'content3': '-',
        'content4': '-',
        'period': '-',
        'skill': ''
    }
    
    if pd.isna(href) or not href:
        return result
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9',
        }
        
        response = requests.get(href, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return result
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # __NEXT_DATA__에서 JSON 추출
        next_data_script = soup.find('script', id='__NEXT_DATA__')
        
        if next_data_script:
            try:
                json_data = json.loads(next_data_script.string)
                props = json_data.get('props', {})
                page_props = props.get('pageProps', {})
                job_detail = page_props.get('jobDetail', {})
                
                # 포지션 상세
                result['position'] = job_detail.get('position', '')
                
                # 주요업무, 자격요건, 우대사항, 혜택
                detail = job_detail.get('detail', {})
                
                # 주요업무
                intro = detail.get('intro', '')
                result['content1'] = intro.replace('\n', ' ').replace('• ', '').strip() if intro else ''
                
                # 자격요건
                requirements = detail.get('requirements', '')
                result['content2'] = requirements.replace('\n', ' ').replace('• ', '').strip() if requirements else ''
                
                # 우대사항
                preferred = detail.get('preferred', '')
                result['content3'] = preferred.replace('\n', ' ').replace('• ', '').strip() if preferred else '-'
                
                # 혜택 및 복지
                benefits = detail.get('benefits', '')
                result['content4'] = benefits.replace('\n', ' ').replace('• ', '').strip() if benefits else '-'
                
                # 마감일
                due_time = job_detail.get('dueTime', '')
                result['period'] = due_time if due_time else '-'
                
                # 기술스택
                skill_tags = job_detail.get('skillTags', [])
                if skill_tags:
                    result['skill'] = '::'.join([tag.get('name', '') for tag in skill_tags if tag.get('name')])
                
            except json.JSONDecodeError:
                pass
        
        # JSON이 없으면 HTML 파싱 폴백
        if not result['content1']:
            try:
                # 주요업무
                content1_div = soup.find('h3', string=lambda x: x and '주요업무' in x)
                if content1_div:
                    parent = content1_div.find_parent('div')
                    if parent:
                        result['content1'] = parent.get_text(' ', strip=True).replace('주요업무', '').replace('• ', '').strip()
            except:
                pass
            
            try:
                # 자격요건
                content2_div = soup.find('h3', string=lambda x: x and '자격요건' in x)
                if content2_div:
                    parent = content2_div.find_parent('div')
                    if parent:
                        result['content2'] = parent.get_text(' ', strip=True).replace('자격요건', '').replace('• ', '').strip()
            except:
                pass
    
    except Exception as e:
        pass
    
    # 진행 상황 업데이트
    with progress_lock:
        completed_count += 1
        total = row_data['total']
        status = "✓" if result['content1'] or result['content2'] else "-"
        print(f"\r  [{completed_count}/{total}] 상세 크롤링 중... ({completed_count/total*100:.0f}%) {status}", end='', flush=True)
    
    return result

# 병렬 크롤링 실행
df_detail = pd.read_excel(list_save_path, engine='openpyxl')
total = len(df_detail)

# row_data 준비
row_data_list = []
for idx, row in df_detail.iterrows():
    row_data_list.append({
        'idx': idx,
        'link': row['link'],
        'company_name': row.get('company_name', ''),
        'total': total
    })

detail_results = []
start_time = time.time()

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = [executor.submit(crawl_detail_page, rd) for rd in row_data_list]
    
    for future in as_completed(futures):
        detail_results.append(future.result())

# 결과 정렬 (원래 순서대로)
detail_results.sort(key=lambda x: x['idx'])

elapsed_time = time.time() - start_time
print(f"\n✓ 상세 크롤링 완료! ({elapsed_time:.1f}초, {elapsed_time/total:.2f}초/건)")

# ============================================
# 3단계: 결과 합치기 및 저장
# ============================================
print(f"\n[3단계] 결과 저장 중...")

# 상세 정보를 DataFrame으로 변환
detail_info_list = [{k: v for k, v in r.items() if k != 'idx'} for r in detail_results]
df_detail_info = pd.DataFrame(detail_info_list)

# 기존 데이터와 합치기
df_final = pd.concat([df_detail, df_detail_info], axis=1)
df_final['job_category'] = DEFAULT_JOB_CATEGORY

# 엑셀 저장 전 불법 문자 제거 (openpyxl 오류 방지)
import re
ILLEGAL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')

def clean_illegal_chars(value):
    """엑셀에서 허용되지 않는 제어 문자 제거"""
    if isinstance(value, str):
        return ILLEGAL_CHARS_RE.sub('', value)
    return value

print("  → 불법 문자 정리 중...")
for col in df_final.columns:
    if df_final[col].dtype == 'object':
        df_final[col] = df_final[col].apply(clean_illegal_chars)

# 최종 저장
final_save_path = f"C://Users//MULTICAMPUS//Desktop//curosr-playground//wanted//2.{DEFAULT_JOB_CATEGORY}_wanted_{now_str}.xlsx"
df_final.to_excel(final_save_path, index=False, engine='openpyxl')

# 통계
content_count = sum(1 for r in detail_results if r['content1'] or r['content2'])

print("=" * 70)
print("📊 크롤링 결과")
print("=" * 70)
print(f"총 공고 수: {len(df_final)}개")
print(f"상세 정보 수집: {content_count}개 ({content_count/len(df_final)*100:.1f}%)")
print(f"소요 시간: {elapsed_time:.1f}초 ({elapsed_time/total:.2f}초/건)")
print(f"job_category: {DEFAULT_JOB_CATEGORY}")
print("=" * 70)
print(f"✓ 리스트 파일: {list_save_path}")
print(f"✓ 최종 파일: {final_save_path}")
print("\n🎉 작업 완료!")
