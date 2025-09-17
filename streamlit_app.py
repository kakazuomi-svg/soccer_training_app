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
worksheet = client.open("サッカー特訓記録").worksheet("シート1")

# 入力フォーム
with st.form("training_form"):
    日付 = st.date_input("日付", value=date.today())
    項目1 = st.text_input("項目1")
    項目2 = st.text_input("項目2")
    項目3 = st.number_input("数値", min_value=0, max_value=100)
    submitted = st.form_submit_button("保存")

if submitted:
    日付キー = 日付.strftime("%Y%m%d")
    dates = worksheet.col_values(1)  # A列の全データ

    if 日付キー in dates:
        # 既存行を上書き
        row_index = dates.index(日付キー) + 1
        worksheet.update(f"A{row_index}:D{row_index}",
                         [[日付キー, 項目1, 項目2, 項目3]])
        st.success(f"{日付キー} のデータを上書きしました！")
    else:
        # 新規追加
        worksheet.append_row([日付キー, 項目1, 項目2, 項目3])
        st.success(f"{日付キー} のデータを追加しました！")

    # ソート処理
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values(by="日付")  # 日付列でソート
        worksheet.clear()
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        st.info("日付順にソートしました！")

