"""
원티드 채용공고 통합 크롤링 스크립트
=====================================
1단계: 원티드 채용공고 리스트 및 상세 정보 크롤링
2단계: OpenAI로 AI 관련 공고 분류
3단계: 기업 정보 크롤링 및 산업분야 분석

모든 단계가 병렬 처리로 최적화되어 있습니다.
"""

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
import re
import os
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

warnings.filterwarnings('ignore')

# ============================================
# 설정
# ============================================
# 크롤링할 URL과 직무 카테고리 설정
URL = "https://www.wanted.co.kr/wdlist/518/10110"   # 소프트웨어 엔지니어
#URL = "https://www.wanted.co.kr/wdlist/518/899"      # 파이썬 개발자 
DEFAULT_JOB_CATEGORY = '소프트웨어 엔지니어'

# 병렬 처리 설정
MAX_WORKERS_CRAWL = 10   # 크롤링 동시 처리 수
MAX_WORKERS_OPENAI = 5   # OpenAI API 동시 처리 수

# ============================================
# OpenAI API 설정
# ============================================
try:
    from openai import OpenAI
except ImportError:
    print("openai 패키지가 필요합니다. pip install openai 를 실행해주세요.")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / 'API' / 'config.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print("✓ config.env 파일에서 API 키를 로드했습니다.")
except:
    pass

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    config_path = "../API/config.env"
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("OPENAI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    print("✓ config.env에서 OpenAI API 키를 읽었습니다.")
                    break

if not api_key:
    print("\n환경 변수에서 API 키를 찾지 못했습니다.")
    api_key = input("OpenAI API 키를 입력하세요: ").strip()

if not api_key:
    print("오류: API 키가 제공되지 않았습니다.")
    sys.exit(1)

openai_client = OpenAI(api_key=api_key)

# 진행 상황 추적
progress_lock = threading.Lock()
completed_count = 0

# 타임스탬프
now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BASE_PATH = "C://Users//MULTICAMPUS//Desktop//curosr-playground//wanted//"

print("\n" + "=" * 80)
print("🚀 원티드 채용공고 통합 크롤링 스크립트")
print("=" * 80)
print(f"URL: {URL}")
print(f"직무 카테고리: {DEFAULT_JOB_CATEGORY}")
print(f"병렬 처리: 크롤링 {MAX_WORKERS_CRAWL}개, OpenAI {MAX_WORKERS_OPENAI}개")
print("=" * 80)

total_start_time = time.time()

# ============================================
# [STEP 1] 원티드 채용공고 리스트 및 상세 정보 크롤링
# ============================================
print("\n" + "=" * 80)
print("[STEP 1/3] 원티드 채용공고 크롤링")
print("=" * 80)

# 1-1: Selenium으로 리스트 페이지 스크롤
print("\n[1-1] 리스트 페이지 스크롤 중...")

chrome_options = webdriver.ChromeOptions()
chrome_options.add_experimental_option("detach", True)
chrome_options.add_argument('--start-maximized')

driver = webdriver.Chrome(options=chrome_options)
driver.get(URL)
time.sleep(3)

element_xpath = "//div[@data-cy='job-card']/a"
alternative_xpaths = [
    "//div[@data-cy='job-card']/a",
    "//a[contains(@href, '/wd/')]",
    "//div[contains(@class, 'JobCard_JobCard')]/a",
]

wait = WebDriverWait(driver, 20)

element_found = False
for xpath in alternative_xpaths:
    try:
        wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        element_xpath = xpath
        element_found = True
        print(f"  ✓ 요소를 찾았습니다")
        break
    except:
        continue

# 스크롤 다운
SCROLL_PAUSE_TIME = 1.5
try:
    last_height = driver.execute_script("return document.body.scrollHeight")
except:
    driver.quit()
    raise

same_count = 0
while True:
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE_TIME)
        new_height = driver.execute_script("return document.body.scrollHeight")
    except:
        break

    if new_height == last_height:
        same_count += 1
    else:
        same_count = 0

    if same_count >= 2:
        print("  ✓ 스크롤 완료")
        break

    last_height = new_height

# 요소 수집
elements = driver.find_elements(By.XPATH, element_xpath)
print(f"  ✓ {len(elements)}개 공고 발견")

# 리스트 정보 수집
list_data = []
for idx, e in enumerate(elements):
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
            job_category_id = company_id = company_name = position_name = position_id = ''
        
        if href:
            list_data.append({
                'job_category_id': job_category_id,
                'job_category': DEFAULT_JOB_CATEGORY,
                'company_id': company_id,
                'company_name': company_name,
                'position_name': position_name,
                'position_id': position_id,
                'link': href,
            })
    except:
        continue

print(f"  ✓ 리스트 정보 수집 완료: {len(list_data)}개")

# 브라우저 종료
driver.quit()
print("  ✓ 브라우저 종료")

# 1-2: 상세 페이지 병렬 크롤링
print(f"\n[1-2] 상세 페이지 병렬 크롤링 ({MAX_WORKERS_CRAWL}개 동시)...")

completed_count = 0

def crawl_detail_page(row_data):
    """상세 페이지 크롤링"""
    global completed_count
    
    idx = row_data['idx']
    href = row_data['link']
    total = row_data['total']
    
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
    
    if not href:
        return result
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(href, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return result
        
        soup = BeautifulSoup(response.text, 'html.parser')
        next_data_script = soup.find('script', id='__NEXT_DATA__')
        
        if next_data_script:
            try:
                json_data = json.loads(next_data_script.string)
                job_detail = json_data.get('props', {}).get('pageProps', {}).get('jobDetail', {})
                
                result['position'] = job_detail.get('position', '')
                detail = job_detail.get('detail', {})
                
                intro = detail.get('intro', '')
                result['content1'] = intro.replace('\n', ' ').replace('• ', '').strip() if intro else ''
                
                requirements = detail.get('requirements', '')
                result['content2'] = requirements.replace('\n', ' ').replace('• ', '').strip() if requirements else ''
                
                preferred = detail.get('preferred', '')
                result['content3'] = preferred.replace('\n', ' ').replace('• ', '').strip() if preferred else '-'
                
                benefits = detail.get('benefits', '')
                result['content4'] = benefits.replace('\n', ' ').replace('• ', '').strip() if benefits else '-'
                
                result['period'] = job_detail.get('dueTime', '-') or '-'
                
                skill_tags = job_detail.get('skillTags', [])
                if skill_tags:
                    result['skill'] = '::'.join([tag.get('name', '') for tag in skill_tags if tag.get('name')])
            except:
                pass
    except:
        pass
    
    with progress_lock:
        completed_count += 1
        print(f"\r  [{completed_count}/{total}] 상세 크롤링 중... ({completed_count/total*100:.0f}%)", end='', flush=True)
    
    return result

row_data_list = [{'idx': i, 'link': d['link'], 'total': len(list_data)} for i, d in enumerate(list_data)]

detail_results = []
step1_start = time.time()

with ThreadPoolExecutor(max_workers=MAX_WORKERS_CRAWL) as executor:
    futures = [executor.submit(crawl_detail_page, rd) for rd in row_data_list]
    for future in as_completed(futures):
        detail_results.append(future.result())

detail_results.sort(key=lambda x: x['idx'])

step1_time = time.time() - step1_start
print(f"\n  ✓ 상세 크롤링 완료! ({step1_time:.1f}초)")

# 결과 합치기
df_list = pd.DataFrame(list_data)
df_detail = pd.DataFrame([{k: v for k, v in r.items() if k != 'idx'} for r in detail_results])
df_step1 = pd.concat([df_list, df_detail], axis=1)

step1_file = f"{BASE_PATH}wanted_step1_crawl_{now_str}.xlsx"
df_step1.to_excel(step1_file, index=False, engine='openpyxl')
print(f"  ✓ STEP 1 저장: {step1_file}")

# ============================================
# [STEP 2] OpenAI로 AI 관련 공고 분류
# ============================================
print("\n" + "=" * 80)
print("[STEP 2/3] AI 관련 공고 분류 (OpenAI)")
print("=" * 80)

def create_combined_text(row):
    columns = ['position_name', 'position', 'content1', 'content2', 'content3', 'content4']
    texts = []
    for col in columns:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            texts.append(str(row[col]).strip())
    return " ".join(texts)

df_step1['combined_text'] = df_step1.apply(create_combined_text, axis=1)

completed_count = 0

def classify_with_openai(task_data):
    """OpenAI로 AI 공고 분류"""
    global completed_count
    
    idx = task_data['idx']
    text = task_data['text']
    total = task_data['total']
    
    result = {'idx': idx, 'classification': 'AI비관련', 'reason': '', 'summary': ''}
    
    if not text or len(str(text).strip()) < 10:
        result['reason'] = '내용 부족'
        with progress_lock:
            completed_count += 1
            print(f"\r  [{completed_count}/{total}] 분류 중... ({completed_count/total*100:.0f}%)", end='', flush=True)
        return result
    
    prompt = f"""채용 공고를 분석하세요:
1. AI 관련 직무인지 판단 (AI관련/AI비관련)
2. 판단 근거 (1-2문장)
3. 150자 이내 요약

AI 키워드: AI, 인공지능, 머신러닝, 딥러닝, LLM, 프롬프트 엔지니어링, Agent, RAG, 비전 AI, Computer Vision

공고 내용:
{text[:2000]}

형식:
분류: [AI관련/AI비관련]
근거: [근거]
요약: [요약]"""
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "채용 공고 분석 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        result_text = response.choices[0].message.content.strip()
        for line in result_text.split('\n'):
            line = line.strip()
            if line.startswith('분류:'):
                result['classification'] = 'AI관련' if 'AI관련' in line else 'AI비관련'
            elif line.startswith('근거:'):
                result['reason'] = line.replace('근거:', '').strip()
            elif line.startswith('요약:'):
                result['summary'] = line.replace('요약:', '').strip()
    except:
        result['reason'] = '분석 실패'
    
    with progress_lock:
        completed_count += 1
        status = "AI" if result['classification'] == 'AI관련' else "-"
        print(f"\r  [{completed_count}/{total}] 분류 중... ({completed_count/total*100:.0f}%) {status}", end='', flush=True)
    
    return result

print(f"\n[2-1] AI 공고 분류 중 ({MAX_WORKERS_OPENAI}개 동시)...")

task_list = [{'idx': i, 'text': row.get('combined_text', ''), 'total': len(df_step1)} 
             for i, row in df_step1.iterrows()]

step2_start = time.time()
classify_results = []

with ThreadPoolExecutor(max_workers=MAX_WORKERS_OPENAI) as executor:
    futures = [executor.submit(classify_with_openai, task) for task in task_list]
    for future in as_completed(futures):
        classify_results.append(future.result())

classify_results.sort(key=lambda x: x['idx'])

step2_time = time.time() - step2_start
print(f"\n  ✓ 분류 완료! ({step2_time:.1f}초)")

# 결과 추가
df_step1['AI_classification'] = [r['classification'] for r in classify_results]
df_step1['AI_reason'] = [r['reason'] for r in classify_results]
df_step1['summary'] = [r['summary'] for r in classify_results]

# AI 관련 공고만 필터링
df_ai_only = df_step1[df_step1['AI_classification'] == 'AI관련'].copy()

ai_count = len(df_ai_only)
print(f"  ✓ AI관련: {ai_count}개 ({ai_count/len(df_step1)*100:.1f}%)")

step2_file = f"{BASE_PATH}wanted_step2_classified_{now_str}.xlsx"
df_step1.to_excel(step2_file, index=False, engine='openpyxl')
print(f"  ✓ STEP 2 저장: {step2_file}")

# ============================================
# [STEP 3] 기업 정보 크롤링 (AI 관련 공고만)
# ============================================
print("\n" + "=" * 80)
print(f"[STEP 3/3] 기업 정보 크롤링 (AI 관련 {len(df_ai_only)}개)")
print("=" * 80)

completed_count = 0

def crawl_company_info(company_id, company_name, idx, total):
    """기업 정보 크롤링"""
    global completed_count
    
    result = {
        'idx': idx,
        '표준산업분류': '',
        '연혁': '',
        '매출액': '',
        '고용보험가입사원수': '',
        '회사소개': ''
    }
    
    if pd.isna(company_id):
        return result
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(f"https://www.wanted.co.kr/company/{company_id}", headers=headers, timeout=10)
        
        if response.status_code != 200:
            return result
        
        soup = BeautifulSoup(response.text, 'html.parser')
        next_data_script = soup.find('script', id='__NEXT_DATA__')
        
        if next_data_script:
            try:
                json_data = json.loads(next_data_script.string)
                company_data = json_data.get('props', {}).get('pageProps', {}).get('company', {})
                
                result['회사소개'] = company_data.get('description', '')
                
                for item in company_data.get('companyInfoTable', []):
                    label = item.get('label', '')
                    value = item.get('value', '')
                    if label == '표준산업분류':
                        result['표준산업분류'] = value
                    elif label == '연혁':
                        result['연혁'] = value
                    elif label == '매출액':
                        result['매출액'] = value
                    elif label == '고용보험 가입 사원수':
                        result['고용보험가입사원수'] = value
            except:
                pass
    except:
        pass
    
    with progress_lock:
        completed_count += 1
        status = "✓" if result['회사소개'] else "-"
        print(f"\r  [{completed_count}/{total}] 기업 크롤링 중... ({completed_count/total*100:.0f}%) {status}", end='', flush=True)
    
    return result

def analyze_company_with_openai(result, company_name, idx, total):
    """OpenAI로 회사소개 분석"""
    desc = result.get('회사소개', '')
    
    result['회사소개요약'] = ''
    result['산업분야'] = ''
    
    if desc and desc.strip():
        try:
            completion = openai_client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {"role": "system", "content": "회사 소개글을 150자 이내로 요약하세요."},
                    {"role": "user", "content": f"[회사명: {company_name}]\n{desc}"},
                ],
                max_tokens=200,
                temperature=0.3
            )
            result['회사소개요약'] = completion.choices[0].message.content.strip()
        except:
            pass
        
        try:
            completion = openai_client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {"role": "system", "content": "산업분야를 한두 단어로 답하세요. 예: 게임, 소프트웨어, 헬스케어"},
                    {"role": "user", "content": f"[회사명: {company_name}]\n{desc}"},
                ],
                max_tokens=16,
                temperature=0
            )
            result['산업분야'] = completion.choices[0].message.content.strip().split('\n')[0]
        except:
            pass
    
    print(f"\r  [OpenAI] {idx+1}/{total} → {result['산업분야']}", end='', flush=True)
    
    return result

if len(df_ai_only) > 0:
    # 3-1: 기업 정보 크롤링
    print(f"\n[3-1] 기업 정보 크롤링 ({MAX_WORKERS_CRAWL}개 동시)...")
    
    company_id_col = 'company_id'
    step3_start = time.time()
    
    company_results = []
    total = len(df_ai_only)
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS_CRAWL) as executor:
        futures = []
        for idx, (_, row) in enumerate(df_ai_only.iterrows()):
            company_id = row.get(company_id_col, '')
            company_name = row.get('company_name', '')
            future = executor.submit(crawl_company_info, company_id, company_name, idx, total)
            futures.append(future)
        
        for future in as_completed(futures):
            company_results.append(future.result())
    
    company_results.sort(key=lambda x: x['idx'])
    
    crawl_time = time.time() - step3_start
    print(f"\n  ✓ 기업 크롤링 완료! ({crawl_time:.1f}초)")
    
    # 3-2: OpenAI 분석
    print(f"\n[3-2] OpenAI 분석 ({MAX_WORKERS_OPENAI}개 동시)...")
    
    openai_start = time.time()
    final_results = []
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS_OPENAI) as executor:
        futures = []
        for idx, (result, (_, row)) in enumerate(zip(company_results, df_ai_only.iterrows())):
            company_name = row.get('company_name', '')
            future = executor.submit(analyze_company_with_openai, result, company_name, idx, total)
            futures.append((idx, future))
        
        final_results = [None] * len(company_results)
        for idx, future in futures:
            final_results[idx] = future.result()
    
    openai_time = time.time() - openai_start
    print(f"\n  ✓ OpenAI 분석 완료! ({openai_time:.1f}초)")
    
    # 결과 추가
    df_ai_only['표준산업분류'] = [r['표준산업분류'] for r in final_results]
    df_ai_only['연혁'] = [r['연혁'] for r in final_results]
    df_ai_only['매출액'] = [r['매출액'] for r in final_results]
    df_ai_only['고용보험가입사원수'] = [r['고용보험가입사원수'] for r in final_results]
    df_ai_only['회사소개'] = [r.get('회사소개', '') for r in final_results]
    df_ai_only['회사소개요약(OpenAI)'] = [r.get('회사소개요약', '') for r in final_results]
    df_ai_only['산업분야(OpenAI)'] = [r.get('산업분야', '') for r in final_results]

# ============================================
# 최종 저장
# ============================================
print("\n" + "=" * 80)
print("[최종 저장]")
print("=" * 80)

# 컬럼명 변경
column_rename = {
    'AI_classification': 'AI여부',
    'AI_reason': 'AI이유',
    'job_category': '직무분야',
    'company_name': '회사명',
    'position_name': '포지션명',
    'summary': '요약',
    'link': '링크',
    'position': '포지션상세',
    'content1': '주요업무',
    'content2': '자격요건',
    'content3': '우대사항',
    'content4': '혜택 및 복지'
}

# 불법 문자 제거
ILLEGAL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')
def clean_illegal_chars(value):
    if isinstance(value, str):
        return ILLEGAL_CHARS_RE.sub('', value)
    return value

# 전체 결과 저장
df_step1 = df_step1.rename(columns=column_rename)
for col in df_step1.columns:
    if df_step1[col].dtype == 'object':
        df_step1[col] = df_step1[col].apply(clean_illegal_chars)

all_file = f"{BASE_PATH}wanted_all_{now_str}.xlsx"
df_step1.to_excel(all_file, index=False, engine='openpyxl')
print(f"✓ 전체 결과: {all_file} ({len(df_step1)}개)")

# AI 관련 + 기업정보 저장
if len(df_ai_only) > 0:
    df_ai_only = df_ai_only.rename(columns=column_rename)
    for col in df_ai_only.columns:
        if df_ai_only[col].dtype == 'object':
            df_ai_only[col] = df_ai_only[col].apply(clean_illegal_chars)
    
    ai_file = f"{BASE_PATH}wanted_AI_final_{now_str}.xlsx"
    df_ai_only.to_excel(ai_file, index=False, engine='openpyxl')
    print(f"✓ AI관련 결과: {ai_file} ({len(df_ai_only)}개)")

# ============================================
# 최종 통계
# ============================================
total_time = time.time() - total_start_time

print("\n" + "=" * 80)
print("📊 최종 결과")
print("=" * 80)
print(f"총 소요 시간: {total_time:.1f}초 ({total_time/60:.1f}분)")
print(f"")
print(f"[STEP 1] 채용공고 크롤링: {len(list_data)}개")
print(f"[STEP 2] AI 공고 분류: AI관련 {ai_count}개 / 총 {len(df_step1)}개 ({ai_count/len(df_step1)*100:.1f}%)")
if len(df_ai_only) > 0:
    desc_count = sum(1 for r in final_results if r.get('회사소개'))
    print(f"[STEP 3] 기업정보 수집: {desc_count}개 / {len(df_ai_only)}개")
print("=" * 80)

print("\n🎉 모든 작업 완료!")

