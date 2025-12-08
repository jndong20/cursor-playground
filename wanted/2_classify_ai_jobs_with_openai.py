import pandas as pd
from datetime import datetime
import os
from pathlib import Path
from openai import OpenAI
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# config.env 파일에서 환경 변수 로드
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / 'API' / 'config.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print("✓ config.env 파일에서 API 키를 로드했습니다.")
    else:
        print("⚠ config.env 파일이 없습니다.")
except ImportError:
    print("⚠ python-dotenv가 설치되지 않았습니다.")
except Exception as e:
    print(f"⚠ config.env 파일 로드 중 오류: {e}")

# API 키 확인
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("\n환경 변수에서 API 키를 찾지 못했습니다.")
    api_key = input("OpenAI API 키를 입력하세요: ").strip()

if not api_key:
    print("오류: API 키가 제공되지 않았습니다.")
    exit(1)

client = OpenAI(api_key=api_key)

print("\n" + "=" * 70)
print("OpenAI API를 사용한 AI 공고 분류 및 요약 (병렬 처리) 🚀")
print("=" * 70)

# ============================================
# 설정
# ============================================
MAX_WORKERS = 5  # 병렬 처리 워커 수 (OpenAI Rate limit 고려)

# 엑셀 파일 경로
input_file = "2.소프트웨어 엔지니어_wanted_20251208_172702.xlsx"

print(f"\n파일 읽기: {input_file}")
df = pd.read_excel(input_file, engine='openpyxl')
print(f"✓ 총 {len(df)}개 공고 로드 완료")

# 텍스트 합치기
def create_combined_text(row):
    """여러 컬럼을 합쳐서 하나의 텍스트로 만들기"""
    columns = ['position_name', 'position', 'content1', 'content2', 'content3', 'content4']
    texts = []
    
    for col in columns:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            texts.append(str(row[col]).strip())
    
    return " ".join(texts)

print("\n텍스트 합치는 중...")
df['combined_text'] = df.apply(create_combined_text, axis=1)

# 진행 상황 추적
progress_lock = threading.Lock()
completed_count = 0

# OpenAI API를 사용한 분류 및 요약 (병렬 처리용)
def analyze_with_openai(task_data, retry=3):
    """OpenAI API로 AI 여부 판단 및 요약 생성"""
    global completed_count
    
    idx = task_data['idx']
    text = task_data['text']
    company_name = task_data['company_name']
    position_name = task_data['position_name']
    total = task_data['total']
    
    result = {
        'idx': idx,
        'classification': 'AI비관련',
        'reason': '',
        'summary': ''
    }
    
    if not text or pd.isna(text) or len(str(text).strip()) < 10:
        result['reason'] = '내용이 부족합니다.'
        with progress_lock:
            completed_count += 1
            print(f"\r[{completed_count}/{total}] 분석 중... ({completed_count/total*100:.0f}%)", end='', flush=True)
        return result
    
    prompt = f"""다음은 채용 공고 내용입니다. 아래 작업을 수행해주세요:

1. 이 공고가 AI 관련 직무인지 판단 (AI관련/AI비관련)
2. 판단 근거를 간단히 설명 (1-2문장)
3. 공고 내용을 150자 이내로 요약

AI 관련 키워드: AI, 인공지능, 머신러닝, Machine Learning, 딥러닝, Deep Learning, LLM, 대규모 언어 모델, 프롬프트 엔지니어링, Agent, 에이전트, RAG, MCP, 비전 AI, 머신비전, 영상 처리 알고리즘, Computer Vision

채용 공고 내용:
{text[:2000]}

아래 형식으로 답변해주세요:
분류: [AI관련 또는 AI비관련]
근거: [판단 근거]
요약: [공고 요약]
"""
    
    for attempt in range(retry):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 채용 공고를 분석하는 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # 응답 파싱
            lines = result_text.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('분류:'):
                    classification_text = line.replace('분류:', '').strip()
                    if 'AI관련' in classification_text:
                        result['classification'] = 'AI관련'
                    else:
                        result['classification'] = 'AI비관련'
                elif line.startswith('근거:'):
                    result['reason'] = line.replace('근거:', '').strip()
                elif line.startswith('요약:'):
                    result['summary'] = line.replace('요약:', '').strip()
            
            break
            
        except Exception as e:
            if attempt < retry - 1:
                time.sleep(2)
            else:
                result['reason'] = f'분석 실패: {str(e)[:50]}'
    
    # 진행 상황 업데이트
    with progress_lock:
        completed_count += 1
        status = "AI" if result['classification'] == 'AI관련' else "-"
        print(f"\r[{completed_count}/{total}] 분석 중... ({completed_count/total*100:.0f}%) {status}", end='', flush=True)
    
    return result

# ============================================
# 병렬 처리로 OpenAI API 호출
# ============================================
print(f"\n[병렬 처리] OpenAI API로 공고 분석 중... ({MAX_WORKERS}개 동시 처리) 🚀")

# 작업 데이터 준비
task_list = []
for idx, row in df.iterrows():
    task_list.append({
        'idx': idx,
        'text': row.get('combined_text', ''),
        'company_name': row.get('company_name', ''),
        'position_name': row.get('position_name', ''),
        'total': len(df)
    })

# 병렬 실행
start_time = time.time()
results = []

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = [executor.submit(analyze_with_openai, task) for task in task_list]
    
    for future in as_completed(futures):
        results.append(future.result())

# 결과 정렬 (원래 순서대로)
results.sort(key=lambda x: x['idx'])

elapsed_time = time.time() - start_time
print(f"\n✓ 분석 완료! ({elapsed_time:.1f}초, {elapsed_time/len(df):.2f}초/건)")

# 결과를 DataFrame에 추가
df['AI_classification'] = [r['classification'] for r in results]
df['AI_reason'] = [r['reason'] for r in results]
df['summary'] = [r['summary'] for r in results]

# 통계
ai_count = (df['AI_classification'] == 'AI관련').sum()
non_ai_count = (df['AI_classification'] == 'AI비관련').sum()

print("\n" + "=" * 70)
print("📊 분류 결과")
print("=" * 70)
print(f"⏱ 소요 시간: {elapsed_time:.1f}초 ({elapsed_time/len(df):.2f}초/건)")
print(f"AI관련: {ai_count}개 ({ai_count/len(df)*100:.1f}%)")
print(f"AI비관련: {non_ai_count}개 ({non_ai_count/len(df)*100:.1f}%)")
print(f"총: {len(df)}개")
print("=" * 70)

# 컬럼 순서 조정
column_order = [
    'AI_classification', 'AI_reason', 'job_category', 'company_name', 'position_name', 
    'summary', 'link', 'position', 'content1', 'content2', 'content3', 
    'content4', 'period', 'skill'
]

existing_columns = [col for col in column_order if col in df.columns]
remaining_columns = [col for col in df.columns if col not in existing_columns and col != 'combined_text']
final_column_order = existing_columns + remaining_columns

df_final = df[final_column_order]

# 저장
now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"3_wanted_classified_openai_{now_str}.xlsx"

print(f"\n저장 중: {output_file}")
df_final.to_excel(output_file, index=False, engine='openpyxl')
print(f"✓ 분류 완료 엑셀 저장: {output_file}")

# AI관련 공고만 저장
# ai_only_file = f"wanted_AI_only_openai_{now_str}.xlsx"
# df_ai_only = df_final[df_final['AI_classification'] == 'AI관련']
# df_ai_only.to_excel(ai_only_file, index=False, engine='openpyxl')
# print(f"✓ AI관련 공고만 저장: {ai_only_file} ({len(df_ai_only)}개)")

print("\n🎉 작업 완료!")
