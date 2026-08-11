"""
place_client.py
Kakao Local API 또는 Naver Local Search API를 활용하여 국내 맛집 정보를 검색하는 모듈.
도시명 정규화(FAIL #17 보완), 대체 재검색(PASS #15 보완), 지수 백오프(PASS #12 보완) 및 정교한 오류 메타데이터(PASS #9 보완)를 제공합니다.
"""

import re
import time
import requests
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

ALIAS_MAP = {
    "제주도": "제주",
    "제주특별자치도": "제주",
    "서울특별시": "서울",
    "부산광역시": "부산",
    "대구광역시": "대구",
    "인천광역시": "인천",
    "광주광역시": "광주",
    "대전광역시": "대전",
    "울산광역시": "울산",
    "세종특별자치시": "세종",
    "강원도 강릉시": "강릉",
    "강원특별자치도 강릉시": "강릉",
    "경상북도 경주시": "경주",
}

def normalize_city_name(raw_city: str) -> str:
    """
    도시명/지명 입력 정규화 모듈 (FAIL #17 보완)
    별칭 매핑, 행정구역 수식어(특별시, 광역시, 도 등) 정제 및 불필요 특수문자 제거를 수행합니다.
    """
    if not raw_city:
        return "제주"

    # 공백 및 특수문자 제거
    city = raw_city.strip()
    city = re.sub(r'[^\w\s]', '', city).strip()

    # 별칭 테이블 우선 매핑
    if city in ALIAS_MAP:
        return ALIAS_MAP[city]

    # "강원도 강릉시" -> "강릉" 도+시 구문 분해
    match = re.search(r'(?:강원도|강원특별자치도|경기도|충청북도|충청남도|전라북도|전라남도|전북특별자치도|경상북도|경상남도|제주도|제주특별자치도)\s*(.+)', city)
    if match:
        city = match.group(1).strip()

    # "경주시" -> "경주", "강릉시" -> "강릉", "평창군" -> "평창"
    cleaned = re.sub(r'(특별시|광역시|특별자치시|특별자치도|시|군)$', '', city).strip()
    return cleaned if len(cleaned) >= 2 else (city if city else "제주")

def make_error_entry(step: str, error_type: str, message: str, severity: str = "ERROR") -> Dict[str, Any]:
    """타임스탬프와 심각도가 포함된 구조화된 에러 객체를 생성합니다."""
    return {
        "step": step,
        "type": error_type,
        "severity": severity,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": message
    }

class PlaceClient:
    def __init__(self, config: Dict[str, Optional[str]]):
        self.kakao_api_key = config.get("KAKAO_REST_API_KEY")
        self.naver_client_id = config.get("NAVER_CLIENT_ID")
        self.naver_client_secret = config.get("NAVER_CLIENT_SECRET")

    def search_restaurants(self, city: str, errors: List[Dict[str, Any]], count: int = 5) -> List[Dict[str, Any]]:
        """
        도시명 기준 맛집 N곳을 검색합니다.
        도시명 정규화 및 0건 검색 시 대체 키워드 재검색(Fallback Search)을 진행합니다.
        """
        normalized_city = normalize_city_name(city)
        primary_query = f"{normalized_city} 맛집"

        if self.kakao_api_key:
            results = self._search_kakao(primary_query, errors, count)
            # 1차 검색 결과가 0건이면 대체 키워드로 2차 재검색 (PASS #15 보완)
            if not results and not any(e.get("type") == "AUTH_ERROR" for e in errors):
                fallback_query = f"{normalized_city} 대표 식당"
                results = self._search_kakao(fallback_query, errors, count, is_fallback=True)
            return results

        elif self.naver_client_id and self.naver_client_secret:
            results = self._search_naver(primary_query, errors, count)
            if not results and not any(e.get("type") == "AUTH_ERROR" for e in errors):
                fallback_query = f"{normalized_city} 대표 식당"
                results = self._search_naver(fallback_query, errors, count, is_fallback=True)
            return results

        else:
            errors.append(make_error_entry(
                step="place_search",
                error_type="NO_API_KEY",
                message="지도/장소 API 키가 설정되지 않았습니다.",
                severity="WARNING"
            ))
            return []

    def _search_kakao(self, query: str, errors: List[Dict[str, Any]], count: int = 5, is_fallback: bool = False) -> List[Dict[str, Any]]:
        """Kakao Local 키워드 검색 API 호출 (지수 백오프 재시도 포함)"""
        url = "https://dapi.kakao.com/v2/local/search/keyword.json"
        headers = {
            "Authorization": f"KakaoAK {self.kakao_api_key}"
        }
        params = {
            "query": query,
            "size": min(count, 15)
        }

        last_exception = None
        for attempt in range(1, 3):  # 최대 2회 (네트워크/5xx 시 1회 백오프 재시도)
            try:
                if attempt == 2:
                    time.sleep(1.0)  # Exponential Backoff

                response = requests.get(url, headers=headers, params=params, timeout=10)

                if response.status_code in (401, 403):
                    errors.append(make_error_entry(
                        step="place_search",
                        error_type="AUTH_ERROR",
                        message=f"Kakao API 인증 실패 (HTTP {response.status_code}). API 키 및 카카오맵 동의 설정을 확인하세요.",
                        severity="ERROR"
                    ))
                    return []

                if response.status_code >= 500 and attempt == 1:
                    continue  # 서버 오류 시 2차 재시도

                response.raise_for_status()
                data = response.json()
                documents = data.get("documents", [])

                if not documents:
                    if is_fallback:
                        errors.append(make_error_entry(
                            step="place_search",
                            error_type="EMPTY_RESULT",
                            message=f"0 results for query='{query}' (대체 검색 포함)",
                            severity="WARNING"
                        ))
                    return []

                results = []
                for doc in documents[:count]:
                    x_val = float(doc.get("x")) if doc.get("x") else None
                    y_val = float(doc.get("y")) if doc.get("y") else None
                    results.append({
                        "name": doc.get("place_name", ""),
                        "address": doc.get("road_address_name") or doc.get("address_name") or "",
                        "category": doc.get("category_name", ""),
                        "url": doc.get("place_url", ""),
                        "x": x_val,
                        "y": y_val
                    })
                return results

            except requests.exceptions.RequestException as e:
                last_exception = e

        errors.append(make_error_entry(
            step="place_search",
            error_type="NETWORK_ERROR",
            message=f"Kakao 장소 검색 네트워크 오류: {str(last_exception)}",
            severity="ERROR"
        ))
        return []

    def _search_naver(self, query: str, errors: List[Dict[str, Any]], count: int = 5, is_fallback: bool = False) -> List[Dict[str, Any]]:
        """Naver Local Search API 호출 (지수 백오프 재시도 포함)"""
        url = "https://openapi.naver.com/v1/search/local.json"
        headers = {
            "X-Naver-Client-Id": self.naver_client_id or "",
            "X-Naver-Client-Secret": self.naver_client_secret or ""
        }
        params = {
            "query": query,
            "display": min(count, 5)
        }

        last_exception = None
        for attempt in range(1, 3):
            try:
                if attempt == 2:
                    time.sleep(1.0)

                response = requests.get(url, headers=headers, params=params, timeout=10)

                if response.status_code in (401, 403):
                    errors.append(make_error_entry(
                        step="place_search",
                        error_type="AUTH_ERROR",
                        message=f"Naver API 인증 실패 (HTTP {response.status_code}). Client ID/Secret을 확인하세요.",
                        severity="ERROR"
                    ))
                    return []

                if response.status_code >= 500 and attempt == 1:
                    continue

                response.raise_for_status()
                data = response.json()
                items = data.get("items", [])

                if not items:
                    if is_fallback:
                        errors.append(make_error_entry(
                            step="place_search",
                            error_type="EMPTY_RESULT",
                            message=f"0 results for query='{query}' (대체 검색 포함)",
                            severity="WARNING"
                        ))
                    return []

                results = []
                for item in items[:count]:
                    raw_title = item.get("title", "")
                    clean_title = re.sub(r'<[^>]+>', '', raw_title)
                    
                    results.append({
                        "name": clean_title,
                        "address": item.get("roadAddress") or item.get("address") or "",
                        "category": item.get("category", ""),
                        "url": item.get("link", ""),
                        "x": float(item.get("mapx")) if item.get("mapx") else None,
                        "y": float(item.get("mapy")) if item.get("mapy") else None
                    })
                return results

            except requests.exceptions.RequestException as e:
                last_exception = e

        errors.append(make_error_entry(
            step="place_search",
            error_type="NETWORK_ERROR",
            message=f"Naver 장소 검색 네트워크 오류: {str(last_exception)}",
            severity="ERROR"
        ))
        return []

