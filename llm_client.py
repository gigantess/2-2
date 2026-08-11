"""
llm_client.py
LLM API (OpenAI 또는 Google Gemini) 연동 및 JSON 추출 모듈
1차 추천(JSON) 생성, 파싱 실패 시 재시도(1회), 최종 Markdown 리포트 생성을 담당합니다.
"""

import json
import re
import requests
from typing import Dict, Any, List, Tuple, Optional

class LLMClient:
    def __init__(self, config: Dict[str, Optional[str]]):
        self.openai_api_key = config.get("OPENAI_API_KEY")
        self.gemini_api_key = config.get("GEMINI_API_KEY")

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
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
        headers = {"Content-Type": "application/json"}

        full_text = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
        payload = {
            "contents": [{
                "parts": [{"text": full_text}]
            }]
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

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

    def get_recommendation(self, date_str: str, errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        1차 추천 데이터를 생성하고 JSON으로 파싱합니다.
        실패 시 1회 재시도하며, 최종 실패 시 errors 목록에 기록하고 기본값을 반환합니다.
        """
        system_prompt = (
            "당신은 국내 여행 전문가입니다. 반드시 아래 지정된 JSON 형식으로만 응답해야 합니다.\n"
            "다른 인사말이나 설명 텍스트, 마크다운 외 텍스트는 절대 포함하지 마세요."
        )

        user_prompt = f"""
여행 날짜: {date_str}

위 여행 날짜에 맞춰 국내 여행지를 1곳 추천하고, 해당 시기의 날씨 요약 및 행사/축제 정보, 추천 근거를 작성하세요.

반드시 아래 필드를 포함하는 JSON 객체로만 응답하세요:
{{
  "recommended_city": "추천 도시 이름 (예: 제주, 강릉, 경주)",
  "weather": "해당 시기의 일반적인 날씨 요약 (1문장)",
  "events": ["행사/축제 후보 1", "행사/축제 후보 2"],
  "reason": "추천 근거 (2~4문장)"
}}
"""

        for attempt in range(1, 3):  # 최초 시도 + 최대 1회 재시도 (총 2회)
            try:
                current_prompt = user_prompt
                if attempt == 2:
                    current_prompt += "\n\n[주의: 이전 응답이 올바른 JSON이 아니었습니다. 다른 문자 없이 오직 순수한 JSON 객체만 응답하세요.]"

                raw_text = self._call_raw_llm(current_prompt, system_prompt)
                cleaned_text = self._clean_json_text(raw_text)
                data = json.loads(cleaned_text)

                # 필수 키 검증
                required_keys = ["recommended_city", "weather", "events", "reason"]
                missing_keys = [k for k in required_keys if k not in data]
                if missing_keys:
                    raise ValueError(f"필수 키 누락: {missing_keys}")

                return data

            except Exception as e:
                if attempt == 2:
                    error_entry = {
                        "step": "llm_recommendation",
                        "type": "PARSE_ERROR",
                        "message": f"LLM 1차 추천 JSON 파싱 2회 실패: {self._sanitize_error_message(str(e))}"
                    }
                    errors.append(error_entry)
                    # 파싱 최종 실패 시 폴백 데이터 반환
                    return {
                        "recommended_city": "제주",
                        "weather": f"{date_str} 주변 계절 날씨",
                        "events": ["지역 문화 행사"],
                        "reason": "자동 추천 JSON 파싱 실패로 기본 도시가 설정되었습니다."
                    }

    def generate_markdown_report(
        self,
        date_str: str,
        rec_data: Dict[str, Any],
        places: List[Dict[str, Any]],
        errors: List[Dict[str, Any]]
    ) -> str:
        """1차 추천 데이터, 맛집 검색 결과, 에러 목록을 종합하여 마크다운 리포트를 생성합니다."""
        system_prompt = "당신은 여행 리포트 작성 전문가입니다. 지정된 형식에 맞춰 완성도 높은 Markdown 여행 리포트를 작성하세요."

        places_formatted = ""
        if places:
            for idx, p in enumerate(places, 1):
                name = p.get("name", "이름 없음")
                addr = p.get("address", "주소 정보 없음")
                cat = p.get("category", "")
                url = p.get("url", "")
                places_formatted += f"{idx}. **{name}** ({cat})\n   - 주소: {addr}\n"
                if url:
                    places_formatted += f"   - 링크: {url}\n"
        else:
            places_formatted = "- 데이터 없음 (장소 검색 결과 0건 또는 API 호출 불가)"

        errors_formatted = ""
        if errors:
            errors_formatted = "\n## 오류 요약(errors)\n"
            for err in errors:
                errors_formatted += f"- [{err.get('step')}] {err.get('type')}: {err.get('message')}\n"

        prompt = f"""
여행 날짜: {date_str}

[1차 추천 데이터]
- 추천 지역: {rec_data.get('recommended_city')}
- 날씨 요약: {rec_data.get('weather')}
- 행사/축제: {', '.join(rec_data.get('events', []))}
- 추천 이유: {rec_data.get('reason')}

[맛집 검색 결과 목록]
{places_formatted}

위 데이터를 바탕으로 아래 섹션을 포함하는 아름다운 마크다운 여행 리포트를 작성해주세요:

# {date_str} 국내 여행 추천 리포트

## 추천 지역
(추천 도시 및 요약)

## 추천 이유
(추천 근거 상세)

## 날씨 요약
(날씨 설명)

## 행사/축제
(축제/행사 리스트)

## 맛집 추천
(위 맛집 목록 정리 또는 데이터 없음 표기)

## 1일 일정 제안
(오전, 오후, 저녁 시간대별 1일 동선 제안)
{errors_formatted}
"""

        try:
            return self._call_raw_llm(prompt, system_prompt)
        except Exception as e:
            # LLM 2차 리포트 생성 실패 시 템플릿 마크다운 반환
            errors.append({
                "step": "report_generation",
                "type": "LLM_ERROR",
                "message": f"마크다운 리포트 LLM 생성 실패: {self._sanitize_error_message(str(e))}"
            })

            # 직접 템플릿 생성
            events_str = "\n".join([f"- {ev}" for ev in rec_data.get("events", [])])
            report_md = f"""# {date_str} 국내 여행 추천 리포트

## 추천 지역
- **{rec_data.get('recommended_city')}**

## 추천 이유
{rec_data.get('reason')}

## 날씨 요약
{rec_data.get('weather')}

## 행사/축제
{events_str}

## 맛집 추천
{places_formatted}

## 1일 일정 제안
- **오전**: {rec_data.get('recommended_city')} 도착 및 주요 명소 둘러보기
- **오후**: 추천 맛집 방문 및 지역 대표 축제/행사 참여
- **저녁**: 지역 야경 감상 및 마무리
"""
            if errors:
                report_md += "\n## 오류 요약(errors)\n"
                for err in errors:
                    report_md += f"- [{err.get('step')}] {err.get('type')}: {err.get('message')}\n"

            return report_md
