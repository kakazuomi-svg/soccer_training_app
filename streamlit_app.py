import streamlit as st
from datetime import date
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread

# Google認証
SCOPE = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(
    st.secrets["google_service_account"], scopes=SCOPE
)
client = gspread.authorize(creds)
worksheet = client.open("soccer_training").worksheet("シート1")

# ヘッダー行を取得
headers = worksheet.row_values(1)

# 入力フォーム
with st.form("training_form"):
    日付 = st.date_input("日付", value=date.today())
    日付キー = 日付.strftime("%Y%m%d")
    dates = worksheet.col_values(1)

    inputs = {}

    if 日付キー in dates:
        # 既存データを読み込み
        row_index = dates.index(日付キー) + 1
        existing = worksheet.row_values(row_index)

        st.info(f"{日付キー} のデータが既にあります。変更して保存すると上書きされます。")

        for i, col in enumerate(headers[1:], start=2):  # B列以降
            val = existing[i-1] if i-1 < len(existing) else ""
            inputs[col] = st.text_input(col, value=val, key=col)

    else:
        # 新規入力フォーム
        for col in headers:
            if col != "日付":
                inputs[col] = st.text_input(col, key=col)

    submitted = st.form_submit_button("保存")

# 保存処理
if submitted:
    row_data = [日付キー] + [inputs[col] for col in headers if col != "日付"]

    if 日付キー in dates:
        row_index = dates.index(日付キー) + 1
        worksheet.update(
            f"A{row_index}:{chr(65+len(headers)-1)}{row_index}", [row_data]
        )
        st.success(f"{日付キー} のデータを上書きしました！")
    else:
        worksheet.append_row(row_data)
        st.success(f"{日付キー} のデータを追加しました！")

    # 入力欄をリセット
    for col in inputs.keys():
        st.session_state[col] = ""

    # 日付順にソート
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values(by="日付")
        worksheet.clear()
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        st.info("日付順にソートしました！")


