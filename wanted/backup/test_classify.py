import pandas as pd
from datetime import datetime

print("=" * 70)
print("AI 분류 스크립트 테스트")
print("=" * 70)

# 엑셀 파일 경로
input_file = "wanted_final_20251205_172607.xlsx"

print(f"\n파일 읽기: {input_file}")

try:
    df = pd.read_excel(input_file, engine='openpyxl')
    print(f"✓ 총 {len(df)}개 공고 로드 완료")
    print(f"✓ 컬럼: {list(df.columns)}")
    
    # AI 키워드
    ai_keywords = [
        "AI", "인공지능", "머신러닝", "Machine Learning", "딥러닝", "Deep Learning",
        "LLM", "대규모 언어 모델", "프롬프트 엔지니어링", "Prompt Engineering",
        "Agent", "에이전트", "RAG", "MCP",
        "비전 AI", "머신비전", "영상 처리 알고리즘", "Computer Vision"
    ]
    
    ai_keywords_lower = [kw.lower() for kw in ai_keywords]
    
    # 텍스트 합치기
    def create_combined_text(row):
        columns = ['position_name', 'position', 'content1', 'content2', 'content3', 'content4']
        texts = []
        for col in columns:
            if col in row and pd.notna(row[col]) and str(row[col]).strip():
                texts.append(str(row[col]).strip())
        return " ".join(texts)
    
    # 분류
    def classify_ai(text):
        if not text or pd.isna(text):
            return "AI비관련"
        text_lower = str(text).lower()
        for kw in ai_keywords_lower:
            if kw in text_lower:
                return "AI관련"
        return "AI비관련"
    
    # 요약
    def create_summary(text, max_len=200):
        if not text or pd.isna(text):
            return ""
        text = str(text).strip()
        return text[:max_len] + "..." if len(text) > max_len else text
    
    print("\n데이터 처리 중...")
    df['combined_text'] = df.apply(create_combined_text, axis=1)
    df['AI_classification'] = df['combined_text'].apply(classify_ai)
    df['summary'] = df['combined_text'].apply(create_summary)
    
    # 통계
    ai_count = (df['AI_classification'] == 'AI관련').sum()
    non_ai_count = (df['AI_classification'] == 'AI비관련').sum()
    
    print("\n" + "=" * 70)
    print("분류 결과")
    print("=" * 70)
    print(f"AI관련: {ai_count}개")
    print(f"AI비관련: {non_ai_count}개")
    print(f"총: {len(df)}개")
    print("=" * 70)
    
    # 저장
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"wanted_classified_{now_str}.xlsx"
    
    # 컬럼 순서
    column_order = ['AI_classification', 'job_category', 'company_name', 'position_name', 
                    'summary', 'link', 'position', 'content1', 'content2', 'content3', 
                    'content4', 'period', 'skill']
    existing_columns = [col for col in column_order if col in df.columns]
    remaining_columns = [col for col in df.columns if col not in existing_columns and col != 'combined_text']
    final_column_order = existing_columns + remaining_columns
    
    df_final = df[final_column_order]
    
    print(f"\n저장 중: {output_file}")
    df_final.to_excel(output_file, index=False, engine='openpyxl')
    print(f"✓ 분류 완료 엑셀 저장: {output_file}")
    
    # AI관련 공고만 저장
    ai_only_file = f"wanted_AI_only_{now_str}.xlsx"
    df_ai_only = df_final[df_final['AI_classification'] == 'AI관련']
    df_ai_only.to_excel(ai_only_file, index=False, engine='openpyxl')
    print(f"✓ AI관련 공고만 저장: {ai_only_file} ({len(df_ai_only)}개)")
    
    print("\n작업 완료!")
    
except Exception as e:
    print(f"\n오류 발생: {e}")
    import traceback
    traceback.print_exc()

