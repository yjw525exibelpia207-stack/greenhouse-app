import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime

# ページ基本設定（スマホ表示最適化）
st.set_page_config(
    page_title="温室管理",
    page_icon="🍇",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# カスタムCSS（ボタン風ラジオボタンとアプリ風デザイン）
st.markdown("""
<style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 3rem;
        max-width: 500px;
    }
    /* 保存ボタンのデザイン */
    div.stButton > button:first-child {
        width: 100%;
        border-radius: 12px;
        height: 3.2em;
        background-color: #2e7d32;
        color: white;
        font-weight: bold;
        font-size: 1.1rem;
        border: none;
        margin-top: 10px;
    }
    /* ラジオボタンをアプリ風ボタン化 */
    div[data-testid="stMarkdownContainer"] > p {
        font-weight: bold;
        margin-bottom: 0.2rem;
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
tab_input, tab_log = st.tabs(["📝 ハウス設定・記録", "📋 ログ閲覧"])

# --- 1. ハウス設定・記録タブ ---
with tab_input:
    st.subheader("⚙️ ハウス設定変更")
    
    with st.form("house_setting_form", clear_on_submit=True):
        
        # 1. 対象ハウス選択（セレクトボックス）
        greenhouse_name = st.selectbox(
            "📍 対象ハウス", 
            ["D-7", "D-8", "D-9", "D-15", "D-21", "D-23", "D-24", "D-25", "D-26", "D-27"]
        )
        
        st.write("---")
        
        # 2. ボタンで切替：遮光設定
        shading = st.segmented_control(
            "☀️ 遮光カーテン",
            options=["開け", "閉め", "9-15", "10-14"],
            default="開け"
        )
        
        # 3. ボタンで切替：ボイラー状態
        boiler_status = st.segmented_control(
            "🔥 ボイラー状態",
            options=["停止中", "稼働中", "自動"],
            default="停止中"
        )
        
        # 4. ボタンで切替：サイド開閉
        side_window = st.segmented_control(
            "🪟 サイド開閉",
            options=["全開", "半開", "全閉"],
            default="全閉"
        )
        
        st.write("---")
        
        # 温度入力
        col_b, col_w = st.columns(2)
        with col_b:
            boiler_temp = st.number_input("ボイラー設定温度 (°C)", value=20.0, step=0.5)
        with col_w:
            window_temp = st.number_input("天側窓設定温度 (°C)", value=22.0, step=0.5)
            
        # 送信ボタン
        submitted = st.form_submit_button("設定をスプレッドシートに保存")
        
        if submitted:
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # スプレッドシートへ書き込み（列順: 温室, サイド開閉, 遮光, ボイラー状態, ボイラー温度, 天側窓温度, 除湿機, 最終入力者, 更新日時）
            new_row = [
                greenhouse_name,
                side_window,
                shading,
                boiler_status,
                boiler_temp,
                window_temp,
                "-",
                "Webアプリ",
                now_str
            ]
            worksheet.append_row(new_row)
            st.success(f"✅ {greenhouse_name} の設定を更新しました！")

# --- 2. ログ閲覧タブ ---
with tab_log:
    st.subheader("📋 最新の設定・測定ログ")
    
    try:
        data = worksheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            # 直近のデータを上に表示
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
