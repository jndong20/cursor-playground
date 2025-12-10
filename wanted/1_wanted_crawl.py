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
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

warnings.filterwarnings('ignore')

# ============================================
# 설정
# ============================================
# 크롤링할 직무 카테고리 목록 (직무명, URL)
JOB_CATEGORIES = [
    # 개발발 카테고리

    # ('소프트웨어 엔지니어', 'https://www.wanted.co.kr/wdlist/518/10110'),
    # ('서버 개발자', 'https://www.wanted.co.kr/wdlist/518/872'),
    # ('웹 개발자', 'https://www.wanted.co.kr/wdlist/518/873'),
    # ('프론트엔드 개발자', 'https://www.wanted.co.kr/wdlist/518/669'),
    # ('자바 개발자', 'https://www.wanted.co.kr/wdlist/518/660'),
    # ('파이썬 개발자', 'https://www.wanted.co.kr/wdlist/518/899'),
    # ('머신러닝 엔지니어', 'https://www.wanted.co.kr/wdlist/518/1634'),
    # ('C,C++ 개발자', 'https://www.wanted.co.kr/wdlist/518/900'),
    # ('DevOps / 시스템 관리자', 'https://www.wanted.co.kr/wdlist/518/674'),
    # ('시스템,네트워크 관리자', 'https://www.wanted.co.kr/wdlist/518/665'),
    # ('데이터 엔지니어', 'https://www.wanted.co.kr/wdlist/518/655'),
    # ('Node.js 개발자', 'https://www.wanted.co.kr/wdlist/518/895'),
    # ('개발 매니저', 'https://www.wanted.co.kr/wdlist/518/877'),
    # ('임베디드 개발자', 'https://www.wanted.co.kr/wdlist/518/658'),
    # ('QA,테스트 엔지니어', 'https://www.wanted.co.kr/wdlist/518/676'),
    # ('데이터 사이언티스트', 'https://www.wanted.co.kr/wdlist/518/1024'),
    # ('빅데이터 엔지니어', 'https://www.wanted.co.kr/wdlist/518/1025'),
    # ('안드로이드 개발자', 'https://www.wanted.co.kr/wdlist/518/677'),
    # ('iOS 개발자', 'https://www.wanted.co.kr/wdlist/518/678'),
    # ('기술지원', 'https://www.wanted.co.kr/wdlist/518/1026'),
    # ('하드웨어 엔지니어', 'https://www.wanted.co.kr/wdlist/518/672'),
    # ('크로스플랫폼 앱 개발자', 'https://www.wanted.co.kr/wdlist/518/10111'),
    # ('프로덕트 매니저', 'https://www.wanted.co.kr/wdlist/518/876'),
    # ('블록체인 플랫폼 엔지니어', 'https://www.wanted.co.kr/wdlist/518/1027'),
    # ('DBA', 'https://www.wanted.co.kr/wdlist/518/10231'),
    # ('웹 퍼블리셔', 'https://www.wanted.co.kr/wdlist/518/939'),
    # ('영상,음성 엔지니어', 'https://www.wanted.co.kr/wdlist/518/896'),
    # ('PHP 개발자', 'https://www.wanted.co.kr/wdlist/518/893'),
    # ('.NET 개발자', 'https://www.wanted.co.kr/wdlist/518/661'),
    # ('CTO,Chief Technology Officer', 'https://www.wanted.co.kr/wdlist/518/795'),
    # ('그래픽스 엔지니어', 'https://www.wanted.co.kr/wdlist/518/898'),
    # ('ERP전문가', 'https://www.wanted.co.kr/wdlist/518/10230'),
    # ('BI 엔지니어', 'https://www.wanted.co.kr/wdlist/518/1022'),
    # ('VR 엔지니어', 'https://www.wanted.co.kr/wdlist/518/10112'),
    # ('루비온레일즈 개발자', 'https://www.wanted.co.kr/wdlist/518/894'),
    # ('테크니컬 라이터', 'https://www.wanted.co.kr/wdlist/518/10536'),
    # ('CIO,Chief Information Officer', 'https://www.wanted.co.kr/wdlist/518/793'),
    # ('RPA 엔지니어', 'https://www.wanted.co.kr/wdlist/518/10531'),

   # 게임 카테고리 추가,   enumerate(list_data) 변경
     #('게임 기획자', 'https://www.wanted.co.kr/wdlist/959/892'),
     #('게임 그래픽 디자이너', 'https://www.wanted.co.kr/wdlist/959/880'),
     #('게임 클라이언트 개발자', 'https://www.wanted.co.kr/wdlist/959/961'),
     #('게임 아티스트', 'https://www.wanted.co.kr/wdlist/959/881'),
     #('게임 서버 개발자', 'https://www.wanted.co.kr/wdlist/959/960'),
     #('모바일 게임 개발자', 'https://www.wanted.co.kr/wdlist/959/962'),
     #('언리얼 개발자', 'https://www.wanted.co.kr/wdlist/959/897'),
     #('유니티 개발자', 'https://www.wanted.co.kr/wdlist/959/878'),
     #('게임운영자(GM)', 'https://www.wanted.co.kr/wdlist/959/958'),

    # 제조·생산
    ('품질 관리자', 'https://www.wanted.co.kr/wdlist/522/704'),
    ('생산 관리자', 'https://www.wanted.co.kr/wdlist/522/701'),
    ('자재관리·구매', 'https://www.wanted.co.kr/wdlist/522/699'),
    ('기계·설비·설계', 'https://www.wanted.co.kr/wdlist/522/700'),
    ('섬유·의류·패션', 'https://www.wanted.co.kr/wdlist/522/10113'),
    ('공정 관리자', 'https://www.wanted.co.kr/wdlist/522/703'),
    ('제조 엔지니어', 'https://www.wanted.co.kr/wdlist/522/698'),
    ('생산직 종사자', 'https://www.wanted.co.kr/wdlist/522/702'),
    ('반도체·디스플레이', 'https://www.wanted.co.kr/wdlist/522/10114'),
    ('안전 관리자', 'https://www.wanted.co.kr/wdlist/522/705'),
    ('화학자', 'https://www.wanted.co.kr/wdlist/522/696'),
    ('기계제작 기술자', 'https://www.wanted.co.kr/wdlist/522/697'),
    ('조립 기술자', 'https://www.wanted.co.kr/wdlist/522/695'),
    ('제조 테스트 엔지니어', 'https://www.wanted.co.kr/wdlist/522/706'),

    
]

MAX_WORKERS = 10  # 병렬 처리 워커 수

# 엑셀 불법 문자 제거용
ILLEGAL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')

def clean_illegal_chars(value):
    """엑셀에서 허용되지 않는 제어 문자 제거"""
    if isinstance(value, str):
        return ILLEGAL_CHARS_RE.sub('', value)
    return value

# ============================================
# 상세 페이지 크롤링 함수
# ============================================
def crawl_detail_page(row_data, progress_lock, progress_info):
    """상세 페이지 크롤링 (requests + __NEXT_DATA__ JSON)"""
    
    idx = row_data['idx']
    href = row_data['link']
    
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
                
                # 포지션 상세 (description 필드에서 가져옴)
                description = job_detail.get('description', '')
                result['position'] = description.replace('\n', ' ').strip() if description else ''
                
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
        # 포지션 상세 폴백
        if not result['position']:
            try:
                # article.JobDescription_JobDescription__s2Keo 내부의 첫 번째 span.wds-h4ga6o 내용
                article = soup.find('article', class_=lambda x: x and 'JobDescription_JobDescription' in x)
                if article:
                    # 주요업무/자격요건 등 h3 태그가 있는 div 이전의 span 내용 가져오기
                    wrapper = article.find('div', class_=lambda x: x and 'paragraph__wrapper' in x)
                    if wrapper:
                        first_span = wrapper.find('span', class_='wds-h4ga6o', recursive=False)
                        if not first_span:
                            first_span = wrapper.find('span', class_='wds-h4ga6o')
                        if first_span:
                            # h3 태그가 없는 첫 번째 span 내용만 가져오기
                            inner_span = first_span.find('span')
                            if inner_span and not inner_span.find('h3'):
                                result['position'] = inner_span.get_text(' ', strip=True).replace('• ', '')
            except:
                pass
        
        if not result['content1']:
            try:
                content1_div = soup.find('h3', string=lambda x: x and '주요업무' in x)
                if content1_div:
                    parent = content1_div.find_parent('div')
                    if parent:
                        result['content1'] = parent.get_text(' ', strip=True).replace('주요업무', '').replace('• ', '').strip()
            except:
                pass
            
            try:
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
        progress_info['completed'] += 1
        total = progress_info['total']
        completed = progress_info['completed']
        status = "✓" if result['content1'] or result['content2'] else "-"
        print(f"\r  [{completed}/{total}] 상세 크롤링 중... ({completed/total*100:.0f}%) {status}", end='', flush=True)
    
    return result


def crawl_job_list(job_category, url, driver):
    """특정 직무 카테고리의 채용공고 리스트 크롤링 (Selenium)"""
    
    driver.get(url)
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
            wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            element_xpath = xpath
            element_found = True
            break
        except Exception:
            continue
    
    if not element_found:
        element_xpath = alternative_xpaths[0]
    
    # 스크롤 다운
    SCROLL_PAUSE_TIME = 1.5
    try:
        last_height = driver.execute_script("return document.body.scrollHeight")
    except InvalidSessionIdException:
        driver.quit()
        return []
    
    same_count = 0
    
    while True:
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SCROLL_PAUSE_TIME)
            new_height = driver.execute_script("return document.body.scrollHeight")
        except (InvalidSessionIdException, WebDriverException):
            break
        
        if new_height == last_height:
            same_count += 1
        else:
            same_count = 0
        
        if same_count >= 2:
            break
        
        last_height = new_height
    
    # 요소 수집
    elements = []
    try:
        elements = driver.find_elements(By.XPATH, element_xpath)
    except Exception:
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
                'job_category': job_category,
                'company_id': company_id,
                'company_name': company_name,
                'position_name': position_name,
                'position_id': position_id,
                'link': href or '',
            })
        
        except Exception:
            continue
    
    return list_data


def crawl_detail_pages(list_data):
    """상세 페이지 병렬 크롤링"""
    
    if not list_data:
        return []
    
    # 진행 상황 추적
    progress_lock = threading.Lock()
    progress_info = {'completed': 0, 'total': len(list_data)}
    
    # row_data 준비
    row_data_list = []
    for idx, row in enumerate(list_data):
        row_data_list.append({
            'idx': idx,
            'link': row['link'],
            'company_name': row.get('company_name', ''),
        })
    
    detail_results = []
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(crawl_detail_page, rd, progress_lock, progress_info) for rd in row_data_list]
        
        for future in as_completed(futures):
            detail_results.append(future.result())
    
    # 결과 정렬 (원래 순서대로)
    detail_results.sort(key=lambda x: x['idx'])
    
    print()  # 줄바꿈
    
    return detail_results


def merge_list_and_detail(list_data, detail_results):
    """리스트 데이터와 상세 데이터 병합"""
    
    merged_data = []
    
    for i, (list_item, detail_item) in enumerate(zip(list_data, detail_results)):
        merged = {**list_item}
        merged['position'] = detail_item.get('position', '')
        merged['content1'] = detail_item.get('content1', '')
        merged['content2'] = detail_item.get('content2', '')
        merged['content3'] = detail_item.get('content3', '-')
        merged['content4'] = detail_item.get('content4', '-')
        merged['period'] = detail_item.get('period', '-')
        merged['skill'] = detail_item.get('skill', '')
        merged_data.append(merged)
    
    return merged_data


# ============================================
# 메인 실행
# ============================================
if __name__ == "__main__":
    print("=" * 80)
    print("🚀 원티드 채용공고 크롤링 (전체 직무 카테고리)")
    print(f"   총 {len(JOB_CATEGORIES)}개 직무 카테고리")
    print("=" * 80)
    
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    start_total_time = time.time()
    
    # Chrome 드라이버 한 번만 초기화 (전체 카테고리에서 재사용)
    print("\n🌐 Chrome 드라이버 초기화 중...")
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    # chrome_options.add_argument('--headless')  # 백그라운드 실행 원하면 주석 해제
    
    driver = webdriver.Chrome(options=chrome_options)
    print("✓ Chrome 드라이버 준비 완료")
    
    all_data = []  # 모든 직무의 데이터를 누적
    
    try:
        for category_idx, (job_category, url) in enumerate(JOB_CATEGORIES, 1):
            print(f"\n{'='*80}")
            print(f"[{category_idx}/{len(JOB_CATEGORIES)}] 📋 {job_category}")
            print(f"URL: {url}")
            print("="*80)
            
            # 1단계: 리스트 페이지 크롤링
            print("\n[1단계] 리스트 페이지 스크롤 및 수집 중...")
            start_time = time.time()
            list_data = crawl_job_list(job_category, url, driver)
            list_time = time.time() - start_time
            print(f"✓ {len(list_data)}개 공고 발견 ({list_time:.1f}초)")
            
            if not list_data:
                print("⚠ 공고가 없습니다. 다음 카테고리로 넘어갑니다.")
                continue
            
            # 2단계: 상세 페이지 병렬 크롤링
            print(f"\n[2단계] 상세 페이지 병렬 크롤링 ({MAX_WORKERS}개 동시 처리)")
            start_time = time.time()
            detail_results = crawl_detail_pages(list_data)
            detail_time = time.time() - start_time
            
            content_count = sum(1 for r in detail_results if r.get('content1') or r.get('content2'))
            print(f"✓ 상세 크롤링 완료: {content_count}/{len(detail_results)}개 ({detail_time:.1f}초)")
            
            # 3단계: 데이터 병합
            merged_data = merge_list_and_detail(list_data, detail_results)
            all_data.extend(merged_data)
            
            print(f"✓ 누적 데이터: {len(all_data)}개")
    
    finally:
        # Chrome 드라이버 종료
        print("\n🔚 Chrome 드라이버 종료 중...")
        driver.quit()
        print("✓ Chrome 드라이버 종료 완료")
    
    # ============================================
    # 최종 저장
    # ============================================
    print("\n" + "=" * 80)
    print("📊 최종 결과 저장 중...")
    print("=" * 80)
    
    df_final = pd.DataFrame(all_data)
    
    # 불법 문자 제거
    print("  → 불법 문자 정리 중...")
    for col in df_final.columns:
        if df_final[col].dtype == 'object':
            df_final[col] = df_final[col].apply(clean_illegal_chars)
    
    # 최종 저장
    final_save_path = f"C://Users//MULTICAMPUS//Desktop//curosr-playground//wanted//wanted_all_jobs_{now_str}.xlsx"
    df_final.to_excel(final_save_path, index=False, engine='openpyxl')
    
    total_elapsed_time = time.time() - start_total_time
    
    # 카테고리별 통계
    print("\n" + "=" * 80)
    print("📊 크롤링 완료!")
    print("=" * 80)
    print(f"총 직무 카테고리: {len(JOB_CATEGORIES)}개")
    print(f"총 공고 수: {len(df_final)}개")
    
    # 직무별 통계
    print("\n📋 직무별 공고 수:")
    category_counts = df_final['job_category'].value_counts()
    for cat, cnt in category_counts.items():
        print(f"  - {cat}: {cnt}개")
    
    print(f"\n총 소요 시간: {total_elapsed_time/60:.1f}분 ({total_elapsed_time:.0f}초)")
    print(f"\n✓ 최종 파일: {final_save_path}")
    print("\n🎉 전체 작업 완료!")
