# OpenAI API 테스트: 텍스트 생성 & 이미지 생성
# API 키는 config.env 파일에 저장되어 있습니다

from openai import OpenAI
import os
from pathlib import Path

# config.env 파일에서 환경 변수 로드 (python-dotenv 라이브러리 사용)
try:
    from dotenv import load_dotenv
    # 현재 스크립트가 있는 디렉토리의 config.env 파일 로드
    env_path = Path(__file__).parent / 'config.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print("✓ config.env 파일에서 환경 변수를 로드했습니다.")
    else:
        print("⚠ config.env 파일이 없습니다.")
except ImportError:
    print("⚠ python-dotenv가 설치되지 않았습니다.")
    print("설치 방법: pip install python-dotenv")
    print("config.env 파일을 사용하려면 위 명령어로 설치하세요.\n")
except Exception as e:
    print(f"⚠ config.env 파일 로드 중 오류: {e}\n")

# 환경 변수에서 API 키를 읽거나, 직접 입력
api_key = os.getenv("OPENAI_API_KEY")  # 환경 변수에서 읽기

if not api_key:
    print("=" * 70)
    print("API 키가 설정되지 않았습니다.")
    print("\n환경 변수 설정 방법:")
    print("   PowerShell: $env:OPENAI_API_KEY='your-api-key-here'")
    print("   CMD: set OPENAI_API_KEY=your-api-key-here")
    print("\n또는 직접 입력:")
    api_key = input("   OpenAI API 키를 입력하세요: ").strip()
    print("\nAPI 키 확인: https://platform.openai.com/api-keys")
    print("=" * 70)

if not api_key:
    print("\n오류: API 키가 제공되지 않았습니다.")
    exit(1)

try:
    client = OpenAI(api_key=api_key)
    
    # 이미지 생성 여부 선택
    print("\n" + "=" * 70)
    print("OpenAI API 테스트 프로그램")
    print("=" * 70)
    print("\n무엇을 생성하시겠습니까?")
    print("1. 텍스트 생성 (GPT 모델)")
    print("2. 이미지 생성 (DALL-E 모델)")
    choice = input("\n선택 (1 또는 2): ").strip()
    
    if choice == "2":
        # 이미지 생성
        print("\n[ 이미지 생성 모드 ]")
        print("모델: DALL-E 3")
        prompt = input("\n이미지 생성 프롬프트를 입력하세요: ").strip()
        
        if not prompt:
            print("오류: 프롬프트가 비어있습니다.")
            exit(1)
        
        print("\n이미지 생성 중... (시간이 걸릴 수 있습니다)")
        
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",  # 1024x1024, 1024x1792, 1792x1024
            quality="standard",  # standard 또는 hd
            n=1
        )
        
        image_url = response.data[0].url
        print("\n✓ 이미지 생성 완료!")
        print(f"\n이미지 URL: {image_url}")
        print("\n위 URL을 브라우저에서 열어 이미지를 확인하세요.")
        
        # 이미지를 로컬에 저장할지 선택
        save_choice = input("\n이미지를 다운로드하시겠습니까? (y/n): ").strip().lower()
        if save_choice == 'y':
            import requests
            import datetime
            
            img_data = requests.get(image_url).content
            filename = f"generated_image_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            with open(filename, 'wb') as f:
                f.write(img_data)
            print(f"\n✓ 이미지 저장 완료: {filename}")
    
    else:
        # 텍스트 생성
        print("\n[ 텍스트 생성 모드 ]")
        print("모델: gpt-4o (GPT-5.1은 아직 출시되지 않았습니다)")
        prompt = input("\n프롬프트를 입력하세요: ").strip()
        
        if not prompt:
            print("오류: 프롬프트가 비어있습니다.")
            exit(1)
        
        print("\n응답 생성 중...")
        
        response = client.chat.completions.create(
            model="gpt-4o",  # 최신 GPT 모델 (GPT-5.1은 아직 없음)
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        print("\n" + "=" * 70)
        print("[ 응답 ]")
        print("=" * 70)
        print(response.choices[0].message.content)
        print("\n✓ 응답 생성 완료!")
    
except Exception as e:
    print(f"\n✗ 오류 발생: {e}")
    print(f"오류 타입: {type(e).__name__}")
    print("\n해결 방법:")
    print("1. API 키가 올바른지 확인: https://platform.openai.com/api-keys")
    print("2. API 키에 충분한 크레딧이 있는지 확인")
    print("3. 네트워크 연결 확인")
    print("4. 모델 접근 권한 확인 (일부 모델은 별도 권한 필요)")
