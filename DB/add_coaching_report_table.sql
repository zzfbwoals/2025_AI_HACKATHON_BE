-- 코칭 리포트 테이블 생성
-- 이 파일은 코칭 리포트를 저장하기 위한 테이블을 생성합니다.

USE myapp;

-- coaching_report 테이블 생성
CREATE TABLE IF NOT EXISTS coaching_report (
    id INT AUTO_INCREMENT PRIMARY KEY,              -- 리포트 고유 ID
    user_id INT NOT NULL,                           -- 부모(사용자) ID (FK)
    report_date DATE NOT NULL,                      -- 리포트 생성 날짜
    summary_insight TEXT,                           -- 요약 인사이트
    custom_coaching_phrase TEXT,                    -- 맞춤 코칭 문구
    adaptation_rate VARCHAR(100),                   -- 루틴 적응도 (예: "75%")
    
    -- 코칭 인사이트 (JSON 형태로 저장)
    strengths JSON,                                  -- 잘하고 있는 점
    improvements JSON,                               -- 개선할 점
    suggestions JSON,                                -- 코칭 제안
    
    -- 주간 패턴 분석 (JSON 형태로 저장)
    weekly_patterns JSON,                           -- 주간 패턴 (routine, sleep, emotion)
    
    -- 주간 차트 데이터 (JSON 형태로 저장)
    weekly_chart JSON,                              -- 주간 차트 데이터
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 생성일자
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, -- 업데이트일자

    FOREIGN KEY (user_id) REFERENCES users(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    
    -- 인덱스 추가 (조회 성능 향상)
    INDEX idx_user_date (user_id, report_date),
    INDEX idx_report_date (report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 테이블 생성 확인
SELECT 'coaching_report 테이블이 성공적으로 생성되었습니다.' AS status;
