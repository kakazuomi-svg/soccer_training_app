import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials
import json

# ====== 認証とシート接続 ======
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(st.secrets["gcp_service_account"])
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)
sheet = client.open("soccer_training")  # あなたのスプレッドシート名
worksheet = sheet.worksheet("シート1")  # ワークシート名

# ====== 項目定義 ======
headers = worksheet.row_values(1) if worksheet.row_values(1) else ["日付", "年齢", "身長", "体重", "4mダッシュ"]

# ====== データ読み込みと整形 ======
data = worksheet.get_all_records()
df = pd.DataFrame(data)
if not df.empty:
    df["日付"] = df["日付"].astype(str)
    dates = df["日付"].tolist()
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
                st.session_state[col] = 0.0
            st.number_input(col, key=col)
    submitted = st.form_submit_button("保存")

# ====== 保存処理 ======
if submitted:
    日付キー = st.session_state["日付"]
    日付8桁 = 日付キー.strftime("%Y%m%d")
    row_data = [日付8桁] + [st.session_state[col] for col in headers if col != "日付"]

    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    df["日付"] = df["日付"].astype(str)
    dates = df["日付"].tolist()

    if 日付8桁 in dates:
        row_index = dates.index(日付8桁) + 2
        worksheet.update(f"A{row_index}:{chr(65+len(headers)-1)}{row_index}", [row_data])
        st.success(f"{日付8桁} のデータを上書きしました！")
    else:
        worksheet.append_row(row_data)
        st.success(f"{日付8桁} のデータを追加しました！")

    for col in headers:
        if col != "日付" and col in st.session_state:
            st.session_state[col] = "" if isinstance(st.session_state[col], str) else 0.0

    # ====== 再読み込み＆ソート ======
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty:
        df["日付"] = df["日付"].astype(str)
        df = df.sort_values("日付")
        worksheet.clear()
        worksheet.update([df.columns.tolist()] + df.values.tolist())
        st.info("日付順にソートしました！")
        


