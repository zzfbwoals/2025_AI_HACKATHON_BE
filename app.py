import re
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

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
def home():
   return 'index.html'

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

@app.route('/adult', methods=['POST'])
def chat_adult():
   data = request.get_json()
   response = client_adult.responses.create(
      model=model_name,
      input=[
         {
            'role': 'developer',
            'content': '시스템 프롬프트 (아이와 대화)'
         },
         {
            'role': 'user',
            'content': data.get('prompt')
         }
        ]
    )
   return response.output_text

@app.route('/child', methods=['POST'])
def chat_child():
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

if __name__ == '__main__':  
   app.run('0.0.0.0', port=5001, debug=True)