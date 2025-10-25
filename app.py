import bcrypt
import mysql.connector
import re
from flask import Flask, render_template, request, jsonify, send_file, make_response
from openai import OpenAI
import speech_recognition as sr
from gtts import gTTS
import tempfile
import os

DB_CONFIG ={
   'host': '127.0.01',
   'user': 'app_user',
   'password': 'flask_app_password',
   'database': 'myapp'
}

def get_db_connenction():
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

app = Flask(__name__)

@app.route('/')
def process_data_and_display():
    conn = None
    cursor = None
    user_id_to_delete = None
    users_after_insert = []
    
    # 출력 결과를 저장할 문자열
    output_message = "<h1>MySQL CRUD 테스트 결과</h1>"

    try:
        conn = get_db_connenction()
        cursor = conn.cursor(dictionary=True)

        # 1. 데이터 삽입 (CREATE)
        # ----------------------------------------------------
        hashed_password = bcrypt.hashpw(
            DUMMY_DATA['password_plain'].encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')
        
        insert_sql = """
            INSERT INTO users (name, email, password, child_name, child_age, character_id) 
            VALUES (%s, %s, %s, %s, %s, NULL)
        """
        cursor.execute(insert_sql, (
            DUMMY_DATA['name'], 
            DUMMY_DATA['email'], 
            hashed_password, 
            DUMMY_DATA['child_name'], 
            DUMMY_DATA['child_age']
        ))
        conn.commit()
        user_id_to_delete = cursor.lastrowid
        
        output_message += f"<p style='color: green;'>✅ **삽입 성공:** ID {user_id_to_delete} (이후 즉시 삭제 예정)</p>"
        
        
        # 2. 데이터 조회 (READ)
        # ----------------------------------------------------
        read_sql = "SELECT id, name, child_name, email FROM users ORDER BY id DESC LIMIT 5"
        cursor.execute(read_sql)
        users_after_insert = cursor.fetchall()
        
        output_message += "<h2>현재 users 테이블 데이터 (삽입 직후)</h2><ul>"
        
        for user in users_after_insert:
            is_dummy = "★더미 데이터★" if user['id'] == user_id_to_delete else ""
            output_message += f"<li>ID: {user['id']}, 부모: {user['name']}, 아이: {user['child_name']} ({is_dummy})</li>"
        output_message += "</ul>"


        # 3. 데이터 삭제 (DELETE)
        # ----------------------------------------------------
        delete_sql = "DELETE FROM users WHERE id = %s"
        cursor.execute(delete_sql, (user_id_to_delete,))
        conn.commit()
        
        output_message += f"<p style='color: blue;'>🗑️ **삭제 성공:** ID {user_id_to_delete} 삭제 완료.</p>"


        # 4. 결과 출력
        # HTML 템플릿 없이 문자열을 바로 반환합니다.
        response = make_response(output_message)
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        return response

    except mysql.connector.Error as err:
        # 데이터베이스 오류 처리
        if conn:
            conn.rollback()
        error_msg = f"<h2 style='color: red;'>❌ 데이터베이스 오류 발생</h2><p>오류 내용: {err}</p>"
        response = make_response(error_msg)
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        return response, 500

    finally:
        # 연결 자원 해제
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/signup', methods=['POST'])
def signup():
   data = request.get_json()
   name = data.get('name')
   email = data.get('email')
   password = data.get('password')
   password_confirm = data.get('password_confirm')
   child_name = data.get('child_name')
   child_age = data.get('child_age')

   #이메일 확인 정규식
   if not is_valid_email(email):
      return jsonify({'result': 'fail', 'msg': '잘못된 이메일 형식'})
   
   #비밀번호 확인 로직
   if (password != password_confirm):
      return jsonify({'result': 'fail', 'msg': '비밀번호 불일치'})

   #데이터 베이스에 저장 로직
   return jsonify({'result': 'success', 'msg': '회원가입 성공'})

@app.route('/login', methods=['POST'])
def login():
   data = request.get_json()
   email = data.get('email')
   password = data.get('password')

   #데이터 베이스와 비교 로직
   return jsonify({'result': 'success'})

@app.route('/home', methods=['GET'])
def home():
   # 데이터 베이스에서 유저 정보 불러오기 (총 루틴, 이번 주 성공 루틴, 이번 주 통계(완료 루틴, 연속 일수, 총 루틴), 오늘 루틴)
   # 웹에 출력
   return jsonify({'result': 'success', })

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