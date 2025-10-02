import streamlit as st
import pandas as pd
import gspread
from datetime import date
from oauth2client.service_account import ServiceAccountCredentials

# ====== Google Sheets認証・接続 ======
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# スプレッドシートとワークシートを指定
SHEET_NAME = "シート1"
WORKSHEET_NAME = "シート1"
worksheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)

# ====== ヘッダーを定義（シートと合わせて） ======
headers = ["日付", "年齢", "メモ"]  # 必要に応じて増やしてOK！

# ====== データ読み込みと日付整形 ======
data = worksheet.get_all_records()
df = pd.DataFrame(data)

if not df.empty:
    df["日付"] = pd.to_datetime(df["日付"], errors="coerce")
    dates = df["日付"].dt.strftime("%Y-%m-%d").tolist()
else:
    df = pd.DataFrame(columns=headers)
    dates = []

# ====== 入力フォーム ======
with st.form("入力フォーム"):
    for col in headers:
        if col == "日付":
            if col not in st.session_state:
                st.session_state[col] = date.today()
            st.date_input(col, key=col)
        elif col == "メモ":
            if col not in st.session_state:
                st.session_state[col] = ""
            st.text_input(col, key=col)
        else:
            if col not in st.session_state:
                st.session_state[col] = 0
            st.number_input(col, key=col)

    submitted = st.form_submit_button("保存")

# ====== 保存処理 ======
if submitted:
    日付キー = st.session_state["日付"]
    日付文字列 = 日付キー.strftime("%Y-%m-%d")

    row_data = [日付文字列] + [st.session_state[col] for col in headers if col != "日付"]

    if 日付文字列 in dates:
        row_index = dates.index(日付文字列) + 2  # +2 = ヘッダー行 + 1-index
        worksheet.update(
            f"A{row_index}:{chr(65 + len(headers) - 1)}{row_index}",
            [row_data]
        )
        st.success(f"{日付文字列} のデータを上書きしました！")
    else:
        worksheet.append_row(row_data)
        st.success(f"{日付文字列} のデータを追加しました！")

    # 入力欄リセット
    for col in headers:
        if col != "日付":
            st.session_state[col] = "" if isinstance(st.session_state[col], str) else 0

    # データ再取得＋日付ソート
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)

    if not df.empty:
        df["日付"] = pd.to_datetime(df["日付"], errors="coerce")
        df = df.sort_values(by="日付")
        worksheet.clear()
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        st.info("日付順にソートしました！")



