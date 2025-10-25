import bcrypt
import mysql.connector
import re
from flask import Flask, render_template, request, jsonify, send_file, make_response, send_from_directory
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager
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

app.config["JWT_SECRET_KEY"] = "super-secret"
jwt = JWTManager(app)

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

@app.route('/api/auth/register', methods=['POST'])
def signup():
   conn = None
   cursor = None

   # 1. (수정됨) 주석을 풀어서 실제 플러터 요청을 받습니다.
   data = request.get_json()
   
   # (개선) 데이터가 아예 없는 경우 예외 처리
   if not data:
       return jsonify({'result': 'fail', 'msg': '요청 데이터가 없습니다.'}), 400

   # 2. (수정됨) data.get()을 사용하여 JSON에서 값을 추출합니다.
   name = data.get('name')
   email = data.get('email')
   password = data.get('password')
   child_name = data.get('child_name')
   child_age = data.get('child_age')

   # (개선) 필수 값들이 모두 들어왔는지 확인
   if not all([name, email, password, child_name, child_age is not None]):
        return jsonify({'result': 'fail', 'msg': '필수 항목이 누락되었습니다.'}), 400

   #이메일 확인 정규식 (이 함수는 이미 구현되어 있다고 가정)
   if not is_valid_email(email):
      return jsonify({'result': 'fail', 'msg': '잘못된 이메일 형식'}), 400
   
   # 4. (삭제됨) 비밀번호 확인 로직 삭제
   #    플러터 앱에서 'password' 하나만 보내므로 이 로직은 필요 없습니다.
   # if (password != password_confirm):
   #    return jsonify({'result': 'fail', 'msg': '비밀번호 불일치'})

   #데이터 베이스에 저장 로직
   try:
      # (이 함수는 이미 구현되어 있다고 가정)
      conn = get_db_connection() 
      cursor = conn.cursor(dictionary=True)

      check_sql = "SELECT id FROM users WHERE email = %s"
      cursor.execute(check_sql, (email,))
      if cursor.fetchone():
         # (개선) 이미 존재하는 리소스는 409 Conflict
         return jsonify({'result': 'fail', 'msg': '이미 존재하는 이메일입니다.'}), 409
      
      # (중요) bcrypt가 import 되어 있어야 함
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

      # (개선) 성공 시 201 Created
      return jsonify({'result': 'success', 'msg': '회원가입 성공'}), 201
   
   except mysql.connector.Error as err:
      print(f"DB Error: {err}") # (개선) 에러 로그
      if conn and conn.is_connected():
         conn.rollback()
      # (개선) 서버 내부는 500 Internal Server Error
      return jsonify({'result': 'fail', 'msg': '데이터베이스 처리 중 오류가 발생했습니다.'}), 500
   
   finally:
      if cursor:
          cursor.close()
      if conn and conn.is_connected():
          conn.close()

@app.route('/login', methods=['POST'])
def login():
   conn = None
   cursor = None

   # 1. (수정) 플러터에서 보낸 실제 JSON 데이터 받기
   data = request.get_json()
   
   if not data:
       app.logger.warning("로그인: 요청 데이터가 없습니다.")
       return jsonify({'result': 'fail', 'msg': '요청 데이터가 없습니다.'}), 400

   email = data.get('email')
   password = data.get('password')

   # 2. (삭제) 테스트용 하드코딩 데이터 삭제
   # email = 'tester_01@example.com'
   # password = 'StrongPassword123!'

   if not email or not password:
       app.logger.warning("로그인: 이메일 또는 비밀번호가 누락되었습니다.")
       return jsonify({'result': 'fail', 'msg': '이메일과 비밀번호를 모두 입력해주세요.'}), 400

   app.logger.info(f"로그인 시도: {email}")

   try:
      conn = get_db_connection()
      cursor = conn.cursor(dictionary=True)

      cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
      user = cursor.fetchone()

      # 3. 사용자 및 비밀번호 검증
      if not user:
         app.logger.warning(f"로그인 실패: 존재하지 않는 이메일 {email}")
         return jsonify({'result': 'fail', 'msg': '존재하지 않는 이메일입니다.'}), 404

      if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
         app.logger.warning(f"로그인 실패: 비밀번호 불일치 {email}")
         return jsonify({'result': 'fail', 'msg': '비밀번호가 일치하지 않습니다.'}), 401

      # 4. (중요) 로그인 성공 시 토큰 생성
      app.logger.info(f"로그인 성공: {email}")
      
      # 토큰에 사용자의 'id' (혹은 'email')를 담아서 생성합니다.
      access_token = create_access_token(identity=user['id'])
      
      # 5. 플러터에 토큰과 함께 성공 응답 전송
      return jsonify({
          'result': 'success', 
          'msg': '로그인 성공',
          'token': access_token,      # ⬅️ 플러터가 저장할 토큰
          'user_id': user['id']   # ⬅️ (선택사항) 사용자 ID
      })

   except Exception as e:
      app.logger.error(f"로그인 중 DB 오류: {e}")
      return jsonify({'result': 'fail', 'msg': '서버 오류가 발생했습니다.'}), 500
   
   finally:
      if cursor:
          cursor.close()
      if conn and conn.is_connected():
          conn.close()

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

if __name__ == '__main__':
    app.run(debug=True)


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

    # 2️⃣ AI 응답 생성
    response = client_child.responses.create(
        model=model_name,
        input=[
            {"role": "developer", "content": "시스템 프롬프트 (아이와 대화)"},
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
