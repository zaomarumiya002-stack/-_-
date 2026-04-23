# --- START OF FILE sheets.py ---
"""Google Sheets 接続・読み書きモジュール"""
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# シート名定義
SHEET_ARRIVALS  = "入荷記録"
SHEET_BREWING   = "仕込み記録"
SHEET_MATERIALS = "原料マスター"
SHEET_MAKERS    = "メーカーマスター"

# 列定義
ARRIVAL_COLS = [
    "arrival_no", "arrival_date", "maker", "lot_no", "material_type",
    "bags", "bags_per_kg", "total_kg",
    "transport_temp", "appearance", "odor", "packaging",
    "color_check", "contamination", "moisture", "expiry_check",
    "abnormal_detail", "inspector", "remarks", "registered_at"
]

BREWING_COLS = [
    "no", "brew_date", "product_name", "maker", "lot_no",
    "seaweed_lot", "starch_lot",  # ← 新規追加
    "brew_amount", "material_kg", "seaweed_kg", "starch_kg",
    "starch_type", "lime_kg", "lime_water_l", "notes", "registered_at"
]

@st.cache_resource(ttl=0)
def get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    return gspread.authorize(creds)

def get_spreadsheet():
    client = get_client()
    return client.open_by_key(st.secrets["spreadsheet"]["sheet_id"])

def ensure_sheet(ss, name: str, headers: list):
    try:
        ws = ss.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=name, rows=1000, cols=len(headers))
        ws.append_row(headers, value_input_option="RAW")
    return ws

def _sheet_to_df(ws, cols: list) -> pd.DataFrame:
    records = ws.get_all_records(expected_headers=cols)
    if not records:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(records)

# ── 入荷記録 ─────────────────────────────────────────────────────
def load_arrivals() -> list[dict]:
    try:
        ss = get_spreadsheet()
        ws = ensure_sheet(ss, SHEET_ARRIVALS, ARRIVAL_COLS)
        df = _sheet_to_df(ws, ARRIVAL_COLS)
        return df.to_dict("records")
    except Exception as e:
        st.error(f"入荷記録の読み込みエラー: {e}")
        return []

def append_arrival(record: dict):
    ss = get_spreadsheet()
    ws = ensure_sheet(ss, SHEET_ARRIVALS, ARRIVAL_COLS)
    row = [str(record.get(c, "")) for c in ARRIVAL_COLS]
    ws.append_row(row, value_input_option="USER_ENTERED")

# ── 仕込み記録 ───────────────────────────────────────────────────
def load_brewing() -> list[dict]:
    try:
        ss = get_spreadsheet()
        ws = ensure_sheet(ss, SHEET_BREWING, BREWING_COLS)
        df = _sheet_to_df(ws, BREWING_COLS)
        # 数値列を変換
        for col in ["no","brew_amount","material_kg","seaweed_kg","starch_kg","lime_kg","lime_water_l"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        return df.to_dict("records")
    except Exception as e:
        st.error(f"仕込み記録の読み込みエラー: {e}")
        return []

def append_brewing(record: dict):
    ss = get_spreadsheet()
    ws = ensure_sheet(ss, SHEET_BREWING, BREWING_COLS)
    row = [str(record.get(c, "")) for c in BREWING_COLS]
    ws.append_row(row, value_input_option="USER_ENTERED")

# ── マスター ─────────────────────────────────────────────────────
DEFAULT_MATERIALS = [
    "こんにゃく精粉（国産）", "こんにゃく精粉（輸入）",
    "海藻粉", "加工デンプン（ゆり8）", "加工デンプン（VA70）",
    "加工デンプン（その他）", "石灰", "食塩",
    "こんにゃくマンナン", "芋こんにゃく粉",
    "乾燥こんにゃく粉", "混合こんにゃく粉",
    "海藻エキス", "炭酸水素ナトリウム",
    "焼成貝カルシウム", "グルコマンナン",
    "凝固剤（水酸化カルシウム）", "天然着色料（黒ごま）",
    "天然着色料（海藻）", "その他原料"
]
DEFAULT_MAKERS = ["滝田商店", "荻野", "オリヒロ", "クリタ", "その他"]

def load_materials() -> list[str]:
    try:
        ss = get_spreadsheet()
        ws = ensure_sheet(ss, SHEET_MATERIALS, ["material_name"])
        vals = ws.col_values(1)[1:] 
        return vals if vals else DEFAULT_MATERIALS
    except:
        return DEFAULT_MATERIALS

def save_materials(materials: list[str]):
    ss = get_spreadsheet()
    ws = ensure_sheet(ss, SHEET_MATERIALS, ["material_name"])
    ws.clear()
    ws.append_row(["material_name"])
    for m in materials:
        ws.append_row([m])

def load_makers() -> list[str]:
    try:
        ss = get_spreadsheet()
        ws = ensure_sheet(ss, SHEET_MAKERS, ["maker_name"])
        vals = ws.col_values(1)[1:]
        return vals if vals else DEFAULT_MAKERS
    except:
        return DEFAULT_MAKERS

def save_makers(makers: list[str]):
    ss = get_spreadsheet()
    ws = ensure_sheet(ss, SHEET_MAKERS, ["maker_name"])
    ws.clear()
    ws.append_row(["maker_name"])
    for m in makers:
        ws.append_row([m])

def next_arrival_no(arrivals: list) -> str:
    if not arrivals:
        return "A-0001"
    nums = []
    for a in arrivals:
        no = str(a.get("arrival_no", ""))
        if "-" in no:
            try:
                nums.append(int(no.split("-")[1]))
            except:
                pass
    return f"A-{max(nums)+1:04d}" if nums else "A-0001"

def next_brewing_no(brewing: list) -> int:
    if not brewing:
        return 1
    nos = [int(b.get("no", 0)) for b in brewing if b.get("no")]
    return max(nos) + 1 if nos else 1
# --- END OF FILE sheets.py ---
