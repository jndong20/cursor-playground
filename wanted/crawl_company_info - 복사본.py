import pandas as pd
from datetime import datetime
import time
import requests
from bs4 import BeautifulSoup
import re
import json
from pathlib import Path
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# OpenAI API 준비
try:
    from openai import OpenAI
except ImportError:
    print("openai 패키지가 필요합니다. pip install openai 를 실행해주세요.")
    sys.exit(1)

def get_openai_api_key():
    api_key = os.getenv("OPENAI_API_KEY", None)
    config_path = "../API/config.env"
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
print("원티드 기업 정보 크롤링 (병렬 처리) 🚀🚀🚀")
print("=" * 70)

# 엑셀 파일 경로
input_file = "wanted_classified_openai_20251208_105624.xlsx"

print(f"\n파일 읽기: {input_file}")
df = pd.read_excel(input_file, engine='openpyxl')
print(f"✓ 총 {len(df)}개 레코드 로드 완료")

# 테스트용: 처음 N개만 처리 (전체 처리하려면 이 줄을 주석 처리하세요)
df = df.head(10)
print(f"⚠ 테스트 모드: {len(df)}개만 처리합니다")

# 컬럼 확인
print(f"\n컬럼 목록: {list(df.columns)}")

# P 컬럼 확인
if len(df.columns) >= 16:
    company_id_col = df.columns[15]
    print(f"P 컬럼명: {company_id_col}")
else:
    if 'company_id' in df.columns:
        company_id_col = 'company_id'
        print(f"company_id 컬럼을 찾았습니다.")
    else:
        print("오류: company_id 컬럼을 찾을 수 없습니다.")
        exit(1)

# 병렬 처리 설정
MAX_WORKERS_CRAWL = 10  # 크롤링 동시 처리 수
MAX_WORKERS_OPENAI = 5  # OpenAI API 동시 처리 수

# 진행 상황 추적용
progress_lock = threading.Lock()
completed_count = 0

def crawl_company_info(company_id, company_name, idx, total):
    """원티드 기업 정보 크롤링 (requests + BeautifulSoup)"""
    global completed_count
    
    result = {
        'idx': idx,
        'company_id': company_id,
        'company_name': company_name,
        '표준산업분류': '',
        '연혁': '',
        '매출액': '',
        '고용보험가입사원수': '',
        '회사소개': ''
    }
    
    if pd.isna(company_id):
        return result
    
    url = f"https://www.wanted.co.kr/company/{company_id}"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return result
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 방법 1: __NEXT_DATA__ JSON에서 추출 (가장 빠름)
        next_data_script = soup.find('script', id='__NEXT_DATA__')
        
        if next_data_script:
            try:
                json_data = json.loads(next_data_script.string)
                props = json_data.get('props', {})
                page_props = props.get('pageProps', {})
                company_data = page_props.get('company', {})
                
                # 회사소개
                description = company_data.get('description', '')
                if description:
                    result['회사소개'] = description
                
                # 기업 정보 테이블
                info_table = company_data.get('companyInfoTable', [])
                for item in info_table:
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
                
            except json.JSONDecodeError:
                pass
        
        # 방법 2: HTML 직접 파싱 (폴백)
        if not result['회사소개']:
            desc_div = soup.find("div", attrs={"data-testid": "company-info-description"})
            if desc_div:
                result['회사소개'] = desc_div.get_text("\n", strip=True)
        
        if not result['표준산업분류']:
            all_sections = soup.find_all('section')
            for section in all_sections:
                h2 = section.find('h2')
                if h2 and h2.get_text(strip=True) == '기업 정보':
                    dl_tags = section.find_all('dl')
                    for dl in dl_tags:
                        dt = dl.find('dt')
                        dd = dl.find('dd')
                        if dt and dd:
                            key = dt.get_text(strip=True)
                            value = dd.get_text(strip=True)
                            
                            if key == '표준산업분류':
                                result['표준산업분류'] = value
                            elif key == '연혁':
                                result['연혁'] = value
                            elif key == '매출액':
                                result['매출액'] = value
                            elif key == '고용보험 가입 사원수':
                                result['고용보험가입사원수'] = value
                    break
        
    except Exception as e:
        pass
    
    # 진행 상황 업데이트
    with progress_lock:
        completed_count += 1
        status = "✓" if result['회사소개'] or result['표준산업분류'] else "-"
        print(f"\r[크롤링] {completed_count}/{total} 완료 ({completed_count/total*100:.0f}%) - {company_name[:15]} {status}", end='', flush=True)
    
    return result

def analyze_with_openai(result, idx, total):
    """OpenAI로 회사소개 요약 및 산업분야 추출"""
    desc = result.get('회사소개', '')
    company_name = result.get('company_name', '')
    
    summary = ''
    industry = ''
    
    if desc and desc.strip():
        try:
            # 요약 생성
            completion = client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {"role": "system", "content": "다음 회사 소개글을 읽고, 핵심 내용을 150자 이내로 간결하게 요약해 주세요. 회사의 주요 사업, 제품/서비스, 특징을 중심으로 요약하세요."},
                    {"role": "user", "content": f"[회사명: {company_name}]\n회사소개:\n{desc}"},
                ],
                max_tokens=200,
                temperature=0.3
            )
            summary = completion.choices[0].message.content.strip()
        except:
            pass
        
        try:
            # 산업분야 추출
            completion = client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {"role": "system", "content": "다음 회사 소개글을 읽고, 회사의 산업분야를 한두 단어로 답해주세요. 예: 게임, 소프트웨어, 헬스케어, 제조, 물류, 교육 등. 알 수 없으면 '미상'"},
                    {"role": "user", "content": f"[회사명: {company_name}]\n회사소개:\n{desc}"},
                ],
                max_tokens=16,
                temperature=0
            )
            industry = completion.choices[0].message.content.strip().split('\n')[0].strip()
            industry = industry.replace("산업분야:", "").replace("산업:", "").strip()
        except:
            pass
    
    result['회사소개요약'] = summary
    result['산업분야'] = industry
    
    print(f"\r[OpenAI] {idx+1}/{total} 분석 완료 - {company_name[:15]} → {industry}", end='', flush=True)
    
    return result

print(f"\n🚀 병렬 처리 시작 (크롤링: {MAX_WORKERS_CRAWL}개, OpenAI: {MAX_WORKERS_OPENAI}개 동시 처리)")
print("-" * 70)

start_time = time.time()

# 1단계: 병렬 크롤링
print("\n[1단계] 기업 정보 크롤링 중...")
crawl_results = []
total = len(df)

with ThreadPoolExecutor(max_workers=MAX_WORKERS_CRAWL) as executor:
    futures = []
    for idx, row in df.iterrows():
        company_id = row[company_id_col]
        company_name = row.get('company_name', '') if 'company_name' in row else ""
        future = executor.submit(crawl_company_info, company_id, company_name, idx, total)
        futures.append(future)
    
    for future in as_completed(futures):
        crawl_results.append(future.result())

# 결과를 원래 순서대로 정렬
crawl_results.sort(key=lambda x: x['idx'])

crawl_time = time.time() - start_time
print(f"\n✓ 크롤링 완료! ({crawl_time:.1f}초)")

# 2단계: 병렬 OpenAI 분석
print("\n[2단계] OpenAI 분석 중...")
completed_count = 0  # 리셋

openai_start = time.time()

with ThreadPoolExecutor(max_workers=MAX_WORKERS_OPENAI) as executor:
    futures = []
    for idx, result in enumerate(crawl_results):
        future = executor.submit(analyze_with_openai, result, idx, total)
        futures.append((idx, future))
    
    final_results = [None] * len(crawl_results)
    for idx, future in futures:
        final_results[idx] = future.result()

openai_time = time.time() - openai_start
print(f"\n✓ OpenAI 분석 완료! ({openai_time:.1f}초)")

total_time = time.time() - start_time

# 결과를 DataFrame에 추가
df['표준산업분류'] = [r['표준산업분류'] for r in final_results]
df['연혁'] = [r['연혁'] for r in final_results]
df['매출액'] = [r['매출액'] for r in final_results]
df['고용보험가입사원수'] = [r['고용보험가입사원수'] for r in final_results]
df['회사소개'] = [r.get('회사소개', '') for r in final_results]
df['회사소개요약(OpenAI)'] = [r.get('회사소개요약', '') for r in final_results]
df['산업분야(OpenAI)'] = [r.get('산업분야', '') for r in final_results]

# 통계
desc_count = sum(1 for r in final_results if r.get('회사소개'))
info_count = sum(1 for r in final_results if r['표준산업분류'])
summary_count = sum(1 for r in final_results if r.get('회사소개요약'))
industry_count = sum(1 for r in final_results if r.get('산업분야') and r.get('산업분야') != '미상')

print("\n" + "=" * 70)
print("📊 크롤링 결과")
print("=" * 70)
print(f"⏱ 총 소요 시간: {total_time:.1f}초 ({total_time/len(df):.2f}초/건)")
print(f"   - 크롤링: {crawl_time:.1f}초")
print(f"   - OpenAI: {openai_time:.1f}초")
print(f"")
print(f"회사소개 수집: {desc_count}개 ({desc_count/len(df)*100:.1f}%)")
print(f"기업정보 수집: {info_count}개 ({info_count/len(df)*100:.1f}%)")
print(f"OpenAI 요약: {summary_count}개")
print(f"OpenAI 산업분야: {industry_count}개")
print(f"총 처리: {len(df)}개")
print("=" * 70)

# 저장
now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"wanted_AI_with_company_info_{now_str}.xlsx"

# 엑셀 저장 전 불법 문자 제거 (openpyxl 오류 방지)
ILLEGAL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')

def clean_illegal_chars(value):
    """엑셀에서 허용되지 않는 제어 문자 제거"""
    if isinstance(value, str):
        return ILLEGAL_CHARS_RE.sub('', value)
    return value

print(f"\n저장 중: {output_file}")

# 컬럼명 변경
column_rename = {
    'AI_classification':'AI여부',
    'AI_reason':'AI이유',
    'job_category':'직무분야',
    'company_name':'회사명',
    'position_name':'포지션명',
    'summary':'요약',
    'link':'링크',
    'position':'포지션상세',
    'content1':'주요업무',
    'content2':'자격요건',
    'content3':'우대사항',
    'content4':'혜택 및 복지'
}
df = df.rename(columns=column_rename)
print("  → 컬럼명 변경 완료")

# 모든 문자열 컬럼에서 불법 문자 제거
print("  → 불법 문자 정리 중...")
for col in df.columns:
    if df[col].dtype == 'object':
        df[col] = df[col].apply(clean_illegal_chars)

df.to_excel(output_file, index=False, engine='openpyxl')
print(f"✓ 완료: {output_file}")

print("\n🎉 작업 완료!")
