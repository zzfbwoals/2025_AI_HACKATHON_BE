-- 데이터베이스 생성
CREATE DATABASE myapp CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE myapp;

-- 1️ character 테이블 (캐릭터 정보)
CREATE TABLE characters (
    id INT AUTO_INCREMENT PRIMARY KEY,   -- 캐릭터 고유 ID
    name VARCHAR(50) NOT NULL,           -- 캐릭터 이름
    description VARCHAR(255),            -- 캐릭터 설명
    personality VARCHAR(100)             -- 캐릭터 특징
);

-- 2️ User 테이블 (부모 + 자녀 + 구독 정보)
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,          -- 부모(사용자) 고유 ID
    character_id INT,                           -- 연결된 캐릭터 ID (FK)
    name VARCHAR(50) NOT NULL,                  -- 부모 이름
    email VARCHAR(100) NOT NULL UNIQUE,         -- 이메일 (중복 불가)
    password VARCHAR(255) NOT NULL,             -- 비밀번호
    child_name VARCHAR(50) NOT NULL,            -- 아이 이름
    child_age INT,                              -- 아이 나이
    subscribe VARCHAR(20) DEFAULT 'Free',       -- 구독 플랜 (기본 Free)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 생성 시각 자동 저장

    FOREIGN KEY (character_id) REFERENCES characters(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

-- 3️ Routine 테이블 (아이의 루틴 정보)
CREATE TABLE routine (
    id INT AUTO_INCREMENT PRIMARY KEY,          -- 루틴 고유 ID
    user_id INT NOT NULL,                       -- 부모(사용자) ID (FK)
    routin VARCHAR(100) NOT NULL,               -- 루틴 이름
    routine_time DATETIME NOT NULL,             -- 루틴 시간
    routine_content VARCHAR(255) NOT NULL,      -- 루틴 내용
    is_success TINYINT DEFAULT 0,               -- 루틴 성공 여부 (0: 미완료, 1: 완료)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 생성일자
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, -- 업데이트일자

    FOREIGN KEY (user_id) REFERENCES users(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

-- 4️ Routine Option 테이블 (루틴 세부 옵션)
CREATE TABLE routine_options (
    id INT AUTO_INCREMENT PRIMARY KEY,          -- 옵션 고유 ID
    routine_id INT NOT NULL,                    -- 루틴 ID (FK)
    minut INT,                                  -- 분
    option_content VARCHAR(255),                -- 옵션 내용

    FOREIGN KEY (routine_id) REFERENCES routine(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

-- 5️ Learning Contents 테이블 (학습 콘텐츠)
CREATE TABLE learning_contents (
    id INT AUTO_INCREMENT PRIMARY KEY,          -- 콘텐츠 고유 ID
    user_id INT NOT NULL,                       -- 사용자 ID (FK)
    title VARCHAR(100) NOT NULL,                -- 콘텐츠 제목
    description TEXT,                           -- 콘텐츠 설명
    category VARCHAR(50),                       -- 콘텐츠 종류
    content_type VARCHAR(50),                   -- 형식 (예: 동영상, 게임, 퀴즈 등)
    url VARCHAR(255),                           -- 링크
    difficulty VARCHAR(20),                     -- 난이도
    recommended_time INT,                       -- 권장 시청 시간 (분 단위)

    FOREIGN KEY (user_id) REFERENCES users(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

-- 'Dialogue' 테이블 생성
CREATE TABLE Dialogue (
    -- 기본 키 (Primary Key), INT 타입, 자동 증가 설정
    id INT NOT NULL AUTO_INCREMENT,
    
    -- Character 테이블을 참조하는 외래 키 (Foreign Key)
    character_id INT NOT NULL,
    
    -- 발화자 유형 (예: 'user', 'ai')
    sender_type VARCHAR(20) NOT NULL,
    
    -- 실제 대화 내용을 저장하는 필드 (긴 텍스트 저장을 위해 TEXT 타입 사용)
    message_text TEXT NOT NULL,
    
    -- 대화 생성 시간 (자동으로 현재 시간이 기록됨)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 감정 태그 저장
    emotion_tag VARCHAR(50),
    
    -- PK 설정
    PRIMARY KEY (id),
    
    -- FK 설정: character_id는 Character 테이블의 ID를 참조
    FOREIGN KEY (character_id) REFERENCES characters(id)
);

-- 참고:
-- 1. 이 코드를 실행하기 전에 Character 테이블(ID 필드가 포함된)이 데이터베이스에 먼저 생성되어 있어야 합니다.
-- 2. VARCHAR 길이 (20, 50)는 필요에 따라 조절할 수 있습니다.

-- 'ToDoList' 테이블 생성
CREATE TABLE ToDoList (
    -- 기본 키 (Primary Key) 설정 및 자동 증가 설정
    id INT NOT NULL AUTO_INCREMENT,
    
    -- User 테이블의 ID를 참조하는 외래 키 (Foreign Key). NULL 불가능
    user_id INT NOT NULL,
    
    -- 체크리스트/할 일 이름. NULL 불가능
    name VARCHAR(255) NOT NULL,
    
    -- 생성 일자. DATE 타입, NULL 불가능
    created_at DATE NOT NULL,
    
    -- 업데이트 일자. DATE 타입, NULL 불가능
    updated_at DATE NOT NULL,
    
    -- 완료 여부. BOOLEAN 타입 (MySQL에서는 TINYINT(1)로 처리됨), 기본 값은 FALSE(0)
    is_checked BOOLEAN DEFAULT FALSE,
    
    -- PK 설정
    PRIMARY KEY (id),
    
    -- user_id를 User 테이블의 ID에 연결하는 FK 설정
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 'ActivityLog' (행동 기록) 테이블 생성
CREATE TABLE ActivityLog (
    -- 기본 키 (Primary Key) 설정 및 자동 증가 설정
    id INT NOT NULL AUTO_INCREMENT,
    
    -- User 테이블의 ID를 참조하는 외래 키 (Foreign Key). user_id에도 AUTO_INCREMENT가 있지만, FK에서는 이 속성을 사용하지 않습니다.
    user_id INT NOT NULL,
    
    -- 날짜 기록
    date DATE NOT NULL,
    
    -- 기분 (예: VARCHAR 또는 ENUM으로 기분 상태를 정의할 수 있습니다)
    mood VARCHAR(50),
    
    -- 집중도 (예: INT, 1-5 범위의 척도 또는 VARCHAR)
    focus_level INT,
    
    -- 하루 행동 요약 (긴 텍스트 저장을 위해 TEXT 타입 사용)
    activity_note TEXT,
    
    -- 수면의 질 (예: INT, 1-5 범위의 척도 또는 VARCHAR)
    sleep_quality INT,
    
    -- 기록 작성 시간 (자동으로 현재 시간이 기록됨)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- PK 설정
    PRIMARY KEY (id),
    
    -- user_id를 User 테이블의 ID에 연결하는 FK 설정
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 캐릭터 데이터 삽입
INSERT INTO characters (id, name, description, personality) VALUES
(1, '루티', '활발하고 에너지가 넘치는 캐릭터', '활발함'),
(2, '미니', '조용하고 차분한 성격의 캐릭터', '차분함'),
(3, '스마트', '똑똑하고 호기심이 많은 캐릭터', '똑똑함'),
(4, '체리', '사랑스럽고 귀여운 캐릭터', '사랑스러움'),
(5, '스타', '밝고 긍정적인 에너지의 캐릭터', '긍정적');