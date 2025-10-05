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

# -------- シート接続（丸ごと置き換え）--------
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

    # ヘッダー取得＆初期化
    headers = ws.row_values(1)
    if not headers:
        headers = [DATE_COL_NAME, "メモ"]
        ws.insert_row(headers, 1)

    # ===== 列フォーマットを見出し名ベースで固定 =====
    from gspread.utils import rowcol_to_a1

    # 見出し名 -> 列番号（1始まり）
    _col_idx = {name: i + 1 for i, name in enumerate(headers)}

    def _col_letter(idx: int) -> str:
        return rowcol_to_a1(1, idx).rstrip("0123456789")

    def _col_range(idx: int) -> str:
        L = _col_letter(idx)
        return f"{L}2:{L}"  # ヘッダー除外で下まで

    # A列はテキスト（'YYYY/MM/DD を壊さない）
    ws.format(_col_range(1), {"numberFormat": {"type": "TEXT"}})

    # 年齢 / リフティングレベル / 疲労度 は整数表示（0桁）
    for name in ("年齢", "リフティングレベル", "疲労度"):
        if name in _col_idx:
            ws.format(_col_range(_col_idx[name]),
                      {"numberFormat": {"type": "NUMBER", "pattern": "0"}})

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

from gspread.utils import rowcol_to_a1  # 先頭のimportに無ければ追加

def _col_end_ref(n_cols: int) -> str:
    """列数から終端列参照（例: 'Z' や 'AD'）だけを返す。"""
    return rowcol_to_a1(1, n_cols).rstrip("0123456789")


def normalize_date_str(s: str) -> str:
    """日付文字列から数字だけを取り出し、8桁(YYYYMMDD)なら返す。ダメなら空を返す。"""
    digits = "".join(ch for ch in (s or "") if ch.isdigit())
    return digits if len(digits) == 8 else ""
                  
def display_date_str(date_key: str) -> str:
    """YYYYMMDD -> YYYY/MM/DD（常に文字列）"""
    return f"{date_key[0:4]}/{date_key[4:6]}/{date_key[6:8]}"

# ★ 整数しか許さない列名（ヘッダー名で判定：B=年齢, K=リフティングレベル, P=疲労度）
INT_COLS = {"年齢", "リフティングレベル", "疲労度"}

def parse_number_or_blank(label: str, s: str):
    """
    空文字は空のまま返す。
    数字なら int/float に変換して返す。
    数字でない文字が入っていたらエラー表示して停止。
    """
    s = (s or "").strip()
    if s == "":
        return ""  # 空は許容
    try:
        f = float(s)
        return int(f) if f.is_integer() else f
    except ValueError:
        st.error(f"『{label}』は数値で入力してください（例: 12, 12.3）。\n入力値: {s}")
        st.stop()
def parse_int_or_blank(label: str, s: str):
    """
    空は空のまま。整数以外はエラーで停止。
    12 や 12.0 はOK（→ 12 にする）。12.3 はNG。
    全角数字は半角に寄せる。
    """
    s = (s or "").strip()
    if s == "":
        return ""
    # 全角→半角
    table = str.maketrans("０１２３４５６７８９＋－．", "0123456789+-.")
    s = s.translate(table)
    try:
        f = float(s)
        if f.is_integer():
            return int(f)
        else:
            st.error(f"『{label}』は整数で入力してください（例: 12）。小数は不可：{s}")
            st.stop()
    except ValueError:
        st.error(f"『{label}』は整数で入力してください（例: 12）。入力値：{s}")
        st.stop()

def load_existing_data():
    """入力欄の日付から既存データを読み込み、session_state に反映"""
    raw = st.session_state.get(f"form_{DATE_COL_NAME}", "")
    date_key = normalize_date_str(raw)
    if not date_key:
        return

    if DATE_COL_NAME not in headers:
        return

    date_col_idx = headers.index(DATE_COL_NAME) + 1
    existing = ws.col_values(date_col_idx)[1:]  # 見出し除外

    target_row = None
    for i, v in enumerate(existing, start=2):
        if normalize_date_str(v) == date_key:
            target_row = i
            break

    if target_row:
        row_vals = ws.row_values(target_row)
        for j, col in enumerate(headers):
            key = f"form_{col}"
            val = row_vals[j] if j < len(row_vals) else ""
            st.session_state[key] = "" if val is None else str(val)
        st.toast(f"登録済みデータを読み込みました（日付: {display_date_str(date_key)}）", icon="📅")

# -------- UI（見出しに自動追従・全部 text_input）--------
st.title("サッカー特訓入力（全部文字列モード）")

# === 既存データの自動読み込み（入力欄の日付に追従） ===
prefill = {}          # ← フォームの value に渡す辞書
loaded_row_index = None

if DATE_COL_NAME in headers:
    # 入力欄に現在表示されている日付（なければ今日）を8桁に正規化
    raw_in_form = st.session_state.get(f"form_{DATE_COL_NAME}", today_str())
    pending_key = normalize_date_str(raw_in_form) or today_str()

    # シートの「日付」列から該当行を探す
    date_col_idx = headers.index(DATE_COL_NAME) + 1
    col_vals = ws.col_values(date_col_idx)[1:]  # ヘッダー除外
    for i, v in enumerate(col_vals, start=2):
        if normalize_date_str(v) == pending_key:
            loaded_row_index = i
            break

    # 見つかったら、その行の値をフォームにプリセット
    if loaded_row_index:
        row_vals = ws.row_values(loaded_row_index)
        for j, col in enumerate(headers):
            val = row_vals[j] if j < len(row_vals) else ""
            if col == DATE_COL_NAME:
                # 入力欄では常に 8桁（YYYYMMDD）で見せる
                prefill[col] = normalize_date_str(val) or pending_key
            else:
                prefill[col] = "" if val is None else str(val)


# フォームの前
日付キー = f"form_{DATE_COL_NAME}"
default_date = today_str()
st.text_input(
    f"{DATE_COL_NAME}（例: 20250715）",
    key=日付キー,
    value=st.session_state.get(日付キー, default_date),
    placeholder="YYYYMMDD",
    on_change=load_existing_data,   # ← フォームの外なら動く！
)

with st.form("入力フォーム"):
    for col in headers:
        if col == DATE_COL_NAME:
            continue  # ← 外に出したのでスキップ
        key = f"form_{col}"
        st.text_input(col, key=key, placeholder="任意 or 数値OKなど")
    submitted = st.form_submit_button("保存")





# -------- 保存（同日付は上書き／なければ追加）--------
if submitted:
    # --- 多重保存ガード（直前と同じキーならスキップ） ---
    pending_raw = st.session_state.get(f"form_{DATE_COL_NAME}", "")
    pending_norm = normalize_date_str(pending_raw)
    last_norm = normalize_date_str(st.session_state.get("_last_saved_key", ""))
    if pending_norm and pending_norm == last_norm:
        st.info("同じ日付の保存は直前に完了しています。")
    else:
        # 1) 日付キー（8桁）と表示用を作成
        date_key = normalize_date_str(pending_raw)
        if len(date_key) != 8:
            st.error(f"{DATE_COL_NAME} は 8桁の数字（例: {DATE_EXAMPLE}）で入力してください。")
            st.stop()
        date_disp = display_date_str(date_key)  # "YYYY/MM/DD"

        # 2) 既存検索（DATE_COL_NAME 列で探す）
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

        # 3) 行データを構築（A列=文字列、日付/メモ=文字列、INT_COLS=整数、その他=数値）
        row = []
        for col_idx, col in enumerate(headers, start=1):  # A=1, B=2, ...
            key = f"form_{col}"
            if col_idx == 1:
                # ★ A列は必ず文字列
                if col == DATE_COL_NAME:
                    row.append(f"'{date_disp}")  # 'YYYY/MM/DD
                else:
                    v = st.session_state.get(key, "")
                    row.append("" if v is None else f"'{str(v)}")
            elif col == DATE_COL_NAME:
                row.append(date_disp)
            elif col == "メモ":
                v = st.session_state.get(key, "")
                row.append("" if v is None else str(v))
            elif col in INT_COLS:
                v = st.session_state.get(key, "")
                row.append(parse_int_or_blank(col, v))      # 整数限定
            else:
                v = st.session_state.get(key, "")
                row.append(parse_number_or_blank(col, v))   # 小数OK（空は空）

        # 4) 更新 or 追加
        from gspread.utils import rowcol_to_a1
        if row_index:
            end_cell = rowcol_to_a1(row_index, len(headers))
            ws.update(f"A{row_index}:{end_cell}", [row], value_input_option="USER_ENTERED")
        else:
            ws.append_row(row, value_input_option="USER_ENTERED")

        # 4.5) 保存直後ソート（ヘッダー除外で全列）
        end_cell = rowcol_to_a1(ws.row_count, len(headers))
        ws.sort((date_col_idx, 'asc'), range=f"A2:{end_cell}")

        # 5) 入力欄クリア & 直前キー記録（多重保存ガード用）
        for col in headers:
            st.session_state.pop(f"form_{col}", None)
        st.session_state["_last_saved_key"] = pending_raw

        st.success("保存しました。")



























