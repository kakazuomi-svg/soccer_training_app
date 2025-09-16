import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe, get_as_dataframe

# ===== Google Sheets 接続 =====
SHEET_NAME = "soccer_training"   # スプレッドシート名
WORKSHEET = "シート1"             # ワークシート名（変更してOK）

# 認証スコープ
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# credentials.json を使って認証
creds = Credentials.from_service_account_file(
    r"C:\Users\kakaz\Desktop\soccer_training_app\credentials.json",
    scopes=SCOPE
)
client = gspread.authorize(creds)# ワークシートを開く
sheet = client.open(SHEET_NAME).worksheet(WORKSHEET)

# ===== データ読み込み =====
df = get_as_dataframe(sheet, evaluate_formulas=True, header=0)
df = df.dropna(how="all")  # 空行削除

# ===== Streamlit アプリ =====
st.title("⚽ サッカー特訓データ編集アプリ")

# 編集用テーブル
edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

# 保存ボタン
if st.button("変更を保存"):
    sheet.clear()  # ワークシートをクリア
    set_with_dataframe(sheet, edited_df)
    st.success("✅ スプレッドシートを更新しました！")
