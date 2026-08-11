# [Walkthrough] 국내 여행지 추천 CLI 프로그램 구현 및 사전 평가 보완 결과

본 문서는 `mission_description.md` 요구사항에 따른 초판 개발 내역과, 1차 사전 평가(88%, 15/17 통과) 이후 식별된 보완 사항(FAIL 2개 및 PASS 15개 항목의 고도화)을 연속적으로 반영하여 작성한 통합 워크스루 문서입니다.

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

1차 사전 평가 결과(**15/17 통과, 88%**)의 지적 항목을 반영하여 아래와 같이 기능을 대폭 보완·고도화하였습니다:

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
7. **[PASS #6, #10, #11, #13 보완] 문서화 강화**: `README.md`에 Mermaid 아키텍처 다이어그램, REST API GET/POST cURL 호출 예시, JSON 파싱 사례 코드블록, 비밀관리 시스템 연계 권장사항 보강.

---

## 3. 종합 검증 및 테스트 결과 (Verification Results)

### 3.1. 자동 단위 테스트 (`test_planner.py`)
7개 핵심 단위/통합 테스트 케이스를 구축하고 100% 통과했습니다.
```bash
python -m unittest test_planner.py
.......
----------------------------------------------------------------------
Ran 7 tests in 0.041s
OK
```

### 3.2. 실시간 연동 테스트 (`--refresh` 플래그)
```bash
python travel_planner.py --date "2026-08-11" --refresh
```
- LLM API (`gemini-flash-lite-latest`)로 1차 추천 도시 `"강릉"` 수집
- `normalize_city_name` 정규화 및 Kakao Local API 맛집 5곳 성공적 수집
- 스키마 검증 통과, 원자적 저장 및 시크릿 스캔을 거쳐 `results/` 폴더 내 JSON과 MD 파일이 에러 0건으로 정상 저장됨 확인.

---

## 4. 사용 방법 (Usage)

```bash
# 일반 실행 (24시간 내 기존 결과가 있으면 캐시 로드)
python travel_planner.py --date "2026-08-11"

# 강제 캐시 무효화 및 새로 호출 (--refresh)
python travel_planner.py --date "2026-08-11" --refresh
```
