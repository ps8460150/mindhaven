# mindhaven_allinone.py
# Single-file MindHaven: frontend + backend + voice + memory + mood tracking
# Requires: Flask
# Run: python mindhaven_allinone.py
from flask import Flask, request, jsonify, send_file, make_response
from flask import render_template_string
import random
import html
import datetime

app = Flask(__name__)

# ----------------------------
# In-memory memory & stats
# ----------------------------
conversation_history = []   # list of (timestamp_iso, user, bot, emotion)
mood_counts = {"joy":0, "sadness":0, "anger":0, "fear":0, "neutral":0, "disgust":0}

# ----------------------------
# Crisis detection keywords
# ----------------------------
CRISIS_KEYWORDS = [
    "suicide", "kill myself", "end my life", "i want to die", "i'm going to die",
    "i want to end it", "worthless", "cant go on", "can't go on", "die now"
]

# ----------------------------
# Lightweight emotion heuristics (keyword-based)
# ----------------------------
EMOTION_KEYWORDS = {
    "sadness": ["sad", "depress", "hopeless", "alone", "tired", "low", "unhappy", "miserable", "cry"],
    "joy": ["happy", "good", "great", "awesome", "joy", "excited", "glad", "relieved"],
    "anger": ["angry", "hate", "furious", "annoyed", "frustrat", "irritat"],
    "fear": ["scared", "afraid", "anxious", "panic", "worried", "fear"],
    "disgust": ["disgust", "gross", "nasty", "repulsed"]
}

# ----------------------------
# Empathy and reply templates
# ----------------------------
EMPATHY = {
    "sadness": [
        "I’m really sorry you’re feeling this way 💙. I’m here with you.",
        "That sounds heavy. Would you like to tell me what happened?",
        "Your feelings are valid — thank you for sharing that with me."
    ],
    "joy": [
        "That’s wonderful! I’m happy for you 😊",
        "Amazing — I love hearing good news like this!",
        "Enjoy this moment — you deserve it."
    ],
    "anger": [
        "I hear your frustration 😤. Want to say what triggered it?",
        "It makes sense to feel angry. Let’s try to understand it together.",
        "Anger can be heavy. I’m with you to work through it."
    ],
    "fear": [
        "It sounds scary — you’re not alone. Breathe slowly with me.",
        "I understand that worry. Tell me what exactly you’re fearing.",
        "Fear is valid and okay. We can handle this step by step."
    ],
    "disgust": [
        "That must have been unpleasant. Do you want to share more?",
        "I’m sorry you experienced that — thank you for telling me.",
    ],
    "neutral": [
        "I’m listening. Tell me more about what’s on your mind.",
        "Thanks for sharing — I’m here to help however I can.",
        "Go on, I’m paying attention."
    ]
}

# Extra helpful suggestions for common needs
PRACTICAL_SUGGESTIONS = [
    "Try a breathing exercise: inhale 4s — hold 4s — exhale 6s. Repeat 4 times.",
    "If possible, stand up and stretch your arms — small movement helps.",
    "Write down one small thing you can do in the next hour to feel better.",
    "If it helps, call a trusted friend or family member and tell them you need support."
]

# Helplines (India shown) — change if needed for other country
HELPLINES = {
    "India": "KIRAN Helpline: 1800-599-0019 | Tele-MANAS: 14416",
    "International": "If you're outside India, check local emergency numbers or local mental health helplines."
}

# ----------------------------
# Utilities
# ----------------------------
def detect_crisis(text: str) -> bool:
    t = text.lower()
    for kw in CRISIS_KEYWORDS:
        if kw in t:
            return True
    return False

def detect_emotion(text: str) -> str:
    t = text.lower()
    scores = {k:0 for k in mood_counts.keys()}
    # count keyword occurrences
    for emo, kwlist in EMOTION_KEYWORDS.items():
        for kw in kwlist:
            if kw in t:
                scores[emo] += 1
    # fallback: check simple polarity words
    if sum(scores.values()) == 0:
        # neutral or try simple sentiment words
        if any(w in t for w in ["not", "n't", "no", "never"]):
            scores["sadness"] += 0.5
        else:
            scores["neutral"] += 1
    # choose highest
    emo = max(scores.items(), key=lambda x: x[1])[0]
    # if tie or zero, return neutral
    if scores[emo] <= 0:
        return "neutral"
    return emo

def make_bot_reply(user_text: str, emotion: str) -> str:
    # crisis prioritized
    if detect_crisis(user_text):
        return (
            "⚠️ It sounds like you might be in crisis. "
            "Please reach out for immediate help:\n"
            f"{HELPLINES['India']}\n"
            "If you are outside India, contact local emergency services now."
        )
    # empathy prefix
    prefix = random.choice(EMPATHY.get(emotion, EMPATHY["neutral"]))
    # follow-up: varied suggestions or question
    follow = ""
    # if sadness or fear, add breathing suggestion sometimes
    if emotion in ["sadness", "fear"]:
        follow = random.choice(PRACTICAL_SUGGESTIONS)
    else:
        # either ask a follow-up question or give a suggestion
        if random.random() < 0.6:
            follow = "Would you like to try a breathing exercise or hear a distraction (joke/short story)?"
        else:
            follow = random.choice(PRACTICAL_SUGGESTIONS)
    return f"{prefix}\n\n{follow}"

# ----------------------------
# Flask routes: serve UI & API
# ----------------------------

HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MindHaven — Emotional AI</title>
<style>
:root{--bg:#0b0b0b;--card:#0f0f0f;--muted:#9b9b9b;--accent:#fff;}
html,body{height:100%;margin:0;font-family:Inter,Segoe UI,system-ui,Arial;color:#eee;background:linear-gradient(180deg,#000,#0b0b0b);}
.container{max-width:980px;margin:20px auto;padding:18px;display:grid;grid-template-columns:1fr 370px;gap:18px;}
.left{background:var(--card);border-radius:12px;padding:18px;min-height:70vh;display:flex;flex-direction:column;}
.header{display:flex;align-items:center;gap:12px;}
.logo{width:56px;height:56px;border-radius:10px;background:#111;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:20px;color:#fff;border:1px solid rgba(255,255,255,0.04);}
.title{font-size:20px;font-weight:700;}
.chat{flex:1;overflow:auto;padding-top:12px;display:flex;flex-direction:column;gap:10px;}
.msg{max-width:78%;padding:12px;border-radius:10px;}
.user{align-self:flex-end;background:#121212;color:#fff;border:1px solid rgba(255,255,255,0.03);}
.bot{align-self:flex-start;background:#0b1220;color:#fff;border-left:4px solid #fff;padding-left:10px;}
.controls{display:flex;gap:8px;margin-top:12px;align-items:center;}
.input{flex:1;padding:12px;border-radius:10px;border:1px solid rgba(255,255,255,0.04);background:#060606;color:#fff;}
.btn{background:#fff;color:#000;padding:10px 14px;border-radius:10px;border:none;cursor:pointer;transition:all .18s;}
.btn:hover{transform:translateY(-2px);box-shadow:0 6px 22px rgba(0,0,0,0.6);}

.mic{width:46px;height:46px;border-radius:50%;background:transparent;border:2px solid #fff;color:#fff;display:flex;align-items:center;justify-content:center;font-size:18px;cursor:pointer;transition:transform .12s;}
.mic.recording{background:#ff4d6d;transform:scale(1.05);}

.right{background:transparent;display:flex;flex-direction:column;gap:12px;}
.panel{background:linear-gradient(180deg,#0f0f0f,#0b0b0b);padding:16px;border-radius:12px;border:1px solid rgba(255,255,255,0.03);}
.stat{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;}
.small{font-size:13px;color:var(--muted);}

.footer{font-size:12px;color:var(--muted);margin-top:12px;text-align:center;}
@media(max-width:900px){.container{grid-template-columns:1fr;}.right{order:2}}
</style>
</head>
<body>
<div class="container">
  <div class="left">
    <div class="header">
      <div class="logo">MH</div>
      <div>
        <div class="title">MindHaven</div>
        <div class="small">AI companion — supportive, private, offline-first</div>
      </div>
    </div>

    <div class="chat" id="chat"></div>

    <div class="controls">
      <input id="userInput" class="input" placeholder="Type how you feel or press mic..." />
      <button id="sendBtn" class="btn">Send</button>
      <div id="micBtn" class="mic" title="Record voice (browser)"><span id="micDot">🎤</span></div>
    </div>

    <div class="footer">
      <div>Not medical advice. If in crisis, call helplines shown on the right.</div>
    </div>
  </div>

  <div class="right">
    <div class="panel">
      <strong>Mood Stats</strong>
      <div id="stats" style="margin-top:8px"></div>
    </div>

    <div class="panel">
      <strong>Quick Actions</strong>
      <div style="margin-top:8px" class="small">
        <button class="btn" onclick="sendPreset('breathing')">Start Breathing Exercise</button>
        <button class="btn" onclick="sendPreset('grounding')">Grounding Technique</button>
        <button class="btn" onclick="sendPreset('joke')">Get a Light Distraction (Joke)</button>
      </div>
    </div>

    <div class="panel">
      <strong>Helplines</strong>
      <div class="small" style="margin-top:8px">
        <div>India: KIRAN 1800-599-0019 | Tele-MANAS 14416</div>
        <div style="margin-top:8px">If outside India, contact your local emergency services.</div>
      </div>
    </div>
  </div>
</div>

<script>
/* Simple front-end logic: sends messages to /api/chat and uses Web Speech for mic + TTS */
const chatEl = document.getElementById('chat');
const input = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const micBtn = document.getElementById('micBtn');
let recognizing = false;
let recognition = null;

/* Post message to server */
async function postMessage(text){
  if(!text || !text.trim()) return;
  addMessage(text, 'user');
  input.value = '';
  try {
    const res = await fetch('/api/chat', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({message: text})
    });
    const data = await res.json();
    addMessage(data.reply, 'bot');
    updateStats(data.stats);
    // speak
    speakText(data.reply);
    // if crisis -> visual alert
    if(data.crisis){
      addMessage("⚠️ If you are in immediate danger, please contact emergency services or the helpline shown.", 'bot');
    }
  } catch(err){
    addMessage("⚠️ Server not reachable. Please ensure the app is running.", 'bot');
  }
}

/* Add chat bubble */
function addMessage(txt, who){
  const d = document.createElement('div');
  d.className = 'msg ' + (who==='user' ? 'user' : 'bot');
  d.innerText = txt;
  chatEl.appendChild(d);
  chatEl.scrollTop = chatEl.scrollHeight;
}

/* Speak text using browser TTS */
function speakText(txt){
  if(!('speechSynthesis' in window)) return;
  try {
    const u = new SpeechSynthesisUtterance(txt);
    u.lang = 'en-US';
    u.rate = 1;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(u);
  } catch(e){}
}

/* Voice recognition setup */
function initMic(){
  if(!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    micBtn.style.display = 'none';
    return;
  }
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.lang = 'en-US';
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => { recognizing = true; micBtn.classList.add('recording'); }
  recognition.onend = () => { recognizing = false; micBtn.classList.remove('recording'); }
  recognition.onresult = (e) => {
    const text = e.results[0][0].transcript;
    postMessage(text);
  };
}

micBtn.addEventListener('click', ()=>{
  if(!recognition) initMic();
  if(!recognition) return;
  if(recognizing){
    recognition.stop();
  } else {
    recognition.start();
  }
});

/* Send button */
sendBtn.addEventListener('click', ()=> postMessage(input.value));
input.addEventListener('keydown', (e)=>{ if(e.key==='Enter' && !e.shiftKey) { e.preventDefault(); postMessage(input.value); } });

/* Presets */
function sendPreset(kind){
  if(kind==='breathing') postMessage("I want to do a breathing exercise");
  if(kind==='grounding') postMessage("I need a grounding technique");
  if(kind==='joke') postMessage("Tell me a light joke or distraction");
}

/* Update stats panel */
function updateStats(stats){
  const el = document.getElementById('stats');
  let html = '';
  for(const k in stats){
    html += `<div class="stat"><div>${k}</div><div>${stats[k]}</div></div>`;
  }
  el.innerHTML = html;
}

/* Load initial stats */
(async function(){
  try{
    const res = await fetch('/api/stats');
    const s = await res.json();
    updateStats(s);
  }catch(e){}
})();

</script>
</body>
</html>
"""

# ----------------------------
# API endpoints
# ----------------------------

@app.route('/')
def index():
    # Serve combined UI
    return render_template_string(HTML)

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json() or {}
    user_text = data.get('message','').strip()
    if not user_text:
        return jsonify({"reply":"Please say or type something so I can help.","stats":mood_counts,"crisis":False})

    # detect crisis first
    crisis = detect_crisis(user_text)
    emotion = detect_emotion(user_text)
    # update stats/memory
    ts = datetime.datetime.utcnow().isoformat()
    # store limited history to avoid memory growth
    conversation_history.append((ts, user_text, None, emotion))
    if emotion in mood_counts:
        try:
            mood_counts[emotion] += 1
        except:
            mood_counts[emotion] = 1

    # generate reply
    reply = make_bot_reply(user_text, emotion)
    # attach reply to last memory record
    if conversation_history:
        conversation_history[-1] = (ts, user_text, reply, emotion)

    # Return JSON
    return jsonify({"reply": reply, "stats": mood_counts, "crisis": crisis})

@app.route('/api/stats', methods=['GET'])
def api_stats():
    return jsonify(mood_counts)

@app.route('/api/history', methods=['GET'])
def api_history():
    # returns recent history
    hist = [{"ts":h[0],"user":h[1],"bot":h[2],"emotion":h[3]} for h in conversation_history[-50:]]
    return jsonify(hist)

# ----------------------------
# Run server
# ----------------------------
if __name__ == '__main__':
    print("🚀 MindHaven local app — open http://127.0.0.1:5050")
    app.run(host='127.0.0.1', port=5050, debug=True)
