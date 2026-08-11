"""
report_generator.py
결과 파일(results/ 폴더 내 JSON 및 MD 파일)을 안전하게 원자적(Atomic)으로 저장하고 캐싱을 관리하는 모듈.
파일 쓰기 안전성(PASS #4 보완), 시크릿 2차 스캔(PASS #5 보완), 캐시 만료(PASS #16 보완)를 제공합니다.
"""

import os
import re
import json
import time
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

def check_cache(date_str: str, max_age_hours: float = 24.0, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    """
    [보너스/품질 보완] 동일한 date로 저장된 원본 JSON 캐시가 있는지 확인합니다 (PASS #16 보완).
    force_refresh가 True이거나 TTL(기본 24시간)이 만료되면 None을 반환합니다.
    """
    if force_refresh:
        return None

    json_path = get_json_filepath(date_str)
    if os.path.exists(json_path):
        try:
            # 캐시 만료 시간(TTL: 24시간) 검증
            mtime = os.path.getmtime(json_path)
            age_hours = (time.time() - mtime) / 3600.0
            if age_hours > max_age_hours:
                return None  # 캐시 만료됨

            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception:
            return None
    return None

def _sanitize_output_text(text: str) -> str:
    """저장 전 잠재적 API 키 패턴 2차 스캔 및 마스킹 (PASS #5 보완)"""
    text = re.sub(r'([?&]key=)[^&\s"\']+', r'\1***REDACTED***', text)
    text = re.sub(r'AIzaSy[a-zA-Z0-9_\-]{33}', 'AIzaSy***REDACTED***', text)
    text = re.sub(r'sk-proj-[a-zA-Z0-9_\-]{30,}', 'sk-proj-***REDACTED***', text)
    return text

def _atomic_write_file(filepath: str, content: str) -> None:
    """임시 파일(.tmp) 생성 후 os.replace를 사용하는 안전한 원자적(Atomic) 파일 쓰기 (PASS #4 보완)"""
    tmp_path = filepath + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, filepath)
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise e

def save_raw_json(
    date_str: str,
    rec_data: Dict[str, Any],
    places: List[Dict[str, Any]],
    errors: List[Dict[str, Any]]
) -> str:
    """
    원본 데이터 JSON 1개를 원자적으로 저장합니다 (PASS #4, #5 보완).
    """
    ensure_results_dir()
    filepath = get_json_filepath(date_str)

    data_payload = {
        "date": date_str,
        "recommendation": rec_data,
        "restaurants": places,
        "errors": errors
    }

    raw_json_str = json.dumps(data_payload, ensure_ascii=False, indent=2)
    sanitized_str = _sanitize_output_text(raw_json_str)

    _atomic_write_file(filepath, sanitized_str)
    return filepath

def save_markdown_report(date_str: str, markdown_content: str) -> str:
    """최종 여행 리포트 Markdown 파일 1개를 원자적으로 저장합니다 (PASS #4, #5 보완)."""
    ensure_results_dir()
    filepath = get_markdown_filepath(date_str)

    sanitized_md = _sanitize_output_text(markdown_content)
    _atomic_write_file(filepath, sanitized_md)

    return filepath
