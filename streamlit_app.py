# ================== streamlit_app.py（このファイルに丸ごと貼る）==================
import streamlit as st
from datetime import date
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound

# ---------- 0) 設定（ここだけあなたの環境に合わせる） ----------
WORKSHEET_NAME = "シート1"  # ここを別名にしているなら変えてOK（例: "Sheet1"）

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_info(
    st.secrets["google_service_account"], scopes=SCOPE
)
client = gspread.authorize(creds)

# secrets.toml に SHEET_URL か SHEET_KEY を用意（URL推奨）
SHEET_URL = st.secrets.get("SHEET_URL", None)
SHEET_KEY = st.secrets.get("SHEET_KEY", None)

# ---------- 1) シート接続 ----------
try:
    if SHEET_URL:
        sh = client.open_by_url(SHEET_URL)
    elif SHEET_KEY:
        sh = client.open_by_key(SHEET_KEY)
    else:
        # 無い場合の最終手段（同名が複数あったり権限で失敗しがちなので非推奨）
        sh = client.open("soccer_training")

    try:
        ws = sh.worksheet(WORKSHEET_NAME)
    except WorksheetNotFound:
        ws = sh.get_worksheet(0)  # 先頭シートにフォールバック

    headers = ws.row_values(1)
    if not headers:
        headers = ["日付キー", "メモ"]  # 最低限の見出し
        ws.insert_row(headers, 1)

except SpreadsheetNotFound:
    st.error("スプレッドシートが見つかりません。secrets に SHEET_URL か SHEET_KEY を設定してください。")
    st.stop()
except APIError:
    svc_email = st.secrets["google_service_account"].get("client_email", "(不明)")
    st.error(
        "シートにアクセスできません。\n"
        f"・Googleスプレッドシートを **{svc_email}** に“編集者”で共有してください\n"
        "・GCPで『Google Sheets API』『Google Drive API』を有効化してください\n"
        "・.streamlit/secrets.toml に SHEET_URL か SHEET_KEY を設定してください\n"
    )
    st.stop()

# ---------- 2) ユーティリティ ----------
def safe_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

# ---------- 3) セッション初期化（今回のエラー対策の本丸） ----------
def ensure_state(defaults: dict):
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

FORM_KEYS_DEFAULTS = {
    "form_日付_dt": date.today(),
    "form_メモ": "",
}
ensure_state(FORM_KEYS_DEFAULTS)

# ---------- 4) UI ----------
st.title("サッカー特訓入力")

with st.form("入力フォーム"):
    st.date_input("日付", key="form_日付_dt")   # valueを渡さず、keyのみ
    st.text_input("メモ", key="form_メモ")     # valueを渡さず、keyのみ
    submitted = st.form_submit_button("保存")

# ---------- 5) 保存処理（フォームの“後”で読む） ----------
if submitted:
    dt = st.session_state["form_日付_dt"]      # ← 描画後なのでKeyErrorにならない
    memo = st.session_state["form_メモ"]
    date_key = dt.strftime("%Y%m%d")

    # A列=日付キー で既存確認して更新 or 追加
    dates = ws.col_values(1)[1:]  # 1行目はヘッダーなので除外
    row_index = None
    for i, v in enumerate(dates, start=2):     # 2行目からデータ
        if str(v).strip() == date_key:
            row_index = i
            break

    values = [date_key, memo]

    if row_index:
        ws.update(f"A{row_index}:B{row_index}", [values])
    else:
        ws.append_row(values, value_input_option="USER_ENTERED")

    # 入力欄クリア（キーは消さず、値を再セット）
    st.session_state["form_日付_dt"] = date.today()
    st.session_state["form_メモ"] = ""
    st.success("保存しました。")

# ---------- 6) 一覧表示（確認用） ----------
try:
    data = ws.get_all_values()
    if len(data) >= 2:
        df = pd.DataFrame(data[1:], columns=data[0])
        # 日付キーは YYYYMMDD なので文字列でも正しく昇順化できる
        if "日付キー" in df.columns:
            df = df.sort_values("日付キー").reset_index(drop=True)
        st.dataframe(df, use_container_width=True)
except Exception:
    pass
# ===================================================================


