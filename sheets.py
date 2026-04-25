# --- START OF FILE sheets.py ---
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SH_ARRIVALS   = "入荷記録"
SH_BREWING    = "仕込み記録"
SH_ADJ        = "在庫調整"
SH_SUPPLIES   = "資材マスター"
SH_SUP_LOGS   = "資材入出庫"
SH_MATERIALS  = "原料マスター"
SH_MAKERS     = "メーカーマスター"
SH_INSPECTORS = "担当者マスター"
SH_ORDER_PTS  = "発注点マスター"

COLS_ARRIVALS = [
    "arrival_no","arrival_date","maker","lot_no","material_type",
    "bags","bags_per_kg","total_kg","transport_temp","appearance","odor","packaging",
    "color_check","contamination","moisture","expiry_check","abnormal_detail",
    "inspector","remarks","registered_at","check_name_std"
]
COLS_BREWING = [
    "no","brew_date","product_name","maker","lot_no",
    "brew_amount","material_kg","seaweed_kg","seaweed_lot",
    "starch_kg","starch_lot","starch_type",
    "lime_kg","lime_water_l","other_additives","notes","registered_at"
]
COLS_ADJ = ["adj_id","arrival_no","adj_date","diff_bags","reason","inspector","registered_at"]
COLS_SUPPLIES = ["supply_id","name","category","image_url","initial_stock"]
COLS_SUP_LOGS = ["log_id","date","supply_id","action_type","amount","inspector","note","registered_at"]

DEFAULT_MATERIALS = [
    "こんにゃく精粉（国産）","こんにゃく精粉（輸入）","海藻粉",
    "加工デンプン（ゆり8）","加工デンプン（VA70）","加工デンプン（その他）",
    "石灰","食塩","こんにゃくマンナン","芋こんにゃく粉",
    "乾燥こんにゃく粉","混合こんにゃく粉","海藻エキス",
    "炭酸水素ナトリウム","焼成貝カルシウム","グルコマンナン",
    "凝固剤（水酸化カルシウム）","天然着色料（黒ごま）",
    "天然着色料（海藻）","その他原料"
]
DEFAULT_MAKERS     = ["滝田商店","荻野","オリヒロ","クリタ","その他"]
DEFAULT_INSPECTORS = ["若槻","志村","斎藤","その他"]

@st.cache_resource(ttl=0)
def _client():
    info = dict(st.secrets["gcp_service_account"])
    if "private_key" in info:
        pk = info["private_key"].replace("\\n", "\n")
        pk = pk.replace("-----BEGIN PRIVATE KEY-----", "-----BEGIN PRIVATE KEY-----\n")
        pk = pk.replace("-----END PRIVATE KEY-----", "\n-----END PRIVATE KEY-----\n")
        info["private_key"] = pk.replace("\n\n\n", "\n").replace("\n\n", "\n")
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)

def _ss(): return _client().open_by_key(st.secrets["spreadsheet"]["sheet_id"])

def _ws(ss, name: str, headers: list):
    try: return ss.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=name, rows=2000, cols=max(10, len(headers)))
        ws.update(range_name="A1", values=[headers])
        return ws

def _read(sheet_name: str, cols: list) -> list[dict]:
    try:
        ss = _ss()
        ws = _ws(ss, sheet_name, cols)
        
        # 🌟 修正ポイント: expected_headers 制約を外し、列が足りなくてもエラーにせず読み込む
        records = ws.get_all_records(default_blank="")
        if not records: return []
        
        # 自己修復: 足りない列名があればシート1行目に書き足し、データにも空欄を補完する
        df = pd.DataFrame(records)
        missing_cols = [c for c in cols if c not in df.columns]
        if missing_cols:
            ws.update(range_name="A1", values=[cols])
            for c in missing_cols: df[c] = ""
            
        for c in cols:
            if c not in df.columns: df[c] = ""
            
        return df[cols].to_dict("records")
    except Exception as e:
        print(f"Error reading {sheet_name}: {e}")
        return []

def _append(sheet_name: str, cols: list, record: dict):
    ss = _ss()
    ws = _ws(ss, sheet_name, cols)
    row = [str(record.get(c, "")) for c in cols]
    ws.append_row(row, value_input_option="USER_ENTERED")

def _update_row(sheet_name: str, cols: list, key_col: str, key_val: str, record: dict):
    ss = _ss()
    ws = _ws(ss, sheet_name, cols)
    col_idx = cols.index(key_col) + 1
    col_vals = ws.col_values(col_idx)
    
    if str(key_val) in col_vals:
        row = col_vals.index(str(key_val)) + 1
        ws.update(range_name=f"A{row}", values=[[str(record.get(c, "")) for c in cols]])
    else:
        _append(sheet_name, cols, record)

def _overwrite_sheet(sheet_name: str, cols: list, records: list[dict]):
    ss = _ss()
    ws = _ws(ss, sheet_name, cols)
    ws.clear()
    ws.update(range_name="A1", values=[cols] + [[str(r.get(c, "")) for c in cols] for r in records])

# ── 数値変換（カンマ対応） ──
def _flt(v, default=0.0) -> float:
    try:
        if isinstance(v, str): v = v.replace(",", "")
        return float(v) if str(v).strip() != "" else default
    except: return default

def _int(v, default=0) -> int:
    try:
        if isinstance(v, str): v = v.replace(",", "")
        return int(float(v)) if str(v).strip() != "" else default
    except: return default

# ── 各テーブルアクセス ──
def load_arrivals() -> list[dict]:
    rows = _read(SH_ARRIVALS, COLS_ARRIVALS)
    for r in rows:
        r["bags"] = _flt(r.get("bags", 0))
        r["bags_per_kg"] = _flt(r.get("bags_per_kg", 20))
        r["total_kg"] = _flt(r.get("total_kg", 0))
    return rows
def append_arrival(record: dict): _append(SH_ARRIVALS, COLS_ARRIVALS, record)
def update_arrival(arrival_no: str, record: dict): _update_row(SH_ARRIVALS, COLS_ARRIVALS, "arrival_no", arrival_no, record)
def next_arrival_no(arrivals: list) -> str:
    nums = [int(a["arrival_no"].split("-")[1]) for a in arrivals if "arrival_no" in a and "-" in str(a["arrival_no"])]
    return f"A-{(max(nums)+1 if nums else 1):04d}"

def load_brewing() -> list[dict]:
    rows = _read(SH_BREWING, COLS_BREWING)
    num_cols = ["brew_amount","material_kg","seaweed_kg","starch_kg","lime_kg","lime_water_l"]
    for r in rows:
        for c in num_cols: r[c] = _flt(r.get(c, 0))
        r["no"] = _int(r.get("no", 0))
    return rows
def append_brewing(record: dict): _append(SH_BREWING, COLS_BREWING, record)
def update_brewing(no: int, record: dict): _update_row(SH_BREWING, COLS_BREWING, "no", str(no), record)
def next_brewing_no(brewing: list) -> int:
    nos = [_int(b.get("no", 0)) for b in brewing]
    return (max(nos) + 1) if nos else 1

def load_adjustments() -> list[dict]:
    rows = _read(SH_ADJ, COLS_ADJ)
    for r in rows: r["diff_bags"] = _flt(r.get("diff_bags", 0))
    return rows
def append_adjustment(record: dict): _append(SH_ADJ, COLS_ADJ, record)

def load_supplies() -> list[dict]:
    rows = _read(SH_SUPPLIES, COLS_SUPPLIES)
    for r in rows: r["initial_stock"] = _flt(r.get("initial_stock", 0))
    return rows
def save_supplies(records: list[dict]): _overwrite_sheet(SH_SUPPLIES, COLS_SUPPLIES, records)

def load_supply_logs() -> list[dict]:
    rows = _read(SH_SUP_LOGS, COLS_SUP_LOGS)
    for r in rows: r["amount"] = _flt(r.get("amount", 0))
    return rows
def append_supply_log(record: dict): _append(SH_SUP_LOGS, COLS_SUP_LOGS, record)

def _load_single_col(sheet_name: str, default: list) -> list[str]:
    try:
        vals = _ws(_ss(), sheet_name, ["name"]).col_values(1)[1:]
        return [v for v in vals if v] or default
    except: return default
def _save_single_col(sheet_name: str, values: list[str]):
    ws = _ws(_ss(), sheet_name, ["name"])
    ws.clear()
    ws.update(range_name="A1", values=[["name"]] + [[v] for v in values])

def load_materials()  -> list[str]: return _load_single_col(SH_MATERIALS, DEFAULT_MATERIALS)
def save_materials(v) -> None:       _save_single_col(SH_MATERIALS, v)
def load_makers()     -> list[str]: return _load_single_col(SH_MAKERS, DEFAULT_MAKERS)
def save_makers(v)    -> None:       _save_single_col(SH_MAKERS, v)
def load_inspectors() -> list[str]: return _load_single_col(SH_INSPECTORS, DEFAULT_INSPECTORS)
def save_inspectors(v)-> None:       _save_single_col(SH_INSPECTORS, v)

def load_order_points() -> dict:
    try:
        rows = _ws(_ss(), SH_ORDER_PTS, ["material", "order_point"]).get_all_records(default_blank="")
        return {r["material"]: _flt(r.get("order_point", 0)) for r in rows if r.get("material")}
    except: return {}
def save_order_points(data: dict):
    ws = _ws(_ss(), SH_ORDER_PTS, ["material","order_point"])
    ws.clear()
    ws.update(range_name="A1", values=[["material","order_point"]] + [[k, str(v)] for k, v in data.items()])
# --- END OF FILE sheets.py ---
