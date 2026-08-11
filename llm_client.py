"""
llm_client.py
LLM API (OpenAI 또는 Google Gemini) 연동 및 JSON 추출 모듈
1차 추천(JSON) 생성, 파싱 실패 시 재시도(1회), 최종 Markdown 리포트 생성을 담당합니다.
"""

import json
import re
import requests
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional

def make_error_entry(step: str, error_type: str, message: str, severity: str = "ERROR") -> Dict[str, Any]:
    """타임스탬프와 심각도가 포함된 구조화된 에러 객체를 생성합니다."""
    return {
        "step": step,
        "type": error_type,
        "severity": severity,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": message
    }

class LLMClient:
    def __init__(self, config: Dict[str, Optional[str]]):
        self.openai_api_key = config.get("OPENAI_API_KEY")
        self.gemini_api_key = config.get("GEMINI_API_KEY")
        self.gemini_model = config.get("GEMINI_MODEL") or "gemini-flash-lite-latest"

    def _call_raw_llm(self, prompt: str, system_instruction: str = "") -> str:
        """설정된 API 키에 따라 OpenAI 또는 Gemini API를 호출합니다."""
        if self.openai_api_key:
            return self._call_openai(prompt, system_instruction)
        elif self.gemini_api_key:
            return self._call_gemini(prompt, system_instruction)
        else:
            raise ValueError("사용 가능한 LLM API 키가 없습니다.")

    def _call_openai(self, prompt: str, system_instruction: str = "") -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": "gpt-4o-mini",
            "messages": messages,
            "temperature": 0.7
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _call_gemini(self, prompt: str, system_instruction: str = "") -> str:
        """Gemini Flash-Lite (gemini-flash-lite-latest) 모델 호출로 비용 절감"""
        models_to_try = [self.gemini_model]
        for m in ["gemini-flash-lite-latest", "gemini-flash-latest", "gemini-3.5-flash-lite"]:
            if m not in models_to_try:
                models_to_try.append(m)

        full_text = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
        payload = {
            "contents": [{
                "parts": [{"text": full_text}]
            }]
        }
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": self.gemini_api_key
        }
        last_exception = None

        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except requests.exceptions.HTTPError as e:
                last_exception = e
                if response.status_code == 404:
                    continue  # 모델명이 404면 다음 후보 모델 시도
                raise e
            except Exception as e:
                raise e

        if last_exception:
            raise last_exception

    @staticmethod
    def _clean_json_text(text: str) -> str:
        """마크다운 코드블록 제거 등 JSON 텍스트 정교화"""
        text = text.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return text

    @staticmethod
    def _sanitize_error_message(msg: str) -> str:
        """에러 메시지에 포함될 수 있는 API 키(URL 쿼리 등)를 마스킹합니다."""
        return re.sub(r'([?&]key=)[^&\s"\']+', r'\1***REDACTED***', str(msg))

    @staticmethod
    def validate_schema(data: Any) -> None:
        """1차 추천 JSON 데이터의 키 존재, 데이터 타입, 값 유효성을 정밀 검증합니다 (복수 지역 지원)."""
        if not isinstance(data, dict):
            raise TypeError(f"최상위 응답은 JSON 객체(dict)여야 합니다. (수신 타입: {type(data).__name__})")

        # recommended_cities 또는 recommended_city 필수
        if "recommended_cities" not in data and "recommended_city" not in data:
            raise ValueError("필수 키 누락: 'recommended_cities' 또는 'recommended_city'")

        # recommended_cities 가 없는 경우 단일 recommended_city를 배열로 정규화
        if "recommended_cities" not in data or not data["recommended_cities"]:
            city = data.get("recommended_city")
            if not isinstance(city, str) or not city.strip():
                raise TypeError(f"'recommended_city'는 비어있지 않은 문자열이어야 합니다. (수신 값: {city})")
            data["recommended_cities"] = [city.strip()]

        cities = data.get("recommended_cities")
        if not isinstance(cities, list) or len(cities) == 0:
            raise TypeError(f"'recommended_cities'는 비어있지 않은 문자열 목록(list)이어야 합니다. (수신 값: {cities})")

        for idx, c in enumerate(cities):
            if not isinstance(c, str) or not c.strip():
                raise TypeError(f"'recommended_cities[{idx}]' 항목은 비어있지 않은 문자열이어야 합니다. (수신 값: {c})")

        # 하위 호환성을 위해 recommended_city도 첫 번째 도시로 유지
        data["recommended_city"] = cities[0]

        # weather 타입 및 값 검증
        weather = data.get("weather")
        if not isinstance(weather, str) or not weather.strip():
            raise TypeError(f"'weather'는 비어있지 않은 문자열(str)이어야 합니다. (수신 값: {weather})")

        # events 타입(리스트) 및 항목 검증
        events = data.get("events")
        if not isinstance(events, list) or len(events) == 0:
            raise TypeError(f"'events'는 최소 1개 이상의 항목을 가진 리스트(array)여야 합니다. (수신 값: {events})")
        for idx, item in enumerate(events):
            if not isinstance(item, str) or not item.strip():
                raise TypeError(f"'events[{idx}]' 항목은 비어있지 않은 문자열(str)이어야 합니다. (수신 값: {item})")

        # reason 타입 및 값 검증
        reason = data.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise TypeError(f"'reason'은 비어있지 않은 문자열(str)이어야 합니다. (수신 값: {reason})")

    def get_recommendation(self, date_str: str, errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        1차 추천 데이터(복수 지역 포함)를 생성하고 JSON 및 정밀 스키마 타입을 검증합니다.
        실패 시 1회 재시도하며, 최종 실패 시 errors 목록에 기록하고 기본값을 반환합니다.
        """
        system_prompt = (
            "당신은 국내 여행 전문가입니다. 반드시 아래 지정된 JSON 형식으로만 응답해야 합니다.\n"
            "다른 인사말이나 설명 텍스트, 마크다운 외 텍스트는 절대 포함하지 마세요."
        )

        user_prompt = f"""
여행 날짜: {date_str}

위 여행 날짜에 맞춰 서로 방문하기 좋은 국내 추천 여행지 2곳을 추천하고, 해당 시기의 날씨 요약 및 행사/축제 정보, 추천 근거를 작성하세요.

반드시 아래 필드를 포함하는 JSON 객체로만 응답하세요:
{{
  "recommended_cities": ["추천 도시 1 (예: 강릉)", "추천 도시 2 (예: 속초)"],
  "weather": "해당 시기의 일반적인 날씨 요약 (1문장)",
  "events": ["행사/축제 후보 1", "행사/축제 후보 2"],
  "reason": "추천 근거 (2~4문장)"
}}
"""

        for attempt in range(1, 3):  # 최초 시도 + 최대 1회 재시도 (총 2회)
            try:
                current_prompt = user_prompt
                if attempt == 2:
                    current_prompt += "\n\n[주의: 이전 응답이 올바른 JSON이 아니거나 스키마 타입이 일치하지 않았습니다. 반드시 recommended_cities와 events는 리스트, weather/reason은 비어있지 않은 문자열로 지정하여 오직 순수한 JSON 객체로만 응답하세요.]"

                raw_text = self._call_raw_llm(current_prompt, system_prompt)
                cleaned_text = self._clean_json_text(raw_text)
                data = json.loads(cleaned_text)

                # 정밀 타입 및 스키마 검증 수행
                self.validate_schema(data)

                return data

            except Exception as e:
                if attempt == 2:
                    error_entry = make_error_entry(
                        step="llm_recommendation",
                        error_type="PARSE_ERROR",
                        message=f"LLM 1차 추천 JSON 파싱/타입검증 2회 실패: {self._sanitize_error_message(str(e))}",
                        severity="ERROR"
                    )
                    errors.append(error_entry)
                    # 파싱 최종 실패 시 폴백 데이터 반환
                    return {
                        "recommended_cities": ["제주"],
                        "recommended_city": "제주",
                        "weather": f"{date_str} 주변 계절 날씨",
                        "events": ["지역 문화 행사"],
                        "reason": "자동 추천 JSON 파싱 실패로 기본 도시가 설정되었습니다."
                    }

    def generate_markdown_report(
        self,
        date_str: str,
        rec_data: Dict[str, Any],
        places_by_city: Dict[str, List[Dict[str, Any]]],
        errors: List[Dict[str, Any]]
    ) -> str:
        """1차 추천 데이터(복수 지역), 지역별 맛집 검색 결과, 에러 목록을 종합하여 마크다운 리포트를 생성합니다."""
        system_prompt = "당신은 여행 리포트 작성 전문가입니다. 지정된 형식에 맞춰 완성도 높은 Markdown 여행 리포트를 작성하세요."

        cities = rec_data.get("recommended_cities") or [rec_data.get("recommended_city", "제주")]
        cities_str = ", ".join(cities)

        places_formatted = ""
        if places_by_city and any(places_by_city.values()):
            for city_name, place_list in places_by_city.items():
                places_formatted += f"### 📍 {city_name} 맛집 추천\n"
                if place_list:
                    for idx, p in enumerate(place_list, 1):
                        name = p.get("name", "이름 없음")
                        addr = p.get("address", "주소 정보 없음")
                        cat = p.get("category", "")
                        url = p.get("url", "")
                        places_formatted += f"{idx}. **{name}** ({cat})\n   - 주소: {addr}\n"
                        if url:
                            places_formatted += f"   - 링크: {url}\n"
                else:
                    places_formatted += "- 데이터 없음 (장소 검색 결과 0건 또는 API 호출 불가)\n"
                places_formatted += "\n"
        else:
            places_formatted = "- 데이터 없음 (장소 검색 결과 0건 또는 API 호출 불가)\n"

        errors_formatted = ""
        if errors:
            errors_formatted = "\n## 오류 요약(errors)\n"
            for err in errors:
                errors_formatted += f"- [{err.get('step')}] {err.get('type')}: {err.get('message')}\n"

        prompt = f"""
여행 날짜: {date_str}

[1차 추천 데이터]
- 추천 지역 목록: {cities_str}
- 날씨 요약: {rec_data.get('weather')}
- 행사/축제: {', '.join(rec_data.get('events', []))}
- 추천 이유: {rec_data.get('reason')}

[지역별 맛집 검색 결과 목록]
{places_formatted}

위 데이터를 바탕으로 아래 섹션을 포함하는 아름다운 마크다운 여행 리포트를 작성해주세요:

# {date_str} 국내 여행 추천 리포트

## 추천 지역
(추천 도시들: {cities_str} 및 요약)

## 추천 이유
(추천 근거 상세)

## 날씨 요약
(날씨 설명)

## 행사/축제
(축제/행사 리스트)

## 맛집 추천
(위 지역별 맛집 목록을 지역별 소제목으로 깔끔히 정리)

## 1일 일정 제안
(오전, 오후, 저녁 시간대별 1일 동선 제안)
{errors_formatted}
"""

        try:
            return self._call_raw_llm(prompt, system_prompt)
        except Exception as e:
            # LLM 2차 리포트 생성 실패 시 템플릿 마크다운 반환
            error_entry = make_error_entry(
                step="report_generation",
                error_type="LLM_ERROR",
                message=f"마크다운 리포트 LLM 생성 실패: {self._sanitize_error_message(str(e))}",
                severity="ERROR"
            )
            errors.append(error_entry)

            # 직접 템플릿 생성
            events_str = "\n".join([f"- {ev}" for ev in rec_data.get("events", [])])
            report_md = f"""# {date_str} 국내 여행 추천 리포트

## 추천 지역
- **{cities_str}**

## 추천 이유
{rec_data.get('reason')}

## 날씨 요약
{rec_data.get('weather')}

## 행사/축제
{events_str}

## 맛집 추천
{places_formatted}

## 1일 일정 제안
- **오전**: {cities[0]} 도착 및 주요 명소 둘러보기
- **오후**: 추천 맛집 방문 및 주변 도시({cities[-1]}) 구경
- **저녁**: 지역 야경 감상 및 마무리
"""
            if errors:
                report_md += "\n## 오류 요약(errors)\n"
                for err in errors:
                    report_md += f"- [{err.get('step')}] {err.get('type')}: {err.get('message')}\n"

            return report_md
