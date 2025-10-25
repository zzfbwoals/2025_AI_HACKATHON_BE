import bcrypt
import mysql.connector
import re
import json
from flask import Flask, render_template, request, jsonify, send_file, make_response
from flask_cors import CORS
from openai import OpenAI
import speech_recognition as sr
from gtts import gTTS
import tempfile
import os
import pymysql
from datetime import datetime, timedelta
import jwt
from functools import wraps

DB_CONFIG ={
   'host': '127.0.0.1',
   'user': 'root',  # 기본 root 계정 사용
   'password': '6610',  # 본인의 MySQL root 비밀번호를 입력하세요
   'database': 'myapp',
   'charset': 'utf8mb4',  # UTF-8 인코딩 설정
   'use_unicode': True
}

def get_db_connection():
   conn = mysql.connector.connect(**DB_CONFIG)
   # 연결 후 UTF-8 설정
   conn.set_charset_collation('utf8mb4')
   return conn

# 더미 데이터 설정
DUMMY_DATA = {
    'name': '테스트부모',
    'email': 'test@example.com',
    'password_plain': 'testpassword123!',
    'child_name': '테스트아이',
    'child_age': 5,
    # character_id는 NULL로 처리 (필수 FK가 아니라고 가정)
}

# OpenAI API 키 (환경변수에서 가져오거나 직접 입력)
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
client_adult = OpenAI(api_key=OPENAI_API_KEY)
client_child = OpenAI(api_key=OPENAI_API_KEY)
model_name = "gpt-4o-mini"  # 수정: gpt-5-nano -> gpt-4o-mini

EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"
    r"@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*$"
)

def is_valid_email(addr: str) -> bool:
    return bool(EMAIL_RE.fullmatch(addr))

app = Flask(__name__)
CORS(app)  # CORS 설정 추가

# JSON 한글 깨짐 방지를 위한 설정
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# JWT 설정
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_DELTA = timedelta(days=7)  # 토큰 만료 기간: 7일

# JWT 토큰 생성 함수
def generate_token(user_id: int):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + JWT_EXPIRATION_DELTA,
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)

# JWT 토큰 검증 데코레이터
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # 헤더에서 토큰 가져오기
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # 'Bearer <token>' 형식
            except IndexError:
                return jsonify({'result': 'fail', 'msg': '토큰 형식이 올바르지 않습니다.'}), 401
        
        if not token:
            return jsonify({'result': 'fail', 'msg': '토큰이 없습니다.'}), 401
        
        try:
            # 토큰 검증
            data = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
            current_user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'result': 'fail', 'msg': '토큰이 만료되었습니다.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'result': 'fail', 'msg': '유효하지 않은 토큰입니다.'}), 401
        
        # 함수에 user_id 전달
        return f(current_user_id, *args, **kwargs)
    
    return decorated

@app.route('/')
def process_data_and_display():
   conn = None
   cursor = None
   user_id_to_delete = None
   users_after_insert = []
    
    # 출력 결과를 저장할 문자열
   output_message = "<h1>MySQL CRUD 테스트 결과</h1>"

   try:
      conn = get_db_connection()
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
   conn = None
   cursor = None

   data = request.get_json()  # 활성화
   name = data.get('name')
   email = data.get('email')
   password = data.get('password')
   password_confirm = data.get('password_confirm')
   child_name = data.get('child_name')
   child_age = data.get('child_age')

   #테스트용 더미 데이터 (주석 처리)
   # name = '테스터'
   # email = 'tester_01@example.com'
   # password = 'StrongPassword123!'
   # password_confirm ='StrongPassword123!'
   # child_name = '테스트자녀'
   # child_age = 7

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

   data = request.get_json()  # 활성화
   email = data.get('email')
   password = data.get('password')

   #테스트용 더미 데이터 (주석 처리)
   # email = 'tester_01@example.com'
   # password = 'StrongPassword123!'

   conn = conn = get_db_connection()
   cursor = conn.cursor(dictionary=True)

   cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
   user = cursor.fetchone()

   if not user:
      return jsonify({'result': 'fail', 'msg': '존재하지 않는 이메일입니다.'})

   if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
      return jsonify({'result': 'fail', 'msg': '비밀번호가 일치하지 않습니다.'})
   
   # JWT 토큰 생성
   token = generate_token(user['id'])
   
   # 성공 시 유저 정보와 토큰 반환
   return jsonify({
      'result': 'success',
      'token': token,
      'user': {
         'id': user['id'],
         'name': user['name'],
         'email': user['email'],
         'child_name': user['child_name'],
         'child_age': user['child_age'],
         'character_id': user['character_id']
      }
   })

@app.route('/verify-token', methods=['POST'])
def verify_token():
    """토큰 검증 및 유저 정보 반환"""
    token = None
    
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization']
        try:
            token = auth_header.split(' ')[1]  # 'Bearer <token>' 형식
        except IndexError:
            return jsonify({'result': 'fail', 'msg': '토큰 형식이 올바르지 않습니다.'}), 401
    
    if not token:
        return jsonify({'result': 'fail', 'msg': '토큰이 없습니다.'}), 401
    
    try:
        # 토큰 검증
        data = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = data['user_id']
        
        # DB에서 유저 정보 가져오기
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, email, child_name, child_age, character_id FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user:
            return jsonify({'result': 'fail', 'msg': '사용자를 찾을 수 없습니다.'}), 404
        
        return jsonify({
            'result': 'success',
            'user': user
        })
    except jwt.ExpiredSignatureError:
        return jsonify({'result': 'fail', 'msg': '토큰이 만료되었습니다.'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'result': 'fail', 'msg': '유효하지 않은 토큰입니다.'}), 401

@app.route('/home/<int:user_id>', methods=['GET'])  # 수정: user_id를 URL 파라미터로 받음
def get_routine_stats(user_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)  # 수정: dictionary=True 추가

    try:
        # 📌 0️⃣ 사용자 정보 (character_id, name 포함)
        try:
            cur.execute("SELECT character_id, name FROM users WHERE id = %s", (user_id,))
            user_info = cur.fetchone()
            character_id = user_info['character_id'] if user_info else None
            username = user_info.get('name', '사용자') if user_info else '사용자'
        except Exception as e:
            print(f"⚠️ 사용자 정보 조회 오류: {e}")
            character_id = None
            username = '사용자'
        
        # 📌 1️⃣ 총 루틴 수
        cur.execute("SELECT COUNT(*) AS total_routines FROM routine WHERE user_id = %s;", (user_id,))
        total_routines = cur.fetchone()['total_routines']

        # 📌 2️⃣ 이번 주 성공 루틴 수 (is_success=1인 루틴 중 이번 주에 생성된 것만)
        cur.execute("""
            SELECT COUNT(*) AS success_routines
            FROM routine
            WHERE user_id = %s
              AND is_success = 1
              AND YEARWEEK(routine_time, 1) = YEARWEEK(CURDATE(), 1)
        """, (user_id,))
        success_routines = cur.fetchone()['success_routines']

        # 📌 3️⃣ 이번 주 통계 (완료 루틴 수, 연속 일수, 총 루틴 수)
        # 완료 루틴 수 (이번 주의 routine.is_success=1인 루틴 개수)
        cur.execute("""
            SELECT COUNT(*) AS completed_count
            FROM routine
            WHERE user_id = %s
              AND is_success = 1
              AND YEARWEEK(routine_time, 1) = YEARWEEK(CURDATE(), 1)
        """, (user_id,))
        completed_count = cur.fetchone()['completed_count']

        # 연속 일수 계산 (routine.is_success=1인 루틴이 있는 날짜 기준)
        cur.execute("""
            SELECT DISTINCT DATE(routine_time) AS date
            FROM routine
            WHERE user_id = %s AND is_success = 1
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

        # 📌 4️⃣ 오늘의 루틴 목록 (옵션 개수 포함)
        cur.execute("""
            SELECT r.id, r.routin AS routine_name, r.routine_content, r.is_success, 
                   TIME(r.routine_time) AS time, DATE(r.routine_time) AS routine_time,
                   (SELECT COUNT(*) FROM routine_options WHERE routine_id = r.id) AS option_count
            FROM routine r
            WHERE r.user_id = %s AND DATE(r.routine_time) = CURDATE()
            ORDER BY r.routine_time
        """, (user_id,))
        today_routines_raw = cur.fetchall()
        
        # timedelta를 문자열로 변환하고 딕셔너리로 변환
        today_routines = []
        for routine in today_routines_raw:
            routine_dict = dict(routine)
            if routine_dict.get('time') and hasattr(routine_dict['time'], 'total_seconds'):
                # timedelta를 문자열로 변환 (HH:MM:SS)
                td = routine_dict['time']
                total_seconds = int(td.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                routine_dict['time'] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            # 날짜를 문자열로 변환 (YYYY-MM-DD)
            if routine_dict.get('routine_time'):
                if hasattr(routine_dict['routine_time'], 'strftime'):
                    routine_dict['routine_time'] = routine_dict['routine_time'].strftime('%Y-%m-%d')
                elif isinstance(routine_dict['routine_time'], str):
                    # 이미 문자열인 경우 그대로 사용
                    pass
            
            today_routines.append(routine_dict)

        # 📦 결과 JSON으로 반환
        return jsonify({
            "result": "success",
            "data": {
                "character_id": character_id,
                "name": username,
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
    except mysql.connector.Error as err:
        return jsonify({"result": "fail", "msg": str(err)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/routines/user/<int:user_id>', methods=['GET'])
def get_all_routines(user_id):
    """사용자의 전체 루틴 목록 조회"""
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 사용자의 전체 루틴 조회
        cursor.execute("""
            SELECT r.id, r.routin AS routine_name, r.routine_content, 
                   r.routine_time, r.is_success, r.created_at, r.updated_at,
                   (SELECT COUNT(*) FROM routine_options WHERE routine_id = r.id) AS option_count
            FROM routine r
            WHERE r.user_id = %s
            ORDER BY r.routine_time DESC
        """, (user_id,))
        routines = cursor.fetchall()
        
        return jsonify({
            'result': 'success',
            'data': routines
        })
        
    except mysql.connector.Error as err:
        return jsonify({'result': 'fail', 'msg': str(err)}), 500
    
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/routines', methods=['POST'])
def add_routine():
   data = request.get_json()
   user_id = data.get('user_id')
   routine_name = data.get('routine_name')
   routine_content = data.get('routine_content')
   routine_time = data.get('routine_time')  # 'YYYY-MM-DD HH:MM:SS' 형식
   options = data.get('options', [])  # [{'minutes': 10, 'text': '알림 메시지'}, ...]
   
   if not all([user_id, routine_name, routine_content, routine_time]):
      return jsonify({'result': 'fail', 'msg': '필수 필드가 누락되었습니다.'}), 400
   
   conn = None
   cursor = None
   
   try:
      conn = get_db_connection()
      cursor = conn.cursor(dictionary=True)
      
      # 1. routine 테이블에 루틴 추가
      insert_routine_sql = """
         INSERT INTO routine (user_id, routin, routine_time, routine_content)
         VALUES (%s, %s, %s, %s)
      """
      cursor.execute(insert_routine_sql, (user_id, routine_name, routine_time, routine_content))
      routine_id = cursor.lastrowid
      
      # 2. routine_options 테이블에 옵션 추가 (있는 경우에만)
      if options and len(options) > 0:
         for option in options:
            insert_option_sql = """
               INSERT INTO routine_options (routine_id, minut, option_content, timing_type)
               VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_option_sql, (
               routine_id,
               option.get('minutes'),
               option.get('text', ''),
               option.get('timing', '전')  # 기본값: '전'
            ))
      
      conn.commit()
      
      return jsonify({
         'result': 'success', 
         'msg': '루틴이 저장되었습니다.',
         'routine_id': routine_id
      })
      
   except mysql.connector.Error as err:
      if conn and conn.is_connected():
         conn.rollback()
      return jsonify({'result': 'fail', 'msg': str(err)}), 500
   
   finally:
      if cursor:
         cursor.close()
      if conn and conn.is_connected():
         conn.close()

@app.route('/routines/<int:routine_id>', methods=['GET'])
def get_routine_detail(routine_id):
    """특정 루틴의 상세 정보와 옵션을 가져옴"""
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 1. 루틴 기본 정보 가져오기
        cursor.execute("""
            SELECT id, user_id, routin AS routine_name, routine_time, 
                   routine_content, created_at, updated_at
            FROM routine
            WHERE id = %s
        """, (routine_id,))
        routine = cursor.fetchone()
        
        if not routine:
            return jsonify({'result': 'fail', 'msg': '루틴을 찾을 수 없습니다.'}), 404
        
        # 2. 루틴 옵션 가져오기
        cursor.execute("""
            SELECT id, minut AS minutes, option_content AS text, timing_type AS timing
            FROM routine_options
            WHERE routine_id = %s
            ORDER BY minut ASC
        """, (routine_id,))
        options = cursor.fetchall()
        
        # 3. 결과 반환
        return jsonify({
            'result': 'success',
            'data': {
                'routine': routine,
                'options': options
            }
        })
        
    except mysql.connector.Error as err:
        if conn and conn.is_connected():
            conn.rollback()
        return jsonify({'result': 'fail', 'msg': str(err)}), 500
    
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/routines/<int:routine_id>/success', methods=['PUT'])
def update_routine_success(routine_id):
    """루틴 성공 여부 업데이트"""
    data = request.get_json()
    is_success = data.get('is_success', 0)
    
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 루틴 성공 여부 업데이트
        cursor.execute("""
            UPDATE routine 
            SET is_success = %s 
            WHERE id = %s
        """, (is_success, routine_id))
        
        conn.commit()
        
        return jsonify({
            'result': 'success',
            'msg': '루틴 성공 상태가 업데이트되었습니다.'
        })
        
    except mysql.connector.Error as err:
        if conn and conn.is_connected():
            conn.rollback()
        return jsonify({'result': 'fail', 'msg': str(err)}), 500
    
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/routines/<int:routine_id>/delete', methods=['DELETE'])
def delete_routine(routine_id):
    """루틴 삭제 (관련 옵션도 CASCADE로 자동 삭제됨)"""
    conn = None
    cursor = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 루틴 존재 여부 확인
        cursor.execute("SELECT id FROM routine WHERE id = %s", (routine_id,))
        routine = cursor.fetchone()
        
        if not routine:
            return jsonify({'result': 'fail', 'msg': '루틴을 찾을 수 없습니다.'}), 404
        
        # 삭제 전 옵션 개수 확인 (로깅용)
        cursor.execute("SELECT COUNT(*) as count FROM routine_options WHERE routine_id = %s", (routine_id,))
        option_count = cursor.fetchone()['count']
        print(f'🗑️ 루틴 {routine_id} 삭제 - 관련 옵션 {option_count}개도 함께 삭제됩니다.')
        
        # CASCADE로 인해 routine_options도 자동 삭제됨
        cursor.execute("DELETE FROM routine WHERE id = %s", (routine_id,))
        conn.commit()
        
        print(f'✅ 루틴 {routine_id} 및 관련 옵션 {option_count}개가 성공적으로 삭제되었습니다.')
        
        return jsonify({
            'result': 'success',
            'msg': '루틴 및 관련 옵션이 삭제되었습니다.',
            'deleted_options': option_count
        })
        
    except mysql.connector.Error as err:
        if conn and conn.is_connected():
            conn.rollback()
        return jsonify({'result': 'fail', 'msg': str(err)}), 500
    
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/character/select', methods=['POST'])
def select_character():
   """사용자가 선택한 캐릭터를 DB에 저장"""
   data = request.get_json()
   user_id = data.get('user_id')
   character_id = data.get('character_id')
   
   conn = None
   cursor = None
   
   try:
      conn = get_db_connection()
      cursor = conn.cursor(dictionary=True)
      
      # 사용자의 character_id 업데이트
      update_sql = "UPDATE users SET character_id = %s WHERE id = %s"
      cursor.execute(update_sql, (character_id, user_id))
      conn.commit()
      
      return jsonify({'result': 'success', 'msg': '캐릭터가 선택되었습니다.'})
      
   except mysql.connector.Error as err:
      if conn and conn.is_connected():
         conn.rollback()
      return jsonify({'result': 'fail', 'msg': str(err)}), 500
   
   finally:
      if cursor:
         cursor.close()
      if conn and conn.is_connected():
         conn.close()

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

@app.route('/coaching/insights/<int:user_id>', methods=['GET'])
def get_coaching_insights(user_id):
   """AI 기반 코칭 인사이트 생성"""
   conn = None
   cursor = None
   
   # OpenAI API 키 확인
   if not OPENAI_API_KEY:
      return jsonify({
         'result': 'fail',
         'msg': 'OpenAI API 키가 설정되지 않았습니다. 환경변수 OPENAI_API_KEY를 설정해주세요.'
      }), 500
   
   try:
      conn = get_db_connection()
      cursor = conn.cursor(dictionary=True)
      
      # 아이 정보 조회
      cursor.execute("SELECT child_name, child_age FROM users WHERE id = %s", (user_id,))
      user_info = cursor.fetchone()
      
      if not user_info:
         return jsonify({'result': 'fail', 'msg': '사용자를 찾을 수 없습니다.'}), 404
      
      child_name = user_info['child_name']
      child_age = user_info['child_age']
      
      # 최근 7일간 루틴 데이터 조회
      cursor.execute("""
         SELECT 
            DATE(routine_time) as date,
            COUNT(*) as total,
            SUM(CASE WHEN is_success = 1 THEN 1 ELSE 0 END) as completed
         FROM routine
         WHERE user_id = %s
            AND routine_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
         GROUP BY DATE(routine_time)
         ORDER BY date ASC
      """, (user_id,))
      
      daily_stats = cursor.fetchall()
      
      # 디버깅: 쿼리 결과 출력
      print(f"DEBUG: User ID {user_id} - Daily Stats:")
      for row in daily_stats:
         print(f"  {row['date']}: {row['completed']}/{row['total']} = {row['completed']/row['total']*100:.1f}%")
      
      # 전체 통계 계산
      total_routines = sum(row['total'] for row in daily_stats)
      completed_routines = sum(row['completed'] for row in daily_stats)
      completion_rate = (completed_routines / total_routines * 100) if total_routines > 0 else 0
      
      print(f"DEBUG: Total: {total_routines}, Completed: {completed_routines}, Rate: {completion_rate:.1f}%")
      
      # 루틴 상세 데이터 구성 (요일별)
      weekday_map = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금', 5: '토', 6: '일'}
      weekday_stats = {day: {'total': 0, 'completed': 0} for day in weekday_map.values()}
      
      for row in daily_stats:
         date_obj = row['date']
         weekday_idx = date_obj.weekday()
         weekday_name = weekday_map[weekday_idx]
         weekday_stats[weekday_name]['total'] += row['total']
         weekday_stats[weekday_name]['completed'] += row['completed']
      
      routine_details = []
      for weekday in weekday_map.values():
         stats = weekday_stats[weekday]
         rate = (stats['completed'] / stats['total'] * 100) if stats['total'] > 0 else 0
         routine_details.append({
            'weekday': weekday,
            'total': stats['total'],
            'completed': stats['completed'],
            'rate': rate
         })
      
      # AI 프롬프트 생성
      system_prompt = f"""당신은 ADHD 아동을 위한 전문 루틴 관리 앱 'ROUTY'의 AI 코치입니다.
아이의 이름: {child_name}
아이의 나이: {child_age}세

**주요 역할:**
1. 루틴 이행 데이터를 분석하여 맞춤형 인사이트 제공
2. 긍정적 강화와 부드러운 개선 제안 제공
3. ADHD 아동의 특성을 고려한 실용적인 코칭 제안
4. 최근 1주일간 **루틴·수면·감정 변화 패턴**을 간결하게 요약
5. 주간(월–일) 루틴 이행률 **꺾은선 그래프** 생성을 위한 구조적 데이터와 차트 프롬프트 제공
6. **맞춤 코칭 문구** 생성: 아이의 실제 루틴 이행 패턴을 분석하여, 구체적이고 실행 가능한 다음 주 코칭 제안을 제공. 부모와 교사가 바로 실행할 수 있는 구체적인 루틴 조정 방안 제시

**입력 데이터 가정(예시 키):**
- WEEK_DATA.routines: 각 루틴 항목의 수행 여부/시간/지연(분)
- WEEK_DATA.sleep: 취침/기상 시각, 총 수면시간, 야간 각성
- WEEK_DATA.emotions: 일별 주요 정서 라벨, 강도(0–5), 트리거/완충 요인

**작성 규칙:**
- 퍼센트는 0–100% 정수, 시간은 HH:MM 24시간 형식.
- 비교는 "지난주 대비" 대신 **해당 주 내 상대 비교** 위주.
- 비난 금지, 구체적 행동 문장 사용(환경·신호·보상 중심).
- 꺾은선 그래프용 일자 순서는 고정: ["월","화","수","목","금","토","일"].
- 결측치는 null로 표기. 내부적으로는 선을 끊거나 점선 처리 가능하나 값 보간 금지.

**응답 형식:**
다음 구조로 JSON 형식으로 응답해주세요:
{{
  "summary_insight": "1주일 데이터 요약 (2-3문장)",
  "custom_coaching_phrase": "{child_name}의 특정 루틴 이행 패턴을 분석하여 부모와 교사에게 구체적이고 실행 가능한 다음 주 코칭 제안을 제공하는 1-2문장 문구. 예: '{child_name}이는 아침 루틴에는 잘 적응했지만, 저녁 루틴 지속력이 낮아요. 다음 주는 자기 전 이야기 루틴을 10분으로 늘려보는 게 좋아요.'",
  "adaptation_rate": "{child_name}의 1주일간 루틴 적응도 (0-100%)",
  "weekly_patterns": {{
    "routine_overview": {{
      "consistency_rate": "루틴 지속률(%)",
      "most_skipped_tasks": ["가장 자주 건너뛴 루틴 1", "루틴 2"],
      "best_time_block": "이행이 가장 안정적이었던 시간대(HH:MM–HH:MM)",
      "delay_avg_min": "평균 지연 시간(분)"
    }},
    "sleep_overview": {{
      "avg_bedtime": "평균 취침시각(HH:MM)",
      "avg_sleep_duration": "평균 수면시간(HH:MM)",
      "sleep_variability": "취침시각 변동폭(분)",
      "night_awakenings_avg": "야간 각성 평균(회)"
    }},
    "emotion_trends": {{
      "dominant_moods": ["주요 정서 1", "주요 정서 2"],
      "common_triggers": ["자주 관찰된 트리거 1", "트리거 2"],
      "effective_regulation_strategies": ["효과 있었던 조절 전략 1", "전략 2"]
    }}
  }},
  "coaching_insights": {{
    "strengths": ["잘하고 있는 점 1", "잘하고 있는 점 2"],
    "improvements": ["개선할 점 1", "개선할 점 2"],
    "suggestions": [
      "코칭 제안 1(예: 시작 신호 '타이머+픽토그램'으로 전환, 5분 예열 단계 추가)",
      "코칭 제안 2(예: 취침 루틴에 '불빛 줄이기 30분' 고정, 보상 토큰 연결)"
    ]
  }},
  "weekly_chart": {{
    "labels": ["월","화","수","목","금","토","일"],
    "series_name": "루틴 이행률",
    "values_percent": [월값, 화값, 수값, 목값, 금값, 토값, 일값],
    "y_unit": "%",
    "y_min": 0,
    "y_max": 100,
    "draw_markers": true,
    "draw_area": false,
    "line_smoothing": "none",
    "notes": "결측치는 선 단절 처리, 보간 금지"
  }},
  "chart_generation_prompt": "다음 데이터를 사용해 단일 꺾은선 그래프를 생성하세요. X축: 요일 ['월','화','수','목','금','토','일'], Y축: 이행률(0–100%). 제목: '주간 루틴 이행률'. y축 범위 0–100, 눈금 간격 10. 데이터 포인트에 마커 표시. 결측치(null)는 선을 끊어서 표시. 범례는 '루틴 이행률' 1개만 표시. 보간·평활화 사용 금지.",
  "chart_data": {{
    "labels": ["월","화","수","목","금","토","일"],
    "values_percent": [월값, 화값, 수값, 목값, 금값, 토값, 일값]
  }}
}}"""
      
      user_prompt = f"""다음은 {child_name}({child_age}세)의 최근 7일간 루틴 이행 데이터입니다:

**전체 통계:**
- 총 루틴 수: {total_routines}개
- 완료된 루틴: {completed_routines}개
- 완료율: {completion_rate:.1f}%

**요일별 완료 상황:**
"""
      
      for detail in routine_details:
         weekday = detail['weekday']
         completed = detail['completed']
         total = detail['total']
         rate = detail['rate']
         user_prompt += f"- {weekday}요일: {completed}/{total} 완료 (이행률 {rate:.0f}%)\n"
      
      # 꺾은선 그래프를 위한 값 생성
      chart_values = [detail['rate'] for detail in routine_details]
      user_prompt += f"\n**꺾은선 그래프용 데이터:**\n"
      user_prompt += f"요일: {[detail['weekday'] for detail in routine_details]}\n"
      user_prompt += f"이행률: {chart_values}\n"
      
      user_prompt += "\n위 데이터를 바탕으로 JSON 형식으로 코칭 인사이트를 제공해주세요. weekly_chart.values_percent는 위의 이행률 배열을 그대로 사용하세요."
      user_prompt += f"\n\n**맞춤 코칭 문구 생성 가이드:**"
      user_prompt += f"\n- custom_coaching_phrase 필드는 {child_name}의 실제 루틴 이행 패턴을 분석하여 부모와 교사가 바로 실행할 수 있는 구체적인 다음 주 코칭 제안을 1-2문장으로 작성해주세요."
      user_prompt += f"\n- 예시: '{child_name}이는 아침 루틴에는 잘 적응했지만, 저녁 루틴 지속력이 낮아요. 다음 주는 자기 전 이야기 루틴을 10분으로 늘려보는 게 좋아요.'"
      user_prompt += f"\n- 데이터 기반으로 구체적인 루틴 조정 방안을 제시하세요."
      
      # OpenAI API 호출
      response = client_adult.chat.completions.create(
         model=model_name,
         messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
         ],
         temperature=0.7,
         max_tokens=1000
      )
      
      ai_response = response.choices[0].message.content
      
      # JSON 부분 추출 (마크다운 코드 블록 제거)
      json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
      if json_match:
         insights_json = json.loads(json_match.group())
      else:
         # JSON이 없으면 텍스트 그대로 반환
         insights_json = {
            "summary_insight": ai_response,
            "custom_coaching_phrase": "",
            "adaptation_rate": f"{completion_rate:.0f}%",
            "coaching_insights": {
               "strengths": [],
               "improvements": [],
               "suggestions": []
            }
         }
      
      return jsonify({
         'result': 'success',
         'insights': insights_json,
         'stats': {
            'total_routines': total_routines,
            'completed_routines': completed_routines,
            'completion_rate': completion_rate
         }
      })
      
   except Exception as e:
      import traceback
      error_msg = str(e)
      traceback.print_exc()  # 디버깅을 위한 스택 트레이스 출력
      return jsonify({'result': 'fail', 'msg': f'Error code: {type(e).__name__} - {error_msg}'}), 500
   
   finally:
      if cursor:
         cursor.close()
      if conn and conn.is_connected():
         conn.close()

# 코칭 리포트 저장 엔드포인트
@app.route('/coaching/report', methods=['POST'])
@token_required
def save_coaching_report(user_id):
   """코칭 리포트를 데이터베이스에 저장합니다."""
   conn = None
   cursor = None
   
   try:
      data = request.get_json()
      
      # 필수 필드 확인
      required_fields = ['summary_insight', 'custom_coaching_phrase', 'adaptation_rate']
      for field in required_fields:
         if field not in data:
            return jsonify({'result': 'fail', 'msg': f'필수 필드가 누락되었습니다: {field}'}), 400
      
      conn = get_db_connection()
      cursor = conn.cursor()
      
      # 오늘 날짜로 리포트 저장
      today = datetime.now().date()
      
      # 기존 리포트 확인 (같은 날짜의 리포트가 있는지)
      cursor.execute("""
         SELECT id FROM coaching_report 
         WHERE user_id = %s AND report_date = %s
      """, (user_id, today))
      
      existing_report = cursor.fetchone()
      
      # JSON 필드들을 문자열로 변환
      strengths_json = json.dumps(data.get('strengths', []), ensure_ascii=False)
      improvements_json = json.dumps(data.get('improvements', []), ensure_ascii=False)
      suggestions_json = json.dumps(data.get('suggestions', []), ensure_ascii=False)
      weekly_patterns_json = json.dumps(data.get('weekly_patterns', {}), ensure_ascii=False)
      weekly_chart_json = json.dumps(data.get('weekly_chart', {}), ensure_ascii=False)
      
      if existing_report:
         # 기존 리포트 업데이트
         cursor.execute("""
            UPDATE coaching_report 
            SET summary_insight = %s,
                custom_coaching_phrase = %s,
                adaptation_rate = %s,
                strengths = %s,
                improvements = %s,
                suggestions = %s,
                weekly_patterns = %s,
                weekly_chart = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
         """, (
            data['summary_insight'],
            data['custom_coaching_phrase'],
            data['adaptation_rate'],
            strengths_json,
            improvements_json,
            suggestions_json,
            weekly_patterns_json,
            weekly_chart_json,
            existing_report[0]
         ))
         
         conn.commit()
         return jsonify({
            'result': 'success',
            'msg': '리포트가 성공적으로 업데이트되었습니다.',
            'report_id': existing_report[0]
         })
      else:
         # 새 리포트 생성
         cursor.execute("""
            INSERT INTO coaching_report (
               user_id, report_date, summary_insight, custom_coaching_phrase,
               adaptation_rate, strengths, improvements, suggestions,
               weekly_patterns, weekly_chart
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
         """, (
            user_id, today, data['summary_insight'], data['custom_coaching_phrase'],
            data['adaptation_rate'], strengths_json, improvements_json, suggestions_json,
            weekly_patterns_json, weekly_chart_json
         ))
         
         conn.commit()
         report_id = cursor.lastrowid
         
         return jsonify({
            'result': 'success',
            'msg': '리포트가 성공적으로 저장되었습니다.',
            'report_id': report_id
         })
      
   except Exception as e:
      import traceback
      error_msg = str(e)
      traceback.print_exc()
      return jsonify({'result': 'fail', 'msg': f'리포트 저장 실패: {error_msg}'}), 500
   
   finally:
      if cursor:
         cursor.close()
      if conn and conn.is_connected():
         conn.close()

# 저장된 코칭 리포트 조회 엔드포인트
@app.route('/coaching/report/<int:user_id>', methods=['GET'])
@token_required
def get_saved_coaching_report(user_id_param, user_id):
   """저장된 코칭 리포트를 조회합니다."""
   conn = None
   cursor = None
   
   try:
      # URL의 user_id와 토큰의 user_id가 일치하는지 확인
      if user_id_param != user_id:
         return jsonify({'result': 'fail', 'msg': '권한이 없습니다.'}), 403
      
      conn = get_db_connection()
      cursor = conn.cursor()
      
      # 최근 리포트 조회 (최신순)
      cursor.execute("""
         SELECT id, report_date, summary_insight, custom_coaching_phrase,
                adaptation_rate, strengths, improvements, suggestions,
                weekly_patterns, weekly_chart, created_at, updated_at
         FROM coaching_report
         WHERE user_id = %s
         ORDER BY report_date DESC
         LIMIT 1
      """, (user_id,))
      
      report = cursor.fetchone()
      
      if not report:
         return jsonify({
            'result': 'success',
            'report': None,
            'msg': '저장된 리포트가 없습니다.'
         })
      
      # 리포트 데이터 파싱
      report_data = {
         'id': report[0],
         'report_date': str(report[1]),
         'summary_insight': report[2],
         'custom_coaching_phrase': report[3],
         'adaptation_rate': report[4],
         'strengths': json.loads(report[5]) if report[5] else [],
         'improvements': json.loads(report[6]) if report[6] else [],
         'suggestions': json.loads(report[7]) if report[7] else [],
         'weekly_patterns': json.loads(report[8]) if report[8] else {},
         'weekly_chart': json.loads(report[9]) if report[9] else {},
         'created_at': str(report[10]),
         'updated_at': str(report[11])
      }
      
      return jsonify({
         'result': 'success',
         'report': report_data
      })
      
   except Exception as e:
      import traceback
      error_msg = str(e)
      traceback.print_exc()
      return jsonify({'result': 'fail', 'msg': f'리포트 조회 실패: {error_msg}'}), 500
   
   finally:
      if cursor:
         cursor.close()
      if conn and conn.is_connected():
         conn.close()

# 음성 대화 저장 엔드포인트
@app.route('/voice/dialogue', methods=['POST'])
@token_required
def save_dialogue(user_id):
   """음성 대화 내용을 데이터베이스에 저장합니다."""
   conn = None
   cursor = None
   
   try:
      data = request.get_json()
      
      # 필수 필드 확인
      required_fields = ['character_id', 'sender_type', 'message_text']
      for field in required_fields:
         if field not in data:
            return jsonify({'result': 'fail', 'msg': f'필수 필드가 누락되었습니다: {field}'}), 400
      
      conn = get_db_connection()
      cursor = conn.cursor()
      
      # 대화 저장
      cursor.execute("""
         INSERT INTO Dialogue (user_id, character_id, sender_type, message_text, emotion_tag)
         VALUES (%s, %s, %s, %s, %s)
      """, (
         user_id,
         data['character_id'],
         data['sender_type'],
         data['message_text'],
         data.get('emotion_tag')
      ))
      
      conn.commit()
      dialogue_id = cursor.lastrowid
      
      return jsonify({
         'result': 'success',
         'msg': '대화가 저장되었습니다.',
         'dialogue_id': dialogue_id
      })
      
   except Exception as e:
      import traceback
      error_msg = str(e)
      traceback.print_exc()
      return jsonify({'result': 'fail', 'msg': f'대화 저장 실패: {error_msg}'}), 500
   
   finally:
      if cursor:
         cursor.close()
      if conn and conn.is_connected():
         conn.close()

# 음성 대화 조회 엔드포인트
@app.route('/voice/dialogue/<int:user_id>', methods=['GET'])
@token_required
def get_dialogue(user_id_param, user_id):
   """사용자의 음성 대화 기록을 조회합니다."""
   conn = None
   cursor = None
   
   try:
      # URL의 user_id와 토큰의 user_id가 일치하는지 확인
      if user_id_param != user_id:
         return jsonify({'result': 'fail', 'msg': '권한이 없습니다.'}), 403
      
      conn = get_db_connection()
      cursor = conn.cursor(dictionary=True)
      
      # 최근 대화 조회 (최신순, 최대 50개)
      cursor.execute("""
         SELECT id, user_id, character_id, sender_type, message_text, 
                emotion_tag, created_at
         FROM Dialogue
         WHERE user_id = %s
         ORDER BY created_at DESC
         LIMIT 50
      """, (user_id,))
      
      dialogues = cursor.fetchall()
      
      # JSON 필드 처리
      for dialogue in dialogues:
         dialogue['created_at'] = str(dialogue['created_at']) if dialogue['created_at'] else None
      
      return jsonify({
         'result': 'success',
         'dialogues': dialogues,
         'count': len(dialogues)
      })
      
   except Exception as e:
      import traceback
      error_msg = str(e)
      traceback.print_exc()
      return jsonify({'result': 'fail', 'msg': f'대화 조회 실패: {error_msg}'}), 500
   
   finally:
      if cursor:
         cursor.close()
      if conn and conn.is_connected():
         conn.close()

# PDF 리포트 생성을 위한 OpenAI API 엔드포인트
@app.route('/ai/generate-pdf-report', methods=['POST'])
@token_required
def generate_pdf_report(user_id):
   """PDF 생성을 위한 OpenAI 리포트 생성"""
   
   # OpenAI API 키 확인
   if not OPENAI_API_KEY:
      return jsonify({
         'result': 'fail',
         'msg': 'OpenAI API 키가 설정되지 않았습니다.'
      }), 500
   
   try:
      data = request.get_json()
      prompt = data.get('prompt', '')
      report_data = data.get('report_data', {})
      
      # 기존에 정의된 client_adult 클라이언트 사용
      response = client_adult.chat.completions.create(
         model="gpt-4o-mini",
         messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(report_data, ensure_ascii=False)}
         ],
         temperature=0.7,
         max_tokens=2000
      )
      
      # JSON 응답 파싱 시도
      generated_content = response.choices[0].message.content
      
      # JSON 형태가 아니면 전체 내용을 구조화
      try:
         generated_report = json.loads(generated_content)
      except:
         # JSON이 아니면 기본 구조로 반환
         generated_report = {
            'executive_summary': generated_content[:200] if generated_content else '리포트 생성 실패',
            'detailed_analysis': generated_content if generated_content else '',
            'key_achievements': report_data.get('strengths', []),
            'areas_for_improvement': report_data.get('improvements', []),
            'recommendations': report_data.get('suggestions', []),
            'behavioral_patterns': '',
            'motivation_strategies': [],
            'next_steps': '',
            'family_involvement': ''
         }
      
      return jsonify({
         'result': 'success',
         'generated_report': generated_report
      })
      
   except Exception as e:
      import traceback
      error_msg = str(e)
      traceback.print_exc()
      return jsonify({'result': 'fail', 'msg': f'리포트 생성 실패: {error_msg}'}), 500

if __name__ == '__main__':  
   app.run('0.0.0.0', port=5001, debug=True)
