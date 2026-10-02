import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime

# ページ基本設定（スマホ表示を最適化）
st.set_page_config(
    page_title="温室管理",
    page_icon="🍇",
    layout="centered",  # スマホで見やすい中央寄せ
    initial_sidebar_state="collapsed"
)

# カスタムCSS（AppSheet風のUIデザイン適用）
st.markdown("""
<style>
    /* 全体の余白調整 */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 500px;
    }
    /* ボタンのアプリ風デザイン */
    .stButton > button {
        width: 100%;
        border-radius: 12px;
        height: 3em;
        background-color: #2e7d32;
        color: white;
        font-weight: bold;
        border: none;
    }
    /* カード風コンテナ */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Googleスプレッドシートへの接続設定
@st.cache_resource
def init_connection():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    service_account_info = dict(st.secrets["gcp_service_account"])
    if "private_key" in service_account_info:
        service_account_info["private_key"] = service_account_info["private_key"].replace("\\n", "\n")
        
    creds = Credentials.from_service_account_info(
        service_account_info,
        scopes=scope
    )
    return gspread.authorize(creds)

try:
    gc = init_connection()
    sh = gc.open("温室管理")
    worksheet = sh.get_worksheet(0)
except Exception as e:
    st.error(f"⚠️ 接続エラーが発生しました: {e}")
    st.stop()

# --- AppSheet風タブナビゲーション ---
tab_input, tab_log = st.tabs(["📝 温度入力", "📋 ログ閲覧"])

# --- 1. 温度入力タブ ---
with tab_input:
    st.subheader("🌡️ 測定値の記録")
    
    with st.form("temp_form", clear_on_submit=True):
        # 温室選択
        greenhouse_name = st.selectbox(
            "対象温室", 
            ["D-7", "D-8", "D-9", "D-15", "D-21", "D-23", "D-24", "D-25", "D-26", "D-27"]
        )
        
        col_b, col_w = st.columns(2)
        with col_b:
            boiler_temp = st.number_input("ボイラー温度 (°C)", value=20.0, step=0.5)
        with col_w:
            window_temp = st.number_input("天側窓温度 (°C)", value=22.0, step=0.5)
            
        submitted = st.form_submit_button("保存する")
        
        if submitted:
            temp_diff = window_temp - boiler_temp
            status = "⚠️ 異常 (<5°C)" if temp_diff < 5.0 else "正常"
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # スプレッドシート追加（既存列に合わせて設定）
            new_row = [greenhouse_name, "-", "-", "停止中", boiler_temp, window_temp, "-", "Webユーザー", now_str]
            worksheet.append_row(new_row)
            st.success("✅ スプレッドシートへ保存しました！")

# --- 2. ログ閲覧タブ ---
with tab_log:
    st.subheader("📋 最新の測定データ")
    
    try:
        data = worksheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            # アプリっぽく直近のデータを上に表示
            df_reversed = df.iloc[::-1].reset_index(drop=True)
            
            st.dataframe(
                df_reversed,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("データがありません。")
    except Exception as e:
        st.warning("データの読み込みに失敗しました。")
