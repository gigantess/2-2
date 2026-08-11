# 국내 여행지 추천 및 맛집 정보 연동 CLI 프로그램

본 프로젝트는 **LLM API**(OpenAI / Google Gemini)와 **지도/장소 검색 API**(Kakao Local / Naver Local Search)를 연동하여, 사용자가 입력한 여행 날짜(`-date YYYY-MM-DD`)에 맞는 추천 여행지, 날씨, 축제 정보 및 맛집 목록을 종합한 **원본 JSON 데이터**와 **최종 마크다운 리포트**를 자동 생성하는 CLI 응용 프로그램입니다.

---

## 📌 1. 프로그램 개요 및 특징

- **CLI 기반 인터페이스**: `argparse`를 활용하여 `-date "YYYY-MM-DD"` 형태의 날짜 입력을 받아 검증합니다.
- **다중 API 연동 파이프라인**:
  1. **LLM 1차 호출**: 입력받은 날짜에 대한 추천 도시, 날씨 요약, 축제 정보, 추천 근거를 **구조화된 JSON**으로 수집
  2. **지도/장소 API 호출**: 1차 추천 도시를 기반으로 맛집 5곳(상호명, 주소, 카테고리, 좌표, 지도 링크) 검색
  3. **LLM 2차 호출**: 추천 정보와 맛집 목록을 결합하여 완성도 높은 **Markdown 여행 리포트** 작성
- **보안 및 장애 대처(Fault Tolerance)**:
  - API 키 미설정 시 가이드 출력 후 빠른 종료 (`sys.exit(1)`)
  - LLM JSON 파싱 오류 시 자동 1회 재시도 (Retry)
  - 지도 API 인증 오류(401/403) 또는 검색 결과 0건 시, 프로그램 중단 없이 `데이터 없음`으로 리포트 생성 계속 진행
- **결과 캐싱 (보너스 과제)**: 동일한 날짜로 재실행 시 기존 수집된 원본 JSON 데이터를 자동 감지 및 재활용하여 API 비용과 속도를 최적화합니다.

---

## 🛠️ 2. 개발 및 실행 환경

- **언어**: Python 3.10 이상
- **의존성 라이브러리**:
  - `python-dotenv`: `.env` 파일 기반 환경변수 로드
  - `requests`: 지도/장소 REST API 및 Gemini API HTTP 통신
  - `openai`: OpenAI GPT API 연동 (선택)

---

## 🔑 3. API 키 설정 방법 및 보안 정책 (필수)

> [!CAUTION]
> **보안 관리 정책**: API 키를 소스코드, README, Public Git 저장소에 절대로 노출하지 마세요. 과금 방지 및 개인정보 보호를 위해 반드시 `.env` 파일로 관리하며, `.gitignore`에 등록되어 있습니다.

### 설정 방법
1. 프로젝트 루트에 `.env` 파일을 생성합니다 (또는 `.env.example` 복사).
2. 발급받은 API 키를 설정합니다:

```env
# LLM API 키 (OpenAI 또는 Gemini 중 1개 선택 설정)
# OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Gemini LLM 모델 지정 (기본값: gemini-flash-lite-latest)
# GEMINI_MODEL=gemini-flash-lite-latest

# 지도/장소 검색 API 키 (Kakao 또는 Naver 중 1개 선택 설정)
KAKAO_REST_API_KEY=your_kakao_rest_api_key_here
# NAVER_CLIENT_ID=your_naver_client_id_here
# NAVER_CLIENT_SECRET=your_naver_client_secret_here
```

---

## 🚀 4. 프로그램 실행 및 미션별 스크린샷 가이드

### 4.1. 미션 1: 정상 CLI 실행 및 API 조합 파이프라인 (Pass 1)
여행 날짜를 입력받아 LLM 1차 추천 → 지도 맛집 검색 → LLM 2차 리포트 생성을 순차적으로 진행합니다.

```bash
python travel_planner.py --date "2026-08-11"
```

![1차 정상 실행 (Pass 1)](screenshot/execution_plan_pass1.png)

---

### 4.2. 미션 2: 결과 캐싱을 통한 최적화 (Pass 2 - 보너스 과제)
동일한 날짜로 재실행할 경우, 이미 생성된 `results/{date}_travel_data.json` 파일을 감지하여 외부 API 추가 호출을 건너뛰고 기존 데이터를 재활용합니다.

```bash
python travel_planner.py --date "2026-08-11"
```

![캐시 감지 재실행 (Pass 2)](screenshot/execution_plan_pass2.png)

---

### 4.3. 미션 3: CLI 입력 검증 및 API 키 미설정 예외 처리
- **날짜 형식 검증**: 올바르지 않은 날짜 형식(`YYYY-MM-DD`)이나 존재하지 않는 날짜가 입력될 경우 사용법을 안내하고 종료합니다.
- **API 키 검증**: 필수 API 키가 설정되지 않은 경우 설정 방법을 상세히 안내하고 즉시 종료합니다.

```bash
# 날짜 형식 오류 테스트
python travel_planner.py --date "invalid-date"
```

![CLI 입력 검증 및 API 키 미설정 예외 처리](screenshot/execution_plan_error.png)

---

### 4.4. 미션 4: 외부 API 연동 오류 핸들링 및 유연한 복구 (Fault Tolerance)
지도 API 인증 실패(401/403)나 검색 결과가 0건인 경우에도 프로그램이 중단되지 않고, 맛집 섹션을 `"데이터 없음"`으로 처리하며 최종 마크다운 리포트에 `## 오류 요약(errors)` 섹션을 남기고 계속 진행합니다.

![외부 API 오류 핸들링 및 예외 복구](screenshot/api_connect_error.png)

---

## 📂 5. 결과물 데이터 구조 및 확인 (`results/`)

프로그램 실행이 완료되면 `results/` 폴더에 2개의 파일이 자동으로 저장됩니다.

```
results/
├── 2026-08-11_travel_data.json  # 원본 데이터 JSON
├── 2026-08-11_travel_plan.md    # 최종 여행 리포트 Markdown
├── 2026-08-12_travel_data.json
└── 2026-08-12_travel_plan.md
```

### 5.1. 원본 데이터 JSON 구조 예시 (`2026-08-11_travel_data.json`)
```json
{
  "date": "2026-08-11",
  "recommendation": {
    "recommended_city": "강릉",
    "weather": "8월 중순의 강릉은 한여름 무더위가 이어지며, 맑고 화창한 날씨와 함께 해수욕을 즐기기 가장 좋은 기온을 보입니다.",
    "events": [
      "경포 여름바다예술제",
      "강릉 수제맥주 페스티벌"
    ],
    "reason": "8월 11일은 본격적인 휴가 성수기 시즌으로 동해안의 에메랄드빛 바다와 송림이 어우러진 경포해변..."
  },
  "restaurants": [
    {
      "name": "9남매두부집",
      "address": "강원특별자치도 강릉시 초당원길 63-2",
      "category": "음식점 > 한식 > 두부전문점",
      "url": "http://place.map.kakao.com/18636898",
      "x": 128.91390117047928,
      "y": 37.786906250322346
    }
  ],
  "errors": []
}
```

### 5.2. 최종 마크다운 리포트 예시 (`2026-08-11_travel_plan.md`)
```markdown
# 2026-08-11 국내 여행 추천 리포트

## 추천 지역
**강릉**

## 추천 이유
8월 11일은 본격적인 휴가 성수기 시즌으로 동해안의 아름다운 자연을 만끽하기에 최적의 시기입니다...

## 날씨 요약
8월 중순의 강릉은 한여름 무더위가 이어지며 맑고 화창합니다.

## 행사/축제
- 경포 여름바다예술제
- 강릉 수제맥주 페스티벌

## 맛집 추천
1. **[9남매두부집](http://place.map.kakao.com/18636898)** - 강원특별자치도 강릉시 초당원길 63-2

## 1일 일정 제안
- **[오전]**: 경포해변 산책 및 초당순두부 점심 식사
- **[오후]**: 안목해변 커피거리 방문 및 휴식
- **[저녁]**: 장칼국수 저녁 식사 및 경포 여름바다예술제 참여
```

---

## 🎓 6. 과제 목표 달성 및 학습 정리

본 미션을 통해 아래 핵심 개념과 실무 대처 원칙을 습득하였습니다:

1. **REST API 및 HTTP 메서드 (GET vs POST)**:
   - GET 요청: Kakao/Naver 장소 검색 API 호출 시 쿼리 파라미터를 사용한 데이터 조회
   - POST 요청: OpenAI/Gemini LLM API 호출 시 헤더 인증(`X-goog-api-key`, `Authorization`)과 JSON 페이로드를 전달하여 인공지능 응답 생성
2. **구조화된 출력(JSON)과 데이터 파이프라인 연동**:
   - 비구조적인 LLM 텍스트 응답을 JSON 형식으로 강제 및 파싱하여, 파이썬 코드에서 추천 도시(`recommended_city`)를 추출한 뒤 다음 단계인 지도 API 맛집 검색 키워드로 연결하는 체인 구성
3. **외부 API 오류 대처 원칙 (Fault Tolerance)**:
   - 인증 오류(401/403), 네트워크 장애, 파싱 실패, 0건 검색 상황에서도 전체 프로그램이 다운되지 않고 폴백(Fallback) 데이터와 `errors` 로그를 남기며 최종 리포트를 생성하는 복구력 확보
4. **환경 변수를 활용한 자격 증명 보안 관리**:
   - API 키를 코드나 Git 저장소에 하드코딩하지 않고 `.env` 파일과 `.gitignore`로 분리하여 유출 위험 및 기습 과금 차단
