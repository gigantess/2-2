# [Walkthrough] 보너스 과제 (복수 지역 추천 & 결과 캐싱) 구현 및 검증 리포트

본 문서는 `mission_description.md`의 **"5. 보너스 과제 (선택)"** 2가지 선택 과제의 구현 내용 및 검증 결과를 정리한 전용 워크스루 문서입니다.

---

## 1. 보너스 과제 구현 내용

### 1.1. 보너스 과제 1: 복수 지역 추천 (Multi-city Recommendation)
- **1차 추천 스키마 확장 ([llm_client.py](file:///d:/cody/2-2/llm_client.py))**:
  - LLM 1차 추천에서 `recommended_cities: ["강릉", "속초"]`와 같이 2~3개 추천 도시를 수집하도록 프롬프트 및 `validate_schema()` 정밀 검증 확장.
  - 단일 도시(`recommended_city`) 응답이 반환되는 경우에도 `[recommended_city]` 형태로 자동 정규화하여 완벽한 하위 호환성 유지.
- **다중 지역 맛집 반복 검색 (루프) ([place_client.py](file:///d:/cody/2-2/place_client.py) & [travel_planner.py](file:///d:/cody/2-2/travel_planner.py))**:
  - `recommended_cities` 배열의 각 도시에 대해 지명 정규화(`normalize_city_name`)를 거친 후, 도시별로 맛집 N곳(3~5곳)을 순차적으로 검색하는 반복 루프 처리 구현.
  - 데이터 구조: `restaurants_by_city: {"강릉": [...], "속초": [...]}`
- **리포트 내 지역별 소제목 그룹화 ([llm_client.py](file:///d:/cody/2-2/llm_client.py))**:
  - 2차 마크다운 리포트 작성 시 맛집 섹션을 `### 📍 강릉 맛집 추천`, `### 📍 속초 맛집 추천` 등 지역별 소제목으로 정돈하여 작성.

### 1.2. 보너스 과제 2: 결과 캐싱 최적화 (Result Caching)
- **24시간 TTL 기반 캐싱 ([report_generator.py](file:///d:/cody/2-2/report_generator.py))**:
  - 동일한 `-date`로 재실행 시, 이미 저장된 `results/{date}_travel_data.json` 파일의 생성 시각(mtime)을 체크하여 24시간 이내인 경우 외부 API 호출을 생략하고 저장된 JSON 데이터를 즉시 재활용.
- **강제 캐시 갱신 옵션 ([travel_planner.py](file:///d:/cody/2-2/travel_planner.py))**:
  - CLI 명령에 `--refresh` 플래그를 추가하여 사용자가 필요 시 기존 캐시를 즉시 무효화하고 최신 정보로 갱신할 수 있도록 지원.

---

## 2. 검증 및 라이브 실행 테스트 결과

### 2.1. 단위 및 통합 테스트 (`test_planner.py`)
`test_multi_city_report_generation_and_caching` 테스트를 포함한 7개 핵심 검증 테스트 100% 통과:
```bash
python -m unittest test_planner.py
.......
----------------------------------------------------------------------
Ran 7 tests in 0.039s
OK
```

### 2.2. 복수 지역 실시간 연동 실행 결과 (`python travel_planner.py --date 2026-08-15 --refresh`)
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

#### 생성된 마크다운 리포트 예시 (`results/2026-08-15_travel_plan.md`)
```markdown
# 2026-08-15 국내 여행 추천 리포트

## 추천 지역
**강릉 & 속초**

## 맛집 추천

### 📍 강릉 맛집 추천
1. **9남매두부집** (두부전문점) - 주소: 강원특별자치도 강릉시 초당원길 63-2
2. **형제칼국수** (칼국수) - 주소: 강원특별자치도 강릉시 강릉대로204번길 2

### 📍 속초 맛집 추천
1. **사돈집** (해물/생선요리) - 주소: 강원특별자치도 속초시 영랑해안1길 8
2. **미가황태요리** (해물/생선요리) - 주소: 강원특별자치도 속초시 신흥2길 41

## 1일 일정 제안 (강릉 & 속초 연계 코스)
- **오전**: 강릉 도착 후 초당순두부 점심 식사
- **오후**: 속초로 이동 및 속초 썸머 페스티벌 참여
```

---

## 3. 관련 파일 및 경로

- **메인 실행 파일**: [travel_planner.py](file:///d:/cody/2-2/travel_planner.py)
- **전체 통합 워크스루**: [doc/walkthrough.md](file:///d:/cody/2-2/doc/walkthrough.md)
- **보완 구현 계획서**: [pre-review1/implementation_plan.md](file:///d:/cody/2-2/pre-review1/implementation_plan.md)
