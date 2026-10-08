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

# Custom CSS（スマホ表示・プレビューカードのスタイリング）
st.markdown("""
<style>
    /* 全体コンテナの幅と上部余白調整 */
    .block-container {
        padding-top: 2.5rem;
        padding-bottom: 3rem;
        padding-left: 0.5rem;
        padding-right: 0.5rem;
        max-width: 500px;
    }
    
    /* スマホ画面でも7列を横に並べる */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 2px !important;
    }
    
    /* 7列の各カラム幅を均等化 */
    div[data-testid="stHorizontalBlock"] > div {
        width: 14.28% !important;
        min-width: 0px !important;
        flex: 1 1 14.28% !important;
    }

    /* カレンダーボタンのデザイン */
    div.stButton > button {
        border-radius: 8px;
        font-weight: bold;
        padding: 2px 0px !important;
        width: 100% !important;
        min-height: 44px !important;
        font-size: 0.85rem !important;
        line-height: 1.2 !important;
    }
    
    /* 日曜（1列目）の文字色：赤 */
    div[data-testid="stHorizontalBlock"] > div:nth-child(1) button p {
        color: #f44336 !important;
    }
    
    /* 土曜（7列目）の文字色：青 */
    div[data-testid="stHorizontalBlock"] > div:nth-child(7) button p {
        color: #2196f3 !important;
    }

    /* 曜日ヘッダー */
    .weekday-header {
        text-align: center;
        font-weight: bold;
        font-size: 0.85rem;
        padding-bottom: 4px;
        color: #888888;
    }
    .sat-header { color: #2196f3 !important; }
    .sun-header { color: #f44336 !important; }

    /* プレビュー表示エリアのスタイル（背景：白、文字：黒） */
    .preview-box {
        background-color: #ffffff;
        border: 1px solid #cccccc;
        border-radius: 12px;
        padding: 16px;
        margin-top: 15px;
        margin-bottom: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        text-align: left !important;
    }
    .preview-date {
        font-size: 1.2rem;
        font-weight: bold;
        color: #111111;
        margin-bottom: 8px;
        border-bottom: 1px solid #eeeeee;
        padding-bottom: 6px;
        text-align: left !important;
    }
    .preview-content {
        font-size: 0.95rem;
        color: #222222;
        white-space: pre-wrap;
        line-height: 1.5;
        min-height: 60px;
        text-align: left !important;
    }
    .preview-empty {
        font-size: 0.9rem;
        color: #888888;
        font-style: italic;
    }

    /* 保存・編集ボタン */
    .edit-btn > button {
        width: 100%;
        height: 3rem;
        background-color: #1976d2 !important;
        color: white !important;
        font-size: 1rem !important;
        border-radius: 8px !important;
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

SPREADSHEET_NAME = "作業日誌"

# スプレッドシートから最新データを取得
def load_data():
    try:
        gc = init_connection()
        sh = gc.open(SPREADSHEET_NAME)
        worksheet = sh.get_worksheet(0)
        
        data = worksheet.get_all_values()
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=data[0])
            if "日付" in df.columns:
                df["日付"] = pd.to_datetime(df["日付"], errors="coerce").dt.strftime("%Y-%m-%d")
            return worksheet, df
        else:
            return worksheet, pd.DataFrame(columns=["日付", "作業内容", "更新日時"])
    except Exception as e:
        st.error(f"⚠️ スプレッドシート「{SPREADSHEET_NAME}」の接続エラー: {e}")
        st.stop()

worksheet, df_raw = load_data()

# ステート管理（アプリ起動時に自動で「今日」にセット）
today = datetime.date.today()
today_str = today.strftime("%Y-%m-%d")

if "mode" not in st.session_state:
    st.session_state.mode = "view"

# 起動時・初期化時に「今日」を選択状態にする
if "focused_date" not in st.session_state:
    st.session_state.focused_date = today_str

if "current_year_month" not in st.session_state:
    st.session_state.current_year_month = (today.year, today.month)

# --- A. カレンダー ＆ プレビュー画面 ---
if st.session_state.mode == "view":
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

    # 日付ごとの作業内容辞書を作成
    log_map = {}
    if not df_raw.empty and "日付" in df_raw.columns and "作業内容" in df_raw.columns:
        for date, group in df_raw.groupby("日付"):
            if pd.notna(date) and date != "None":
                content = str(group.iloc[-1]["作業内容"]).strip()
                if content:
                    log_map[str(date)] = content

    # カレンダーグリッド描画
    cal = calendar.monthcalendar(year, month)
    
    weekdays_html = [
        "<div class='weekday-header sun-header'>日</div>", 
        "<div class='weekday-header'>月</div>", 
        "<div class='weekday-header'>火</div>", 
        "<div class='weekday-header'>水</div>", 
        "<div class='weekday-header'>木</div>", 
        "<div class='weekday-header'>金</div>", 
        "<div class='weekday-header sat-header'>土</div>"
    ]
    cols = st.columns(7)
    for idx, day_html in enumerate(weekdays_html):
        cols[idx].markdown(day_html, unsafe_allow_html=True)
        
    st.write("---")

    for week in cal:
        cols = st.columns(7)
        for idx, day in enumerate(week):
            if day == 0:
                cols[idx].write("")
            else:
                date_str = f"{year:04d}-{month:02d}-{day:02d}"
                has_log = date_str in log_map
                is_focused = (date_str == st.session_state.focused_date)

                label = f"{day}"
                if has_log:
                    label += "\n●"

                btn_type = "primary" if is_focused else "secondary"

                if cols[idx].button(label, key=f"btn_{date_str}", type=btn_type, use_container_width=True):
                    if st.session_state.focused_date == date_str:
                        st.session_state.mode = "edit"
                    else:
                        st.session_state.focused_date = date_str
                    st.rerun()

    # --- 下部：選択日付のプレビュー表示エリア ---
    focused_date_str = st.session_state.focused_date
    focused_content = log_map.get(focused_date_str, "")

    st.markdown("---")
    
    display_text = focused_content if focused_content else '<span class="preview-empty">（作業内容の入力はありません）</span>'
    
    preview_html = f'<div class="preview-box"><div class="preview-date">📅 {focused_date_str}</div><div class="preview-content">{display_text}</div></div>'
    st.markdown(preview_html, unsafe_allow_html=True)

    st.markdown('<div class="edit-btn">', unsafe_allow_html=True)
    if st.button("✏️ この日の作業内容を編集・入力する", use_container_width=True):
        st.session_state.mode = "edit"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- B. 作業日誌入力フォーム画面 ---
else:
    target_date_str = st.session_state.focused_date
    current_dt = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()

    col_day_prev, col_back, col_day_next = st.columns([1, 2, 1])
    
    with col_day_prev:
        if st.button("◀ 前の日", use_container_width=True):
            prev_dt = current_dt - datetime.timedelta(days=1)
            st.session_state.focused_date = prev_dt.strftime("%Y-%m-%d")
            st.session_state.current_year_month = (prev_dt.year, prev_dt.month)
            st.rerun()

    with col_back:
        st.markdown('<div class="back-btn">', unsafe_allow_html=True)
        if st.button("⬅ カレンダー", use_container_width=True):
            st.session_state.mode = "view"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col_day_next:
        if st.button("次の日 ▶", use_container_width=True):
            next_dt = current_dt + datetime.timedelta(days=1)
            st.session_state.focused_date = next_dt.strftime("%Y-%m-%d")
            st.session_state.current_year_month = (next_dt.year, next_dt.month)
            st.rerun()

    st.subheader(f"📅 {target_date_str} の作業日誌")

    existing_log = ""
    if not df_raw.empty and "日付" in df_raw.columns:
        date_matched = df_raw[df_raw["日付"] == target_date_str]
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

            # スプレッドシートに追加書き込み
            worksheet.append_row(new_row)
            
            # キャッシュをリセットして画面遷移
            st.cache_data.clear()
            st.session_state.mode = "view"
            st.rerun()
