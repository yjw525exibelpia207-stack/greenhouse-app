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
    div.stButton > button {
        border-radius: 10px;
        font-weight: bold;
    }
    .save-btn > button {
        width: 100%;
        height: 3.2em;
        background-color: #2e7d32 !important;
        color: white !important;
        font-size: 1.1rem !important;
        border: none !important;
        margin-top: 15px;
    }
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

# 各温室の最新設定を取得する関数
def get_latest_status(house_list):
    if df_raw.empty or "温室" not in df_raw.columns:
        # データがない場合でも温室一覧の枠を作成
        return pd.DataFrame({"温室": house_list})
    
    latest_rows = []
    for h in house_list:
        house_data = df_raw[df_raw["温室"].astype(str) == str(h)]
        if not house_data.empty:
            latest_rows.append(house_data.iloc[-1])
        else:
            latest_rows.append({"温室": h})
            
    df_latest = pd.DataFrame(latest_rows)
    cols_to_show = [c for c in df_latest.columns if c not in ["最終入力者"]]
    return df_latest[cols_to_show]

# --- メインタブ：現在設定一覧と全ログ ---
tab_main, tab_log = st.tabs(["📊 現在の設定一覧", "📋 全履歴ログ"])

# --- 1. 現在の設定一覧タブ ---
with tab_main:
    
    # 【パターンA】ハウス未選択：各ハウスの最新設定表（行選択で画面遷移）
    if st.session_state.selected_house is None:
        st.subheader("📍 各ハウスの現在設定")
        st.caption("👇 **表の中の行（ハウス）をタップ** すると設定変更画面に進みます")
        
        tab_status_d, tab_status_pipe = st.tabs(["🏢 D群", "🏠 パイプハウス"])
        
        def render_interactive_table(house_list, key_prefix):
            df_latest = get_latest_status(house_list)
            
            # st.dataframe の行選択を有効化 (selection_mode="single-row")
            event = st.dataframe(
                df_latest,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key=f"table_{key_prefix}"
            )
            
            # 行がタップされた場合の処理
            selected_rows = event.selection.get("rows", [])
            if selected_rows:
                selected_index = selected_rows[0]
                house_name = str(df_latest.iloc[selected_index]["温室"])
                st.session_state.selected_house = house_name
                st.rerun()

        with tab_status_d:
            render_interactive_table(d_houses, "d")

        with tab_status_pipe:
            render_interactive_table(pipe_houses, "pipe")

    # 【パターンB】ハウス選択済み：設定変更フォーム
    else:
        house = st.session_state.selected_house
        
        # 戻るボタン
        st.markdown('<div class="back-btn">', unsafe_allow_html=True)
        if st.button("⬅️ 設定一覧に戻る", use_container_width=True):
            st.session_state.selected_house = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.subheader(f"⚙️ {house} の設定変更")
        
        # 選択したハウスの最新設定を取得して初期値に反映
        house_latest = df_raw[df_raw["温室"].astype(str) == str(house)] if not df_raw.empty else pd.DataFrame()
        latest_val = house_latest.iloc[-1] if not house_latest.empty else {}
        
        with st.form("house_detail_form", clear_on_submit=True):
            
            curr_side = str(latest_val.get("サイド開閉", "全閉"))
            side_window = st.segmented_control(
                "🪟 サイド開閉",
                options=["全開", "半開", "全閉", "-"],
                default=curr_side if curr_side in ["全開", "半開", "全閉", "-"] else "全閉"
            )
            
            curr_shading = str(latest_val.get("遮光", "開け"))
            shading = st.segmented_control(
                "☀️ 遮光カーテン",
                options=["開け", "閉め", "9-15", "10-14", "-"],
                default=curr_shading if curr_shading in ["開け", "閉め", "9-15", "10-14", "-"] else "開け"
            )
            
            curr_boiler = str(latest_val.get("ボイラー状態", "停止中"))
            boiler_status = st.segmented_control(
                "🔥 ボイラー状態",
                options=["停止中", "稼働中", "自動", "-"],
                default=curr_boiler if curr_boiler in ["停止中", "稼働中", "自動", "-"] else "停止中"
            )
            
            st.write("---")
            
            def safe_float(val, default):
                try: return float(val)
                except: return default

            col1, col2 = st.columns(2)
            with col1:
                b_val = safe_float(latest_val.get("ボイラー温度"), 15.0)
                boiler_temp = st.number_input("ボイラー設定温度 (°C)", value=b_val, step=0.5)
            with col2:
                w_val = safe_float(latest_val.get("天側窓温度"), 20.0)
                window_temp = st.number_input("天側窓設定温度 (°C)", value=w_val, step=0.5)
                
            col3, col4 = st.columns(2)
            with col3:
                uw_val = safe_float(latest_val.get("上段開閉温度"), 22.0)
                upper_window_temp = st.number_input("上段開閉温度 (°C)", value=uw_val, step=0.5)
            with col4:
                curr_dh = str(latest_val.get("除湿機", "-"))
                dehumidifier = st.segmented_control(
                    "💧 除湿機",
                    options=["稼働", "停止", "-"],
                    default=curr_dh if curr_dh in ["稼働", "停止", "-"] else "-"
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
                st.session_state.selected_house = None  # 保存後は一覧へ復帰
                st.success(f"✅ {house} の設定を更新しました！")
                st.rerun()

# --- 2. ログ閲覧タブ ---
with tab_log:
    st.subheader("📋 最新の設定・測定ログ（全履歴）")
    
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
