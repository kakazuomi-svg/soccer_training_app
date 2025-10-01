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

# ヘッダー取得
headers = worksheet.row_values(1)

# カラム分類
date_cols = ["日付"]
int_cols = ["年齢", "リフティングレベル"]
float_cols = [
    "身長", "体重", "4mダッシュ", "50m走", "1.3km",
    "立ち幅跳び", "握力（右）", "握力（左）",
    "リフティング時間", "パントキック", "ゴールキック", "ソフトボール投げ", "疲労度"
]
string_cols = ["メモ"]

# 日付入力
日付 = st.date_input("日付を選んでください", value=date.today())
日付キー = 日付.strftime("%Y%m%d")
dates = worksheet.col_values(1)

# 読み込みボタン
if st.button("読み込み"):
    if 日付キー in dates:
        row_index = dates.index(日付キー) + 1
        existing = worksheet.row_values(row_index)
        st.info(f"{日付キー} のデータを読み込みました（編集モード）")
        for i, col in enumerate(headers[1:], start=1):  # B列以降
            if col in int_cols:
                st.session_state[col] = int(existing[i]) if i < len(existing) and existing[i] != "" else 0
            elif col in float_cols:
                st.session_state[col] = float(existing[i]) if i < len(existing) and existing[i] != "" else 0.0
            elif col in string_cols:
                st.session_state[col] = existing[i] if i < len(existing) else ""
            else:
                st.session_state[col] = ""
    else:
        st.info(f"{日付キー} は未登録です（新規入力モード）")
        for col in headers:
            if col in int_cols:
                st.session_state[col] = 0
            elif col in float_cols:
                st.session_state[col] = 0.0
            elif col in string_cols:
                st.session_state[col] = ""
            else:
                st.session_state[col] = ""

# フォーム
with st.form("training_form"):
    for col in headers:
        if col == "日付":
            continue
        if col in int_cols:
            st.number_input(col, key=col, step=1, format="%d", value=int(st.session_state[col]))
        elif col in float_cols:
            st.number_input(col, key=col, step=0.01, format="%.2f", value=float(st.session_state[col]))
        elif col in string_cols:
            st.text_input(col, key=col, value=st.session_state[col])
    submitted = st.form_submit_button("保存")

# 保存処理
if submitted:
    row_data = [日付キー] + [st.session_state[col] for col in headers if col != "日付"]

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
    for col in headers:
        if col in int_cols:
            st.session_state[col] = 0
        elif col in float_cols:
            st.session_state[col] = 0.0
        elif col in string_cols:
            st.session_state[col] = ""

    # ソート
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values(by="日付")
        worksheet.clear()
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        st.info("日付順にソートしました！")








