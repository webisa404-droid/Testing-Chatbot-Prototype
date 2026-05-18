# =========================================================
# AI CHATBOT WITH DATA INTEGRATION
# CHATBOT FIRST DESIGN
# =========================================================

import streamlit as st
import pandas as pd
import sqlite3
import pymysql
from sqlalchemy import create_engine
import requests
from datetime import datetime

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="AI Chatbot Assistant",
    page_icon="🤖",
    layout="wide"
)

# =========================================================
# SESSION STATE
# =========================================================

if "df" not in st.session_state:
    st.session_state.df = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "first_load" not in st.session_state:
    st.session_state.first_load = True
# 
# =========================================================
# API CONFIG (NO UI)
# =========================================================

PRIMARY_API_KEY = "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"
BACKUP_API_KEY = "ISI_API_KEY_CADANGAN"

MODEL_NAME = "openai/gpt-oss-20b:free"

# =========================================================
# LLM FUNCTION
# =========================================================

def ask_llm(prompt):
    
    api_keys = [
        PRIMARY_API_KEY,
        BACKUP_API_KEY
    ]

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": """
                Kamu adalah AI Data Assistant yang ramah dan profesional.
                Tugasmu membantu user membaca, mencari, mengedit, dan menganalisis data.
                Berikan respon yang jelas, ringkas, dan membantu.
                """
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    for api_key in api_keys:

        try:

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:

                result = response.json()

                return result["choices"][0]["message"]["content"]

        except:
            continue

    return "❌ Semua API gagal. Silakan coba lagi."

# =========================================================
# SIDEBAR - DATA INPUT
# =========================================================

st.sidebar.title("📥 Data Management")
st.sidebar.markdown("---")

# Menu untuk pilih sumber data
data_source = st.sidebar.selectbox(
    "Pilih Sumber Data",
    [
        "-- Tidak Ada --",
        "📂 Upload CSV",
        "🗄️ SQLite",
        "🐬 MySQL"
    ],
    key="data_source"
)

# =========================================================
# CSV UPLOAD
# =========================================================

if data_source == "📂 Upload CSV":

    st.sidebar.subheader("📂 Upload CSV")

    uploaded_file = st.sidebar.file_uploader(
        "Pilih file CSV",
        type=["csv"]
    )

    if uploaded_file:

        df = pd.read_csv(uploaded_file)
        st.session_state.df = df

        st.sidebar.success("✅ CSV berhasil diupload!")
        st.sidebar.info(f"📊 Data: {df.shape[0]} baris, {df.shape[1]} kolom")

# =========================================================
# SQLITE UPLOAD
# =========================================================

elif data_source == "🗄️ SQLite":

    st.sidebar.subheader("🗄️ SQLite Database")

    sqlite_file = st.sidebar.file_uploader(
        "Pilih file SQLite",
        type=["db", "sqlite", "sqlite3"]
    )

    if sqlite_file:

        with open("temp.db", "wb") as f:
            f.write(sqlite_file.read())

        conn = sqlite3.connect("temp.db")

        tables = pd.read_sql(
            "SELECT name FROM sqlite_master WHERE type='table';",
            conn
        )

        table_list = tables["name"].tolist()

        selected_table = st.sidebar.selectbox(
            "Pilih Tabel",
            table_list
        )

        if selected_table:

            df = pd.read_sql(
                f"SELECT * FROM {selected_table}",
                conn
            )

            st.session_state.df = df

            st.sidebar.success("✅ Data berhasil dibaca!")
            st.sidebar.info(f"📊 Data: {df.shape[0]} baris, {df.shape[1]} kolom")

# =========================================================
# MYSQL UPLOAD
# =========================================================

elif data_source == "🐬 MySQL":

    st.sidebar.subheader("🐬 MySQL Database")

    with st.sidebar.expander("⚙️ Konfigurasi Koneksi"):

        host = st.text_input("Host", "localhost")
        user = st.text_input("Username", "root")
        password = st.text_input("Password", type="password")
        database = st.text_input("Database")

    if st.sidebar.button("🔗 Connect", key="mysql_connect"):

        try:

            engine = create_engine(
                f"mysql+pymysql://{user}:{password}@{host}/{database}"
            )

            tables = pd.read_sql(
                "SHOW TABLES",
                engine
            )

            table_list = tables.iloc[:, 0].tolist()

            selected_table = st.sidebar.selectbox(
                "Pilih Tabel",
                table_list
            )

            if selected_table:

                df = pd.read_sql(
                    f"SELECT * FROM {selected_table}",
                    engine
                )

                st.session_state.df = df

                st.sidebar.success("✅ Berhasil connect!")
                st.sidebar.info(f"📊 Data: {df.shape[0]} baris, {df.shape[1]} kolom")

        except Exception as e:
            st.sidebar.error(f"❌ Error: {str(e)}")

# =========================================================
# DATA STATUS
# =========================================================

st.sidebar.markdown("---")

if st.session_state.df is not None:
    st.sidebar.success("✅ Data Aktif")
    with st.sidebar.expander("👀 Preview Data"):
        st.dataframe(st.session_state.df.head(), use_container_width=True)
else:
    st.sidebar.warning("⚠️ Belum Ada Data")

# =========================================================
# MAIN PAGE - CHATBOT
# =========================================================

st.title("🤖 AI Chatbot Assistant")

# =========================================================
# GREETING MESSAGE (First Load)
# =========================================================

if st.session_state.first_load:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": """👋 **Halo! Saya adalah AI Chatbot Assistant Anda.**

Saya siap membantu Anda dengan:
- 📊 Membaca dan menganalisis data
- 🔍 Mencari informasi spesifik dalam dataset
- 📈 Memberikan insight dari data Anda
- ❓ Menjawab pertanyaan tentang data

**Cara Menggunakan:**
1. Upload atau koneksikan data Anda dari sidebar
2. Tanyakan apa pun tentang data Anda di chat ini
3. Saya akan membantu Anda mendapatkan jawaban yang tepat

Mulai percakapan sekarang! 😊"""
        }
    ]
    st.session_state.first_load = False

# =========================================================
# DISPLAY CHAT MESSAGES
# =========================================================

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# =========================================================
# CHAT INPUT
# =========================================================

user_input = st.chat_input("Tanyakan sesuatu tentang data Anda...")

if user_input:

    # Add user message
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_input
        }
    )

    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)

    # Get AI response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()

        # Build context from dataframe if available
        if st.session_state.df is not None:
            df_preview = st.session_state.df.head(10).to_string()
            full_prompt = f"""
DATASET PREVIEW:
{df_preview}

PERTANYAAN USER:
{user_input}

Silakan analisis data dan berikan jawaban yang jelas dan berguna.
"""
        else:
            full_prompt = f"""
CATATAN: User belum upload data apapun.

PERTANYAAN USER:
{user_input}

Berikan respon yang membantu. Jika pertanyaan terkait data, ingatkan user untuk upload data terlebih dahulu.
"""

        with st.spinner("🤔 Berpikir..."):
            response = ask_llm(full_prompt)

        message_placeholder.markdown(response)

    # Add assistant message to history
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response
        }
    )

# =========================================================
# FOOTER
# =========================================================

st.markdown("---")

col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    st.caption("🤖 AI Chatbot Assistant")

with col2:
    if st.session_state.df is not None:
        st.caption(f"📊 Data: {st.session_state.df.shape[0]} baris")
    else:
        st.caption("⚠️ Belum ada data")

with col3:
    st.caption("© 2024")
