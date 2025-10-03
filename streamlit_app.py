# ================== streamlit_app.py（全文コピペ）==================
import streamlit as st
import pandas as pd
from datetime import date
from google.oauth2.service_account import Credentials
import gspread
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound
from gspread.utils import rowcol_to_a1

# -------- 設定（必要なら変えるのはここだけ） --------
WORKSHEET_NAME = "シート1"
DATE_COL_NAME  = "日付"          # ← 日付列の見出し名（B1が「日付」ならこのままでOK）
DATE_EXAMPLE   = "20250715"      # ← “全部文字列”で使う基準フォーマット（YYYYMMDD）

# Google 認証（secrets 必須）
SCOPE = ["https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(
    st.secrets["google_service_account"], scopes=SCOPE
)
client = gspread.authorize(creds)
SHEET_URL = st.secrets.get("SHEET_URL")
SHEET_KEY = st.secrets.get("SHEET_KEY")

# -------- シート接続 --------
try:
    if SHEET_URL:
        sh = client.open_by_url(SHEET_URL)
    elif SHEET_KEY:
        sh = client.open_by_key(SHEET_KEY)
    else:
        sh = client.open("soccer_training")  # 最終手段
    try:
        ws = sh.worksheet(WORKSHEET_NAME)
    except WorksheetNotFound:
        ws = sh.get_worksheet(0)

    headers = ws.row_values(1)
    if not headers:
        headers = [DATE_COL_NAME, "メモ"]
        ws.insert_row(headers, 1)
except SpreadsheetNotFound:
    st.error("スプレッドシートが見つかりません。.streamlit/secrets.toml に SHEET_URL か SHEET_KEY を入れてください。")
    st.stop()
except APIError:
    svc = st.secrets["google_service_account"].get("client_email", "(不明)")
    st.error(f"アクセス不可。シートを **{svc}** に“編集者”で共有、Sheets/Drive API有効化、SHEET_URL/KEY を確認。")
    st.stop()

# -------- ユーティリティ（全部文字列） --------
def today_str() -> str:
    # きょうを "YYYYMMDD" で返す（例: 20251002）
    d = date.today()
    return f"{d.year:04d}{d.month:02d}{d.day:02d}"

def normalize_date_str(s: str) -> str:
    """日付文字列から数字だけを取り出し、8桁(YYYYMMDD)なら返す。ダメなら空を返す。"""
    digits = "".join(ch for ch in (s or "") if ch.isdigit())
    return digits if len(digits) == 8 else ""
                  
def display_date_str(date_key: str) -> str:
    """YYYYMMDD -> YYYY/MM/DD（常に文字列）"""
    return f"{date_key[0:4]}/{date_key[4:6]}/{date_key[6:8]}"

# -------- セッション初期化（全部テキスト） --------
for col in headers:
    key = f"form_{col}"
    if key not in st.session_state:
        if col == DATE_COL_NAME:
            st.session_state[key] = today_str()  # 例: "20251002"
        else:
            st.session_state[key] = ""           # それ以外は空文字

# -------- UI（見出しに自動追従・全部 text_input）--------
st.title("サッカー特訓入力（全部文字列モード）")
with st.form("入力フォーム"):
    for col in headers:
        key = f"form_{col}"
        if col == DATE_COL_NAME:
            st.text_input(f"{col}（{DATE_EXAMPLE} 形式推奨）", key=key, placeholder=DATE_EXAMPLE)
        else:
            st.text_input(col, key=key, placeholder="空でもOK（数値も文字列で保存）")
    submitted = st.form_submit_button("保存")

# -------- 保存（同日付は上書き／なければ追加）--------
if submitted:
    # 1) キー（DATE_COL_NAME）を正規化
    raw = st.session_state[f"form_{DATE_COL_NAME}"]
    date_key = normalize_date_str(raw)
    date_disp = display_date_str(date_key) 
    if not date_key:
        st.error(f"{DATE_COL_NAME} は 8桁の数字（例: {DATE_EXAMPLE} / 2025-07-15 も可）で入力してください。")
        st.stop()

    # 2) 既存検索：DATE_COL_NAME の列で探す
    if DATE_COL_NAME not in headers:
        st.error(f"ヘッダーに『{DATE_COL_NAME}』がありません。")
        st.stop()
    date_col_idx = headers.index(DATE_COL_NAME) + 1  # 1始まり
    existing = ws.col_values(date_col_idx)[1:]       # 見出し除外
    row_index = None
    for i, v in enumerate(existing, start=2):
        if normalize_date_str(v) == date_key:
            row_index = i
            break

    # 3) 行データを“全部文字列”で構築（見出し順）
    row = []
    for col in headers:
        if col == DATE_COL_NAME:
            row.append(date_disp)
        else:
            val = st.session_state.get(f"form_{col}", "")
            row.append("" if val is None else str(val))

    # 4) 更新 or 追加
    end_cell = rowcol_to_a1(row_index if row_index else 1, len(headers))
    rng = f"A{row_index}:{end_cell}" if row_index else None
    if row_index:
        ws.update(rng, [row])
    else:
        ws.append_row(row, value_input_option="USER_ENTERED")

    # 5) 入力欄クリア（文字列でリセット）
    for col in headers:
        key = f"form_{col}"
        st.session_state[key] = today_str() if col == DATE_COL_NAME else ""
    st.success("保存しました。")

# -------- 一覧（文字列ソート：YYYYMMDDならそのまま昇順OK）--------
try:
    data = ws.get_all_values()
    if len(data) >= 2:
        df = pd.DataFrame(data[1:], columns=data[0])
        if DATE_COL_NAME in df.columns:
            # 非数字も混ざる可能性があるので、normalize してからソートキーに
            df["_k"] = df[DATE_COL_NAME].apply(normalize_date_str)
            df = df.sort_values("_k", na_position="last").drop(columns=["_k"]).reset_index(drop=True)
        st.dataframe(df, use_container_width=True)
except Exception:
    pass
# ================================================================


