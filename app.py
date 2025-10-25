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
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files['audio']

    # 임시 wav 파일 저장
    temp_audio_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
    audio_file.save(temp_audio_path)

    # 1️⃣ STT 변환
    r = sr.Recognizer()
    with sr.AudioFile(temp_audio_path) as source:
        audio_data = r.record(source)
        try:
            user_text = r.recognize_google(audio_data, language='ko-KR')
            print("🎙️ 아이가 말한 내용:", user_text)
        except Exception as e:
            return jsonify({"error": f"음성 인식 실패: {str(e)}"}), 400


import json

def export_sql_to_json(user_id):
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
        SELECT r.id AS routine_id, ro.minut, ro.option_content
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

    # 7️⃣ Dialogue (최근 대화만)
    cur.execute("""
        SELECT * FROM Dialogue 
        WHERE character_id IN (
            SELECT character_id FROM users WHERE id = %s
        )
        ORDER BY created_at DESC LIMIT 10
    """, (user_id,))
    dialogue = cur.fetchall()

    cur.close()
    conn.close()

    # JSON 구조로 합치기
    data = {
        "users": user,
        "routine": routines,
        "routine_options": routine_opts,
        "ActivityLog": activities,
        "ToDoList": todos,
        "learning_contents": learning,
        "Dialogue": dialogue
    }

    # JSON 파일로 저장
    with open("user_report_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return data

    #JSON 파일 불러오기
    with open("user_report_data.json", "r", encoding="utf-8") as f:
        sql_json_data = json.load(f)

    #시스템 프롬프트
    SYSTEM_PROMPT = """
    당신은 "부모 코칭 리포트 생성 AI"입니다.

당신의 임무는 SQL 데이터베이스에 저장된 아동의 루틴 기록, 감정 상태, 수면 패턴 등 데이터를 분석하여

부모에게 제공할 맞춤형 코칭 리포트를 자동으로 생성하는 것입니다.

당신은 아래 단계를 반드시 따릅니다.

──────────────────────────────

# 1. 데이터 분석

당신은 SQL 쿼리 결과(스키마 기반 데이터)를 입력으로 받습니다.
데이터에는 다음 항목들이 포함되어 있습니다:

- sleep_quality
- routine (이름)
- routine_time
- routine_content(루틴 내용)
- created_at
- updated_at
- minute
- option_content
- title
- description
- category
- content_type
- difficulty
- recommended_time
- date
- mood
- focus_level
- activity_note
- ischecked

이 데이터를 기반으로,

주간/월간 루틴 수행률, 감정 상태의 변화, 수면 패턴 변화를 분석합니다.

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

SQL 데이터에서 주간/월간 변화 추이를 분석하여 그래프에 사용할 데이터 포인트를 구조적으로 출력하세요.

예시 출력 구조:
{
"week_progress": [
{"week": "2025-10-1", "routine_rate": 65},
{"week": "2025-10-2", "routine_rate": 77},
{"week": "2025-10-3", "routine_rate": 82}
],
"sleep_pattern": [
{"week": "2025-10-1", "avg_sleep": 7.5},
{"week": "2025-10-2", "avg_sleep": 8.0}
],
"emotion_trend": [
{"date": "2025-10-15", "positive": 70, "negative": 30}
]
}

──────────────────────────────

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

- SQL 데이터에 없는 정보는 추정하지 마세요.
- 모든 문장은 실제 데이터에 기반해야 합니다.
- 리포트 문체는 보고서 형식이 아니라 코칭 톤으로 유지하세요.
──────────────────────────────"""

    # 2️⃣ AI 응답 생성
    response = client_child.responses.create(
        model=model_name,
        input=[
            {"role": "developer", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ]
    )
    ai_text = response.output_text
    print("🤖 AI 응답:", ai_text)

    # 3️⃣ TTS 변환 (텍스트 → 음성)
    tts = gTTS(text=ai_text, lang='ko')
    output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    tts.save(output_path)

    # 4️⃣ mp3 음성 반환
    return send_file(output_path, mimetype="audio/mpeg")

@app.route('/generate-routine', methods=['POST'])
def chat_adult():
   data = request.get_json()
   response = client_child.responses.create(
      model=model_name,
      input=[
         {
            'role': 'developer',
            'content': '시스템 프롬프트 (루틴 제공, 부모에게 리포트 제공)'
         },
         {
            'role': 'user',
            'content': data.get('prompt')
         }
        ]
   )
   return response.output_text

@app.route('/adult', methods=['POST'])
def chat_adult():
   data = request.get_json()
   response = client_child.responses.create(
      model=model_name,
      input=[
         {
            'role': 'developer',
            'content': '시스템 프롬프트 (루틴 제공, 부모에게 리포트 제공)'
         },
         {
            'role': 'user',
            'content': data.get('prompt')
         }
        ]
   )
   return response.output_text

@app.route('/mypage', methods=['GET'])
def mypage():
   # 데이터 베이스에서 유저 정보 불러오기 (유저 이름, 유저 이메일, 총 루틴 수, 완료율)
   # 웹에 출력
   return jsonify({'result': 'success', })

if __name__ == '__main__':  
   app.run('0.0.0.0', port=5001, debug=True)
