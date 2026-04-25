# --- START OF FILE sheets.py ---
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

SHEET_ARRIVALS    = "入荷記録"
SHEET_BREWING     = "仕込み記録"
SHEET_MATERIALS   = "原料マスター"
SHEET_MAKERS      = "メーカーマスター"
SHEET_INSPECTORS  = "担当者マスター"
SHEET_ORDER_PTS   = "発注点マスター"
SHEET_ADJUSTMENTS = "在庫調整記録"
SHEET_SUPPLIES    = "資材マスター"
SHEET_SUPPLY_LOGS = "資材入出庫記録"

ARRIVAL_COLS = [
    "arrival_no", "arrival_date", "maker", "lot_no", "material_type",
    "bags", "bags_per_kg", "total_kg", "transport_temp", "appearance", "odor", "packaging",
    "color_check", "contamination", "moisture", "expiry_check", "abnormal_detail", "inspector", "remarks", "registered_at",
    "check_name_std"
]
BREWING_COLS = [
    "no", "brew_date", "product_name", "maker", "lot_no",
    "brew_amount", "material_kg", "seaweed_kg", "starch_kg",
    "starch_type", "lime_kg", "lime_water_l", "notes", "registered_at",
    "seaweed_lot", "starch_lot", "other_additives"
]
ADJUSTMENT_COLS = ["adj_date", "arrival_no", "lot_no", "material_type", "diff_bags", "reason", "registered_at"]
SUPPLY_COLS = ["supply_id", "name", "category", "image_url", "initial_stock"]
SUPPLY_LOG_COLS = ["date", "supply_id", "action_type", "amount", "inspector", "note", "registered_at"]

@st.cache_resource(ttl=0)
def get_client():
    info = dict(st.secrets["gcp_service_account"])
    
    # 🔑 秘密鍵のフォーマット強制補正
    if "private_key" in info:
        pk = info["private_key"]
        # 1. バックスラッシュ+n を実際の改行に変換
        pk = pk.replace("\\n", "\n")
        # 2. 改行が消えて繋がってしまった場合、ヘッダーとフッターで強制的に改行を入れる
        pk = pk.replace("-----BEGIN PRIVATE KEY-----", "-----BEGIN PRIVATE KEY-----\n")
        pk = pk.replace("-----END PRIVATE KEY-----", "\n-----END PRIVATE KEY-----\n")
        # 3. 余分な連続改行を整える
        pk = pk.replace("\n\n\n", "\n").replace("\n\n", "\n")
        info["private_key"] = pk
        
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)

def get_spreadsheet():
    return get_client().open_by_key(st.secrets["spreadsheet"]["sheet_id"])

def ensure_sheet(ss, name: str, headers: list):
    try: return ss.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=name, rows=1000, cols=max(10, len(headers)))
        ws.append_row(headers, value_input_option="RAW")
        return ws

def _sheet_to_df(ws, cols: list) -> pd.DataFrame:
    records = ws.get_all_records()
    if not records: return pd.DataFrame(columns=cols)
    df = pd.DataFrame(records)
    for col in cols:
        if col not in df.columns: df[col] = ""
    return df[cols]

# データの読み書き
def load_arrivals():
    try: return _sheet_to_df(ensure_sheet(get_spreadsheet(), SHEET_ARRIVALS, ARRIVAL_COLS), ARRIVAL_COLS).to_dict("records")
    except: return []
def append_arrival(record):
    ensure_sheet(get_spreadsheet(), SHEET_ARRIVALS, ARRIVAL_COLS).append_row([str(record.get(c, "")) for c in ARRIVAL_COLS], value_input_option="USER_ENTERED")

def load_brewing():
    try:
        df = _sheet_to_df(ensure_sheet(get_spreadsheet(), SHEET_BREWING, BREWING_COLS), BREWING_COLS)
        for col in ["no", "brew_amount", "material_kg", "seaweed_kg", "starch_kg", "lime_kg", "lime_water_l"]:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        return df.to_dict("records")
    except: return []
def append_brewing(record):
    ensure_sheet(get_spreadsheet(), SHEET_BREWING, BREWING_COLS).append_row([str(record.get(c, "")) for c in BREWING_COLS], value_input_option="USER_ENTERED")

def load_adjustments():
    try:
        df = _sheet_to_df(ensure_sheet(get_spreadsheet(), SHEET_ADJUSTMENTS, ADJUSTMENT_COLS), ADJUSTMENT_COLS)
        df["diff_bags"] = pd.to_numeric(df["diff_bags"], errors="coerce").fillna(0)
        return df.to_dict("records")
    except: return []
def append_adjustment(record):
    ensure_sheet(get_spreadsheet(), SHEET_ADJUSTMENTS, ADJUSTMENT_COLS).append_row([str(record.get(c, "")) for c in ADJUSTMENT_COLS], value_input_option="USER_ENTERED")

def load_supplies():
    try: return _sheet_to_df(ensure_sheet(get_spreadsheet(), SHEET_SUPPLIES, SUPPLY_COLS), SUPPLY_COLS).to_dict("records")
    except: return []
def save_supplies(data):
    ws = ensure_sheet(get_spreadsheet(), SHEET_SUPPLIES, SUPPLY_COLS)
    ws.clear(); ws.append_row(SUPPLY_COLS)
    for d in data: ws.append_row([str(d.get(c, "")) for c in SUPPLY_COLS])

def load_supply_logs():
    try: return _sheet_to_df(ensure_sheet(get_spreadsheet(), SHEET_SUPPLY_LOGS, SUPPLY_LOG_COLS), SUPPLY_LOG_COLS).to_dict("records")
    except: return []
def append_supply_log(record):
    ensure_sheet(get_spreadsheet(), SHEET_SUPPLY_LOGS, SUPPLY_LOG_COLS).append_row([str(record.get(c, "")) for c in SUPPLY_LOG_COLS], value_input_option="USER_ENTERED")

# マスター関連
def load_master_list(sheet_name, default_list):
    try:
        vals = ensure_sheet(get_spreadsheet(), sheet_name, ["name"]).col_values(1)[1:]
        return vals if vals else default_list
    except: return default_list
def save_master_list(sheet_name, data):
    ws = ensure_sheet(get_spreadsheet(), sheet_name, ["name"])
    ws.clear(); ws.append_row(["name"])
    for d in data: ws.append_row([d])

def load_materials(): return load_master_list(SHEET_MATERIALS, ["こんにゃく精粉（国産）", "海藻粉", "加工デンプン", "石灰", "食塩"])
def save_materials(data): save_master_list(SHEET_MATERIALS, data)
def load_makers(): return load_master_list(SHEET_MAKERS, ["滝田商店", "荻野", "オリヒロ", "その他"])
def save_makers(data): save_master_list(SHEET_MAKERS, data)
def load_inspectors(): return load_master_list(SHEET_INSPECTORS, ["若槻", "志村", "斎藤"])
def save_inspectors(data): save_master_list(SHEET_INSPECTORS, data)

def load_order_points():
    try:
        df = _sheet_to_df(ensure_sheet(get_spreadsheet(), SHEET_ORDER_PTS, ["material", "pt"]), ["material", "pt"])
        return {r["material"]: float(r["pt"]) for _, r in df.iterrows() if r["material"]}
    except: return {}
def save_order_points(data_dict):
    ws = ensure_sheet(get_spreadsheet(), SHEET_ORDER_PTS, ["material", "pt"])
    ws.clear(); ws.append_row(["material", "pt"])
    for k, v in data_dict.items(): ws.append_row([k, v])

def next_arrival_no(arrivals):
    nums = [int(a["arrival_no"].split("-")[1]) for a in arrivals if "arrival_no" in a and "-" in str(a["arrival_no"])]
    return f"A-{max(nums)+1:04d}" if nums else "A-0001"
def next_brewing_no(brewing):
    nos = [int(b.get("no", 0)) for b in brewing if b.get("no")]
    return max(nos) + 1 if nos else 1
# --- END OF FILE sheets.py ---
