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

# カスタムCSS（スマホ最適化デザイン）
st.markdown("""
<style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 3rem;
        max-width: 500px;
    }
    div.stButton > button:first-child {
        width: 100%;
        border-radius: 12px;
        height: 3.2em;
        background-color: #2e7d32;
        color: white;
        font-weight: bold;
        font-size: 1.1rem;
        border: none;
        margin-top: 15px;
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
    
    # 既存データの読み込み
    records = worksheet.get_all_records()
    df_raw = pd.DataFrame(records) if records else pd.DataFrame()
except Exception as e:
    st.error(f"⚠️ 接続エラーが発生しました: {e}")
    st.stop()

# --- メインタブ：入力フォームとログ ---
tab_input, tab_log = st.tabs(["📝 ハウス設定・記録", "📋 ログ閲覧"])

# スプレッドシートから実際に入力されている温室名を取得
if not df_raw.empty and "温室" in df_raw.columns:
    all_greenhouses = [str(x) for x in df_raw["温室"].unique() if str(x).strip() != ""]
else:
    all_greenhouses = ["D-7", "D-8", "D-9", "D-15", "D-21", "D-23", "D-24", "D-25", "D-26", "D-27", "パイプ1号", "パイプ2号"]

# D群とパイプハウスに振り分け（「D」が含まれるかどうか）
d_houses = [h for h in all_greenhouses if "D" in h or "d" in h]
pipe_houses = [h for h in all_greenhouses if h not in d_houses]

if not d_houses:
    d_houses = all_greenhouses
if not pipe_houses:
    pipe_houses = ["パイプハウス1", "パイプハウス2"]


# --- 1. ハウス設定・記録タブ ---
with tab_input:
    st.subheader("⚙️ ハウス設定変更")

    # 群切り替え用サブタブ
    group_d, group_pipe = st.tabs(["🏢 D群", "🏠 パイプハウス"])
    
    def render_setting_form(group_name, house_list, key_prefix):
        with st.form(f"setting_form_{key_prefix}", clear_on_submit=True):
            
            # 1. 実際の温室名から選択
            greenhouse_name = st.selectbox(
                f"📍 対象ハウス ({group_name})", 
                house_list
            )
            
            st.write("---")
            
            # 2. 設定項目のボタン切替
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
            
            # 3. 各種温度設定（数値入力）
            col1, col2 = st.columns(2)
            with col1:
                boiler_temp = st.number_input("ボイラー設定温度 (°C)", value=15.0, step=0.5, key=f"b_{key_prefix}")
            with col2:
                window_temp = st.number_input("天側窓設定温度 (°C)", value=20.0, step=0.5, key=f"w_{key_prefix}")
                
            col3, col4 = st.columns(2)
            with col3:
                upper_window_temp = st.number_input("上段開閉温度 (°C)", value=22.0, step=0.5, key=f"uw_{key_prefix}")
            with col4:
                dehumidifier = st.segmented_control(
                    "💧 除湿機",
                    options=["稼働", "停止", "-"],
                    default="-",
                    key=f"dh_{key_prefix}"
                )
            
            # 送信ボタン
            submitted = st.form_submit_button("設定をスプレッドシートに保存")
            
            if submitted:
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # スプレッドシートの1行目の列名に合わせて dictionary を作成
                row_data = {
                    "温室": greenhouse_name,
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
                
                # スプレッドシートの実際のヘッダー列順に合わせて並べ替えて追加
                if not df_raw.empty:
                    headers = list(df_raw.columns)
                    new_row = [row_data.get(col, "-") for col in headers]
                else:
                    new_row = list(row_data.values())

                worksheet.append_row(new_row)
                st.success(f"✅ {greenhouse_name} の設定を更新しました！")

    # D群タブ
    with group_d:
        render_setting_form("D群", d_houses, "group_d")

    # パイプハウスタブ
    with group_pipe:
        render_setting_form("パイプハウス", pipe_houses, "group_pipe")

# --- 2. ログ閲覧タブ ---
with tab_log:
    st.subheader("📋 最新の設定・測定ログ")
    
    if not df_raw.empty:
        # ログ切り替え用サブタブ（D群 / パイプハウス）
        log_tab_d, log_tab_pipe = st.tabs(["🏢 D群 ログ", "🏠 パイプハウス ログ"])
        
        # ログを最新順にソート
        df_reversed = df_raw.iloc[::-1].reset_index(drop=True)
        
        # D群ログ表示処理
        with log_tab_d:
            if "温室" in df_reversed.columns:
                df_d = df_reversed[df_reversed["温室"].astype(str).isin(d_houses)]
            else:
                df_d = df_reversed
                
            if not df_d.empty:
                st.dataframe(df_d, use_container_width=True, hide_index=True)
            else:
                st.info("D群のデータがありません。")
                
        # パイプハウスログ表示処理
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
