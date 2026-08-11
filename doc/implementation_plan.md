# [구현 계획서] Python API 활용 국내 여행지 추천 프로그램 개발

이 계획서는 `mission_description.md`의 모든 요구사항을 완벽히 충족하기 위해 작성된 단계별 초보자 가이드입니다.
사용자가 여행 날짜(`-date YYYY-MM-DD`)를 입력하면, **LLM API**(여행지 추천/날씨/행사)와 **지도 API**(Kakao/Naver 맛집 검색)를 조합하여 원본 데이터(`JSON`) 및 최종 여행 리포트(`Markdown`)를 자동 생성하는 CLI 프로그램을 개발합니다.

---

## 1. 개요 및 전체 흐름 (Architecture Overview)

```mermaid
graph TD
    A[CLI 실행: python travel_planner.py --date "2026-03-15"] --> B[1. CLI 입력 검증 & API 키 확인]
    B --> C[2. [1/3] LLM API 1차 호출: 여행지/날씨/축제 추천 (JSON)]
    C -->|JSON 파싱 시도 (실패 시 1회 재시도)| D[3. [2/3] 지도 API 호출: 추천 도시 맛집 검색]
    D -->|검색 성공 또는 실패/0건 처리| E[4. [3/3] LLM API 2차 호출: 최종 리포트 생성 (Markdown)]
    E --> F[5. results/ 폴더에 JSON 원본 및 MD 리포트 저장]
    F --> G[완료 메세지 및 저장 경로 출력]
```

---

## 2. 주요 구성요소 및 파일 구조

| 구분 | 파일 경로 | 설명 |
| :--- | :--- | :--- |
| **[NEW]** | [.env.example](file:///d:/cody/2-2/.env.example) | API 키 설정 템플릿 파일 |
| **[NEW]** | [.gitignore](file:///d:/cody/2-2/.gitignore) | API 키(`.env`) 및 파이썬 캐시 제외 설정 |
| **[NEW]** | [requirements.txt](file:///d:/cody/2-2/requirements.txt) | 필요한 외부 라이브러리 목록 |
| **[NEW]** | [config.py](file:///d:/cody/2-2/config.py) | 환경 변수 로드 및 API 키 검증 모듈 |
| **[NEW]** | [llm_client.py](file:///d:/cody/2-2/llm_client.py) | OpenAI/Gemini LLM API 호출 및 JSON 파싱/재시도 모듈 |
| **[NEW]** | [place_client.py](file:///d:/cody/2-2/place_client.py) | Kakao/Naver 지도 장소 검색 API 연동 및 에러 처리 모듈 |
| **[NEW]** | [report_generator.py](file:///d:/cody/2-2/report_generator.py) | Markdown 리포트 생성 및 JSON 파일 저장 모듈 |
| **[NEW]** | [travel_planner.py](file:///d:/cody/2-2/travel_planner.py) | 메인 CLI 실행 스크립트 |
| **[MODIFY]** | [README.md](file:///d:/cody/2-2/README.md) | 프로젝트 설명, 설치/실행 가이드, API 키 설정 방법 |

---

## 3. 사용자 검토 항목 (User Review Required)

> [!IMPORTANT]
> **사용자 선택 필요 (API 제공자)**
> 본 프로그램은 요구사항에 따라 2가지 API 계열을 선택할 수 있습니다. 본 기본 계획에서는 아래 조합을 기본 표준으로 채택하여 작성되었습니다.
> - **LLM API**: `OpenAI API` (`gpt-4o-mini` 또는 `gpt-3.5-turbo`) 또는 `Google Gemini API`
> - **지도/장소 API**: `Kakao Local API` (카카오 개발자 디벨로퍼 키) 또는 `Naver Local Search API`
> 
> 기본 구현 시 **OpenAI API + Kakao Local API** (또는 환경변수에 세팅된 서비스)를 자동 감지하도록 유연하게 작성할 예정입니다.

---

## 4. 초보자를 위한 단계별 상세 구현 절차

### Phase 1: 개발 환경 및 보안 설정 (Setup & Security)
- **Step 1.1: 가상환경 구축 및 라이브러리 정의**
  - 파이썬 3.10+ 환경에서 실행할 가상환경(`venv`) 생성
  - `requirements.txt` 작성:
    - `python-dotenv`: `.env` 파일의 환경변수 읽기
    - `requests`: 지도 API HTTP 요청용
    - `openai` / `google-genai`: LLM API 호출용
- **Step 1.2: 보안 정책 적용 (`.env`, `.gitignore`)**
  - `.env.example` 작성: `OPENAI_API_KEY=...`, `KAKAO_REST_API_KEY=...` 안내
  - `.gitignore` 작성하여 `.env` 및 `results/` 파일이 Git에 추가되지 않도록 사전 차단

---

### Phase 2: 설정 로드 및 CLI 입력 검증 (Config & CLI Parsing)
- **Step 2.1: `config.py` - API 키 사전 검증 모듈**
  - 프로그램 시작 시 `.env` 로드
  - 필수 키가 없을 경우: `"API 키가 설정되지 않았습니다. .env 파일을 확인해주세요."` 출력 후 즉시 종료(`sys.exit(1)`)
- **Step 2.2: `travel_planner.py` - argparse 날짜 입력 검증**
  - `-date "YYYY-MM-DD"` 또는 `--date "YYYY-MM-DD"` 필수 옵션 추가
  - 정규표현식(`^\d{4}-\d{2}-\d{2}$`) 및 `datetime.strptime`을 사용하여 유효한 날짜인지 검증
  - 날짜 형식이 올바르지 않으면 사용법을 출력하고 종료

---

### Phase 3: 외부 API 연동 모듈 개발 (API Clients)

- **Step 3.1: `llm_client.py` - 1차 추천 및 JSON 파싱**
  - **입력**: 여행 날짜 (`YYYY-MM-DD`)
  - **프롬프트 설계**: 반드시 JSON 형식으로만 응답하도록 지시
  - **필수 스키마 검증**:
    - `recommended_city` (string)
    - `weather` (string)
    - `events` (array of string)
    - `reason` (string)
  - **JSON 파싱 및 재시도(Retry) 로직**:
    - 마크다운 코드블록(` ```json ... ``` `) 자동 제거 후 `json.loads()` 시도
    - 파싱 실패 시, "반드시 유효한 JSON 형식으로만 응답해달라"는 프롬프트를 추가하여 **최대 1회 재시도**
    - 재시도 실패 시 internal `errors` 목록에 기록

- **Step 3.2: `place_client.py` - 맛집 검색 API**
  - **입력**: 1차 추천 결과의 `recommended_city` (예: `"제주"`)
  - **검색 쿼리**: `f"{city} 맛집"` 기준 5개 검색
  - **필드 추출**: `name`, `address`, `category`, `url`, `x`, `y` (또는 `lat`, `lng`)
  - **예외 처리 & 예외 허용**:
    - HTTP 401/403 (인증 실패): 에러 로그 기록 (`{"step": "place_search", "type": "AUTH_ERROR", "message": "HTTP 401"}`), 맛집 목록은 빈 리스트 `[]` 반환하고 프로세스 진행
    - 검색 결과 0건: 에러 로그 기록 (`{"step": "place_search", "type": "EMPTY_RESULT", "message": "0 results..."}`), 빈 리스트 `[]` 반환 후 계속 진행
    - 네트워크 예외: 프로그램 중단 없이 `errors`에 추가 후 진행

---

### Phase 4: 최종 리포트 생성 및 저장 (Report & Storage)

- **Step 4.1: `report_generator.py` - Markdown 리포트 생성**
  - **입력**: 1차 추천 JSON + 맛집 목록 + 에러 목록 (`errors`)
  - **LLM 2차 호출**: 위 정보들을 종합하여 깔끔한 Markdown 리포트 작성
  - **포함 필수 항목**:
    1. 추천 지역 및 추천 이유
    2. 날씨 요약
    3. 행사/축제 목록
    4. 맛집 리스트 (0건일 경우 `"데이터 없음 (장소 검색 결과 0건)"` 표시)
    5. 1일 일정 제안 (오전 / 오후 / 저녁)
    6. (에러 발생 시) `## 오류 요약(errors)` 섹션 포함
- **Step 4.2: `results/` 결과 파일 저장**
  - `results/` 폴더가 없으면 자동 생성 (`os.makedirs("results", exist_ok=True)`)
  - 원본 데이터 JSON 저장: `results/{date}_travel_data.json`
    - 포함 내용: 1차 추천 JSON, 맛집 검색 결과 배열, `errors` 배열
  - 최종 리포트 MD 저장: `results/{date}_travel_plan.md`

---

### Phase 5: 보너스 기능 & README 작성 (Bonus & Documentation)

- **Step 5.1: (보너스) 결과 캐싱 기능 구현**
  - 동일한 `-date` 옵션으로 재실행할 경우, 이미 `results/{date}_travel_data.json` 파일이 존재하면 기존 데이터 활용/경고 메세지 출력 선택 가능하도록 지원
- **Step 5.2: `README.md` 작성**
  - **프로그램 개요 및 특징**
  - **개발 환경 및 사전 준비 사항**
  - **API 키 발급 및 `.env` 설정 방법 (보안 주의사항 포함)**
  - **프로그램 설치 및 실행 방법 (`python travel_planner.py --date "2026-03-15"`)**
  - **결과물 파일 확인 방법**

---

## 5. 검증 계획 (Verification Plan)

### 자동 및 수동 검증 절차

1. **정상 입력 실행 검증**:
   - `python travel_planner.py --date "2026-03-15"` 실행
   - 터미널에 진행 로그 `[1/3]`, `[2/3]`, `[3/3]`가 올바르게 표시되는지 확인
   - `results/2026-03-15_travel_data.json` 및 `results/2026-03-15_travel_plan.md` 파일 생성 여부 확인
2. **날짜 입력 검증 테스트**:
   - `python travel_planner.py --date "invalid-date"` 실행 시 사용법 출력 후 즉시 종료되는지 확인
3. **API 키 미설정 예외 테스트**:
   - `.env` 키를 임시 제거 후 실행 시 즉시 종료 및 설정 안내 문구가 나오는지 확인
4. **장소 검색 0건/인증 실패 예외 테스트**:
   - 장소 API 키를 잘못 입력했을 때 프로그램이 멈추지 않고, 맛집 정보는 `"데이터 없음"`으로 표시되며 MD 리포트가 완성되는지 확인
