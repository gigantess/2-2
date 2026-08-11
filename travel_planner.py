"""
travel_planner.py
국내 여행지 추천 및 맛집 정보 연동 CLI 메인 프로그램

실행 방법:
  python travel_planner.py --date "YYYY-MM-DD"
  python travel_planner.py -date "2026-03-15"
"""

import argparse
import sys
import re
from datetime import datetime
from typing import List, Dict, Any

from config import load_config, validate_config
from llm_client import LLMClient
from place_client import PlaceClient
import report_generator


def parse_arguments() -> argparse.Namespace:
    """CLI 인자를 파싱하고 날짜 입력을 검증합니다."""
    parser = argparse.ArgumentParser(
        description="LLM과 지도 API를 연동한 국내 여행 추천 프로그램",
        usage="python travel_planner.py --date YYYY-MM-DD"
    )

    # -date 및 --date 지원
    parser.add_argument(
        "-date", "--date",
        type=str,
        required=True,
        help="여행 날짜 (입력 형식: YYYY-MM-DD, 예: 2026-03-15)"
    )

    args = parser.parse_args()
    date_str = args.date.strip()

    # YYYY-MM-DD 날짜 형식 정규식 및 datetime 검증
    date_pattern = r"^\d{4}-\d{2}-\d{2}$"
    if not re.match(date_pattern, date_str):
        print(f"\n[오류] 날짜 형식이 올바르지 않습니다: '{date_str}'")
        print("사용법: python travel_planner.py --date YYYY-MM-DD (예: 2026-03-15)\n")
        sys.exit(1)

    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print(f"\n[오류] 존재하지 않는 유효하지 않은 날짜입니다: '{date_str}'")
        print("사용법: python travel_planner.py --date YYYY-MM-DD (예: 2026-03-15)\n")
        sys.exit(1)

    return args


def main():
    # 1. CLI 인자 파싱 및 날짜 검증
    args = parse_arguments()
    target_date = args.date

    print("\n" + "=" * 50)
    print(f" [INFO] 국내 여행 추천 프로그램 시작 (날짜: {target_date})")
    print("=" * 50)

    # 2. API 키 검증 (미설정 시 즉시 종료)
    config = load_config()
    validate_config(config)

    # 에러 로그 관리를 위한 목록
    errors: List[Dict[str, Any]] = []

    # 3. 보너스 기능: 결과 캐싱 확인
    cached_data = report_generator.check_cache(target_date)
    if cached_data:
        print(f"\n[캐시 감지] '{target_date}' 날짜의 기존 원본 데이터 JSON을 사용합니다.")
        rec_data = cached_data.get("recommendation", {})
        places = cached_data.get("restaurants", [])
        errors = cached_data.get("errors", [])
    else:
        # 4. [1/3] LLM 1차 추천 생성 (여행지, 날씨, 축제 정보)
        print("\n[1/3] 1차 추천 생성 중(LLM)...")
        llm = LLMClient(config)
        rec_data = llm.get_recommendation(target_date, errors)
        city = rec_data.get("recommended_city", "제주")
        print(f"  - recommended_city: \"{city}\"")

        # 5. [2/3] 맛집 검색 (지도 API)
        print("\n[2/3] 맛집 검색 중(지도/장소 API)...")
        place_client = PlaceClient(config)
        places = place_client.search_restaurants(city, errors, count=5)

        if places:
            print(f"  - 맛집 {len(places)}곳 검색 완료")
        else:
            print("  - 검색 결과 0건 또는 오류 발생 (다음 단계로 진행)")

    # 6. [3/3] 최종 리포트 생성 (LLM Markdown 리포트)
    print("\n[3/3] 최종 리포트 생성 중(LLM)...")
    llm = LLMClient(config)
    report_md = llm.generate_markdown_report(target_date, rec_data, places, errors)
    print("  - 리포트 생성 완료")

    # 7. 결과 저장 (JSON 원본 & Markdown 리포트)
    json_path = report_generator.save_raw_json(target_date, rec_data, places, errors)
    md_path = report_generator.save_markdown_report(target_date, report_md)

    print("\n" + "=" * 50)
    print(f" [완료] 결과물이 저장되었습니다.")
    print(f" - 원본 JSON: {json_path}")
    print(f" - 리포트 MD: {md_path}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
