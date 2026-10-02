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

# カスタムCSS（ボタン風UIとアプリ風デザイン）
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

# --- メインタブ：入力フォームとログ ---
tab_input, tab_log = st.tabs(["📝 ハウス設定・記録", "📋 ログ閲覧"])

# --- 1. ハウス設定・記録タブ ---
with tab_input:
    st.subheader("⚙️ ハウス設定変更")
    
    # 群切り替え用サブタブ（D群 / パイプハウス）
    group_d, group_pipe = st.tabs(["🏢 D群", "🏠 パイプハウス"])
    
    # 各群ごとの入力処理を関数化
    def render_setting_form(group_name, house_list, key_prefix):
        with st.form(f"setting_form_{key_prefix}", clear_on_submit=True):
            
            # ハウス選択
            greenhouse_name = st.selectbox(
                f"📍 対象ハウス ({group_name})", 
                house_list
            )
            
            st.write("---")
            
            # ボタン切替項目
            shading = st.segmented_control(
                "☀️ 遮光カーテン",
                options=["開け", "閉め", "9-15", "10-14"],
                default="開け"
            )
            
            boiler_status = st.segmented_control(
                "🔥 ボイラー状態",
                options=["停止中", "稼働中", "自動"],
                default="停止中"
            )
            
            side_window = st.segmented_control(
                "🪟 サイド開閉",
                options=["全開", "半開", "全閉"],
                default="全閉"
            )
            
            st.write("---")
            
            # 温度入力
            col_b, col_w = st.columns(2)
            with col_b:
                boiler_temp = st.number_input("ボイラー設定温度 (°C)", value=20.0, step=0.5, key=f"b_{key_prefix}")
            with col_w:
                window_temp = st.number_input("天側窓設定温度 (°C)", value=22.0, step=0.5, key=f"w_{key_prefix}")
                
            submitted = st.form_submit_button("設定をスプレッドシートに保存")
            
            if submitted:
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
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

    # D群タブの中身
    with group_d:
        d_houses = ["D-7", "D-8", "D-9", "D-15", "D-21", "D-23", "D-24", "D-25", "D-26", "D-27"]
        render_setting_form("D群", d_houses, "group_d")

    # パイプハウスタブの中身
    with group_pipe:
        # ※パイプハウス側のハウス名リストは実際の名称に変更してください
        pipe_houses = ["パイプ1号", "パイプ2号", "パイプ3号", "パイプ4号", "パイプ5号"]
        render_setting_form("パイプハウス", pipe_houses, "group_pipe")

# --- 2. ログ閲覧タブ ---
with tab_log:
    st.subheader("📋 最新の設定・測定ログ")
    
    try:
        data = worksheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
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
