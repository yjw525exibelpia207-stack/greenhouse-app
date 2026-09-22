import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ページ基本設定
st.set_page_config(page_title="温室管理システム", page_icon="🍇", layout="wide")

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
    # スプレッドシート名「温室管理」を開く
    sh = gc.open("温室管理")
    # 1枚目のシートを取得
    worksheet = sh.get_worksheet(0)
    st.sidebar.success("✅ スプレッドシート接続完了")
except Exception as e:
    st.sidebar.error(f"⚠️ 接続エラー: {e}")
    st.stop()

# タイトル
st.title("🍇 温室温度管理システム")
st.caption("スプレッドシートリアルタイム連動")

# --- 1. 温度データ書き込みフォーム ---
st.subheader("🌡️ 温度データの記録")

with st.form("temp_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        boiler_temp = st.number_input("ボイラー温度 (°C)", value=20.0, step=0.5)
    with col2:
        window_temp = st.number_input("天側窓温度 (°C)", value=22.0, step=0.5)
    with col3:
        greenhouse_name = st.selectbox("対象温室", ["1号温室 (ブドウ)", "2号温室 (ブドウ)", "3号温室 (育苗)"])
    
    submitted = st.form_submit_button("スプレッドシートに保存")
    
    if submitted:
        temp_diff = window_temp - boiler_temp
        status = "⚠️ 異常 (<5°C)" if temp_diff < 5.0 else "正常"
        import datetime
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 新しい行として追加
        new_row = [now_str, greenhouse_name, boiler_temp, window_temp, round(temp_diff, 1), status]
        worksheet.append_row(new_row)
        st.success("スプレッドシートに記録を保存しました！")

st.divider()

# --- 2. 過去ログ表示 ---
st.subheader("📋 測定ログ一覧 (スプレッドシートより取得)")

# スプレッドシートからデータ取得
try:
    data = worksheet.get_all_records()
    if data:
        log_data = pd.DataFrame(data)

        def style_temp_rows(row):
            if "異常" in str(row.get("判定", "")):
                return ['background-color: #ffe6e6; color: #990000; font-weight: bold'] * len(row)
            else:
                return ['background-color: #f0fff0; color: #006600'] * len(row)

        st.dataframe(
            log_data.style.apply(style_temp_rows, axis=1),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("データがまだありません。上のフォームから登録してください。")
except Exception as e:
    st.warning("シートの1行目にヘッダー（日時, 温室名, ボイラー温度, 天側窓温度, 温度差, 判定）が入っているか確認してください。")