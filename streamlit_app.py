import streamlit as st
from datetime import date
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread

SCOPE = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

creds = Credentials.from_service_account_info(
    st.secrets["google_service_account"], scopes=SCOPE
)
client = gspread.authorize(creds)
worksheet = client.open("soccer_training").worksheet("シート1")

# 1行目をヘッダーとして取得
headers = worksheet.row_values(1)
st.write("読み込んだヘッダー:", headers)


with st.form("training_form"):
    日付 = st.date_input("日付", value=date.today())
    inputs = {}
    for col in headers:
        if col != "日付":  # 日付列は自動入力
            inputs[col] = st.text_input(col)
    submitted = st.form_submit_button("保存")

if submitted:
    日付キー = 日付.strftime("%Y%m%d")
    dates = worksheet.col_values(1)

    # 1行分のデータを作成
    row_data = [日付キー] + [inputs[col] for col in headers if col != "日付"]

    if 日付キー in dates:
        row_index = dates.index(日付キー) + 1
        worksheet.update(f"A{row_index}:{chr(65+len(headers)-1)}{row_index}",
                         [row_data])
        st.success(f"{日付キー} のデータを上書きしました！")
    else:
        worksheet.append_row(row_data)
        st.success(f"{日付キー} のデータを追加しました！")

    # ソート
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values(by="日付")
        worksheet.clear()
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        st.info("日付順にソートしました！")

