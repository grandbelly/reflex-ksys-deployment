# KPI 타일 시험 성적서 - 24시간 윈도우

## 테스트 케이스: KPI-24H-001

### 목적
KPI 타일의 계산 로직 (gauge_pct, delta_pct, status_level, range_label) 검증

### 전제 조건
- DB: TimescaleDB with `influx_agg_1m`, `influx_qc_rule`, `influx_latest` 
- 윈도우: 24시간 (1440분)
- 버킷: 1분 집계

### 테스트 데이터 (D100 태그)

#### QC 규칙
```sql
INSERT INTO influx_qc_rule (tag_name, min_val, max_val, warn_min, warn_max, crit_min, crit_max)
VALUES ('D100', 0.0, 200.0, 10.0, 190.0, 5.0, 195.0);
```

#### 최근 두 버킷 데이터 (delta_pct 계산용)
```sql
-- 현재 버킷 (최신)
INSERT INTO influx_agg_1m (bucket, tag_name, n, avg, min, max, last, first)
VALUES (now(), 'D100', 12, 190.0, 190.0, 190.0, 190.0, 190.0);

-- 이전 버킷 (-1분)
INSERT INTO influx_agg_1m (bucket, tag_name, n, avg, min, max, last, first)  
VALUES (now() - interval '1 minute', 'D100', 12, 180.0, 180.0, 180.0, 180.0, 180.0);
```

### 기대값 계산

#### 1. gauge_pct
```
QC 범위 기준: (last - min_val) / (max_val - min_val) * 100
= (190.0 - 0.0) / (200.0 - 0.0) * 100 = 95.0%
```

#### 2. delta_pct  
```
이전 대비 증감: (190.0 - 180.0) / 180.0 * 100 = 5.56%
```

#### 3. status_level
```
190.0 > warn_max(190.0) → status_level = 1 (경고)
```

#### 4. range_label
```
QC 규칙 존재 → "0.0 ~ 200.0"
```

### 수용 기준
- `|ui.gauge_pct - 95.0| ≤ 1.0`
- `|ui.delta_pct - 5.56| ≤ 0.1` 
- `ui.status_level == 1`
- `ui.range_label == "0.0 ~ 200.0"`
- `ui.delta_s == "+5.6%"` (소수점 1자리)
- `ui.value_s == "190.0"`

### 실행 절차
1. DB에 테스트 데이터 삽입
2. Dashboard 페이지 로드 (24시간 윈도우)
3. D100 KPI 타일 값 확인
4. 수용 기준과 비교

### 통과 조건
모든 수용 기준 만족 시 **PASS**

---

## 테스트 케이스: KPI-24H-002 (QC 없는 태그)

### 목적
QC 규칙이 없는 태그의 윈도우 범위 계산 검증

### 테스트 데이터 (D999 태그 - QC 규칙 없음)
```sql
-- 윈도우 내 최소/최대값이 있는 데이터
INSERT INTO influx_agg_1m (bucket, tag_name, n, avg, min, max, last, first)
VALUES 
  (now(), 'D999', 5, 150.0, 140.0, 160.0, 150.0, 145.0),
  (now() - interval '30 minutes', 'D999', 8, 100.0, 80.0, 120.0, 100.0, 90.0);
```

### 기대값
- `gauge_pct`: 윈도우 범위 (80.0~160.0) 기준으로 계산
- `range_label`: "80.0 ~ 160.0" 
- `status_level`: 0 (QC 규칙 없으면 정상)

### 수용 기준
- `ui.range_label == "80.0 ~ 160.0"`
- `ui.status_level == 0`