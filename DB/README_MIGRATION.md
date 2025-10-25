# 데이터베이스 마이그레이션 가이드

## coaching_report 테이블 마이그레이션

### 마이그레이션 파일
- `migrate_coaching_report.sql` - coaching_report 테이블 생성 및 업데이트

### 실행 방법

#### 방법 1: MySQL Workbench 사용
1. MySQL Workbench 실행
2. 데이터베이스 연결 (`myapp` 데이터베이스)
3. `File > Open SQL Script` 선택
4. `DB/migrate_coaching_report.sql` 파일 선택
5. 실행 버튼 클릭 (⚡)

#### 방법 2: MySQL 명령어 사용
```bash
mysql -u [username] -p myapp < DB/migrate_coaching_report.sql
```

#### 방법 3: MySQL Workbench에서 SQL 직접 실행
```sql
USE myapp;
SOURCE DB/migrate_coaching_report.sql;
```

### 마이그레이션 내용

#### 테이블 생성
- `coaching_report` 테이블 생성 (이미 존재하는 경우 건너뜀)

#### 필드 추가
- `custom_coaching_phrase` 필드 추가 (이미 존재하는 경우 건너뜀)

### 테이블 구조

```sql
CREATE TABLE coaching_report (
    id INT AUTO_INCREMENT PRIMARY KEY,              -- 리포트 고유 ID
    user_id INT NOT NULL,                           -- 부모(사용자) ID (FK)
    report_date DATE NOT NULL,                      -- 리포트 생성 날짜
    summary_insight TEXT,                           -- 요약 인사이트
    custom_coaching_phrase TEXT,                    -- 맞춤 코칭 문구
    adaptation_rate VARCHAR(100),                   -- 루틴 적응도
    
    -- 코칭 인사이트 (JSON)
    strengths JSON,                                 -- 잘하고 있는 점
    improvements JSON,                              -- 개선할 점
    suggestions JSON,                               -- 코칭 제안
    
    -- 주간 패턴 분석 (JSON)
    weekly_patterns JSON,                           -- 주간 패턴
    weekly_chart JSON,                              -- 주간 차트 데이터
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON UPDATE CASCADE ON DELETE CASCADE,
    INDEX idx_user_date (user_id, report_date),
    INDEX idx_report_date (report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
```

### 확인
마이그레이션 실행 후 다음 쿼리로 확인:
```sql
DESCRIBE coaching_report;
```

### 주의사항
- 기존 데이터가 있는 경우 마이그레이션은 데이터를 보존합니다
- 마이그레이션은 멱등성(idempotent)을 보장합니다 (여러 번 실행해도 안전)
- 필드가 이미 존재하는 경우 추가하지 않습니다
