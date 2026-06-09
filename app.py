import os
import io
import base64
from flask import Flask, render_template_string, request, jsonify
from openai import OpenAI
from gtts import gTTS

app = Flask(__name__)

# 初始化 OpenRouter 客戶端
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", "OPENROUTER_API_KEY"),
    default_headers={
        "HTTP-Referer": "http://localhost:5001",
        "X-Title": "AI Mirror MVP v2",
    }
)

AVATAR_URL = "https://api.dicebear.com/7.x/bottts/svg?seed=TeacherMingJing"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AI 智能鏡子 MVP v3</title>
    <style>
        body { 
            background-color: black; 
            color: white; 
            font-family: 'PingFang HK', 'Microsoft JhengHei', sans-serif; 
            text-align: center; 
            padding-top: 50px;
            margin: 0;
        }
        .container { max-width: 600px; margin: 0 auto; display: flex; flex-direction: column; align-items: center; }
        #avatar {
            width: 150px; height: 150px; border-radius: 50%;
            border: 3px solid #00d2ff; box-shadow: 0 0 20px #00d2ff;
            margin-bottom: 30px; transition: transform 0.3s ease;
        }
        .speaking { animation: pulse 1.5s infinite alternate; }
        @keyframes pulse {
            0% { transform: scale(1); box-shadow: 0 0 20px #00d2ff; }
            100% { transform: scale(1.08); box-shadow: 0 0 40px #ff007f; border-color: #ff007f; }
        }
        #status { color: #888; font-size: 1.1rem; margin-bottom: 20px; height: 24px; }
        #response { font-size: 1.6rem; min-height: 100px; max-width: 500px; line-height: 1.6; margin-bottom: 40px; color: #e0e0e0; }
        #recordBtn {
            background-color: #111; color: #00d2ff; border: 2px solid #00d2ff;
            padding: 15px 40px; font-size: 1.2rem; border-radius: 30px; cursor: pointer;
            box-shadow: 0 0 10px rgba(0, 210, 255, 0.3); transition: all 0.2s ease;
        }
        #recordBtn:hover { background-color: #00d2ff; color: black; box-shadow: 0 0 20px #00d2ff; }
        #recordBtn:disabled { border-color: #444; color: #444; cursor: not-allowed; box-shadow: none; }
    </style>
</head>
<body>
    <div class="container">
        <img id="avatar" src="{{ avatar_url }}" alt="AI Teacher">
        <div id="status">點擊下方按鈕開始提問</div>
        <div id="response">「老師正在聆聽你的智慧...」</div>
        <button id="recordBtn">🎙️ 開始語音輸入</button>
    </div>

    <script>
        const recordBtn = document.getElementById('recordBtn');
        const statusDiv = document.getElementById('status');
        const responseDiv = document.getElementById('response');
        const avatar = document.getElementById('avatar');
        
        let recognition;

        // 1. 語音辨識初始化 (Web Speech API)
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.lang = 'zh-HK'; // 👈 這裡直接鎖定輸入為香港廣東話
            recognition.interimResults = false;

            recognition.onstart = () => {
                statusDiv.innerText = "🔴 正在錄音，請說話（廣東話/英文）...";
                recordBtn.innerText = "🛑 錄音中...";
                recordBtn.disabled = true;
            };

            recognition.onerror = (e) => { statusDiv.innerText = "❌ 錯誤: " + e.error; resetButton(); };
            recognition.onend = () => { resetButton(); };
            
            recognition.onresult = (event) => {
                const userText = event.results[0][0].transcript;
                statusDiv.innerText = `💬 聽到問題："${userText}"...`;
                sendToAI(userText);
            };
        } else {
            statusDiv.innerText = "❌ 請使用 Chrome 瀏覽器。";
            recordBtn.disabled = true;
        }

        recordBtn.addEventListener('click', () => { recognition.start(); });
        function resetButton() { recordBtn.disabled = false; recordBtn.innerText = "🎙️ 開始語音輸入"; }

        // 2. 呼叫 AI 後端
        async function sendToAI(text) {
            responseDiv.innerText = "AI 老師正在思考答案...";
            try {
                const res = await fetch('/ask-ai', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question: text })
                });
                const data = await res.json();
                
                responseDiv.innerText = data.answer;
                
                // 3. 網頁端原生廣東話發音（終極解決方案）
                speakCantonese(data.answer);

            } catch (err) {
                statusDiv.innerText = "❌ 連線失敗";
            }
        }

        // 🔊 瀏覽器原生廣東話朗讀函數
        function speakCantonese(text) {
            // 取消目前可能正在播放的聲音
            window.speechSynthesis.cancel();

            const utterance = new SpeechSynthesisUtterance(text);
            
            // 關鍵：強制尋找瀏覽器系統自帶的香港廣東話（zh-HK）聲音
            const voices = window.speechSynthesis.getVoices();
            const hkVoice = voices.find(v => v.lang === 'zh-HK' || v.lang === 'zh_HK');
            
            if (hkVoice) {
                utterance.voice = hkVoice;
            }
            
            // 動態效果
            utterance.onstart = () => {
                statusDiv.innerText = "🔊 老師正在用廣東話回答...";
                avatar.classList.add('speaking');
            };
            
            utterance.onend = () => {
                statusDiv.innerText = "🎙️ 回答完畢，點擊按鈕可再次提問";
                avatar.classList.remove('speaking');
            };

            window.speechSynthesis.speak(utterance);
        }

        // 確保語音庫加載完畢（部分瀏覽器需要異步加載聲音列表）
        window.speechSynthesis.onvoiceschanged = () => { window.speechSynthesis.getVoices(); };
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, avatar_url=AVATAR_URL)

@app.route('/ask-ai', methods=['POST'])
def ask_ai():
    try:
        data = request.json
        user_question = data.get('question', '')
        
        # 呼叫 OpenRouter
        response = client.chat.completions.create(
            model="openrouter/free", 
            messages=[
                {
                    "role": "system", 
                    "content": "你係一個中學科學老師。請用親切、鼓勵嘅語氣，喺50字入面用正宗香港廣東話口語（粵語白話文）簡短回答學生嘅問題。唔好用簡體字，要用香港常用字（例如：係、唔、噉、講、攞）。"
                },
                {"role": "user", "content": user_question}
            ]
        )
        ai_answer = response.choices[0].message.content
        
        return jsonify({"answer": ai_answer})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
