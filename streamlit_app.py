import streamlit as st
from datetime import date, datetime
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

# 日付選択
日付 = st.date_input("日付を選んでください", value=date.today())
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






