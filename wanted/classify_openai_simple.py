"""
OpenAI API를 사용한 AI 공고 분류 및 요약
"""
import pandas as pd
from datetime import datetime
import os
import sys
from openai import OpenAI
import time

print("=" * 70, flush=True)
print("OpenAI API를 사용한 AI 공고 분류 및 요약", flush=True)
print("=" * 70, flush=True)

# API 키 설정 - config.env 파일에서 직접 읽기
api_key = None

# 1. config.env 파일에서 읽기 시도
try:
    config_path = "../API/config.env"
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('OPENAI_API_KEY='):
                    api_key = line.split('=', 1)[1].strip()
                    print("✓ config.env 파일에서 API 키를 읽었습니다.", flush=True)
                    break
except Exception as e:
    print(f"config.env 읽기 실패: {e}", flush=True)

# 2. 환경 변수에서 읽기 시도
if not api_key:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print("✓ 환경 변수에서 API 키를 읽었습니다.", flush=True)

# 3. 직접 입력
if not api_key:
    print("\nAPI 키를 찾을 수 없습니다.", flush=True)
    api_key = input("OpenAI API 키를 입력하세요: ").strip()

if not api_key:
    print("오류: API 키가 제공되지 않았습니다.", flush=True)
    sys.exit(1)

try:
    client = OpenAI(api_key=api_key)
    print("✓ OpenAI 클라이언트 초기화 완료", flush=True)
except Exception as e:
    print(f"오류: OpenAI 클라이언트 초기화 실패 - {e}", flush=True)
    sys.exit(1)

# 엑셀 파일 읽기
input_file = "wanted_final_20251205_172607.xlsx"
print(f"\n파일 읽기: {input_file}", flush=True)

try:
    df = pd.read_excel(input_file, engine='openpyxl')
    print(f"✓ 총 {len(df)}개 공고 로드 완료", flush=True)
except Exception as e:
    print(f"오류: 파일 읽기 실패 - {e}", flush=True)
    sys.exit(1)

# 텍스트 합치기
print("\n1단계: 텍스트 합치는 중...", flush=True)
def create_combined_text(row):
    columns = ['position_name', 'position', 'content1', 'content2', 'content3', 'content4']
    texts = []
    for col in columns:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            texts.append(str(row[col]).strip())
    return " ".join(texts)

df['combined_text'] = df.apply(create_combined_text, axis=1)
print("✓ 텍스트 합치기 완료", flush=True)

# OpenAI API로 분석
print("\n2단계: OpenAI API로 각 공고 분석 중...", flush=True)
print("(시간이 걸릴 수 있습니다...)", flush=True)

def analyze_with_openai(text, idx, total):
    """OpenAI API로 AI 여부 판단 및 요약 생성"""
    if not text or pd.isna(text) or len(str(text).strip()) < 10:
        return {
            'classification': 'AI비관련',
            'reason': '내용이 부족합니다.',
            'summary': ''
        }
    
    prompt = f"""다음 채용 공고를 분석해주세요:

{text[:2000]}

작업:
1. AI 관련 직무 여부 판단 (AI관련/AI비관련)
   - AI 키워드: AI, 인공지능, 머신러닝, Machine Learning, 딥러닝, Deep Learning, LLM, Agent, RAG, Computer Vision 등
2. 판단 근거 (1-2문장)
3. 공고 내용 요약 (150자 이내)

응답 형식:
분류: [AI관련 또는 AI비관련]
근거: [판단 근거]
요약: [공고 요약]"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 채용 공고를 분석하는 전문가입니다. 간결하고 정확하게 답변하세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # 응답 파싱
        classification = 'AI비관련'
        reason = ''
        summary = ''
        
        lines = result_text.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('분류:'):
                if 'AI관련' in line:
                    classification = 'AI관련'
                else:
                    classification = 'AI비관련'
            elif line.startswith('근거:'):
                reason = line.replace('근거:', '').strip()
            elif line.startswith('요약:'):
                summary = line.replace('요약:', '').strip()
        
        return {
            'classification': classification,
            'reason': reason,
            'summary': summary
        }
        
    except Exception as e:
        print(f"  오류: {str(e)[:50]}", flush=True)
        return {
            'classification': 'AI비관련',
            'reason': f'분석 실패: {str(e)[:30]}',
            'summary': ''
        }

# 각 공고 분석
results = []
for idx, row in df.iterrows():
    company_name = row.get('company_name', '')
    position_name = row.get('position_name', '')
    combined_text = row.get('combined_text', '')
    
    print(f"[{idx+1}/{len(df)}] {company_name} - {position_name}", flush=True)
    
    result = analyze_with_openai(combined_text, idx+1, len(df))
    results.append(result)
    
    print(f"  → {result['classification']}: {result['reason'][:50]}...", flush=True)
    
    # Rate limit 방지
    time.sleep(1)

# 결과 추가
print("\n3단계: 결과를 DataFrame에 추가 중...", flush=True)
df['AI_classification'] = [r['classification'] for r in results]
df['AI_reason'] = [r['reason'] for r in results]
df['summary'] = [r['summary'] for r in results]

# 통계
ai_count = (df['AI_classification'] == 'AI관련').sum()
non_ai_count = (df['AI_classification'] == 'AI비관련').sum()

print("\n" + "=" * 70, flush=True)
print("분류 결과", flush=True)
print("=" * 70, flush=True)
print(f"AI관련: {ai_count}개 ({ai_count/len(df)*100:.1f}%)", flush=True)
print(f"AI비관련: {non_ai_count}개 ({non_ai_count/len(df)*100:.1f}%)", flush=True)
print(f"총: {len(df)}개", flush=True)
print("=" * 70, flush=True)

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
output_file = f"wanted_classified_openai_{now_str}.xlsx"

print(f"\n4단계: 엑셀 파일 저장 중...", flush=True)
df_final.to_excel(output_file, index=False, engine='openpyxl')
print(f"✓ 분류 완료 엑셀 저장: {output_file}", flush=True)

# AI관련 공고만 저장
ai_only_file = f"wanted_AI_only_openai_{now_str}.xlsx"
df_ai_only = df_final[df_final['AI_classification'] == 'AI관련']
df_ai_only.to_excel(ai_only_file, index=False, engine='openpyxl')
print(f"✓ AI관련 공고만 저장: {ai_only_file} ({len(df_ai_only)}개)", flush=True)

print("\n" + "=" * 70, flush=True)
print("작업 완료!", flush=True)
print("=" * 70, flush=True)

