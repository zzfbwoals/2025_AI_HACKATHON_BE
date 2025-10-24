from flask import Flask, render_template, request, jsonify
from openai import OpenAI

client_adult = OpenAI(api_key='')
client_child = OpenAI(api_key='')
model_name = "gpt-5-nano"

app = Flask(__name__)

@app.route('/')
def home():
   return 'index.html'

@app.route('/signup', methods=['POST'])
def signup():
   data = request.get_json()
   id = data.get('id')
   password = data.get('password')

   #데이터 베이스에 저장 로직
   return jsonify({'result': 'success', 'msg': '회원가입 성공'})

@app.route('/login', methods=['POST'])
def login():
   data = request.get_json()
   id = data.get('id')
   password = data.get('password')

   #데이터 베이스와 비교 로직
   return jsonify({'result': 'success'})

@app.route('/adult', methods=['POST'])
def chat_adult():
   response = client_adult.responses.create(
      model=model_name,
      input=[
         {
            'role': 'developer',
            'content': '시스템 프롬프트'
         },
         {
            'role': 'user',
            'content': '프롬프트'
         }
        ]
    )
   return response.output_text

@app.route('/child', methods=['POST'])
def chat_child():
   response = client_child.responses.create(
      model=model_name,
      input=[
         {
            'role': 'developer',
            'content': '시스템 프롬프트'
         },
         {
            'role': 'user',
            'content': '프롬프트'
         }
        ]
    )
   return response.output_text

if __name__ == '__main__':  
   app.run('0.0.0.0', port=5001, debug=True)