"""
config.py
API 키 및 환경 변수 관리 모듈
.env 파일 또는 시스템 환경 변수에서 API 키를 로드하고 검증합니다.
"""

import os
import sys
from typing import Dict, Optional

# dotenv 라이브러리가 있을 경우 .env 파일 자동 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def load_config() -> Dict[str, Optional[str]]:
    """환경 변수에서 API 키 및 모델 설정을 읽어옵니다."""
    config = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "GEMINI_MODEL": os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest"),
        "KAKAO_REST_API_KEY": os.getenv("KAKAO_REST_API_KEY"),
        "NAVER_CLIENT_ID": os.getenv("NAVER_CLIENT_ID"),
        "NAVER_CLIENT_SECRET": os.getenv("NAVER_CLIENT_SECRET"),
    }
    return config

def validate_config(config: Dict[str, Optional[str]]) -> None:
    """
    필수 API 키가 설정되어 있는지 확인합니다.
    미설정 시 안내 메시지를 출력하고 즉시 프로그램을 종료(sys.exit)합니다.
    """
    has_llm_key = bool(config["OPENAI_API_KEY"] or config["GEMINI_API_KEY"])
    has_kakao_key = bool(config["KAKAO_REST_API_KEY"])
    has_naver_key = bool(config["NAVER_CLIENT_ID"] and config["NAVER_CLIENT_SECRET"])
    has_map_key = has_kakao_key or has_naver_key

    missing = []
    if not has_llm_key:
        missing.append("LLM API 키 (OPENAI_API_KEY 또는 GEMINI_API_KEY)")
    if not has_map_key:
        missing.append("지도/장소 검색 API 키 (KAKAO_REST_API_KEY 또는 NAVER_CLIENT_ID/SECRET)")

    if missing:
        print("\n" + "=" * 60)
        print("[ERROR] API 키 설정 오류: 필수 API 키가 설정되지 않았습니다.")
        for item in missing:
            print(f"  - 누락된 키: {item}")
        print("\n[설정 방법 안내]")
        print(" 1. 프로젝트 루트 디렉토리에 '.env' 파일을 생성하세요.")
        print(" 2. 아래와 같이 발급받은 API 키를 설정해주세요:\n")
        print("    OPENAI_API_KEY=your_openai_api_key_here")
        print("    KAKAO_REST_API_KEY=your_kakao_rest_api_key_here\n")
        print(" 3. 자세한 정보는 README.md 또는 .env.example을 참고하세요.")
        print("=" * 60 + "\n")
        sys.exit(1)
