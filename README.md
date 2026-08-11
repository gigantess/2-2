# 국내 여행지 추천 및 맛집 정보 연동 CLI 프로그램

이 프로그램은 **LLM API**(OpenAI / Google Gemini)와 **지도/장소 검색 API**(Kakao Local / Naver Local Search)를 연동하여 사용자가 입력한 날짜 기준의 맞춤형 국내 여행 리포트 및 원본 데이터를 자동으로 생성해주는 CLI 응용 프로그램입니다.

---

## 📌 주요 기능
1. **CLI 인터페이스**: `argparse` 기반의 날짜 입력 처리 (`--date YYYY-MM-DD`) 및 유효성 검증
2. **1차 추천 (LLM 연동)**: 여행 날짜에 알맞은 국내 추천 도시, 날씨 요약, 지역 축제/행사 정보 및 추천 이유를 구조화된 JSON 데이터로 수집
3. **맛집 검색 (지도 API 연동)**: 추천 도시 기준 맛집 N곳(기본 5곳)의 상호명, 주소, 카테고리, 좌표 및 상세 링크 검색
4. **결과 저장**: `results/` 폴더 내 원본 JSON (`{date}_travel_data.json`) 및 최종 Markdown 리포트 (`{date}_travel_plan.md`) 생성
5. **예외 처리 & 복구**:
   - API 키 미설정 시 안내 후 빠른 종료
   - LLM JSON 파싱 오류 발생 시 자동 1회 재시도 (Retry)
   - 지도 API 401/403 인증 오류 또는 검색 결과 0건 발생 시 프로그램 중단 없이 `데이터 없음`으로 리포트 완성
6. **결과 캐싱 (보너스)**: 동일 날짜 데이터 재실행 시 기존 수집된 JSON 캐시 데이터 재활용

---

## 🛠️ 개발 및 실행 환경
- **언어**: Python 3.10 이상
- **외부 라이브러리**: `requests`, `python-dotenv`, `openai`

---

## 🔑 API 키 설정 방법 (보안)

> [!CAUTION]
> **보안 주의 사항**: API 키를 절대로 소스코드나 README, Public Git 저장소에 올리지 마세요. 과금 방지 및 개인정보 보호를 위해 반드시 `.env` 파일로 관리해야 합니다.

1. 프로젝트 루트 디렉토리에 `.env` 파일을 생성합니다 (또는 `.env.example`을 복사하여 `.env`로 변경).
2. 발급받은 API 키를 작성합니다:

```env
# LLM API 키 (OpenAI 또는 Gemini 중 1개 이상 필수)
OPENAI_API_KEY=sk-proj-...
# GEMINI_API_KEY=AIzaSy...

# 지도/장소 검색 API 키 (Kakao 또는 Naver 중 1개 이상 필수)
KAKAO_REST_API_KEY=1234567890abcdef...
# NAVER_CLIENT_ID=your_naver_client_id
# NAVER_CLIENT_SECRET=your_naver_client_secret
```

---

## 🚀 설치 및 실행 방법

### 1. 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. 프로그램 실행 (CLI)
```bash
# 기본 실행 방식
python travel_planner.py --date "2026-03-15"

# -date 단축 옵션도 지원합니다
python travel_planner.py -date "2026-03-15"
```

### 3. 잘못된 입력 시 동작 예시
```bash
python travel_planner.py --date "2026-99-99"

# [오류] 존재하지 않는 유효하지 않은 날짜입니다: '2026-99-99'
# 사용법: python travel_planner.py --date YYYY-MM-DD (예: 2026-03-15)
```

---

## 📂 결과물 확인 방법

프로그램이 완료되면 `results/` 폴더가 자동 생성되고 2개의 파일이 저장됩니다:

1. **`results/YYYY-MM-DD_travel_data.json`**:
   - 1차 추천 정보 (`recommendation`)
   - 장소 검색 결과 리스트 (`restaurants`)
   - 오류 및 예외 로그 요약 (`errors`)
2. **`results/YYYY-MM-DD_travel_plan.md`**:
   - 최종 작성된 마크다운 여행 리포트 (추천 지역, 추천 이유, 날씨, 축제, 맛집 목록, 1일 일정 제안 포함)

---

## 🎓 학습 포인트 (과제 목표 달성)
- **REST API & HTTP 메서드**: Header 인증(Kakao AK / OpenAI Bearer / Naver Client)과 GET/POST 호출 구조 이해
- **구조화된 출력(JSON)**: LLM 텍스트 응답을 JSON으로 수집하여 지도 API 검색 키워드로 연결하는 파이프라인 구성
- **오류 대응 원칙**: API 키 미설정, 파싱 오류, 검색 결과 0건 등 실무 환경의 장애 대처 구현
- **환경 변수를 활용한 보안**: `.env` 및 `.gitignore`를 통한 보안 자격 증명 관리
