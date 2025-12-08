import pandas as pd

# 가장 최신 분류 파일 확인
file = "wanted_classified_20251205_173852.xlsx"

print("=" * 70)
print("분류 결과 확인")
print("=" * 70)

df = pd.read_excel(file)

print(f"\n총 행 수: {len(df)}")
print(f"\n컬럼 목록:")
for i, col in enumerate(df.columns, 1):
    print(f"  {i}. {col}")

if 'AI_classification' in df.columns:
    ai_count = (df['AI_classification'] == 'AI관련').sum()
    non_ai_count = (df['AI_classification'] == 'AI비관련').sum()
    
    print("\n" + "=" * 70)
    print("분류 통계")
    print("=" * 70)
    print(f"AI관련: {ai_count}개 ({ai_count/len(df)*100:.1f}%)")
    print(f"AI비관련: {non_ai_count}개 ({non_ai_count/len(df)*100:.1f}%)")
    print(f"총: {len(df)}개")
    
    # 샘플 데이터 출력
    print("\n" + "=" * 70)
    print("AI관련 공고 샘플 (처음 3개)")
    print("=" * 70)
    ai_samples = df[df['AI_classification'] == 'AI관련'].head(3)
    for idx, row in ai_samples.iterrows():
        print(f"\n{idx+1}. {row['company_name']} - {row['position_name']}")
        if 'summary' in row:
            print(f"   요약: {row['summary'][:100]}...")
    
    print("\n" + "=" * 70)
    print("AI비관련 공고 샘플 (처음 3개)")
    print("=" * 70)
    non_ai_samples = df[df['AI_classification'] == 'AI비관련'].head(3)
    for idx, row in non_ai_samples.iterrows():
        print(f"\n{idx+1}. {row['company_name']} - {row['position_name']}")
        if 'summary' in row:
            print(f"   요약: {row['summary'][:100]}...")

else:
    print("\n⚠ AI_classification 컬럼이 없습니다.")

print("\n" + "=" * 70)

