# [개선 구현 계획서] 1차 사전 평가 보완 계획 (17개 평가 항목 100% 달성)

1차 사전 평가 결과 **88% (15/17 통과)**를 달성하였습니다.
본 계획서는 **미통과(FAIL) 2개 항목**을 완벽히 보완하고, **통과(PASS) 15개 항목의 보완 권장사항**을 종합적으로 반영하여 프로그램의 완성도, 안정성, 정교함을 100% 수준으로 끌어올리기 위해 작성되었습니다.

---

## 1. 평가 결과 분석 및 보완 대상

| 평가 항목 | 결과 | 주요 지적 사항 | 보완 내용 |
| :--- | :---: | :--- | :--- |
| **#7 (LLM JSON 타입 검증)** | **FAIL** | 필수 키 존재 검증만 수행하고 데이터 타입 및 유효성(길이, 빈문자열 등) 미검증 | `llm_client.py`에 각 키의 기대 타입(`str`, `list`) 및 최소 길이, 빈 문자열/빈 배열 정밀 유효성 검증 구현 |
| **#17 (키워드/도시명 정규화)** | **FAIL** | 입력 도시명을 그대로 쿼리로 사용하여 세부지명/별칭/특수문자 처리 미흡 | `place_client.py`에 도시명 정규화 모듈(`normalize_city_name`) 구현 (별칭 매핑, 행정구역 수식어 정제) |
| **#1 (CLI 예시 및 도움말)** | PASS | CLI 도움말 예시 보강 권장 | `argparse` 도움말 예시 보강 및 `--refresh` (캐시 갱신) 플래그 추가 |
| **#4 (안전한 파일 저장)** | PASS | 파일 쓰기 중 권한/디스크 오류 대비 부족 | `report_generator.py`에 임시 파일(`*.tmp`) 기반 원자적(Atomic) 파일 쓰기 도입 |
| **#5 (시크릿 스캔 자동화)** | PASS | 생성 파일 대상 시크릿 검증 권장 | 파일 저장 직전 2차 시크릿 자동 마스킹 스캐너 적용 |
| **#6 (아키텍처 다이어그램)** | PASS | 전체 모듈 간 데이터 흐름 다이어그램 보완 | `README.md` 및 문서에 Mermaid 아키텍처 다이어그램 반영 |
| **#9 (에러 메타데이터)** | PASS | 에러 로그의 심각도/시각 메타데이터 부족 | `errors` 레코드에 `timestamp` (ISO 8601) 및 `severity` ("ERROR"/"WARNING") 필드 추가 |
| **#10 (REST API cURL 예시)** | PASS | GET/POST 호출 헤더/쿼리 cURL 예시 보강 | `README.md`에 GET/POST cURL 샘플 및 요청 방식 선택 이유 설명 추가 |
| **#11 (JSON 정상/비정상 예시)** | PASS | JSON 파싱 성공/실패 사례 문서화 | `README.md`에 정상 JSON 및 파싱 실패/재시도 예시 보강 |
| **#12 (네트워크 재시도/백오프)** | PASS | 5xx/네트워크 실패 시 재시도 전략 미구현 | `place_client.py`에 일시적 네트워크 오류 시 1~2회 지수 백오프(Exponential Backoff) 재시도 로직 추가 |
| **#15 (0건 시 대체 검색)** | PASS | 검색 0건 시 근접지역/광역 키워드 대체 검색 없음 | 장소 0건 시 광역시/도 단위 대체 키워드로 자동 재검색(Fallback Search) 기능 구현 |
| **#16 (캐시 만료/갱신 정책)** | PASS | 캐시 만료 정책(TTL) 및 강제 갱신 미흡 | 캐시 TTL(예: 24시간) 검증 및 `--refresh` 강제 갱신 CLI 옵션 추가 |

---

## 2. 모듈별 세부 보완 작업 계획

### Component 1: [llm_client.py](file:///d:/cody/2-2/llm_client.py) (FAIL #7 해결 & #9, #14 반영)
1. **정밀 타입 및 유효성 검증 (`validate_recommendation_schema`)**:
   - `recommended_city`: `isinstance(str)` & 공백 제거 후 1글자 이상
   - `weather`: `isinstance(str)` & 1글자 이상
   - `events`: `isinstance(list)` & 1개 이상의 항목 & 각 항목이 비어있지 않은 `str`
   - `reason`: `isinstance(str)` & 1글자 이상
   - 검증 실패 시 `TypeError` / `ValueError`를 발생시켜 LLM 1회 재시도(Retry) 로직이 자동 유발되도록 처리
2. **에러 메타데이터 구조화**:
   - `errors` 요소 추가 시 `timestamp` (ISO 8601 형식, 예: `2026-08-11T17:20:00Z`)와 `severity` (`"ERROR"`, `"WARNING"`) 필드 포함

---

### Component 2: [place_client.py](file:///d:/cody/2-2/place_client.py) (FAIL #17 해결 & #8, #12, #15 반영)
1. **도시명 입력 정규화 모듈 (`normalize_city_name`)**:
   - 별칭 매핑: `"제주도"` $\rightarrow$ `"제주"`, `"서울특별시"` $\rightarrow$ `"서울"`, `"부산광역시"` $\rightarrow$ `"부산"`, `"강원도 강릉시"` $\rightarrow$ `"강릉"`
   - 행정구역 접미사 정제: "특별자치도", "광역시", "특별시", "도", "시", "군" 수식어 제거 후 핵심 시/군 명칭 추출
2. **0건 검색 시 대체 키워드 자동 재검색 (Fallback Search)**:
   - 1차 검색(`f"{normalized_city} 맛집"`) 결과가 0건일 경우, 상위 광역시/도 또는 대명사 키워드(`f"{city} 대표 맛집"`)로 2차 대체 검색 시도 후 결과 반환
3. **네트워크 일시 오류 재시도 (Exponential Backoff)**:
   - 네트워크 연결 장애 또는 HTTP 5xx 서버 오류 발생 시 1초 대기 후 1회 재시도

---

### Component 3: [report_generator.py](file:///d:/cody/2-2/report_generator.py) & [config.py](file:///d:/cody/2-2/config.py) (Pass #4, #5, #16 반영)
1. **안전한 원자적(Atomic) 파일 저장**:
   - 파일 저장 시 `.tmp` 임시 파일에 먼저 기록 후 `os.replace()`를 사용하여 시스템 중단 시 파일 손상 차단
2. **저장 전 자동 시크릿 스캔 (Sanitizer)**:
   - JSON 및 MD 파일 저장 직전 2차 검증 스캐너를 실행하여 혹시라도 잔존할 수 있는 API 키 패턴 마스킹
3. **캐시 유효기간(TTL) 및 강제 갱신 지원**:
   - 저장된 JSON의 생성 시각을 체크하여 24시간 초과 시 자동으로 갱신하거나, CLI `--refresh` 옵션으로 캐시를 강제 무효화

---

### Component 4: [travel_planner.py](file:///d:/cody/2-2/travel_planner.py) & [README.md](file:///d:/cody/2-2/README.md) (Pass #1, #6, #10, #11, #13 반영)
1. **CLI 사용자 경험 보강**:
   - `travel_planner.py`에 `--refresh` (캐시 무효화) 플래그 추가
   - 도움말(`--help`)에 명확한 사용 예시 및 설명 추가
2. **README.md 설명 보강**:
   - 모듈 간 데이터 흐름 아키텍처 Mermaid 다이어그램 추가
   - GET vs POST API cURL 호출 예시 및 헤더/쿼리 차이 상세 설명
   - LLM JSON 응답 정상/비정상 파싱 사례 예시 추가
   - 운영 환경(AWS Secrets Manager, HashiCorp Vault) 연계 보안 권장사항 추가

---

## 3. 검증 계획 (Verification Plan)

1. **타입 검증 및 재시도 테스트**:
   - LLM 응답에서 `events`가 배열이 아닌 문자열로 오거나 빈 배열일 때 1회 재시도가 정상 작동하는지 검증
2. **입력 정규화 테스트**:
   - `"제주특별자치도"`, `"강원도 강릉시"`, `"서울특별시"` 입력 시 각각 `"제주"`, `"강릉"`, `"서울"`로 정상 정규화되어 맛집 검색이 수행되는지 테스트
3. **0건 검색 대체 로직 테스트**:
   - 검색 결과가 없는 가상의 지명 입력 시 대체 키워드로 자동 재검색되는지 확인
4. **전체 단위 테스트 연동**:
   - `test_planner.py`에 정규화, 타입 검증, 원자적 저장 테스트 케이스를 추가하여 100% 통과 확인
