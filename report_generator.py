"""
report_generator.py
결과 파일(results/ 폴더 내 JSON 및 MD 파일)을 저장하고 캐싱을 관리하는 모듈.
"""

import os
import json
from typing import Dict, Any, List, Optional

RESULTS_DIR = "results"

def ensure_results_dir() -> str:
    """results/ 폴더가 없으면 생성하고 경로를 반환합니다."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    return RESULTS_DIR

def get_json_filepath(date_str: str) -> str:
    """원본 데이터 JSON 파일 경로 생성"""
    return os.path.join(RESULTS_DIR, f"{date_str}_travel_data.json")

def get_markdown_filepath(date_str: str) -> str:
    """최종 여행 리포트 Markdown 파일 경로 생성"""
    return os.path.join(RESULTS_DIR, f"{date_str}_travel_plan.md")

def check_cache(date_str: str) -> Optional[Dict[str, Any]]:
    """
    [보너스 기능] 동일한 date로 저장된 원본 JSON 캐시가 있는지 확인합니다.
    존재할 경우 저장된 데이터를 읽어서 반환합니다.
    """
    json_path = get_json_filepath(date_str)
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception:
            return None
    return None

def save_raw_json(
    date_str: str,
    rec_data: Dict[str, Any],
    places: List[Dict[str, Any]],
    errors: List[Dict[str, Any]]
) -> str:
    """
    원본 데이터 JSON 1개를 생성하여 저장합니다.
    필수 포함 항목: 1차 추천 JSON, 맛집 검색 결과 목록, 오류 요약 목록
    """
    ensure_results_dir()
    filepath = get_json_filepath(date_str)

    data_payload = {
        "date": date_str,
        "recommendation": rec_data,
        "restaurants": places,
        "errors": errors
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data_payload, f, ensure_ascii=False, indent=2)

    return filepath

def save_markdown_report(date_str: str, markdown_content: str) -> str:
    """최종 여행 리포트 Markdown 파일 1개를 저장합니다."""
    ensure_results_dir()
    filepath = get_markdown_filepath(date_str)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    return filepath
