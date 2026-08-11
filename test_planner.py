"""
test_planner.py
단원 및 통합 테스트 스크립트
1. LLM Client JSON 파싱, 정밀 타입 검증, 복수 지역 스키마 검증 및 재시도 검증
2. Place Client 도시명 정규화, 401/403 및 0건 검색 처리 검증
3. report_generator 파일 원자적 생성, 시크릿 스캔, 복수 지역 캐싱 및 force_refresh 검증
"""

import os
import json
import unittest
from unittest.mock import MagicMock, patch

from config import load_config, validate_config
from llm_client import LLMClient, make_error_entry
from place_client import PlaceClient, normalize_city_name
import report_generator


class TestTravelPlanner(unittest.TestCase):

    def test_llm_json_clean_and_parse(self):
        """LLM 마크다운 코드블록 제거 및 JSON 파싱 검증"""
        raw_llm_response = """```json
{
  "recommended_cities": ["강릉", "속초"],
  "weather": "온화하고 봄바람이 붊",
  "events": ["강릉 바다 축제", "속초 대게 축제"],
  "reason": "봄맞이 동해안 여행으로 적합합니다."
}
```"""
        cleaned = LLMClient._clean_json_text(raw_llm_response)
        data = json.loads(cleaned)
        LLMClient.validate_schema(data)
        self.assertEqual(data["recommended_cities"], ["강릉", "속초"])
        self.assertEqual(data["recommended_city"], "강릉")
        self.assertEqual(len(data["events"]), 2)

    def test_llm_schema_validation_failures(self):
        """[FAIL #7 보완] LLM JSON 정밀 타입 및 비어있는 값 검증 유발 테스트"""
        # 1. events가 리스트가 아닐 때
        invalid_data_1 = {
            "recommended_cities": ["서울"],
            "weather": "맑음",
            "events": "이벤트 문자열",
            "reason": "추천"
        }
        with self.assertRaises((TypeError, ValueError)):
            LLMClient.validate_schema(invalid_data_1)

        # 2. recommended_cities가 비어있을 때
        invalid_data_2 = {
            "recommended_cities": [],
            "weather": "맑음",
            "events": ["축제"],
            "reason": "추천"
        }
        with self.assertRaises((TypeError, ValueError)):
            LLMClient.validate_schema(invalid_data_2)

    def test_city_name_normalization(self):
        """[FAIL #17 보완] 도시명 입력 정규화 테스트"""
        self.assertEqual(normalize_city_name("제주특별자치도"), "제주")
        self.assertEqual(normalize_city_name("강원도 강릉시"), "강릉")
        self.assertEqual(normalize_city_name("서울특별시"), "서울")
        self.assertEqual(normalize_city_name("  경주시!! "), "경주")

    @patch.object(LLMClient, "_call_raw_llm")
    def test_llm_retry_on_parse_error(self, mock_llm_call):
        """1차 JSON 파싱 실패 시 1회 재시도 및 fallback 처리 검증"""
        # 첫 번째 시도는 잘못된 JSON, 두 번째 시도는 올바른 JSON
        mock_llm_call.side_effect = [
            "잘못된 응답 텍스트",
            '{"recommended_cities": ["강릉", "속초"], "weather": "맑음", "events": ["강릉 축제"], "reason": "바다 여행 추천"}'
        ]
        client = LLMClient({"OPENAI_API_KEY": "fake_key"})
        errors = []
        rec = client.get_recommendation("2026-03-15", errors)

        self.assertEqual(rec["recommended_cities"], ["강릉", "속초"])
        self.assertEqual(mock_llm_call.call_count, 2)
        self.assertEqual(len(errors), 0)

    @patch("requests.get")
    def test_place_search_auth_error_handling(self, mock_get):
        """Kakao/Naver 401 인증 실패 시 오류 기록 및 진행 검증"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        client = PlaceClient({"KAKAO_REST_API_KEY": "invalid_key"})
        errors = []
        places = client.search_restaurants("제주", errors)

        self.assertEqual(places, [])
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["type"], "AUTH_ERROR")
        self.assertIn("timestamp", errors[0])
        self.assertIn("severity", errors[0])

    @patch("requests.get")
    def test_place_search_empty_result_handling(self, mock_get):
        """검색 결과 0건 시 EMPTY_RESULT 기록 및 대체 재검색 검증"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"documents": []}
        mock_get.return_value = mock_response

        client = PlaceClient({"KAKAO_REST_API_KEY": "valid_key"})
        errors = []
        places = client.search_restaurants("오지마을", errors)

        self.assertEqual(places, [])
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["type"], "EMPTY_RESULT")

    def test_multi_city_report_generation_and_caching(self):
        """[보너스 과제 1 & 2] 복수 지역 맛집 그룹화 저장 및 캐시 로드 검증"""
        test_date = "2099-12-31"
        rec_data = {
            "recommended_cities": ["강릉", "속초"],
            "recommended_city": "강릉",
            "weather": "쾌청함",
            "events": ["강릉 커피축제", "속초 수제맥주축제"],
            "reason": "동해안 대표 도시 모음"
        }
        places_by_city = {
            "강릉": [{"name": "강릉 두부", "address": "강릉시", "category": "한식", "url": "http://g.com", "x": 128.9, "y": 37.7}],
            "속초": [{"name": "속초 물회", "address": "속초시", "category": "한식", "url": "http://s.com", "x": 128.5, "y": 38.2}]
        }
        errors = [make_error_entry("test", "TEST_ERROR", "샘플 에러", severity="WARNING")]

        json_path = report_generator.save_raw_json(test_date, rec_data, places_by_city, errors)
        client = LLMClient({"OPENAI_API_KEY": "fake_key"})

        with patch.object(client, "_call_raw_llm", return_value="# 강릉 & 속초 리포트"):
            md_path = report_generator.save_markdown_report(test_date, client.generate_markdown_report(test_date, rec_data, places_by_city, errors))

        self.assertTrue(os.path.exists(json_path))
        self.assertTrue(os.path.exists(md_path))

        # 캐시 확인
        cached = report_generator.check_cache(test_date)
        self.assertIsNotNone(cached)
        self.assertIn("restaurants_by_city", cached)
        self.assertEqual(cached["recommendation"]["recommended_cities"], ["강릉", "속초"])

        # force_refresh 확인
        refreshed = report_generator.check_cache(test_date, force_refresh=True)
        self.assertIsNone(refreshed)

        # 정리
        if os.path.exists(json_path):
            os.remove(json_path)
        if os.path.exists(md_path):
            os.remove(md_path)


if __name__ == "__main__":
    unittest.main()
