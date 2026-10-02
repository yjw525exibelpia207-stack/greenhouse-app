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

# カスタムCSS（スマホ・AppSheet風UI）
st.markdown("""
<style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 3rem;
        max-width: 500px;
    }
    /* アプリ風メインボタン */
    div.stButton > button {
        border-radius: 10px;
        font-weight: bold;
    }
    /* 保存ボタン */
    .save-btn > button {
        width: 100%;
        height: 3.2em;
        background-color: #2e7d32 !important;
        color: white !important;
        font-size: 1.1rem !important;
        border: none !important;
        margin-top: 15px;
    }
    /* 戻るボタン */
    .back-btn > button {
        background-color: #666666 !important;
        color: white !important;
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
    
    # 既存データの読み込み
    records = worksheet.get_all_records()
    df_raw = pd.DataFrame(records) if records else pd.DataFrame()
except Exception as e:
    st.error(f"⚠️ 接続エラーが発生しました: {e}")
    st.stop()

# --- 選択中ハウスのステート管理 ---
if "selected_house" not in st.session_state:
    st.session_state.selected_house = None

# スプレッドシートから実際に入力されている温室名を取得
if not df_raw.empty and "温室" in df_raw.columns:
    all_greenhouses = [str(x) for x in df_raw["温室"].unique() if str(x).strip() != ""]
else:
    all_greenhouses = ["D-7", "D-8", "D-9", "D-15", "D-21", "D-23", "D-24", "D-25", "D-26", "D-27", "パイプ1号", "パイプ2号"]

# D群とパイプハウスに自動振り分け
d_houses = [h for h in all_greenhouses if "D" in h or "d" in h]
pipe_houses = [h for h in all_greenhouses if h not in d_houses]

if not d_houses:
    d_houses = ["D-7", "D-8", "D-9", "D-15", "D-21", "D-23", "D-24", "D-25", "D-26", "D-27"]
if not pipe_houses:
    pipe_houses = ["パイプ1号", "パイプ2号", "パイプ3号"]

# --- メインタブ：入力/選択とログ ---
tab_main, tab_log = st.tabs(["🏡 ハウス選択・設定", "📋 ログ閲覧"])

# --- 1. ハウス選択・設定タブ ---
with tab_main:
    
    # 【パターンA】ハウスが未選択の場合：一覧ボタン画面を表示
    if st.session_state.selected_house is None:
        st.subheader("📍 操作するハウスを選択してください")
        
        tab_list_d, tab_list_pipe = st.tabs(["🏢 D群", "🏠 パイプハウス"])
        
        # ハウス一覧をグリッド状の押しやすい大ボタンで表示する関数
        def render_house_grid(house_list, prefix):
            cols = st.columns(2)  # 2列並びのボタン
            for idx, house in enumerate(house_list):
                col = cols[idx % 2]
                with col:
                    if st.button(f"🏠 {house}", key=f"btn_{prefix}_{house}", use_container_width=True):
                        st.session_state.selected_house = house
                        st.rerun()

        with tab_list_d:
            render_house_grid(d_houses, "d")

        with tab_list_pipe:
            render_house_grid(pipe_houses, "pipe")

    # 【パターンB】ハウスが選択されている場合：設定画面を表示
    else:
        house = st.session_state.selected_house
        
        # 戻るボタン
        st.markdown('<div class="back-btn">', unsafe_allow_html=True)
        if st.button("⬅️ ハウス一覧に戻る", use_container_width=True):
            st.session_state.selected_house = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.subheader(f"⚙️ {house} の設定変更")
        
        with st.form("house_detail_form", clear_on_submit=True):
            
            # 設定項目のボタン切替
            side_window = st.segmented_control(
                "🪟 サイド開閉",
                options=["全開", "半開", "全閉", "-"],
                default="全閉"
            )
            
            shading = st.segmented_control(
                "☀️ 遮光カーテン",
                options=["開け", "閉め", "9-15", "10-14", "-"],
                default="開け"
            )
            
            boiler_status = st.segmented_control(
                "🔥 ボイラー状態",
                options=["停止中", "稼働中", "自動", "-"],
                default="停止中"
            )
            
            st.write("---")
            
            # 各種温度設定（数値入力）
            col1, col2 = st.columns(2)
            with col1:
                boiler_temp = st.number_input("ボイラー設定温度 (°C)", value=15.0, step=0.5)
            with col2:
                window_temp = st.number_input("天側窓設定温度 (°C)", value=20.0, step=0.5)
                
            col3, col4 = st.columns(2)
            with col3:
                upper_window_temp = st.number_input("上段開閉温度 (°C)", value=22.0, step=0.5)
            with col4:
                dehumidifier = st.segmented_control(
                    "💧 除湿機",
                    options=["稼働", "停止", "-"],
                    default="-"
                )
            
            # 保存ボタン
            st.markdown('<div class="save-btn">', unsafe_allow_html=True)
            submitted = st.form_submit_button(f"【{house}】の設定を保存")
            st.markdown('</div>', unsafe_allow_html=True)
            
            if submitted:
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                row_data = {
                    "温室": house,
                    "サイド開閉": side_window,
                    "遮光": shading,
                    "ボイラー状態": boiler_status,
                    "ボイラー温度": boiler_temp,
                    "天側窓温度": window_temp,
                    "上段開閉温度": upper_window_temp,
                    "除湿機": dehumidifier,
                    "最終入力者": "Webアプリ",
                    "更新日時": now_str
                }
                
                if not df_raw.empty:
                    headers = list(df_raw.columns)
                    new_row = [row_data.get(col, "-") for col in headers]
                else:
                    new_row = list(row_data.values())

                worksheet.append_row(new_row)
                st.success(f"✅ {house} の設定を更新しました！")

# --- 2. ログ閲覧タブ ---
with tab_log:
    st.subheader("📋 最新の設定・測定ログ")
    
    if not df_raw.empty:
        log_tab_d, log_tab_pipe = st.tabs(["🏢 D群 ログ", "🏠 パイプハウス ログ"])
        
        df_reversed = df_raw.iloc[::-1].reset_index(drop=True)
        
        with log_tab_d:
            if "温室" in df_reversed.columns:
                df_d = df_reversed[df_reversed["温室"].astype(str).isin(d_houses)]
            else:
                df_d = df_reversed
                
            if not df_d.empty:
                st.dataframe(df_d, use_container_width=True, hide_index=True)
            else:
                st.info("D群のデータがありません。")
                
        with log_tab_pipe:
            if "温室" in df_reversed.columns:
                df_pipe = df_reversed[df_reversed["温室"].astype(str).isin(pipe_houses)]
            else:
                df_pipe = df_reversed
                
            if not df_pipe.empty:
                st.dataframe(df_pipe, use_container_width=True, hide_index=True)
            else:
                st.info("パイプハウスのデータがありません。")
    else:
        st.info("データがありません。")
