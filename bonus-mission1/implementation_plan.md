# [구현 계획서] 보너스 과제(복수 지역 추천 & 결과 캐싱) 검증 및 개선 계획

`mission_description.md`의 **"5. 보너스 과제 (선택)"** 요구사항을 검증한 결과, 현황과 개선 필요사항은 다음과 같습니다.

---

## 1. 보너스 과제 요구사항 검증 결과

| 보너스 과제 항목 | 현재 구현 현황 | 검증 결과 | 미흡 사항 및 개선 계획 |
| :--- | :--- | :---: | :--- |
| **1. 복수 지역 추천** | 단일 도시(`recommended_city`) 중심 추천 | **미흡** | 1차 추천을 2~3개 복수 지역(`recommended_cities: [...]`)으로 확장하고, 각 지역별 맛집 루프 검색 및 마크다운 리포트 내 지역별 그룹화 표기 구현 필요 |
| **2. 결과 캐싱** | `check_cache()` 24h TTL 및 `--refresh` 옵션 완료 | **완료** | 캐시 구조를 복수 지역 맛집 구조(`restaurants_by_city`)와 호환되도록 확장 |

---

## 2. 세부 개선 구현 계획

### Component 1: [llm_client.py](file:///d:/cody/2-2/llm_client.py) - 1차 추천 스키마 및 리포트 그룹화 확장
1. **1차 추천 프롬프트 및 스키마 확장**:
   - `recommended_cities`: 2~3개 추천 도시 배열 (예: `["강릉", "속초"]`)
   - `validate_schema` 정밀 검증 업데이트: `recommended_cities`가 2~3개의 비어있지 않은 문자열 항목을 가진 `list`인지 검증 (단일 `recommended_city`와의 하위 호환성 유지)
2. **2차 마크다운 리포트 생성 (`generate_markdown_report`)**:
   - 맛집 추천 섹션을 지역별로 그룹화하여 가독성 높게 작성하도록 프롬프트 및 템플릿 수정:
     ```markdown
     ## 맛집 추천

     ### 📍 강릉 맛집
     1. **9남매두부집** (한식 > 두부전문점) - 주소: ...

     ### 📍 속초 맛집
     1. **88생선구이** (한식 > 생선구이) - 주소: ...
     ```

---

### Component 2: [place_client.py](file:///d:/cody/2-2/place_client.py) & [travel_planner.py](file:///d:/cody/2-2/travel_planner.py) - 복수 지역 반복 처리 (루프)
1. **다중 지역 맛집 검색 루프 구현 (`search_restaurants_for_cities`)**:
   - `recommended_cities` 목록의 각 지역에 대해 정규화(`normalize_city_name`) 수행 후 맛집 N곳(지역당 3~5곳)을 검색하는 반복 루프 처리
   - 도시별 맛집 맵 구조 생성: `{"강릉": [...], "속초": [...]}`
2. **CLI 진행 로그 보강**:
   - `[2/3] 지역별 맛집 검색 중(지도/장소 API)...`
   - `  - [강릉] 맛집 3곳 검색 완료`
   - `  - [속초] 맛집 3곳 검색 완료`

---

### Component 3: [report_generator.py](file:///d:/cody/2-2/report_generator.py) - 원본 JSON 구조 저장
- 원본 데이터 JSON (`results/{date}_travel_data.json`) 스키마 확장:
  ```json
  {
    "date": "2026-08-11",
    "recommendation": {
      "recommended_cities": ["강릉", "속초"],
      "weather": "...",
      "events": [...],
      "reason": "..."
    },
    "restaurants_by_city": {
      "강릉": [ ... ],
      "속초": [ ... ]
    },
    "errors": [ ... ]
  }
  ```

---

### Component 4: 문서 및 단위 테스트 업데이트
1. **[test_planner.py](file:///d:/cody/2-2/test_planner.py)**: 복수 지역 스키마 검증, 루프 처리 및 지역별 JSON 저장 단위 테스트 케이스 추가
2. **[README.md](file:///d:/cody/2-2/README.md)** & **[walkthrough.md](file:///d:/cody/2-2/doc/walkthrough.md)**: 보너스 과제 복수 지역 추천 기능 추가 반영 및 실행 예시 스크린샷/JSON 구조 갱신

---

## 3. 검증 및 테스트 계획

1. `python -m unittest test_planner.py` 실행 (복수 지역 테스트 포함 8개 이상 통과 확인)
2. `python travel_planner.py --date "2026-08-15" --refresh` 실시간 호출로 복수 지역 추천(예: 강릉, 속초) 및 지역별 맛집 그룹화 리포트 생성 확인
