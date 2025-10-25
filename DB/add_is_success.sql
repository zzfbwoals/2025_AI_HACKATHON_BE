-- routine 테이블에 is_success 컬럼 추가
ALTER TABLE routine ADD COLUMN is_success TINYINT DEFAULT 0 COMMENT '루틴 성공 여부 (0: 미완료, 1: 완료)';
