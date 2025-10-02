import streamlit as st
from datetime import date
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound

# --- 安全な数値変換用の関数（既存の良いところは残す） ---
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

# --- Google認証（やばい所だけ修正） ---
# 古い "feeds" はやめて、公式推奨のスコープに
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# st.secrets の "google_service_account" はそのまま利用（良い）
creds = Credentials.from_service_account_info(
    st.secrets["google_service_account"], scopes=SCOPE
)
client = gspread.authorize(creds)

# --- シートの開き方を「名前」→「キー/URL」へ（やばい所の修正） ---
# 1) .streamlit/secrets.toml に SHEET_URL または SHEET_KEY を入れておく
# 例：
# [google_service_account] ...（省略）...
# SHEET_URL = "https://docs.google.com/spreadsheets/d/xxxxxxxxxxxxxxxxxxxxxxxxxxxx/edit"
# または
# SHEET_KEY = "xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
SHEET_URL = st.secrets.get("SHEET_URL", None)
SHEET_KEY = st.secrets.get("SHEET_KEY", None)

# 2) 開く（URL優先 → KEY）
try:
    if SHEET_URL:
        sh = client.open_by_url(SHEET_URL)
    elif SHEET_KEY:
        sh = client.open_by_key(SHEET_KEY)
    else:
        # 最悪の最悪にだけ名前で開く（非推奨）
        sh = client.open("soccer_training")

    # ここも名前参照はそのままでも良いが、将来に備えて存在チェック
    try:
        worksheet = sh.worksheet("シート1")
    except WorksheetNotFound:
        # もし英語名等なら、先頭シートにフォールバック
        worksheet = sh.get_worksheet(0)

    # ヘッダー取得（良いところは残す）
    headers = worksheet.row_values(1)

except SpreadsheetNotFound:
    st.error("スプレッドシートが見つかりませんでした。SHEET_URL または SHEET_KEY を secrets に設定してください。")
    st.stop()
except APIError as e:
    # もっとも多いのは「シェア権限なし」
    svc_email = st.secrets["google_service_account"].get("client_email", "(不明)")
    st.error(
        "Google API へのアクセスに失敗しました。以下を確認してください：\n"
        "1) スプレッドシートを **サービスアカウントのメール** に“編集者”で共有\n"
        f"   - 共有先メール: **{svc_email}**\n"
        "2) secrets.toml に **SHEET_URL** または **SHEET_KEY** を設定\n"
        "3) GCP で Sheets API / Drive API を有効化\n"
        "4) スプレッドシート自体が削除・アーカイブされていない\n"
        "\n詳細な例外はログに出ています（Streamlit Cloudの Manage app → Logs）。"
    )
    st.stop()

# --- 以降は既存のUI/ロジックを活かす ---
日付 = st.date_input("日付を選んでください", value=date.today())
# ここから下は、あなたが作ってきたフォーム・保存・編集モード等をそのまま続けてOK

日付キー = 日付.strftime("%Y%m%d")

# Googleスプレッドシートの日付列を正規化
dates_raw = worksheet.col_values(1)
def normalize_date(d):
    try:
        return datetime.strptime(str(d).strip(), "%Y/%m/%d").strftime("%Y%m%d")
    except:
        return str(d).strip()

dates = [normalize_date(d) for d in dates_raw]

# 読み込みボタン
if st.button("読み込み", key="load_button"):
    if 日付キー in dates:
        row_index = dates.index(日付キー) + 1
        existing = worksheet.row_values(row_index)
        st.info(f"{日付キー} のデータを読み込みました（編集モード）")
        # ここだけ修正: session_stateにform_を付ける
        for i, col in enumerate(headers[1:], start=1):
            st.session_state[f"form_{col}"] = existing[i] if i < len(existing) else ""
    else:
        st.info(f"{日付キー} は未登録です（新規入力モード）")
        for col in headers:
            if col != "日付":
                st.session_state[f"form_{col}"] = ""

# --- フォーム入力 ---
with st.form("training_form"):
    for col in headers:
        if col == "日付":
            continue

        key_name = f"form_{col}"  # ←重複防止

        # 整数型
        if col in ["年齢", "リフティングレベル"]:
            default_val = safe_int(st.session_state.get(key_name, 0))
            st.number_input(
                label=col, min_value=0, step=1, format="%d",
                value=default_val, key=key_name
            )

        # 小数型
        elif col in [
            "身長", "体重", "4mダッシュ", "50m走", "1.3km",
            "立ち幅跳び", "握力（右）", "握力（左）",
            "リフティング時間", "パントキック", "ゴールキック",
            "ソフトボール投げ", "疲労度"
        ]:
            default_val = safe_float(st.session_state.get(key_name, 0.0))
            st.number_input(
                label=col, step=0.01, format="%.2f",
                value=default_val, key=key_name
            )

        # 文字列
        elif col == "メモ":
            st.text_input(
                label=col,
                value=st.session_state.get(key_name, ""),
                key=key_name
            )

    submitted = st.form_submit_button("保存")

# --- 保存処理 ---
if submitted:
    try:
        日付_str = 日付.strftime("%Y/%m/%d")
        row_data = [日付_str] + [st.session_state[f"form_{col}"] for col in headers if col != "日付"]

        if 日付キー in dates:
            row_index = dates.index(日付キー) + 1
            worksheet.update(
                f"A{row_index}:{chr(65+len(headers)-1)}{row_index}", [row_data]
            )
            st.success(f"{日付_str} のデータを上書きしました！")
        else:
            worksheet.append_row(row_data)
            st.success(f"{日付_str} のデータを追加しました！")

        st.write("✅ 書き込んだデータ:", row_data)

    except Exception as e:
        st.error(f"❌ 保存できませんでした：{e}")

# --- ソート ---
raw_data = worksheet.get_all_values()
headers = raw_data[0]
rows = raw_data[1:]

expected_cols = len(headers)
rows = [r + [""] * (expected_cols - len(r)) for r in rows]

df = pd.DataFrame(rows, columns=headers)
df["日付"] = df["日付"].astype(str).str.strip()

df["日付_dt"] = pd.to_datetime(df["日付"], errors="coerce", format="%Y/%m/%d")
df["日付_dt"] = df["日付_dt"].fillna(pd.to_datetime(df["日付"], errors="coerce", format="%Y%m%d"))
df = df[df["日付_dt"].notna()]
df = df.sort_values(by="日付_dt")
df["日付"] = df["日付_dt"].dt.strftime("%Y/%m/%d")

worksheet.clear()
worksheet.update([df.columns.values.tolist()] + df.drop(columns=["日付_dt"]).astype(str).values.tolist())
st.info("✅ 日付順にソートしました！")







