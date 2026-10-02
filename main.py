import os
import sqlite3
import pandas as pd
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename
from openai import OpenAI

# 1. 초기 설정 및 환경 변수 로드
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "hana_secret_key_1234")
UPLOAD_FOLDER = 'static'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# OpenAI 클라이언트 초기화 (env의 OPENAI_API_KEY 자동 로드)
client = OpenAI()

# 2. 데이터베이스 및 테이블 초기화 (SQLite)
DB_PATH = 'user_data.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            propensity TEXT NOT NULL,
            job TEXT NOT NULL,
            income INTEGER NOT NULL,
            profile_img TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# 3. HTML 템플릿 통합 (하나은행 테마 및 ChatGPT 스타일 챗봇)
BASE_CSS = """
<style>
    :root {
        --hana-green: #008485;
        --hana-light-green: #e6f3f3;
        --hana-gold: #b39257;
        --dark-bg: #ffffff;
        --text-color: #333333;
    }
    body { font-family: 'Noto Sans KR', sans-serif; background-color: #f4f7f7; color: var(--text-color); margin: 0; padding: 0; }
    .navbar { background-color: white; border-bottom: 2px solid var(--hana-green); padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; }
    .navbar img { height: 40px; }
    .container { max-width: 800px; margin: 50px auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
    h2 { color: var(--hana-green); border-bottom: 2px solid var(--hana-light-green); padding-bottom: 10px; }
    .btn-hana { background-color: var(--hana-green); color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; width: 100%; }
    .btn-hana:hover { background-color: #006a6b; }
    .form-group { margin-bottom: 15px; }
    .form-group label { display: block; margin-bottom: 5px; font-weight: bold; color: #555; }
    .form-group input, .form-group select { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
    
    /* 메인 화면 추천 카드 */
    .card-container { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-top: 20px; }
    .card { background: white; border: 1px solid #e0e0e0; border-top: 4px solid var(--hana-green); border-radius: 8px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
    .card h3 { margin-top: 0; color: #333; }
    .card .badge { background: var(--hana-light-green); color: var(--hana-green); padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
    
    /* 챗봇 아이콘 및 창 (ChatGPT 스타일 + 하나은행 테마) */
    #chatbot-icon { position: fixed; bottom: 30px; right: 30px; width: 60px; height: 60px; cursor: pointer; border-radius: 50%; box-shadow: 0 4px 10px rgba(0,0,0,0.2); }
    #chatbot-window { position: fixed; bottom: 100px; right: 30px; width: 380px; height: 500px; background: white; border-radius: 12px; box-shadow: 0 5px 25px rgba(0,0,0,0.15); display: none; flex-direction: column; overflow: hidden; border: 1px solid #e0e0e0; }
    .chat-header { background: var(--hana-green); color: white; padding: 15px; font-weight: bold; display: flex; justify-content: space-between; align-items: center; }
    .chat-messages { flex: 1; padding: 15px; overflow-y: auto; background: #f9f9fb; display: flex; flex-direction: column; gap: 10px; }
    .message { max-width: 80%; padding: 10px 14px; border-radius: 15px; font-size: 14px; line-height: 1.4; }
    .message.user { background: var(--hana-green); color: white; align-self: flex-end; border-bottom-right-radius: 2px; }
    .message.bot { background: white; color: #333; align-self: flex-start; border-bottom-left-radius: 2px; border: 1px solid #e0e0e0; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
    .chat-input-area { border-top: 1px solid #eee; padding: 10px; display: flex; background: white; }
    .chat-input-area input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 6px; outline: none; }
    .chat-input-area button { background: var(--hana-green); color: white; border: none; padding: 0 15px; margin-left: 5px; border-radius: 6px; cursor: pointer; }
</style>
"""

LOGIN_HTML = f"""
<!DOCTYPE html>
<html>
<head>
    <title>하나은행 - 로그인</title>
    {BASE_CSS}
</head>
<body>
    <div class="navbar"><img src="/static/logo.JPG" alt="Hana Bank"></div>
    <div class="container" style="max-width: 400px;">
        <h2>로그인</h2>
        <form action="/login" method="post">
            <div class="form-group">
                <label>아이디</label>
                <input type="text" name="username" required>
            </div>
            <div class="form-group">
                <label>비밀번호</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit" class="btn-hana">로그인</button>
        </form>
        <div style="margin-top: 15px; text-align: center;">
            <a href="/register" style="color: var(--hana-green); text-decoration: none;">회원가입 하러가기</a>
        </div>
    </div>
</body>
</html>
"""

REGISTER_HTML = f"""
<!DOCTYPE html>
<html>
<head>
    <title>하나은행 - 회원가입</title>
    {BASE_CSS}
</head>
<body>
    <div class="navbar"><img src="/static/logo.JPG" alt="Hana Bank"></div>
    <div class="container" style="max-width: 500px;">
        <h2>회원가입</h2>
        <form action="/register" method="post" enctype="multipart/form-data">
            <div class="form-group"><label>아이디</label><input type="text" name="id" required></div>
            <div class="form-group"><label>비밀번호</label><input type="password" name="password" required></div>
            <div class="form-group"><label>이름</label><input type="text" name="name" required></div>
            <div class="form-group"><label>이메일</label><input type="email" name="email" required></div>
            <div class="form-group"><label>나이</label><input type="number" name="age" required></div>
            <div class="form-group">
                <label>성별</label>
                <select name="gender"><option value="남성">남성</option><option value="여성">여성</option></select>
            </div>
            <div class="form-group">
                <label>투자성향</label>
                <select name="propensity">
                    <option value="안정형">안정형</option>
                    <option value="안정추구형">안정추구형</option>
                    <option value="위험선호형">위험선호형</option>
                </select>
            </div>
            <div class="form-group"><label>직업</label><input type="text" name="job" required></div>
            <div class="form-group"><label>연소득 (만원)</label><input type="number" name="income" required></div>
            <div class="form-group"><label>프로필 사진</label><input type="file" name="profile_img"></div>
            <button type="submit" class="btn-hana">가입하기</button>
        </form>
    </div>
</body>
</html>
"""

MAIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>하나은행 - 맞춤 추천</title>
    {{ base_css | safe }}
</head>
<body>
    <div class="navbar">
        <img src="/static/logo.JPG" alt="Hana Bank">
        <div><strong>{{ user.name }}</strong>님 환영합니다 | <a href="/logout" style="color: #666;">로그아웃</a></div>
    </div>
    <div class="container">
        <h2>{{ user.name }}님을 위한 맞춤 금융상품 추천</h2>
        <p style="color: #666;">고객님의 나이({{ user.age }}세), 투자성향({{ user.propensity }}), 직업({{ user.job }}), 소득에 맞춘 최적의 상품입니다.</p>
        
        <div class="card-container">
            {% for item in recommendations %}
            <div class="card">
                <span class="badge">{{ item['유형'] if '유형' in item else '예적금' }}</span>
                <h3 style="margin: 10px 0 5px 0; color: var(--hana-green);">{{ item['상품명'] }}</h3>
                <p style="font-size: 14px; color: #555; margin-bottom: 5px;">{{ item['설명'] if '설명' in item else '우대금리 및 맞춤 혜택 제공' }}</p>
                <p style="font-weight: bold; color: var(--hana-gold); margin: 0;">최고 연 {{ item['금리'] if '금리' in item else '기본' }}%</p>
            </div>
            {% endfor %}
        </div>
    </div>

    <!-- 챗봇 아이콘 및 윈도우 -->
    <img id="chatbot-icon" src="/static/chatbot.JPG" onclick="toggleChat()" alt="Chatbot">
    
    <div id="chatbot-window">
        <div class="chat-header">
            <span>HanaAI 상품상담실</span>
            <span style="cursor:pointer;" onclick="toggleChat()">✕</span>
        </div>
        <div class="chat-messages" id="chat-box">
            <div class="message bot">안녕하세요! 하나은행 맞춤형 AI 상담원입니다. 추천받으신 상품이나 자산 관리에 대해 무엇이든 물어보세요.</div>
        </div>
        <div class="chat-input-area">
            <input type="text" id="chat-input" placeholder="메시지를 입력하세요..." onkeypress="if(event.keyCode==13) sendMessage()">
            <button onclick="sendMessage()">전송</button>
        </div>
    </div>

    <script>
        function toggleChat() {
            var chatWin = document.getElementById('chatbot-window');
            chatWin.style.display = (chatWin.style.display === 'flex') ? 'none' : 'flex';
        }

        function sendMessage() {
            var input = document.getElementById('chat-input');
            var msgText = input.value.trim();
            if(!msgText) return;

            var chatBox = document.getElementById('chat-box');
            
            // 사용자 메시지 추가
            var userDiv = document.createElement('div');
            userDiv.className = 'message user';
            userDiv.innerText = msgText;
            chatBox.appendChild(userDiv);
            input.value = '';
            chatBox.scrollTop = chatBox.scrollHeight;

            // [수정 및 완성] 서버 통신 (Flask의 /chat 엔드포인트로 전송)
            fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: msgText })
            })
            .then(response => response.json())
            .then(data => {
                // 챗봇 답변 추가
                var botDiv = document.createElement('div');
                botDiv.className = 'message bot';
                botDiv.innerText = data.reply;
                chatBox.appendChild(botDiv);
                chatBox.scrollTop = chatBox.scrollHeight;
            })
            .catch(error => {
                console.error('Error:', error);
            });
        }
    </script>
</body>
</html>
"""
