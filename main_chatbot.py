# =========================================================
# AI CHATBOT WITH DATA INTEGRATION
# CHATBOT FIRST DESIGN
# =========================================================

import streamlit as st
import pandas as pd
import sqlite3
import requests
from datetime import datetime
import tempfile
import os
import re

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

# =========================================================
# API CONFIG (NO UI)
# =========================================================

PRIMARY_API_KEY = st.secrets["OPENROUTER_PRIMARY_API_KEY"]
BACKUP_API_KEY = st.secrets["OPENROUTER_BACKUP_API_KEY"]

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
        "🗄️ SQLite / SQL"
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
# SQLITE / SQL UPLOAD
# =========================================================

elif data_source == "🗄️ SQLite / SQL":

    st.sidebar.subheader("🗄️ SQLite / SQL Database")

    uploaded_db = st.sidebar.file_uploader(
        "Pilih file database",
        type=["db", "sqlite", "sqlite3", "sql"]
    )

    if uploaded_db:

        file_extension = uploaded_db.name.split(".")[-1].lower()

        # =====================================================
        # HANDLE SQLITE DATABASE
        # =====================================================

        if file_extension in ["db", "sqlite", "sqlite3"]:

            with open("temp.db", "wb") as f:
                f.write(uploaded_db.read())

            conn = sqlite3.connect("temp.db")

            tables = pd.read_sql(
                "SELECT name FROM sqlite_master WHERE type='table';",
                conn
            )

            table_list = tables["name"].tolist()

            if len(table_list) > 0:

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

                    st.sidebar.success("✅ Database berhasil dibaca!")
                    st.sidebar.info(
                        f"📊 Data: {df.shape[0]} baris, {df.shape[1]} kolom"
                    )

            else:
                st.sidebar.warning("⚠️ Tidak ada tabel ditemukan.")

        # =====================================================
        # HANDLE SQL FILE
        # =====================================================

        elif file_extension == "sql":

            try:

                sql_content = uploaded_db.read().decode("utf-8", errors="ignore")
                sql_content = sql_content.replace("\r\n", "\n").replace("\r", "\n")

                # =====================================================
                # CLEAN MYSQL DUMP FOR SQLITE
                # =====================================================
                
                sql_content = re.sub(r"/\*![\s\S]*?\*/", "", sql_content)
                
                # Remove MySQL-specific syntax
                patterns_to_remove = [
                    r"ENGINE=\w+",
                    r"DEFAULT CHARSET=\w+",
                    r"CHARSET=\w+",
                    r"COLLATE\s*=\s*\w+",
                    r"COLLATE\s+\w+",
                    r"AUTO_INCREMENT=\d+",
                    r"UNSIGNED",
                    r"unsigned",
                    r"ROW_FORMAT=\w+"
                ]
                
                for pattern in patterns_to_remove:
                    sql_content = re.sub(
                        pattern,
                        "",
                        sql_content,
                        flags=re.IGNORECASE
                    )
                
                # Remove backticks
                sql_content = sql_content.replace("`", "")
                
                cleaned_lines = []
                
                for line in sql_content.split("\n"):
                
                    stripped = line.strip()
                
                    if not stripped:
                        continue
                
                    upper = stripped.upper()
                
                    # Skip unsupported MySQL commands
                    skip_keywords = [
                        "SET ",
                        "START TRANSACTION",
                        "COMMIT",
                        "LOCK TABLES",
                        "UNLOCK TABLES",
                        "DELIMITER",
                        "--",
                        "/*"
                    ]
                
                    should_skip = False
                
                    for keyword in skip_keywords:
                
                        if upper.startswith(keyword):
                            should_skip = True
                            break
                
                    if should_skip:
                        continue
                
                    # Remove KEY indexes but KEEP PRIMARY KEY
                    if (
                        upper.startswith("KEY ")
                        or upper.startswith("UNIQUE KEY")
                        or upper.startswith("FULLTEXT KEY")
                        or upper.startswith("SPATIAL KEY")
                    ):
                
                        # Remove trailing comma safely
                        if stripped.endswith(","):
                            continue
                        else:
                            continue
                
                    cleaned_lines.append(stripped)
                
                sql_content = "\n".join(cleaned_lines)
                
                # Fix comma before PRIMARY KEY
                sql_content = sql_content.replace(",\nPRIMARY KEY", "\nPRIMARY KEY")
                conn = sqlite3.connect("temp_sql.db")

                conn.executescript(sql_content)

                tables = pd.read_sql(
                    "SELECT name FROM sqlite_master WHERE type='table';",
                    conn
                )

                table_list = tables["name"].tolist()

                if len(table_list) > 0:

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

                        st.sidebar.success("✅ File SQL berhasil diimport!")
                        st.sidebar.info(
                            f"📊 Data: {df.shape[0]} baris, {df.shape[1]} kolom"
                        )

                else:
                    st.sidebar.warning("⚠️ Tidak ada tabel ditemukan.")

            except Exception as e:
                st.sidebar.error(f"❌ SQL Error: {str(e)}")
                
# =========================================================
# DATA STATUS
# =========================================================

st.sidebar.markdown("---")

if st.session_state.df is not None:

    st.sidebar.success("✅ Data Aktif")

    with st.sidebar.expander("👀 Preview Data"):
        st.dataframe(
            st.session_state.df.head(),
            use_container_width=True
        )

else:
    st.sidebar.warning("⚠️ Belum Ada Data")

# =========================================================
# MAIN PAGE - CHATBOT
# =========================================================

st.title("🤖 AI Chatbot Assistant")

# =========================================================
# GREETING MESSAGE
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

user_input = st.chat_input(
    "Tanyakan sesuatu tentang data Anda..."
)

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

    # Assistant response
    with st.chat_message("assistant"):

        message_placeholder = st.empty()

        # =====================================================
        # BUILD DATA CONTEXT
        # =====================================================

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

Berikan respon yang membantu.
Jika pertanyaan terkait data, ingatkan user untuk upload data terlebih dahulu.
"""

        with st.spinner("🤔 Berpikir..."):

            response = ask_llm(full_prompt)

        message_placeholder.markdown(response)

    # Save assistant response
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
        st.caption(
            f"📊 Data: {st.session_state.df.shape[0]} baris"
        )

    else:
        st.caption("⚠️ Belum ada data")

with col3:
    st.caption("© 2024")
