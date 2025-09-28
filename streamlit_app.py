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

# 日付入力（先に選ぶ）
日付 = st.date_input("日付を選んでください", value=date.today())
日付キー = 日付.strftime("%Y%m%d")
dates = worksheet.col_values(1)

# 「読み込み」ボタン
if st.button("読み込み"):
    if 日付キー in dates:
        # 登録済み → 既存データを読み込む
        row_index = dates.index(日付キー) + 1
        existing = worksheet.row_values(row_index)
        st.session_state["inputs"] = {
            col: (existing[i] if i < len(existing) else "")
            for i, col in enumerate(headers[1:], start=1)
        }
        st.info(f"{日付キー} のデータを読み込みました（編集モード）")
    else:
        # 未登録 → 空欄フォーム
        st.session_state["inputs"] = {col: "" for col in headers if col != "日付"}
        st.info(f"{日付キー} のデータは未登録です（新規入力モード）")

# フォーム
with st.form("training_form"):
    inputs = st.session_state.get("inputs", {col: "" for col in headers if col != "日付"})
    for col in headers:
        if col != "日付":
            inputs[col] = st.text_input(col, value=inputs[col], key=col)
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

    # 入力欄リセット
    st.session_state["inputs"] = {col: "" for col in headers if col != "日付"}

    # 日付順にソート
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values(by="日付")
        worksheet.clear()
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        st.info("日付順にソートしました！")
