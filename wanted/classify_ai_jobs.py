import pandas as pd
import re
from datetime import datetime
import sys

print("스크립트 시작...", flush=True)

# 엑셀 파일 경로
input_file = "wanted_final_20251205_172607.xlsx"

# 엑셀 파일 읽기
print("엑셀 파일 읽는 중...", flush=True)
try:
    df = pd.read_excel(input_file, engine='openpyxl')
    print(f"총 {len(df)}개 공고 로드 완료", flush=True)
except Exception as e:
    print(f"파일 읽기 오류: {e}", flush=True)
    sys.exit(1)

# AI 관련 키워드 정의
ai_keywords = [
    "AI", "인공지능", "머신러닝", "Machine Learning", "딥러닝", "Deep Learning",
    "LLM", "대규모 언어 모델", "프롬프트 엔지니어링", "Prompt Engineering",
    "Agent", "에이전트", "RAG", "MCP",
    "비전 AI", "머신비전", "영상 처리 알고리즘", "Computer Vision"
]

# 키워드를 소문자로 변환 (대소문자 구분 없이 검색)
ai_keywords_lower = [keyword.lower() for keyword in ai_keywords]

def create_combined_text(row):
    """여러 컬럼을 합쳐서 하나의 텍스트로 만들기"""
    columns = ['position_name', 'position', 'content1', 'content2', 'content3', 'content4']
    texts = []
    
    for col in columns:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            texts.append(str(row[col]).strip())
    
    return " ".join(texts)

def classify_ai_related(text):
    """텍스트에 AI 관련 키워드가 있는지 확인"""
    if not text or pd.isna(text):
        return "AI비관련"
    
    text_lower = str(text).lower()
    
    # AI 키워드가 하나라도 있으면 AI관련
    for keyword in ai_keywords_lower:
        if keyword in text_lower:
            return "AI관련"
    
    return "AI비관련"

def create_summary(text, max_length=200):
    """텍스트 요약 생성 (간단한 버전 - 처음 N자 추출)"""
    if not text or pd.isna(text):
        return ""
    
    text = str(text).strip()
    
    # 긴 텍스트는 요약
    if len(text) > max_length:
        return text[:max_length] + "..."
    else:
        return text

# 새로운 컬럼 추가
print("\n데이터 처리 중...")
df['combined_text'] = df.apply(create_combined_text, axis=1)
df['AI_classification'] = df['combined_text'].apply(classify_ai_related)
df['summary'] = df['combined_text'].apply(create_summary)

# 통계 출력
ai_count = (df['AI_classification'] == 'AI관련').sum()
non_ai_count = (df['AI_classification'] == 'AI비관련').sum()

print("\n" + "=" * 70)
print("분류 결과")
print("=" * 70)
print(f"AI관련: {ai_count}개")
print(f"AI비관련: {non_ai_count}개")
print(f"총: {len(df)}개")
print("=" * 70)

# 새로운 엑셀 파일로 저장
now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"wanted_classified_{now_str}.xlsx"

# 컬럼 순서 조정 (중요한 컬럼을 앞으로)
column_order = ['AI_classification', 'job_category', 'company_name', 'position_name', 
                'summary', 'link', 'position', 'content1', 'content2', 'content3', 
                'content4', 'period', 'skill']

# 기존 컬럼 중에서 존재하는 것만 추가
existing_columns = [col for col in column_order if col in df.columns]
# 나머지 컬럼 추가
remaining_columns = [col for col in df.columns if col not in existing_columns and col != 'combined_text']
final_column_order = existing_columns + remaining_columns

df_final = df[final_column_order]

print(f"\n엑셀 파일 저장 중...")
df_final.to_excel(output_file, index=False, engine='openpyxl')
print(f"✓ 분류 완료된 엑셀 저장: {output_file}")

# AI관련 공고만 별도 저장
ai_only_file = f"wanted_AI_only_{now_str}.xlsx"
df_ai_only = df_final[df_final['AI_classification'] == 'AI관련']
df_ai_only.to_excel(ai_only_file, index=False, engine='openpyxl')
print(f"✓ AI관련 공고만 저장: {ai_only_file} ({len(df_ai_only)}개)")

print("\n작업 완료!")

