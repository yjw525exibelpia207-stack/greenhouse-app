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

# Custom CSS（スマホ表示・ボタンデザイン・土日文字色指定）
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
        padding: 0.2rem 0.1rem;
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
    /* 土曜（6列目）のボタン文字色を青に指定 */
    div[data-testid="stHorizontalBlock"] > div:nth-child(6) button p {
        color: #1976d2 !important;
    }
    /* 日曜（7列目）のボタン文字色を赤に指定 */
    div[data-testid="stHorizontalBlock"] > div:nth-child(7) button p {
        color: #d32f2f !important;
    }
    /* 曜日の文字指定 */
    .sat-header { color: #1976d2 !important; font-weight: bold; }
    .sun-header { color: #d32f2f !important; font-weight: bold; }
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

SPREADSHEET_NAME = "作業日誌"

try:
    gc = init_connection()
    sh = gc.open(SPREADSHEET_NAME)
    worksheet = sh.get_worksheet(0)
    
    records = worksheet.get_all_records()
    df_raw = pd.DataFrame(records) if records else pd.DataFrame(columns=["日付", "作業内容", "更新日時"])
except Exception as e:
    st.error(f"⚠️ スプレッドシート「{SPREADSHEET_NAME}」の接続エラー: {e}")
    st.stop()

# ステート管理
if "selected_date" not in st.session_state:
    st.session_state.selected_date = None
if "current_year_month" not in st.session_state:
    today = datetime.date.today()
    st.session_state.current_year_month = (today.year, today.month)

# --- A. カレンダー画面 ---
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

    # 登録済みの日付リスト
    logged_dates = set()
    if not df_raw.empty and "日付" in df_raw.columns:
        logged_dates = set(df_raw["日付"].astype(str).tolist())

    # カレンダーグリッド
    cal = calendar.monthcalendar(year, month)
    
    # 曜日ヘッダー
    weekdays_html = [
        "<div>月</div>", "<div>火</div>", "<div>水</div>", 
        "<div>木</div>", "<div>金</div>", 
        "<div class='sat-header'>土</div>", "<div class='sun-header'>日</div>"
    ]
    cols = st.columns(7)
    for idx, day_html in enumerate(weekdays_html):
        cols[idx].markdown(f"<div style='text-align:center;'>{day_html}</div>", unsafe_allow_html=True)
        
    st.write("---")

    today_str = datetime.date.today().strftime("%Y-%m-%d")

    for week in cal:
        cols = st.columns(7)
        for idx, day in enumerate(week):
            if day == 0:
                cols[idx].write("")
            else:
                date_str = f"{year:04d}-{month:02d}-{day:02d}"
                has_log = date_str in logged_dates
                is_today = (date_str == today_str)

                # 数字のみ表示（入力済みは 📝 マーク付与）
                label = f"{day}"
                if has_log:
                    label += "\n📝"
                
                btn_type = "primary" if is_today else "secondary"

                if cols[idx].button(label, key=f"btn_{date_str}", type=btn_type, use_container_width=True):
                    st.session_state.selected_date = date_str
                    st.rerun()

    st.caption("※ 📝＝入力済み")

# --- B. 作業日誌入力フォーム ---
else:
    target_date_str = st.session_state.selected_date
    current_dt = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()

    # ナビゲーションボタン（◀ 前の日 / ⬅️ カレンダーに戻る / 次の日 ▶）
    col_day_prev, col_back, col_day_next = st.columns([1, 2, 1])
    
    with col_day_prev:
        if st.button("◀ 前の日", use_container_width=True):
            prev_dt = current_dt - datetime.timedelta(days=1)
            st.session_state.selected_date = prev_dt.strftime("%Y-%m-%d")
            st.session_state.current_year_month = (prev_dt.year, prev_dt.month)
            st.rerun()

    with col_back:
        st.markdown('<div class="back-btn">', unsafe_allow_html=True)
        if st.button("⬅️ カレンダー", use_container_width=True):
            st.session_state.selected_date = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col_day_next:
        if st.button("次の日 ▶", use_container_width=True):
            next_dt = current_dt + datetime.timedelta(days=1)
            st.session_state.selected_date = next_dt.strftime("%Y-%m-%d")
            st.session_state.current_year_month = (next_dt.year, next_dt.month)
            st.rerun()

    st.subheader(f"📅 {target_date_str} の作業日誌")

    # 既存データの取得
    existing_log = ""
    if not df_raw.empty and "日付" in df_raw.columns:
        date_matched = df_raw[df_raw["日付"].astype(str) == target_date_str]
        if not date_matched.empty:
            existing_log = str(date_matched.iloc[-1].get("作業内容", ""))

    with st.form("journal_form", clear_on_submit=False):
        work_detail = st.text_area(
            "📝 作業内容",
            value=existing_log,
            height=200,
            placeholder="本日の作業内容を入力してください"
        )

        st.markdown('<div class="save-btn">', unsafe_allow_html=True)
        submitted = st.form_submit_button("日誌を保存する")
        st.markdown('</div>', unsafe_allow_html=True)

        if submitted:
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_row = [target_date_str, work_detail, now_str]

            worksheet.append_row(new_row)
            
            st.success(f"✅ {target_date_str} の作業日誌を保存しました！")
            st.session_state.selected_date = None
            st.rerun()
