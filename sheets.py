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

SHEET_ARRIVALS    = "入荷記録"
SHEET_BREWING     = "仕込み記録"
SHEET_MATERIALS   = "原料マスター"
SHEET_MAKERS      = "メーカーマスター"
SHEET_INSPECTORS  = "担当者マスター"
SHEET_ORDER_PTS   = "発注点マスター"
SHEET_ADJUSTMENTS = "在庫調整記録"

ARRIVAL_COLS = [
    "arrival_no", "arrival_date", "maker", "lot_no", "material_type",
    "bags", "bags_per_kg", "total_kg", "transport_temp", "appearance", "odor", "packaging",
    "color_check", "contamination", "moisture", "expiry_check", "abnormal_detail", "inspector", "remarks", "registered_at"
]

# other_additives を最後に追加
BREWING_COLS = [
    "no", "brew_date", "product_name", "maker", "lot_no",
    "brew_amount", "material_kg", "seaweed_kg", "starch_kg",
    "starch_type", "lime_kg", "lime_water_l", "notes", "registered_at",
    "seaweed_lot", "starch_lot", "other_additives"
]

ADJUSTMENT_COLS = [
    "adj_date", "arrival_no", "lot_no", "material_type", "diff_kg", "reason", "registered_at"
]

@st.cache_resource(ttl=0)
def get_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    return gspread.authorize(creds)

def get_spreadsheet():
    return get_client().open_by_key(st.secrets["spreadsheet"]["sheet_id"])

def ensure_sheet(ss, name: str, headers: list):
    try:
        ws = ss.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=name, rows=1000, cols=max(10, len(headers)))
        ws.append_row(headers, value_input_option="RAW")
    return ws

def _sheet_to_df(ws, cols: list) -> pd.DataFrame:
    records = ws.get_all_records()
    if not records:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(records)
    for col in cols:
        if col not in df.columns: df[col] = ""
    return df[cols]

def load_arrivals() -> list[dict]:
    try: return _sheet_to_df(ensure_sheet(get_spreadsheet(), SHEET_ARRIVALS, ARRIVAL_COLS), ARRIVAL_COLS).to_dict("records")
    except: return []

def append_arrival(record: dict):
    ensure_sheet(get_spreadsheet(), SHEET_ARRIVALS, ARRIVAL_COLS).append_row([str(record.get(c, "")) for c in ARRIVAL_COLS], value_input_option="USER_ENTERED")

def load_brewing() -> list[dict]:
    try:
        df = _sheet_to_df(ensure_sheet(get_spreadsheet(), SHEET_BREWING, BREWING_COLS), BREWING_COLS)
        for col in ["no","brew_amount","material_kg","seaweed_kg","starch_kg","lime_kg","lime_water_l"]:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        return df.to_dict("records")
    except: return []

def append_brewing(record: dict):
    ensure_sheet(get_spreadsheet(), SHEET_BREWING, BREWING_COLS).append_row([str(record.get(c, "")) for c in BREWING_COLS], value_input_option="USER_ENTERED")

def load_adjustments() -> list[dict]:
    try:
        df = _sheet_to_df(ensure_sheet(get_spreadsheet(), SHEET_ADJUSTMENTS, ADJUSTMENT_COLS), ADJUSTMENT_COLS)
        df["diff_kg"] = pd.to_numeric(df["diff_kg"], errors="coerce").fillna(0)
        return df.to_dict("records")
    except: return []

def append_adjustment(record: dict):
    ensure_sheet(get_spreadsheet(), SHEET_ADJUSTMENTS, ADJUSTMENT_COLS).append_row([str(record.get(c, "")) for c in ADJUSTMENT_COLS], value_input_option="USER_ENTERED")

DEFAULT_MATERIALS = ["こんにゃく精粉（国産）", "こんにゃく精粉（輸入）", "海藻粉", "加工デンプン", "石灰", "食塩", "着色料（黒ごま）"]
def load_materials():
    try:
        vals = ensure_sheet(get_spreadsheet(), SHEET_MATERIALS, ["material_name"]).col_values(1)[1:]
        return vals if vals else DEFAULT_MATERIALS
    except: return DEFAULT_MATERIALS
def save_materials(data):
    ws = ensure_sheet(get_spreadsheet(), SHEET_MATERIALS, ["material_name"])
    ws.clear()
    ws.append_row(["material_name"])
    for d in data: ws.append_row([d])

DEFAULT_MAKERS = ["滝田商店", "荻野", "オリヒロ", "クリタ", "その他"]
def load_makers():
    try:
        vals = ensure_sheet(get_spreadsheet(), SHEET_MAKERS, ["maker_name"]).col_values(1)[1:]
        return vals if vals else DEFAULT_MAKERS
    except: return DEFAULT_MAKERS
def save_makers(data):
    ws = ensure_sheet(get_spreadsheet(), SHEET_MAKERS, ["maker_name"])
    ws.clear()
    ws.append_row(["maker_name"])
    for d in data: ws.append_row([d])

DEFAULT_INSPECTORS = ["若槻", "志村", "斎藤"]
def load_inspectors():
    try:
        vals = ensure_sheet(get_spreadsheet(), SHEET_INSPECTORS, ["inspector_name"]).col_values(1)[1:]
        return vals if vals else DEFAULT_INSPECTORS
    except: return DEFAULT_INSPECTORS
def save_inspectors(data):
    ws = ensure_sheet(get_spreadsheet(), SHEET_INSPECTORS, ["inspector_name"])
    ws.clear()
    ws.append_row(["inspector_name"])
    for d in data: ws.append_row([d])

def load_order_points() -> dict:
    try:
        df = _sheet_to_df(ensure_sheet(get_spreadsheet(), SHEET_ORDER_PTS, ["material_name", "order_point_kg"]), ["material_name", "order_point_kg"])
        return {r["material_name"]: float(r["order_point_kg"]) for _, r in df.iterrows() if r["material_name"]}
    except: return {}
def save_order_points(data_dict: dict):
    ws = ensure_sheet(get_spreadsheet(), SHEET_ORDER_PTS, ["material_name", "order_point_kg"])
    ws.clear()
    ws.append_row(["material_name", "order_point_kg"])
    for k, v in data_dict.items(): ws.append_row([k, v])

def next_arrival_no(arrivals):
    nums = [int(a["arrival_no"].split("-")[1]) for a in arrivals if "arrival_no" in a and "-" in str(a["arrival_no"])]
    return f"A-{max(nums)+1:04d}" if nums else "A-0001"
def next_brewing_no(brewing):
    nos = [int(b.get("no", 0)) for b in brewing if b.get("no")]
    return max(nos) + 1 if nos else 1
# --- END OF FILE sheets.py ---
