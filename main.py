import streamlit as st
import json
from pathlib import Path
import random
import difflib
from gtts import gTTS
import speech_recognition as sr
import tempfile
from datetime import datetime
import pandas as pd

# ---------- FILE PATHS ----------
KNOWLEDGE_FILE = Path("learned_knowledge.json")
USERS_FILE = Path("users.json")

# ---------- SAFE JSON LOADING ----------
def load_json(filename):
    file_path = Path(__file__).parent / filename
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ---------- LOAD DATA ----------
education = load_json("education.json")
animals = load_json("animals.json")
science = load_json("science.json")
geography = load_json("geography.json")
greetings = load_json("greetings.json").get("greetings", {})

learned_knowledge = load_json(KNOWLEDGE_FILE)
users = load_json(USERS_FILE)

# ---------- SESSION STATE ----------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "score" not in st.session_state:
    st.session_state.score = 0
if "username" not in st.session_state:
    st.session_state.username = None
if "last_topic" not in st.session_state:
    st.session_state.last_topic = None
if "achievements" not in st.session_state:
    st.session_state.achievements = []
if "session_times" not in st.session_state:
    st.session_state.session_times = []

# ---------- LOGIN ----------
st.sidebar.header("🔑 Login / Profile")
if st.session_state.username is None:
    username_input = st.sidebar.text_input("Username")
    if st.sidebar.button("Login"):
        if username_input:
            st.session_state.username = username_input
            if username_input not in users:
                users[username_input] = {"score":0, "history":[],"achievements":[],"sessions":[]}
                save_json(USERS_FILE, users)
else:
    st.sidebar.write(f"Hello, **{st.session_state.username}**")
    if st.sidebar.button("Logout"):
        st.session_state.username = None
        st.session_state.chat_history = []
        st.session_state.score = 0
        st.session_state.achievements = []
        st.session_state.session_times = []

# ---------- UTILITIES ----------
def clean(text): return text.lower().strip()
def fuzzy(word, choices):
    match = difflib.get_close_matches(word, choices, n=1, cutoff=0.6)
    return match[0] if match else None
def format_dict(d): return "\n".join([f"**{k.title()}:** {v}" for k,v in d.items()])
def get_suggestions(text):
    words = list(animals.keys()) + list(science.get("science", {}).keys()) + list(geography.get("geography", {}).keys())
    return difflib.get_close_matches(text.lower(), words, n=5, cutoff=0.3)

# ---------- AI ENGINE ----------
def get_answer(user_input):
    q = clean(user_input)

    # Greeting
    for word in q.split():
        key = fuzzy(word, greetings.keys())
        if key:
            val = greetings[key]
            return random.choice(val) if isinstance(val, list) else val

    # Learned knowledge (fuzzy match, case-insensitive)
    for k, v in learned_knowledge.items():
        if fuzzy(q, [clean(k)]):
            st.session_state.last_topic = k
            return v

    # Animals
    for k, v in animals.items():
        if fuzzy(q, [clean(k)]):
            st.session_state.last_topic = k
            return "🦁 " + format_dict(v)

    # Science
    for k, v in science.get("science", {}).items():
        if fuzzy(q, [clean(k)]):
            st.session_state.last_topic = k
            return "🔬 " + format_dict(v)

    # Geography
    for k, v in geography.get("geography", {}).items():
        if fuzzy(q, [clean(k)]):
            st.session_state.last_topic = k
            return "🌍 " + format_dict(v)

    # Follow-up
    if "more" in q and st.session_state.last_topic:
        return f"📌 You were learning about {st.session_state.last_topic}. Ask a specific question."

    return "🤖 I don't know that yet. Teach me below!"

# ---------- ACHIEVEMENTS ----------
def check_achievements():
    achieved = []
    if st.session_state.score >= 5 and "Rising Star" not in st.session_state.achievements:
        st.session_state.achievements.append("Rising Star")
        achieved.append("🏅 Rising Star: Score >= 5")
    if st.session_state.score >= 10 and "Advanced Learner" not in st.session_state.achievements:
        st.session_state.achievements.append("Advanced Learner")
        achieved.append("🏅 Advanced Learner: Score >= 10")
    if len(learned_knowledge) >= 5 and "Knowledge Collector" not in st.session_state.achievements:
        st.session_state.achievements.append("Knowledge Collector")
        achieved.append("🏅 Knowledge Collector: Learned 5+ topics")
    if achieved:
        st.success("New Achievements!\n" + "\n".join(achieved))
    if st.session_state.username:
        users[st.session_state.username]["achievements"] = st.session_state.achievements
        save_json(USERS_FILE, users)

# ---------- MAIN PAGE ----------
st.title("🤖 PrinceAI Ultra Offline - Full Platform")
tabs = st.tabs(["Home","Chat","Teach AI","Voice Chat","Progress","Dashboard"])

# --- HOME ---
with tabs[0]:
    st.header("Welcome 👋")
    st.write("Offline AI tutor with memory, scoring, voice chat, analytics, achievements, and user profiles!")

# --- CHAT ---
with tabs[1]:
    st.header("💬 Chat")
    user_input = st.text_input("Type your message")
    if user_input:
        answer = get_answer(user_input)
        timestamp = datetime.now().isoformat()
        st.session_state.chat_history.append(("You", user_input, timestamp))
        st.session_state.chat_history.append(("Bot", answer, timestamp))
        if isinstance(answer, str) and "don't know" not in answer.lower():
            st.session_state.score += 1
        if st.session_state.username:
            users[st.session_state.username]["score"] = st.session_state.score
            users[st.session_state.username]["history"] = st.session_state.chat_history
            users[st.session_state.username]["sessions"].append(timestamp)
            save_json(USERS_FILE, users)
        check_achievements()

    # Render chat history with scrollable boxes
    for speaker, msg, _ in st.session_state.chat_history:
        align = "right" if speaker == "You" else "left"
        color = "#DCF8C6" if speaker == "You" else "#F1F0F0"
        st.markdown(f"""
        <div style='
            text-align: {align};
            background: {color};
            padding: 10px;
            border-radius: 10px;
            margin: 5px;
            max-height: 200px;
            overflow: auto;
            white-space: pre-wrap;
            font-family: Arial, sans-serif;
        '>{msg}</div>
        """, unsafe_allow_html=True)

    # Auto-complete / suggestions
    if user_input:
        suggestions = get_suggestions(user_input)
        if suggestions:
            st.caption("Suggestions: " + ", ".join(suggestions))

# --- TEACH AI ---
with tabs[2]:
    st.header("🧠 Teach AI")
    teach_q = st.text_input("Teach: What should I learn?")
    teach_a = st.text_input("Answer:")
    if st.button("➕ Add Knowledge"):
        if teach_q and teach_a:
            learned_knowledge[teach_q.lower()] = teach_a
            save_json(KNOWLEDGE_FILE, learned_knowledge)
            st.success("I have learned it!")
            check_achievements()

# --- VOICE CHAT ---
with tabs[3]:
    st.header("🎤 Voice Chat")
    if st.button("Record Question"):
        r = sr.Recognizer()
        with sr.Microphone() as source:
            st.info("Listening...")
            audio = r.listen(source, phrase_time_limit=10)
        try:
            voice_input = r.recognize_google(audio)
            st.write(f"You said: {voice_input}")
            answer = get_answer(voice_input)
            st.success(answer)
            timestamp = datetime.now().isoformat()
            st.session_state.chat_history.append(("You", voice_input, timestamp))
            st.session_state.chat_history.append(("Bot", answer, timestamp))
            tts = gTTS(answer)
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tts.save(tfile.name)
            st.audio(tfile.name, format="audio/mp3")
            if st.session_state.username:
                users[st.session_state.username]["score"] = st.session_state.score
                users[st.session_state.username]["history"] = st.session_state.chat_history
                users[st.session_state.username]["sessions"].append(timestamp)
                save_json(USERS_FILE, users)
            check_achievements()
        except:
            st.warning("Could not understand audio")

# --- PROGRESS ---
with tabs[4]:
    st.header("📊 Your Progress")
    st.write(f"Score: {st.session_state.score}")
    st.subheader("Achievements")
    if st.session_state.achievements:
        for a in st.session_state.achievements:
            st.write(f"🏅 {a}")
    else:
        st.write("No achievements yet.")
    st.subheader("Learned Topics")
    if learned_knowledge:
        for k in learned_knowledge.keys():
            st.write(f"✔️ {k.title()}")
    else:
        st.write("No topics learned yet.")
    st.subheader("Chat History Timeline")
    if st.session_state.chat_history:
        df_history = pd.DataFrame(st.session_state.chat_history, columns=["Speaker","Message","Timestamp"])
        df_history["Timestamp"] = pd.to_datetime(df_history["Timestamp"])
        st.dataframe(df_history.sort_values(by="Timestamp", ascending=False))
    else:
        st.write("No chats yet.")

# --- DASHBOARD ---
with tabs[5]:
    st.header("📈 Dashboard & Analytics")
    if st.session_state.username:
        user_data = users.get(st.session_state.username, {})
        st.subheader("Score & Achievements")
        st.write(f"Total Score: {user_data.get('score',0)}")
        if user_data.get("achievements"):
            st.write("🏅 Achievements:")
            for a in user_data["achievements"]:
                st.write(f"- {a}")
        else:
            st.write("No achievements yet.")

        st.subheader("Session Timeline")
        sessions = user_data.get("sessions", [])
        if sessions:
            session_times = pd.to_datetime(sessions)
            session_df = pd.DataFrame({"Session Start": session_times})
            st.line_chart(session_df.index.value_counts())
            session_df["Date"] = session_df["Session Start"].dt.date
            daily_counts = session_df.groupby("Date").size()
            st.subheader("Daily Stats")
            st.bar_chart(daily_counts)
            session_df["Week"] = session_df["Session Start"].dt.to_period('W').apply(lambda r: r.start_time)
            weekly_counts = session_df.groupby("Week").size()
            st.subheader("Weekly Stats")
            st.bar_chart(weekly_counts)
        else:
            st.write("No sessions recorded yet.")

        st.subheader("Knowledge Growth")
        topics_learned = list(learned_knowledge.keys())
        if topics_learned:
            growth_df = pd.DataFrame(
                {"Topics Learned": range(1,len(topics_learned)+1)},
                index=pd.date_range(end=datetime.today(), periods=len(topics_learned))
            )
            st.line_chart(growth_df)
        else:
            st.write("No topics learned yet.")
    else:
        st.info("Login to see your Dashboard and Stats")