-- routine_options 테이블에 timing_type 컬럼 추가
-- '전' 또는 '후' 값을 저장 (기본값: '전')
ALTER TABLE routine_options
ADD COLUMN timing_type VARCHAR(10) DEFAULT '전' COMMENT '루틴 시간 기준: "전" 또는 "후"';
