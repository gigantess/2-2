"""
place_client.py
Kakao Local API 또는 Naver Local Search API를 활용하여 국내 맛집 정보를 검색하는 모듈.
검색 실패, 인증 오류(401/403), 0건 검색 시에도 예외를 처리하고 errors 목록에 기록합니다.
"""

import re
import requests
from typing import Dict, Any, List, Optional

class PlaceClient:
    def __init__(self, config: Dict[str, Optional[str]]):
        self.kakao_api_key = config.get("KAKAO_REST_API_KEY")
        self.naver_client_id = config.get("NAVER_CLIENT_ID")
        self.naver_client_secret = config.get("NAVER_CLIENT_SECRET")

    def search_restaurants(self, city: str, errors: List[Dict[str, Any]], count: int = 5) -> List[Dict[str, Any]]:
        """
        도시명 기준 맛집 N곳을 검색합니다.
        Kakao API 우선 시도 후 없으면 Naver API 시도합니다.
        """
        query = f"{city} 맛집"

        if self.kakao_api_key:
            return self._search_kakao(query, errors, count)
        elif self.naver_client_id and self.naver_client_secret:
            return self._search_naver(query, errors, count)
        else:
            errors.append({
                "step": "place_search",
                "type": "NO_API_KEY",
                "message": "지도/장소 API 키가 설정되지 않았습니다."
            })
            return []

    def _search_kakao(self, query: str, errors: List[Dict[str, Any]], count: int = 5) -> List[Dict[str, Any]]:
        """Kakao Local 키워드 검색 API 호출"""
        url = "https://dapi.kakao.com/v2/local/search/keyword.json"
        headers = {
            "Authorization": f"KakaoAK {self.kakao_api_key}"
        }
        params = {
            "query": query,
            "size": min(count, 15)
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code in (401, 403):
                errors.append({
                    "step": "place_search",
                    "type": "AUTH_ERROR",
                    "message": f"Kakao API 인증 실패 (HTTP {response.status_code}). API 키를 확인하세요."
                })
                return []

            response.raise_for_status()
            data = response.json()
            documents = data.get("documents", [])

            if not documents:
                errors.append({
                    "step": "place_search",
                    "type": "EMPTY_RESULT",
                    "message": f"0 results for query='{query}'"
                })
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
            errors.append({
                "step": "place_search",
                "type": "NETWORK_ERROR",
                "message": f"Kakao 장소 검색 네트워크 오류: {str(e)}"
            })
            return []
        except Exception as e:
            errors.append({
                "step": "place_search",
                "type": "PARSE_ERROR",
                "message": f"Kakao 장소 검색 결과 처리 오류: {str(e)}"
            })
            return []

    def _search_naver(self, query: str, errors: List[Dict[str, Any]], count: int = 5) -> List[Dict[str, Any]]:
        """Naver Local Search API 호출"""
        url = "https://openapi.naver.com/v1/search/local.json"
        headers = {
            "X-Naver-Client-Id": self.naver_client_id or "",
            "X-Naver-Client-Secret": self.naver_client_secret or ""
        }
        params = {
            "query": query,
            "display": min(count, 5)
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code in (401, 403):
                errors.append({
                    "step": "place_search",
                    "type": "AUTH_ERROR",
                    "message": f"Naver API 인증 실패 (HTTP {response.status_code}). Client ID/Secret을 확인하세요."
                })
                return []

            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])

            if not items:
                errors.append({
                    "step": "place_search",
                    "type": "EMPTY_RESULT",
                    "message": f"0 results for query='{query}'"
                })
                return []

            results = []
            for item in items[:count]:
                raw_title = item.get("title", "")
                clean_title = re.sub(r'<[^>]+>', '', raw_title)  # HTML 태그 제거 (예: <b>...</b>)
                
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
            errors.append({
                "step": "place_search",
                "type": "NETWORK_ERROR",
                "message": f"Naver 장소 검색 네트워크 오류: {str(e)}"
            })
            return []
        except Exception as e:
            errors.append({
                "step": "place_search",
                "type": "PARSE_ERROR",
                "message": f"Naver 장소 검색 결과 처리 오류: {str(e)}"
            })
            return []
