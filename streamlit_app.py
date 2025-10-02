# ================== streamlit_app.py（このまま全文コピペ）==================
import streamlit as st
from datetime import date, datetime
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound
from gspread.utils import rowcol_to_a1

# -------- 0) 環境設定 --------
WORKSHEET_NAME = "シート1"
DATE_COL_NAME = "日付"   # ← 日付列の見出し名（B1が「日付」ならこのままでOK）

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_info(
    st.secrets["google_service_account"], scopes=SCOPE
)
client = gspread.authorize(creds)
SHEET_URL = st.secrets.get("SHEET_URL")
SHEET_KEY = st.secrets.get("SHEET_KEY")

# -------- 1) シート接続 --------
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
    st.error(f"アクセスできません。シートを **{svc}** に“編集者”で共有、Sheets/Drive API有効化、SHEET_URL/KEY設定を確認。")
    st.stop()

# -------- 2) 日付列の位置確認 --------
if DATE_COL_NAME not in headers:
    st.error(f"ヘッダーに『{DATE_COL_NAME}』がありません。日付の列名をコード先頭の DATE_COL_NAME に合わせてください。")
    st.stop()
date_col_idx = headers.index(DATE_COL_NAME) + 1  # 1始まり

# -------- 3) セッション初期化 --------
def ensure_state(d: dict):
    for k, v in d.items():
        if k not in st.session_state:
            st.session_state[k] = v

defaults = {f"form_{DATE_COL_NAME}": date.today()}
for col in headers:
    if col != DATE_COL_NAME:
        defaults[f"form_{col}"] = ""
ensure_state(defaults)

# -------- 4) UI（ヘッダーに自動追従）--------
st.title("サッカー特訓入力")
with st.form("入力フォーム"):
    for col in headers:
        key = f"form_{col}"
        if col == DATE_COL_NAME:
            st.date_input(col, key=key)
        elif col == "メモ":
            st.text_input(col, key=key, placeholder="任意")
        else:
            st.text_input(col, key=key, placeholder="空でもOK（数字は半角推奨）")
    submitted = st.form_submit_button("保存")

# -------- 5) 保存（同日付は上書き／なければ追加）--------
def _to_cell_value(s: str):
    s = (s or "").strip()
    if s == "":
        return ""
    try:
        f = float(s)
        return int(f) if f.is_integer() else f
    except ValueError:
        return s

if submitted:
    # 1) キー作成
    dt = st.session_state[f"form_{DATE_COL_NAME}"]      # datetime.date
    date_str = dt.strftime("%Y/%m/%d")                  # 表示形式を統一

    # 2) 既存検索（“日付列”で探す）
    col_vals = ws.col_values(date_col_idx)[1:]          # 見出し除外
    row_index = None
    for i, v in enumerate(col_vals, start=2):
        if str(v).strip() == date_str:
            row_index = i
            break

    # 3) 行データを見出し順で構築
    row = []
    for col in headers:
        if col == DATE_COL_NAME:
            row.append(date_str)
        else:
            row.append(_to_cell_value(st.session_state.get(f"form_{col}", "")))

    # 4) 更新 or 追加
    end_cell = rowcol_to_a1(row_index if row_index else 1, len(headers))
    rng = f"A{row_index}:{end_cell}" if row_index else None
    if row_index:
        ws.update(rng, [row])
    else:
        ws.append_row(row, value_input_option="USER_ENTERED")

    # 5) 入力欄クリア
    st.session_state[f"form_{DATE_COL_NAME}"] = date.today()
    for col in headers:
        if col != DATE_COL_NAME:
            st.session_state[f"form_{col}"] = ""
    st.success("保存しました。")

# -------- 6) 一覧（任意／邪魔なら消してOK）--------
try:
    data = ws.get_all_values()
    if len(data) >= 2:
        df = pd.DataFrame(data[1:], columns=data[0])
        if DATE_COL_NAME in df.columns:
            def _parse(s):
                try:
                    return datetime.strptime(s, "%Y/%m/%d")
                except Exception:
                    return None
            df["_dt"] = df[DATE_COL_NAME].apply(_parse)
            df = df.sort_values("_dt", na_position="last").drop(columns=["_dt"]).reset_index(drop=True)
        st.dataframe(df, use_container_width=True)
except Exception:
    pass
# ===================================================================
