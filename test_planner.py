"""
test_planner.py
단원 및 통합 테스트 스크립트
1. LLM Client JSON 파싱 및 재시도 검증
2. Place Client 401/403 및 0건 검색 처리 검증
3. report_generator 파일 생성 및 캐싱 검증
"""

import os
import json
import unittest
from unittest.mock import MagicMock, patch

from config import load_config, validate_config
from llm_client import LLMClient
from place_client import PlaceClient
import report_generator


class TestTravelPlanner(unittest.TestCase):

    def test_llm_json_clean_and_parse(self):
        """LLM 마크다운 코드블록 제거 및 JSON 파싱 검증"""
        raw_llm_response = """```json
{
  "recommended_city": "제주",
  "weather": "온화하고 봄바람이 붊",
  "events": ["제주 유채꽃 축제"],
  "reason": "봄맞이 제주 여행으로 적합합니다."
}
```"""
        cleaned = LLMClient._clean_json_text(raw_llm_response)
        data = json.loads(cleaned)
        self.assertEqual(data["recommended_city"], "제주")
        self.assertEqual(len(data["events"]), 1)

    @patch.object(LLMClient, "_call_raw_llm")
    def test_llm_retry_on_parse_error(self, mock_llm_call):
        """1차 JSON 파싱 실패 시 1회 재시도 및 fallback 처리 검증"""
        # 첫 번째 시도는 잘못된 JSON, 두 번째 시도는 올바른 JSON
        mock_llm_call.side_effect = [
            "잘못된 응답 텍스트",
            '{"recommended_city": "강릉", "weather": "맑음", "events": ["강릉 축제"], "reason": "바다 여행 추천"}'
        ]
        client = LLMClient({"OPENAI_API_KEY": "fake_key"})
        errors = []
        rec = client.get_recommendation("2026-03-15", errors)

        self.assertEqual(rec["recommended_city"], "강릉")
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

    @patch("requests.get")
    def test_place_search_empty_result_handling(self, mock_get):
        """검색 결과 0건 시 EMPTY_RESULT 기록 및 빈 배열 반환 검증"""
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

    def test_report_generation_and_caching(self):
        """결과 파일 저장 및 캐시 로드 검증"""
        test_date = "2099-12-31"
        rec_data = {
            "recommended_city": "경주",
            "weather": "쾌청함",
            "events": ["경주 신라문화제"],
            "reason": "역사 탐방에 최고의 도시"
        }
        places = [{
            "name": "경주 쌈밥",
            "address": "경주시 첨성로 1",
            "category": "한식",
            "url": "http://example.com",
            "x": 129.2,
            "y": 35.8
        }]
        errors = [{"step": "test", "type": "TEST_ERROR", "message": "샘플 에러"}]

        json_path = report_generator.save_raw_json(test_date, rec_data, places, errors)
        md_path = report_generator.save_markdown_report(test_date, "# 경주 리포트")

        self.assertTrue(os.path.exists(json_path))
        self.assertTrue(os.path.exists(md_path))

        # 캐시 확인
        cached = report_generator.check_cache(test_date)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["recommendation"]["recommended_city"], "경주")

        # 정리
        if os.path.exists(json_path):
            os.remove(json_path)
        if os.path.exists(md_path):
            os.remove(md_path)


if __name__ == "__main__":
    unittest.main()
