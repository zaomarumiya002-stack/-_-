"""
sheets.py  ─  Google Sheets バックエンド（完全版）
全テーブルの読み書き・採番・デフォルト値を一元管理
"""
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ── シート名定数 ────────────────────────────────────────────────
SH_ARRIVALS   = "入荷記録"
SH_BREWING    = "仕込み記録"
SH_ADJ        = "在庫調整"
SH_SUPPLIES   = "資材マスター"
SH_SUP_LOGS   = "資材入出庫"
SH_MATERIALS  = "原料マスター"
SH_MAKERS     = "メーカーマスター"
SH_INSPECTORS = "担当者マスター"
SH_ORDER_PTS  = "発注点マスター"

# ── 列定義 ─────────────────────────────────────────────────────
COLS_ARRIVALS = [
    "arrival_no","arrival_date","maker","lot_no","material_type",
    "bags","bags_per_kg","total_kg",
    "transport_temp","appearance","odor","packaging",
    "color_check","contamination","moisture","expiry_check",
    "abnormal_detail","inspector","remarks","registered_at"
]
COLS_BREWING = [
    "no","brew_date","product_name","maker","lot_no",
    "brew_amount","material_kg","seaweed_kg","seaweed_lot",
    "starch_kg","starch_lot","starch_type",
    "lime_kg","lime_water_l","other_additives","notes","registered_at"
]
COLS_ADJ = [
    "adj_id","arrival_no","adj_date","diff_bags","reason","inspector","registered_at"
]
COLS_SUPPLIES = [
    "supply_id","name","category","image_url","initial_stock"
]
COLS_SUP_LOGS = [
    "log_id","date","supply_id","action_type","amount","inspector","note","registered_at"
]

# ── デフォルトマスター ──────────────────────────────────────────
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
DEFAULT_INSPECTORS = ["若槻","田中","佐藤","鈴木","その他"]


# ═══════════════════════════════════════════════════════════════
# 接続
# ═══════════════════════════════════════════════════════════════
@st.cache_resource(ttl=0)
def _client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    return gspread.authorize(creds)

def _ss():
    return _client().open_by_key(st.secrets["spreadsheet"]["sheet_id"])

def _ws(ss, name: str, headers: list) -> gspread.Worksheet:
    """シートを取得。なければ作成してヘッダを書く"""
    try:
        return ss.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=name, rows=2000, cols=len(headers))
        ws.append_row(headers, value_input_option="RAW")
        return ws


# ═══════════════════════════════════════════════════════════════
# 汎用読み書き
# ═══════════════════════════════════════════════════════════════
def _read(sheet_name: str, cols: list) -> list[dict]:
    """シートを全件読んで list[dict] を返す。空セルは "" に統一"""
    try:
        ss = _ss()
        ws = _ws(ss, sheet_name, cols)
        rows = ws.get_all_records(expected_headers=cols, default_blank="")
        return rows
    except Exception as e:
        st.warning(f"[sheets._read] {sheet_name}: {e}")
        return []

def _append(sheet_name: str, cols: list, record: dict):
    """1行追記"""
    ss = _ss()
    ws = _ws(ss, sheet_name, cols)
    row = [str(record.get(c, "")) for c in cols]
    ws.append_row(row, value_input_option="USER_ENTERED")

def _update_row(sheet_name: str, cols: list, key_col: str, key_val: str, record: dict):
    """key_col == key_val の行を更新（見つからなければ追記）"""
    ss = _ss()
    ws = _ws(ss, sheet_name, cols)
    cell = ws.find(str(key_val), in_column=cols.index(key_col) + 1)
    if cell:
        row = cell.row
        ws.update(f"A{row}", [[str(record.get(c, "")) for c in cols]])
    else:
        _append(sheet_name, cols, record)

def _overwrite_sheet(sheet_name: str, cols: list, records: list[dict]):
    """シートを全件上書き（マスター保存用）"""
    ss = _ss()
    ws = _ws(ss, sheet_name, cols)
    ws.clear()
    ws.append_row(cols, value_input_option="RAW")
    if records:
        rows = [[str(r.get(c, "")) for c in cols] for r in records]
        ws.append_rows(rows, value_input_option="USER_ENTERED")


# ═══════════════════════════════════════════════════════════════
# 入荷記録
# ═══════════════════════════════════════════════════════════════
def load_arrivals() -> list[dict]:
    rows = _read(SH_ARRIVALS, COLS_ARRIVALS)
    for r in rows:
        r["bags"]       = _flt(r.get("bags", 0))
        r["bags_per_kg"]= _flt(r.get("bags_per_kg", 20))
        r["total_kg"]   = _flt(r.get("total_kg", 0))
    return rows

def append_arrival(record: dict):
    _append(SH_ARRIVALS, COLS_ARRIVALS, record)

def update_arrival(arrival_no: str, record: dict):
    _update_row(SH_ARRIVALS, COLS_ARRIVALS, "arrival_no", arrival_no, record)

def next_arrival_no(arrivals: list) -> str:
    nums = []
    for a in arrivals:
        no = str(a.get("arrival_no", ""))
        if no.startswith("A-"):
            try: nums.append(int(no[2:]))
            except: pass
    return f"A-{(max(nums)+1 if nums else 1):04d}"


# ═══════════════════════════════════════════════════════════════
# 仕込み記録
# ═══════════════════════════════════════════════════════════════
def load_brewing() -> list[dict]:
    rows = _read(SH_BREWING, COLS_BREWING)
    num_cols = ["brew_amount","material_kg","seaweed_kg","starch_kg","lime_kg","lime_water_l"]
    for r in rows:
        for c in num_cols:
            r[c] = _flt(r.get(c, 0))
        r["no"] = _int(r.get("no", 0))
    return rows

def append_brewing(record: dict):
    _append(SH_BREWING, COLS_BREWING, record)

def update_brewing(no: int, record: dict):
    _update_row(SH_BREWING, COLS_BREWING, "no", str(no), record)

def next_brewing_no(brewing: list) -> int:
    nos = [_int(b.get("no", 0)) for b in brewing]
    return (max(nos) + 1) if nos else 1


# ═══════════════════════════════════════════════════════════════
# 在庫調整
# ═══════════════════════════════════════════════════════════════
def load_adjustments() -> list[dict]:
    rows = _read(SH_ADJ, COLS_ADJ)
    for r in rows:
        r["diff_bags"] = _flt(r.get("diff_bags", 0))
    return rows

def append_adjustment(record: dict):
    _append(SH_ADJ, COLS_ADJ, record)


# ═══════════════════════════════════════════════════════════════
# 資材マスター・入出庫ログ
# ═══════════════════════════════════════════════════════════════
def load_supplies() -> list[dict]:
    rows = _read(SH_SUPPLIES, COLS_SUPPLIES)
    for r in rows:
        r["initial_stock"] = _flt(r.get("initial_stock", 0))
    return rows

def save_supplies(records: list[dict]):
    _overwrite_sheet(SH_SUPPLIES, COLS_SUPPLIES, records)

def load_supply_logs() -> list[dict]:
    rows = _read(SH_SUP_LOGS, COLS_SUP_LOGS)
    for r in rows:
        r["amount"] = _flt(r.get("amount", 0))
    return rows

def append_supply_log(record: dict):
    _append(SH_SUP_LOGS, COLS_SUP_LOGS, record)


# ═══════════════════════════════════════════════════════════════
# マスターデータ（原料 / メーカー / 担当者 / 発注点）
# ═══════════════════════════════════════════════════════════════
def _load_single_col(sheet_name: str, default: list) -> list[str]:
    try:
        ss = _ss()
        ws = _ws(ss, sheet_name, [sheet_name])
        vals = ws.col_values(1)[1:]
        return [v for v in vals if v] or default
    except:
        return default

def _save_single_col(sheet_name: str, values: list[str]):
    ss = _ss()
    ws = _ws(ss, sheet_name, [sheet_name])
    ws.clear()
    ws.append_row([sheet_name])
    if values:
        ws.append_rows([[v] for v in values])

def load_materials()  -> list[str]: return _load_single_col(SH_MATERIALS,  DEFAULT_MATERIALS)
def save_materials(v) -> None:       _save_single_col(SH_MATERIALS, v)
def load_makers()     -> list[str]: return _load_single_col(SH_MAKERS,     DEFAULT_MAKERS)
def save_makers(v)    -> None:       _save_single_col(SH_MAKERS, v)
def load_inspectors() -> list[str]: return _load_single_col(SH_INSPECTORS, DEFAULT_INSPECTORS)
def save_inspectors(v)-> None:       _save_single_col(SH_INSPECTORS, v)

def load_order_points() -> dict:
    try:
        ss = _ss()
        ws = _ws(ss, SH_ORDER_PTS, ["material", "order_point"])
        rows = ws.get_all_records(expected_headers=["material","order_point"], default_blank="")
        return {r["material"]: _flt(r.get("order_point", 0)) for r in rows if r.get("material")}
    except:
        return {}

def save_order_points(data: dict):
    ss = _ss()
    ws = _ws(ss, SH_ORDER_PTS, ["material","order_point"])
    ws.clear()
    ws.append_row(["material","order_point"])
    ws.append_rows([[k, str(v)] for k, v in data.items()])


# ═══════════════════════════════════════════════════════════════
# ユーティリティ
# ═══════════════════════════════════════════════════════════════
def _flt(v, default=0.0) -> float:
    try: return float(v) if v != "" else default
    except: return default

def _int(v, default=0) -> int:
    try: return int(float(v)) if v != "" else default
    except: return default
