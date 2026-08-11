# [Walkthrough] 국내 여행지 추천 CLI 프로그램 구현 및 보너스 과제 완료 결과

본 문서는 `mission_description.md` 요구사항에 따른 초판 개발 내역, 1차 사전 평가(88%, 15/17 통과) 보완 사항, 그리고 **선택 보너스 과제 2개(복수 지역 추천 & 결과 캐싱 최적화)** 구현 및 검증 결과를 담은 통합 워크스루 문서입니다.

---

## 1. 초기 구현 내용 (Initial Implementation)

### 1.1. 주요 모듈 구조
- **[config.py](file:///d:/cody/2-2/config.py)**: `.env` 환경 변수 로드 및 필수 API 키 미설정 시 안내 후 빠른 종료(`sys.exit(1)`)
- **[llm_client.py](file:///d:/cody/2-2/llm_client.py)**:
  - OpenAI(`OPENAI_API_KEY`) 및 Google Gemini(`GEMINI_API_KEY`) 지원
  - 1차 추천 JSON 생성 및 마크다운 코드블록 제거/파싱
  - JSON 파싱 실패 시 **최대 1회 자동 재시도 (Retry)**
  - 최종 2차 Markdown 리포트 자동 작성
- **[place_client.py](file:///d:/cody/2-2/place_client.py)**:
  - Kakao Local API 및 Naver Local Search API 지원
  - 인증 오류(HTTP 401/403) 및 검색 결과 0건 시 중단 없이 `errors` 목록 기록 후 `데이터 없음`으로 리포트 자동 작성
- **[report_generator.py](file:///d:/cody/2-2/report_generator.py)**:
  - `results/` 디렉터리 자동 생성
  - 원본 데이터 JSON (`results/{date}_travel_data.json`) 및 Markdown 리포트 (`results/{date}_travel_plan.md`) 저장
- **[travel_planner.py](file:///d:/cody/2-2/travel_planner.py)**: 메인 CLI 스크립트 (`-date "YYYY-MM-DD"` 검증 및 진행 로그 출력)
- **[README.md](file:///d:/cody/2-2/README.md)**: 설치, API 키 설정(보안), 실행 방법 및 결과 확인 가이드

---

## 2. 1차 사전 평가 결과 반영 및 보완 내용 (Review Remediation)

### 2.1. 미통과(FAIL) 항목 완전 보완
1. **[FAIL #7 보완] LLM JSON 정밀 타입 및 유효성 검증 (`llm_client.py`)**:
   - `validate_schema()` 정밀 검증 함수 추가: `recommended_city`, `weather`, `reason`이 비어있지 않은 문자열(`str`)인지, `events`가 1개 이상의 항목을 가진 리스트(`list`)인지 타입 및 값 유효성 체킹.
   - 검증 실패 시 예외를 발생시켜 LLM 1회 자동 재시도(Retry)가 정상 유발되도록 처리.
2. **[FAIL #17 보완] 도시명 입력 정규화 모듈 (`place_client.py`)**:
   - `normalize_city_name()` 함수 추가: 지명 별칭 매핑(`"제주특별자치도"` $\rightarrow$ `"제주"`, `"서울특별시"` $\rightarrow$ `"서울"`), 행정구역 수식어 구문 분해(`"강원도 강릉시"` $\rightarrow$ `"강릉"`) 및 접미사 정제.

### 2.2. 통과(PASS) 항목 품질 고도화
1. **[PASS #9 보완] 에러 메타데이터 확장**: `errors` 레코드에 `timestamp` (ISO 8601 UTC) 및 `severity` (`"ERROR"`, `"WARNING"`) 메타데이터 포함.
2. **[PASS #15 보완] 0건 검색 대체 재검색 (Fallback Search)**: 1차 맛집 검색 0건 시 광역시/도 단위 또는 대명사 키워드(`f"{city} 대표 식당"`)로 자동 2차 대체 검색 시도.
3. **[PASS #12 보완] 지수 백오프 재시도**: 네트워크 연결 장애 또는 HTTP 5xx 서버 오류 발생 시 1초 대기 지수 백오프(Exponential Backoff) 재시도 로직 적용.
4. **[PASS #4 보완] 원자적(Atomic) 파일 저장**: `report_generator.py`에 `.tmp` 임시 파일 생성 후 `os.replace()`를 사용하는 안전한 파일 저장 구현.
5. **[PASS #5 보완] 자동 시크릿 2차 스캐너**: 파일 저장 직전 `_sanitize_output_text()`로 혹시 모를 API 키 패턴 자동 마스킹.
6. **[PASS #16 보완] 캐시 TTL 및 `--refresh` 옵션**: 24시간 TTL 기반 캐시 검증 및 CLI `--refresh` (강제 캐시 무효화 및 재호출) 옵션 추가.

---

## 3. 선택 보너스 과제 구현 및 완성 (Bonus Tasks)

### 3.1. 보너스 과제 1: 복수 지역 추천 및 그룹화 리포트
- **1차 추천 스키마 확장**: `recommended_cities: ["강릉", "속초"]`와 같이 2~3개 도시를 수집하도록 프롬프트 및 `validate_schema()` 확장 (단일 도시 하위 호환 유지).
- **다중 지역 맛집 루프 검색**: 추천된 각 도시별로 `place_client.search_restaurants(city)`를 루프 호출하여 `restaurants_by_city` 구조 수집.
- **지역별 맛집 리포트 그룹화**: 2차 마크다운 생성 시 `### 📍 강릉 맛집`, `### 📍 속초 맛집` 등 지역별 소제목으로 정돈하여 1일 동선 연계 리포트 완성.

### 3.2. 보너스 과제 2: 결과 캐싱 최적화
- 동일한 `-date`로 재실행 시 24시간 TTL 이내의 기존 `results/{date}_travel_data.json` 데이터를 감지하여 외부 API 호출을 생략하고 리포트를 재생성.
- 필요 시 `--refresh` 옵션으로 캐시를 즉시 무효화하고 최신 정보 수집 지원.

---

## 4. 종합 검증 및 테스트 결과 (Verification Results)

### 4.1. 자동 단위 테스트 (`test_planner.py`)
복수 지역 추천, 정밀 스키마 검증, 지명 정규화, 에러 타임스탬프, 원자적 저장 및 캐시 무효화 포함 7개 핵심 유닛 테스트 100% 통과.
```bash
python -m unittest test_planner.py
.......
----------------------------------------------------------------------
Ran 7 tests in 0.039s
OK
```

### 4.2. 복수 지역 라이브 연동 테스트 (`travel_planner.py --date "2026-08-15" --refresh`)
```text
==================================================
 [INFO] 국내 여행 추천 프로그램 시작 (날짜: 2026-08-15)
==================================================

[1/3] 1차 추천 생성 중(LLM)...
  - recommended_cities: ['강릉', '속초']

[2/3] 지역별 맛집 검색 중(지도/장소 API)...
  - [강릉] 맛집 3곳 검색 완료
  - [속초] 맛집 3곳 검색 완료

[3/3] 최종 리포트 생성 중(LLM)...
  - 리포트 생성 완료

==================================================
 [완료] 결과물이 저장되었습니다.
 - 원본 JSON: results\2026-08-15_travel_data.json
 - 리포트 MD: results\2026-08-15_travel_plan.md
==================================================
```
- **결과**: `results/2026-08-15_travel_plan.md` 파일에 **강릉 맛집 3곳** 및 **속초 맛집 3곳**이 지역별로 완벽히 그룹화되어 리포트 저장 완료.

---

## 5. 사용 방법 (Usage)

```bash
# 기본 실행 (24시간 내 캐시 활용)
python travel_planner.py --date "2026-08-15"

# 강제 캐시 무효화 및 새로 호출 (--refresh)
python travel_planner.py --date "2026-08-15" --refresh
```
