import streamlit as st
from datetime import date, datetime
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound

# ====== 設定 ======
WORKSHEET_NAME = "シート1"
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_info(
    st.secrets["google_service_account"], scopes=SCOPE
)
client = gspread.authorize(creds)
SHEET_URL = st.secrets.get("SHEET_URL", None)
SHEET_KEY = st.secrets.get("SHEET_KEY", None)

# ====== シート接続 ======
try:
    sh = client.open_by_url(SHEET_URL) if SHEET_URL else (
        client.open_by_key(SHEET_KEY) if SHEET_KEY else client.open("soccer_training")
    )
    try:
        ws = sh.worksheet(WORKSHEET_NAME)
    except WorksheetNotFound:
        ws = sh.get_worksheet(0)

    headers = ws.row_values(1)
    if not headers:
        headers = ["日付", "メモ"]  # 初期化
        ws.insert_row(headers, 1)
except SpreadsheetNotFound:
    st.error("スプレッドシートが見つかりません。secrets に SHEET_URL か SHEET_KEY を設定してください。")
    st.stop()
except APIError:
    svc_email = st.secrets["google_service_account"].get("client_email", "(不明)")
    st.error(
        "シートにアクセスできません。\n"
        f"・{svc_email} をスプレッドシートの編集者に追加\n"
        "・Sheets API / Drive API を有効化\n"
        "・.streamlit/secrets.toml に SHEET_URL か SHEET_KEY を設定\n"
    )
    st.stop()

# ====== ユーティリティ ======
def ensure_state(defaults: dict):
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def to_num_or_blank(s: str):
    s = (s or "").strip()
    if s == "":
        return ""
    try:
        # 整数っぽければint、そうでなければfloat
        f = float(s)
        return int(f) if f.is_integer() else f
    except ValueError:
        return s  # 数字でなければそのまま文字列

# ====== セッション初期値（列に合わせて動的に作る） ======
# 既存シートの列を尊重：日付/メモ以外は「空文字（未入力）」で始める
defaults = {"form_日付": date.today(), "form_メモ": ""}
for col in headers:
    if col in ("日付", "メモ"):
        continue
    defaults[f"form_{col}"] = ""  # 数値列でも“空”スタート（0を入れない）
ensure_state(defaults)

# ====== UI ======
st.title("サッカー特訓入力")

with st.form("入力フォーム"):
    st.date_input("日付", key="form_日付")
    # 列順通りにフォームを並べる（見出しに完全追従）
    for col in headers:
        if col == "日付":
            continue
        elif col == "メモ":
            st.text_input("メモ", key="form_メモ", placeholder="任意")
        else:
            # 数値でも“空を許す”ため text_input を使う（0量産を防止）
            st.text_input(col, key=f"form_{col}", placeholder="数値は空でもOK")
    submitted = st.form_submit_button("保存")

# ====== 保存（同じ日付は上書き、なければ追加） ======
if submitted:
    dt: date = st.session_state["form_日付"]
    date_str = dt.strftime("%Y/%m/%d")  # シートの「日付」表示に合わせる

    # 既存日付行を探索（1列目が「日付」前提）
    all_dates = ws.col_values(1)[1:]  # ヘッダー除外
    row_index = None
    for i, v in enumerate(all_dates, start=2):
        if str(v).strip() == date_str:
            row_index = i
            break

    # 行データを見出し順で組み立て
    row = []
    for col in headers:
        if col == "日付":
            row.append(date_str)
        elif col == "メモ":
            row.append(st.session_state["form_メモ"])
        else:
            row.append(to_num_or_blank(st.session_state.get(f"form_{col}", "")))

    if row_index:
        ws.update(f"A{row_index}:{gspread.utils.rowcol_to_a1(row_index, len(headers)).split(':')[1]}", [row])
    else:
        ws.append_row(row, value_input_option="USER_ENTERED")

    # 入力欄クリア（0は入れない）
    st.session_state["form_日付"] = date.today()
    st.session_state["form_メモ"] = ""
    for col in headers:
        if col not in ("日付", "メモ"):
            st.session_state[f"form_{col}"] = ""
    st.success("保存しました。")

# ====== 一覧（「日付」で並べ替え） ======
try:
    data = ws.get_all_values()
    if len(data) >= 2:
        df = pd.DataFrame(data[1:], columns=data[0])

        if "日付" in df.columns:
            # パースできるものだけ日付にしてソート
            def _parse_dt(s):
                try:
                    return datetime.strptime(s, "%Y/%m/%d")
                except Exception:
                    return None
            df["_dt"] = df["日付"].apply(_parse_dt)
            df = df.sort_values("_dt", na_position="last").drop(columns=["_dt"]).reset_index(drop=True)

        st.dataframe(df, use_container_width=True)
except Exception:
    pass




