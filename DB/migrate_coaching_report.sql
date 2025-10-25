-- coaching_report 테이블 마이그레이션
-- 이 파일은 coaching_report 테이블을 생성하거나 업데이트합니다.

USE myapp;

-- coaching_report 테이블이 존재하는지 확인
SET @table_exists = (
    SELECT COUNT(*)
    FROM information_schema.TABLES
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'coaching_report'
);

-- 테이블이 없으면 생성
SET @sql = IF(@table_exists = 0,
    'CREATE TABLE coaching_report (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        report_date DATE NOT NULL,
        summary_insight TEXT,
        custom_coaching_phrase TEXT,
        adaptation_rate VARCHAR(100),
        strengths JSON,
        improvements JSON,
        suggestions JSON,
        weekly_patterns JSON,
        weekly_chart JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON UPDATE CASCADE ON DELETE CASCADE,
        INDEX idx_user_date (user_id, report_date),
        INDEX idx_report_date (report_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci',
    'SELECT "coaching_report 테이블이 이미 존재합니다." AS status'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- custom_coaching_phrase 필드가 없는 경우 추가
SET @column_exists = (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'coaching_report'
    AND COLUMN_NAME = 'custom_coaching_phrase'
);

SET @sql2 = IF(@column_exists = 0,
    'ALTER TABLE coaching_report ADD COLUMN custom_coaching_phrase TEXT AFTER summary_insight',
    'SELECT "custom_coaching_phrase 필드가 이미 존재합니다." AS status'
);

PREPARE stmt2 FROM @sql2;
EXECUTE stmt2;
DEALLOCATE PREPARE stmt2;

-- 완료 메시지
SELECT 'coaching_report 테이블 마이그레이션이 완료되었습니다.' AS status;
