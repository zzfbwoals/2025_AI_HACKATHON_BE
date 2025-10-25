import bcrypt
import mysql.connector
import re
from flask import Flask, render_template, request, jsonify, send_file, make_response, send_from_directory
from openai import OpenAI
import speech_recognition as sr
from gtts import gTTS
import tempfile
import os
from datetime import datetime, timedelta

DB_CONFIG ={
   'host': '127.0.01',
   'user': 'app_user',
   'password': 'flask_app_password',
   'database': 'myapp'
}

def get_db_connection():
   return mysql.connector.connect(**DB_CONFIG)

# 더미 데이터 설정
DUMMY_DATA = {
   'name': '테스트부모',
   'email': 'test@example.com',
   'password_plain': 'testpassword123!',
   'child_name': '테스트아이',
   'child_age': 5,
   # character_id는 NULL로 처리 (필수 FK가 아니라고 가정)
}

client_adult = OpenAI(api_key='')
client_child = OpenAI(api_key='')
model_name = "gpt-5-nano"

EMAIL_RE = re.compile(
   r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"
   r"@"
   r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
   r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*$"
)

def is_valid_email(addr: str) -> bool:
   return bool(EMAIL_RE.fullmatch(addr))

app = Flask(__name__, static_folder='static')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_flutter_app(path):
    """
    Flutter 웹 앱의 모든 경로 요청을 처리합니다.
    1. path가 실제 파일(JS, CSS, 에셋)이면 해당 파일을 반환합니다.
    2. path가 앱 내부 라우팅 경로(예: /home)이면 index.html을 반환합니다.
    """
    
    # 1. 요청된 경로가 'static' 폴더 내에 실제 파일로 존재하는지 확인 (예: main.dart.js)
    requested_path = os.path.join(app.static_folder, path)
    if path != "" and os.path.exists(requested_path):
        # 파일이 존재하면 해당 정적 파일을 반환합니다.
        return send_from_directory(app.static_folder, path)
    
    # 2. 파일이 없거나 루트 경로(/)인 경우, Flutter의 메인 진입점인 index.html을 반환합니다.
    #    이렇게 해야 Flutter의 JavaScript 코드가 페이지를 로드하고 내부 라우팅을 처리할 수 있습니다.
    try:
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        # 파일이 복사되지 않았을 때 오류 메시지
        return f"Error: Flutter index.html not found in static folder. Check that build/web content is copied to static/. Details: {e}", 500

@app.route('/signup', methods=['POST'])
def signup():
   conn = None
   cursor = None

   # data = request.get_json()
   # name = data.get('name')
   # email = data.get('email')
   # password = data.get('password')
   # password_confirm = data.get('password_confirm')
   # child_name = data.get('child_name')
   # child_age = data.get('child_age')

   name = '테스터'
   email = 'tester_01@example.com'
   password = 'StrongPassword123!'
   password_confirm ='StrongPassword123!'
   child_name = '테스트자녀'
   child_age = 7

   #이메일 확인 정규식
   if not is_valid_email(email):
      return jsonify({'result': 'fail', 'msg': '잘못된 이메일 형식'})
   
   #비밀번호 확인 로직
   if (password != password_confirm):
      return jsonify({'result': 'fail', 'msg': '비밀번호 불일치'})

   #데이터 베이스에 저장 로직
   try:
      conn = get_db_connection()
      cursor = conn.cursor(dictionary=True)

      check_sql = "SELECT id FROM users WHERE email = %s"
      cursor.execute(check_sql, (email,))
      if cursor.fetchone():
         return jsonify({'result': 'fail', 'msg': '이미 존재하는 이메일입니다.'})
      hashed_password = bcrypt.hashpw(
            password.encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')
      insert_sql = """
            INSERT INTO users (name, email, password, child_name, child_age, character_id) 
            VALUES (%s, %s, %s, %s, %s, NULL)
        """
      cursor.execute(insert_sql, (name, email, hashed_password, child_name, child_age))
      conn.commit()

      return jsonify({'result': 'success', 'msg': '회원가입 성공'})
   except mysql.connector.Error as err:
      if conn and conn.is_connected():
         conn.rollback()
      return jsonify({'result': 'fail', 'msg': '데이터베이스 처리 중 오류가 발생했습니다.'})
   
   finally:
      if cursor:
          cursor.close()
      if conn and conn.is_connected():
          conn.close()

@app.route('/login', methods=['POST'])
def login():
   conn = None
   cursor = None

   # data = request.get_json()
   # email = data.get('email')
   # password = data.get('password')

   email = 'tester_01@example.com'
   password = 'StrongPassword123!'

   conn = conn = get_db_connection()
   cursor = conn.cursor(dictionary=True)

   cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
   user = cursor.fetchone()

   if not user:
      return jsonify({'result': 'fail', 'msg': '존재하지 않는 이메일입니다.'})

   if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
      return jsonify({'result': 'fail', 'msg': '비밀번호가 일치하지 않습니다.'})
   return jsonify({'result': 'success'})

@app.route('/home', methods=['GET'])
def get_routine_stats(user_id):
   conn = get_db_connection()
   cur = conn.cursor()

   # 📌 1️⃣ 총 루틴 수
   cur.execute("SELECT COUNT(*) AS total_routines FROM routine WHERE user_id = %s;", (user_id,))
   total_routines = cur.fetchone()['total_routines']

   # 📌 2️⃣ 이번 주 성공 루틴 수
   cur.execute("""
               SELECT COUNT(*) AS success_routines
               FROM ActivityLog
               WHERE user_id = %s
               AND YEARWEEK(date, 1) = YEARWEEK(CURDATE(), 1)
               """, (user_id,))
   success_routines = cur.fetchone()['success_routines']

   # 📌 3️⃣ 이번 주 통계 (완료 루틴 수, 연속 일수, 총 루틴 수)
   # 완료 루틴 수 (이번 주의 ActivityLog 개수 기준)
   cur.execute("""
        SELECT COUNT(*) AS completed_count
        FROM ActivityLog
        WHERE user_id = %s
          AND YEARWEEK(date, 1) = YEARWEEK(CURDATE(), 1)
    """, (user_id,))
   completed_count = cur.fetchone()['completed_count']

   # 연속 일수 계산 (오늘 포함 최근 날짜 기준)
   cur.execute("""
        SELECT DISTINCT date FROM ActivityLog
        WHERE user_id = %s
        ORDER BY date DESC
    """, (user_id,))
   dates = [row['date'] for row in cur.fetchall()]

   streak = 0
   today = datetime.now().date()
   for i, d in enumerate(dates):
      if (today - timedelta(days=i)) == d:
         streak += 1
      else:
         break

   # 📌 4️⃣ 오늘의 루틴 목록
   cur.execute("""
               SELECT routin AS routine_name, routine_content, TIME(routine_time) AS time
               FROM routine
               WHERE user_id = %s AND DATE(routine_time) = CURDATE()
               ORDER BY routine_time
               """, (user_id,))
   today_routines = cur.fetchall()

   # 연결 종료
   cur.close()
   conn.close()

   # 📦 결과 JSON으로 반환
   return jsonify({
      "result": "success",
      "data": {
         "총 루틴 수": total_routines,
         "이번 주 성공 루틴 수": success_routines,
         "이번 주 통계": {
               "완료 루틴 수": completed_count,
               "연속 일수": streak,
               "총 루틴 수": total_routines
               },
               "오늘의 루틴": today_routines
         }
      })

@app.route('/routines', methods=['POST'])
def add_routine():
   data = request.get_json()
   routine_name = data.get('routine_name')
   routine_content = data.get('routine_content')
   start_date = data.get('start_date')

   #데이터 베이스에 루틴 추가 로직
   return jsonify({'result': 'success', 'msg': '루틴 저장 성공'})

@app.route('/character', methods=['POST'])
def gen_character():
   data = request.get_json()
   char_name = data.get('char_name')
   char_description = data.get('char_description')
   char_personality = data.get('char_personality')

   #데이터 베이스에 캐릭터 정보 추가 로직
   return jsonify({'result': 'success'})

@app.route('/child', methods=['POST'])
def chat_child():
    import json

    # 1️⃣ 텍스트 입력 받기
    data = request.get_json()
    user_text = data.get('prompt', '').strip() if data else ''

    # 2️⃣ 입력이 비어 있으면 실패 처리
    if not user_text:
        return jsonify({"error": "음성 인식 실패"}), 400

    print(user_text)

    # 3️⃣ 아이 전용 시스템 프롬프트
    SYSTEM_PROMPT = """
SYSTEM INSTRUCTION: 역할 및 목표

당신은 소아 청소년 ADHD 아동의 행동 치료 및 일상/수면 루틴 관리를 전문으로 하는 숙련된 아동 심리 전문가이자 루틴 설계 AI입니다.

주어진 아동의 데이터를 면밀히 분석하여, 아동의 **주의력 향상** 및 **수면 질 개선**에 가장 효과적일 것으로 기대되는 **새로운 루틴** 또는 **기존 루틴의 개선 방안**을 구상하십시오.

**목표:** 부모가 앱에 즉시 등록할 수 있도록, **아동 친화적인 언어**로 루틴의 구조(이름, 내용, 단계별 알림 문구)를 정의하는 JSON 객체를 생성해야 합니다.

**[INPUT DATA: 아동 프로필 및 누적 데이터 (DB 기반 분석 요청)]**

다음은 분석 대상 아동에 대해 데이터베이스에서 추출된 최근 일주일 간의 루틴 이행 및 행동 데이터입니다.

### 1. 아동 프로필 및 루틴 달성 현황 (Users, Routine, ToDoList 테이블 기반)

| 필드 | 값 | 설명 |
| --- | --- | --- |
| **아동 ID** | {users.id} | 현재 분석 대상 아동의 고유 ID (부모 계정과 연결) |
| **아동 이름/나이** | {users.child_name} / {users.child_age}세 | 아동의 기본 정보 |
| **선택된 챗봇** | {characters.name} | 아동이 현재 선택한 챗봇 캐릭터 |
| **기간 내 전체 루틴 달성률** | {XX}% | `ToDoList` 또는 `Routine` 완료 기록 기반의 평균 달성률 |
| **특정 시간대 루틴 달성률** | {YY}% (오전), {ZZ}% (저녁) | `routine.routine_time` 기준 시간대별 달성률 |

### 2. 구체적인 루틴 및 행동 분석 (Routine, Routine_Options, ToDoList 테이블 기반)

**[데이터]** {루틴 항목, 시도 횟수, 성공 횟수, 평균 소요 시간, 가장 자주 실패한 루틴 스텝(routine_options.option_content) 요약}
*예시:*

- **'양치하기 (저녁)'**: 7회 시도, 4회 성공. 평균 6분 소요 (목표 3분). 화/목요일에 잦은 실패.
- **'숙제 시작하기'**: 5회 시도, 2회 성공. 실패 시 `ActivityLog.activity_note`에 '회피 행동' 기록 많음.
- **가장 취약한 단계**: '루틴 시작(routine_options.minut=0)' 알림 후 5분 이내 실행률이 현저히 낮음.

### 3. 부모 기록 및 행동 패턴 요약 (ActivityLog 테이블 기반)

**[데이터]** {부모가 `ActivityLog`에 기록한 내용 요약}

- **관찰 기록**: `ActivityLog.activity_note` 필드에서 추출된 주간 주요 행동 패턴 요약.
*예시:* "수요일 저녁 8시, TV 시청 후 루틴 시작 알림에 지속적으로 회피함."
- **기분/집중도 패턴**: `ActivityLog.mood`, `ActivityLog.focus_level` 변화 패턴 분석.
*예시:* "오후 4시 이후 집중도(focus_level)가 2점 이하로 급격히 떨어짐."
- **수면의 질**: `ActivityLog.sleep_quality`의 주간 평균 및 최저/최고 기록.

### 4. 챗봇 대화 내용 및 감정 요약 (Dialogue 테이블 기반)

**[데이터]** {`Dialogue` 테이블의 `message_text`, `emotion_tag` 기반 요약}

- **주요 관심사**: 대화 내용에서 가장 많이 언급된 키워드/주제 (예: '축구', '마인크래프트').
- **감정 패턴**: `emotion_tag` 분석을 통한 루틴 시작 전/후 감정 변화 요약 (예: 루틴 시작 전 '짜증' 증가, 루틴 성공 후 '자신감' 언급 증가).
- **특이사항**: 밤 늦은 시간의 대화 톤이나 메시지 길이 변화 등.

**[OUTPUT INSTRUCTION: 결과 출력 형식]**

위 데이터를 분석하여, 아동에게 가장 효과적일 것으로 예상되는 신규 또는 수정 루틴을 **단 하나** 정의하고, 다음 JSON 형식에 맞춰 그 구조를 출력하십시오.

- `routineName`: 루틴의 이름을 긍정적이고 아이의 관심사와 연관된 명칭으로 설정합니다. (예: '마인크래프트 정리 시간', '슈퍼히어로 잠옷 입기 미션')
- `routineTimeframe`: 루틴이 실행되기에 가장 적합한 시간대를 간결하게 제시합니다. (예: '오후 8시 30분', '기상 직후')
- `routineDescription`: 부모에게 보여줄 루틴의 목적 및 내용을 긍정적인 코칭 톤으로 1~2문장으로 설명합니다. (아동이 아닌 부모 대상 메시지)
- `options`: 루틴 실행 단계별로 챗봇이 아동에게 제공할 **음성 알림** 및 **시간**을 정의합니다.
    - `minutes`: 루틴 시작까지 몇 분이 남았는지
    - `text`: 해당 단계에서 아동에게 전달될 **구체적이고 긍정적인** 알림/코칭 메시지입니다.

```
      {
        'name': '오후 집중 독서 시간',
        'content': '아이의 독서 습관이 좋아지고 있어요! 오후 2시부터 30분 동안 책을 읽으며 집중력을 길러봐요. 독서 후에는 작은 보상을 받을 수 있어요!',
        'options': [
          {'minutes': '5', 'text': '책 읽기 준비하세요! 편안한 장소를 찾아보아요.'},
          {'minutes': '30', 'text': '책 읽기 시간이 끝났어요! 잘했어요!'},
        ],
      }
```

**[CONSTRAINTS]**

1. **AI는 데이터를 기반으로만 루틴을 정의해야 합니다.**
2. options 에 정의된 전체 루틴 소요 시간은 30**분을 넘지 않도록** 설계해야 합니다. (ADHD 아동의 실행 가능성을 극대화하기 위함)
3. 출력은 오직 JSON 형식으로만 제공되어야 합니다.
    """

    # 4️⃣ AI 응답 생성
    try:
        response = client_child.responses.create(
            model="gpt-5-nano",
            input=[
                {"role": "developer", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ]
        )
        ai_text = response.output_text
        print(ai_text)
    except Exception as e:
        return jsonify({"error": f"AI 응답 생성 실패: {str(e)}"}), 500

    # 5️⃣ TTS 변환 (AI 응답 → 음성)
    try:
        tts = gTTS(text=ai_text, lang='ko')
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
        tts.save(output_path)
    except Exception as e:
        return jsonify({"error": f"TTS 변환 실패: {str(e)}"}), 500

    # 6️⃣ mp3 파일 반환
    return send_file(output_path, mimetype="audio/mpeg")

def analyze_user_data(user_id):
    """DB 데이터를 JSON으로 변환하고, AI로 분석"""
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor(dictionary=True)

    # 1️⃣ users
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()

    # 2️⃣ routine
    cur.execute("SELECT * FROM routine WHERE user_id = %s", (user_id,))
    routines = cur.fetchall()

    # 3️⃣ routine_options
    cur.execute("""
        SELECT r.id AS routine_id, ro.minute, ro.option_content
        FROM routine r
        LEFT JOIN routine_options ro ON r.id = ro.routine_id
        WHERE r.user_id = %s
    """, (user_id,))
    routine_opts = cur.fetchall()

    # 4️⃣ ActivityLog
    cur.execute("SELECT * FROM ActivityLog WHERE user_id = %s", (user_id,))
    activities = cur.fetchall()

    # 5️⃣ ToDoList
    cur.execute("SELECT * FROM ToDoList WHERE user_id = %s", (user_id,))
    todos = cur.fetchall()

    # 6️⃣ learning_contents
    cur.execute("SELECT * FROM learning_contents WHERE user_id = %s", (user_id,))
    learning = cur.fetchall()

    # 7️⃣ Dialogue
    cur.execute("""
        SELECT * FROM Dialogue 
        WHERE character_id IN (SELECT character_id FROM users WHERE id = %s)
        ORDER BY created_at DESC LIMIT 10
    """, (user_id,))
    dialogue = cur.fetchall()

    cur.close()
    conn.close()

    # 🧩 JSON 구조로 합치기
    data = {
        "users": user,
        "routine": routines,
        "routine_options": routine_opts,
        "ActivityLog": activities,
        "ToDoList": todos,
        "learning_contents": learning,
        "Dialogue": dialogue
    }

    json_str = json.dumps(data, ensure_ascii=False, indent=2)

    # 🧠 시스템 프롬프트
    SYSTEM_PROMPT = """
당신은 "부모 코칭 리포트 생성 AI"입니다.

당신의 임무는 json파일에 에 저장된 아동의 루틴 기록, 감정 상태, 수면 패턴 등 데이터를 분석하여

부모에게 제공할 맞춤형 코칭 리포트를 자동으로 생성하는 것입니다.

당신은 아래 단계를 반드시 따릅니다.

──────────────────────────────

# 1. 데이터 분석

당신은 json 파일을기반으로 주간/월간 루틴 수행률, 감정 상태의 변화, 수면 패턴 변화를 분석합니다.

──────────────────────────────

# 2. 요약 인사이트 작성 (Summary Insight)

다음 내용을 포함한 간결한 요약 문단을 생성하세요:

- 루틴 적응도, 시간대별 집중도, 감정 패턴, 수면 변화 등 핵심 요약
- 주간 및 월간 추세(그래프 형태의 설명 포함)
- 데이터에 기반한 성장 지표 (예: "루틴 수행률이 12% 향상되었습니다.")

예시:

> 민진이는 아침 루틴에는 잘 적응했지만, 저녁 루틴 지속률이 낮아요.
> 
> 
> 최근 2주간 수면 시간이 일정해지면서 감정 안정성이 향상되었습니다.
> 

──────────────────────────────

# 3. 맞춤 코칭 문구 생성 (Personalized Coaching Line)

AI 분석 결과를 바탕으로,
아이의 루틴 지속 향상에 직접적으로 도움이 되는 짧은 문장을 한 줄로 생성하세요.

→ 행동지침, 칭찬 또는 실천 팁 형태로 제시하세요.

예시:

> "자기 전 10분간 스트레칭을 하면 숙면에 도움이 될 거예요."
> 

──────────────────────────────

# 4. 코칭 인사이트 작성 (Coaching Insights)

3가지 영역으로 구분하여 작성하세요:

1. **잘하고 있는 점** — 루틴 수행률, 감정 안정 등 긍정적 측면
2. **개선할 점** — 꾸준함, 특정 시간대 집중력, 피로도 등 개선 포인트
3. **코칭 제안** — 부모가 실천할 수 있는 행동 가이드 (예: "저녁 루틴 전 30분은 조용한 환경을 유지하세요.")

예시:

- 잘하고 있는 점: 아침 8시 기상 루틴을 5일 연속 유지함
- 개선할 점: 금요일 저녁 루틴 수행률 저조
- 코칭 제안: 취침 전 독서 시간을 추가해보세요

──────────────────────────────

# 5. 시각화 데이터 생성 (Graph Generation Guide)

SQL 데이터에서 주간/월간 변화 추이를 분석하여 그래프를 만드세요

───────────────────────────

# 6. 출력 형식

최종 출력은 다음 JSON 구조를 따릅니다:

{
"요약_인사이트": "...",
"맞춤_코칭_문구": "...",
"코칭_인사이트": {
"잘하고_있는_점": "...",
"개선할_점": "...",
"코칭_제안": "..."
},
"그래프_데이터": {...}
}

──────────────────────────────

# 7. 스타일 가이드

- 따뜻하고 부모에게 친근한 말투 사용
- 데이터 기반의 객관적 표현을 유지
- 문장은 짧고 명확하게
- ‘칭찬 → 개선 → 제안’의 흐름을 유지

──────────────────────────────

# 8. 주의 사항

- json파일에 정보는 추정하지 마세요.
- 모든 문장은 실제 데이터에 기반해야 합니다.
- 리포트 문체는 보고서 형식이 아니라 코칭 톤으로 유지하세요.
──────────────────────────────
    """

    # 🧩 AI에게 JSON 데이터 직접 전달
    response = client.responses.create(
        model=model_name,
        input=[
            {"role": "developer", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"다음은 SQL 데이터를 JSON으로 변환한 결과입니다:\n\n{json_str}"}
        ]
    )

    ai_output = response.output_text
    return ai_output   # ✅ 결과를 반환하도록 변경


# 🔹 Flask 라우트 (DB 재조회하지 않고 analyze_user_data만 호출)
@app.route('/adult', methods=['POST'])
def chat_adult():
    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({"result": "fail", "msg": "user_id가 필요합니다."}), 400

    try:
        # analyze_user_data 호출 → AI 리포트 결과 반환
        ai_report = analyze_user_data(user_id)
        return jsonify({
            "result": "success",
            "report": ai_report
        })

    except Exception as e:
        return jsonify({
            "result": "fail",
            "msg": f"처리 중 오류 발생: {str(e)}"
        }), 500


@app.route('/mypage', methods=['GET'])
def mypage():
   # 데이터 베이스에서 유저 정보 불러오기 (유저 이름, 유저 이메일, 총 루틴 수, 완료율)
   # 웹에 출력
   return jsonify({'result': 'success', })

if __name__ == '__main__':  
   app.run('0.0.0.0', port=5001, debug=True)
