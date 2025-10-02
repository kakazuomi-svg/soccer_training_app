import streamlit as st
from datetime import date
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread

# --- 安全な数値変換用の関数 ---
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

# --- Google認証 ---
SCOPE = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(
    st.secrets["google_service_account"], scopes=SCOPE
)
client = gspread.authorize(creds)
worksheet = client.open("soccer_training").worksheet("シート1")

# ヘッダー取得
headers = worksheet.row_values(1)


# 日付入力
日付 = st.date_input("日付を選んでください", value=date.today())
日付キー = int(日付.strftime("%Y%m%d"))  # ← ここを整数にする
dates = worksheet.col_values(1)

# 読み込みボタン
if st.button("読み込み"):
    if 日付キー in dates:
        row_index = dates.index(日付キー) + 1
        existing = worksheet.row_values(row_index)
        st.info(f"{日付キー} のデータを読み込みました（編集モード）")
        for i, col in enumerate(headers[1:], start=1):  # B列以降
            st.session_state[col] = existing[i] if i < len(existing) else ""
    else:
        st.info(f"{日付キー} は未登録です（新規入力モード）")
        for col in headers:
            if col != "日付":
                st.session_state[col] = ""

# --- フォーム入力 ---
with st.form("training_form"):
    for col in headers:
        if col == "日付":
            continue

        # 整数型
        if col in ["年齢", "リフティングレベル"]:
            st.session_state[col] = safe_int(st.session_state.get(col, ""))
            st.number_input(
                col, key=col, step=1, format="%d",
                value=st.session_state[col]
            )

        # 小数型
        elif col in [
            "身長", "体重", "4mダッシュ", "50m走", "1.3km",
            "立ち幅跳び", "握力（右）", "握力（左）",
            "リフティング時間", "パントキック", "ゴールキック",
            "ソフトボール投げ", "疲労度"
        ]:
            st.session_state[col] = safe_float(st.session_state.get(col, ""))
            st.number_input(
                col, key=col, step=0.01, format="%.2f",
                value=st.session_state[col]
            )

        # 文字列
        elif col == "メモ":
            st.text_input(col, key=col, value=st.session_state.get(col, ""))

    submitted = st.form_submit_button("保存")

from datetime import datetime

if submitted:
    try:
        日付_dt = datetime.strptime(str(日付キー), "%Y%m%d")
        日付_str = 日付_dt.strftime("%Y/%m/%d")  # ←★ここ重要！！

        row_data = [日付_str] + [st.session_state[col] for col in headers if col != "日付"]

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

 # 入力欄リセット
if "initialized" not in st.session_state:
    for col in headers:
        if col and col.strip() and col != "日付":
            st.session_state[col] = ""
    st.session_state["initialized"] = True

# ソート
raw_data = worksheet.get_all_values()
headers = raw_data[0]
rows = raw_data[1:]

# 行数補完
expected_cols = len(headers)
rows = [r + [""] * (expected_cols - len(r)) for r in rows]

# DataFrame化（rows: 2次元配列, headers: 1行目）
df = pd.DataFrame(rows, columns=headers)

# 日付列を datetime に変換（形式が2種類混在しても対応）
df["日付_dt"] = pd.to_datetime(df["日付"], errors="coerce", format="%Y/%m/%d")
df["日付_dt"] = df["日付_dt"].fillna(pd.to_datetime(df["日付"], errors="coerce", format="%Y%m%d"))

# NaT（変換失敗）を除外
df = df[df["日付_dt"].notna()]

# ソート
df = df.sort_values(by="日付_dt")

# 「日付」列を統一フォーマットに変換して再保存
df["日付"] = df["日付_dt"].dt.strftime("%Y/%m/%d")

# 書き戻し
worksheet.clear()
worksheet.update([df.columns.values.tolist()] + df.drop(columns=["日付_dt"]).astype(str).values.tolist())

st.info("✅ 日付順にソートしました！")













