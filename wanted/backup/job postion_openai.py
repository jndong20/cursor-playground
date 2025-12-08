import pandas as pd
from openai import OpenAI

client = OpenAI()

# 읽어올 엑셀 파일명 (지정된 파일명 사용)
input_file = "wanted_final_20251205_172607.xlsx"
df = pd.read_excel(input_file, engine='openpyxl')

AI_KEYWORDS = [
    "AI", "인공지능", "머신러닝", "machine learning", "딥러닝", "deep learning",
    "LLM", "대규모 언어 모델", "프롬프트 엔지니어링", "prompt engineering",
    "agent", "에이전트", "RAG", "MCP", "비전 AI", "머신비전", "computer vision"
]

def has_ai_keyword(text: str) -> bool:
    lower = text.lower()
    return any(k.lower() in lower for k in AI_KEYWORDS)

def classify_with_gpt(text: str) -> str:
    prompt = f"""
너는 채용 공고를 'AI 관련'인지 아닌지 이진 분류하는 역할을 한다.
AI 관련이란, AI/ML/딥러닝/LLM/비전 AI/AI Agent가 주요 업무인 포지션이다.
단순히 'AI 서비스 회사에서 일반 백엔드'를 하는 경우는 AI 관련이 아니다.

아래 채용공고 전체를 읽고,
- AI 관련이면: AI_YES
- 아니면: AI_NO
만 출력해.

채용공고:
{text}
"""
    resp = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        max_output_tokens=5,
    )
    out = resp.output[0].content[0].text.strip()
    return "AI_YES" if "AI_YES" in out else "AI_NO"

results = []
for _, row in df.iterrows():
    # 텍스트 합치기 (기본 wanted 엑셀 컬럼 구조에 맞춤)
    text = " ".join([
        str(row.get("position_name", "")),
        str(row.get("position", "")),
        str(row.get("content1", "")),
        str(row.get("content2", "")),
        str(row.get("content3", "")),
        str(row.get("content4", ""))
    ])
    if has_ai_keyword(text):
        ai_flag = classify_with_gpt(text)
    else:
        ai_flag = "AI_NO"
    results.append(ai_flag)

df["AI_관련여부"] = results
output_file = "jobs_with_ai_flag.xlsx"
df.to_excel(output_file, index=False)
