import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import calendar

# ページ基本設定（スマホ表示最適化）
st.set_page_config(
    page_title="作業日誌",
    page_icon="📅",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS（スマホで押しやすい大きめボタンやカレンダーデザイン）
st.markdown("""
<style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 3rem;
        max-width: 500px;
    }
    div.stButton > button {
        border-radius: 8px;
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

# シートへの接続
SPREADSHEET_NAME = "作業日誌"  # スプレッドシート名

try:
    gc = init_connection()
    sh = gc.open(SPREADSHEET_NAME)
    worksheet = sh.get_worksheet(0)
    
    records = worksheet.get_all_records()
    df_raw = pd.DataFrame(records) if records else pd.DataFrame(columns=["日付", "作業内容", "作業者", "更新日時"])
except Exception as e:
    st.error(f"⚠️ スプレッドシート「{SPREADSHEET_NAME}」の接続エラー: {e}")
    st.info("※Googleドライブに「作業日誌」というスプレッドシートを作成し、1行目に「日付」「作業内容」「作業者」「更新日時」を設定してください。")
    st.stop()

# ステート管理
if "selected_date" not in st.session_state:
    st.session_state.selected_date = None
if "current_year_month" not in st.session_state:
    today = datetime.date.today()
    st.session_state.current_year_month = (today.year, today.month)

# --- A. 日付が選択されていないとき：カレンダー画面 ---
if st.session_state.selected_date is None:
    year, month = st.session_state.current_year_month
    
    # 月切り替えヘッダー
    col_prev, col_title, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("◀ 前月", use_container_width=True):
            if month == 1:
                st.session_state.current_year_month = (year - 1, 12)
            else:
                st.session_state.current_year_month = (year, month - 1)
            st.rerun()
            
    with col_title:
        st.markdown(f"<h3 style='text-align: center; margin:0;'>{year}年 {month}月</h3>", unsafe_allow_html=True)
        
    with col_next:
        if st.button("次月 ▶", use_container_width=True):
            if month == 12:
                st.session_state.current_year_month = (year + 1, 1)
            else:
                st.session_state.current_year_month = (year, month + 1)
            st.rerun()

    st.write("")

    # 日誌入力済みの日付リストを取得
    logged_dates = set()
    if not df_raw.empty and "日付" in df_raw.columns:
        logged_dates = set(df_raw["日付"].astype(str).tolist())

    # カレンダーグリッドの作成
    cal = calendar.monthcalendar(year, month)
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    
    # 曜日ヘッダー
    cols = st.columns(7)
    for idx, day_name in enumerate(weekdays):
        cols[idx].markdown(f"<div style='text-align:center; font-weight:bold;'>{day_name}</div>", unsafe_allow_html=True)
        
    st.write("---")

    # 日付ボタンの並び（7列）
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    for week in cal:
        cols = st.columns(7)
        for idx, day in enumerate(week):
            if day == 0:
                cols[idx].write("") # 月外の日付空白
            else:
                date_str = f"{year:04d}-{month:02d}-{day:02d}"
                has_log = date_str in logged_dates
                is_today = (date_str == today_str)

                # ボタンのラベル（記録済みならマーク付き）
                label = f"{day}"
                if has_log:
                    label += "\n📝"
                
                # 今日の日付強調表示用
                btn_type = "primary" if is_today else "secondary"

                if cols[idx].button(label, key=f"btn_{date_str}", type=btn_type, use_container_width=True):
                    st.session_state.selected_date = date_str
                    st.rerun()

    st.caption("※ 日付下の 📝 は既に作業入力がある日です。")

# --- B. 日付選択時：作業日誌入力フォーム ---
else:
    target_date = st.session_state.selected_date

    # 戻るボタン
    st.markdown('<div class="back-btn">', unsafe_allow_html=True)
    if st.button("⬅️ カレンダーに戻る", use_container_width=True):
        st.session_state.selected_date = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.subheader(f"📅 {target_date} の作業日誌")

    # 既存データの読み込み
    existing_log = ""
    existing_worker = ""
    if not df_raw.empty and "日付" in df_raw.columns:
        date_matched = df_raw[df_raw["日付"].astype(str) == target_date]
        if not date_matched.empty:
            existing_log = str(date_matched.iloc[-1].get("作業内容", ""))
            existing_worker = str(date_matched.iloc[-1].get("作業者", ""))

    with st.form("journal_form", clear_on_submit=False):
        work_detail = st.text_area(
            "📝 作業内容",
            value=existing_log,
            height=180,
            placeholder="例: D-7・D-8 摘心作業、水やり、防除作業など"
        )
        
        worker_name = st.text_input(
            "👤 作業者（任意）",
            value=existing_worker,
            placeholder="名前"
        )

        st.markdown('<div class="save-btn">', unsafe_allow_html=True)
        submitted = st.form_submit_button("日誌を保存する")
        st.markdown('</div>', unsafe_allow_html=True)

        if submitted:
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_row = [target_date, work_detail, worker_name, now_str]

            # スプレッドシートへ追加登録
            worksheet.append_row(new_row)
            
            st.success(f"✅ {target_date} の作業日誌を保存しました！")
            st.session_state.selected_date = None
            st.rerun()
