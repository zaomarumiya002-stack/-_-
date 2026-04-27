# --- START OF FILE sheets.py ---
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# スプレッドシートの列名をすべて日本語に統一
COLS_ARR = ["入荷No", "入荷日", "メーカー", "ロットNo", "原料種別", "袋数", "1袋重量(kg)", "総量(kg)", "搬入温度", "外観", "臭い", "包装", "色調", "異物", "水分", "賞味期限", "異常内容", "担当者", "備考", "登録日時", "品名・規格確認"]
COLS_BRW = ["仕込No", "仕込日", "品名", "メーカー", "主原料ロット", "仕込量(kg)", "こんにゃく精粉(kg)", "海藻粉(kg)", "海藻粉ロット", "デンプン(kg)", "デンプンロット", "デンプン種別", "石灰(kg)", "石灰水(L)", "その他添加物", "備考", "登録日時"]
COLS_ADJ = ["調整ID", "入荷No", "調整日", "調整袋数", "理由", "担当者", "登録日時"]
COLS_SUP = ["資材ID", "資材名", "カテゴリ", "画像URL", "初期在庫"]
COLS_LOG = ["ログID", "登録日", "資材ID", "処理", "数量", "作業者", "備考", "登録日時"]

@st.cache_resource(ttl=0)
def _client():
    info = dict(st.secrets["gcp_service_account"])
    if "private_key" in info:
        pk = info["private_key"].replace("\\n", "\n")
        pk = pk.replace("-----BEGIN PRIVATE KEY-----", "-----BEGIN PRIVATE KEY-----\n")
        pk = pk.replace("-----END PRIVATE KEY-----", "\n-----END PRIVATE KEY-----\n")
        info["private_key"] = pk.replace("\n\n\n", "\n").replace("\n\n", "\n")
    return gspread.authorize(Credentials.from_service_account_info(info, scopes=SCOPES))

def _ws(name, cols):
    try: return _client().open_by_key(st.secrets["spreadsheet"]["sheet_id"]).worksheet(name)
    except gspread.WorksheetNotFound:
        w = _client().open_by_key(st.secrets["spreadsheet"]["sheet_id"]).add_worksheet(title=name, rows=2000, cols=max(10, len(cols)))
        w.update(range_name="A1", values=[cols])
        return w

def _read(name, cols):
    try:
        w = _ws(name, cols)
        rec = w.get_all_records(default_blank="")
        if not rec: return []
        df = pd.DataFrame(rec)
        miss = [c for c in cols if c not in df.columns]
        if miss:
            w.update(range_name="A1", values=[cols])
            for c in miss: df[c] = ""
        for c in cols:
            if c not in df.columns: df[c] = ""
        return df[cols].to_dict("records")
    except Exception: return []

def _append(name, cols, rec): _ws(name, cols).append_row([str(rec.get(c, "")) for c in cols])
def _update(name, cols, kcol, kval, rec):
    w = _ws(name, cols)
    cvals = w.col_values(cols.index(kcol)+1)
    if str(kval) in cvals: w.update(range_name=f"A{cvals.index(str(kval))+1}", values=[[str(rec.get(c, "")) for c in cols]])
    else: _append(name, cols, rec)
def _over(name, cols, recs):
    w = _ws(name, cols); w.clear()
    w.update(range_name="A1", values=[cols] + [[str(r.get(c, "")) for c in cols] for r in recs])

def _f(v, d=0.0):
    try: return float(str(v).replace(",","")) if str(v).strip() else d
    except: return d
def _i(v, d=0):
    try: return int(float(str(v).replace(",",""))) if str(v).strip() else d
    except: return d

def load_arrivals():
    rows = _read("入荷記録", COLS_ARR)
    for r in rows: r["袋数"]=_f(r.get("袋数")), r["1袋重量(kg)"]=_f(r.get("1袋重量(kg)",20)), r["総量(kg)"]=_f(r.get("総量(kg)"))
    return rows
def append_arrival(r): _append("入荷記録", COLS_ARR, r)
def update_arrival(no, r): _update("入荷記録", COLS_ARR, "入荷No", no, r)
def next_arrival_no(arr): return f"A-{(max([int(a['入荷No'].split('-')[1]) for a in arr if '入荷No' in a and '-' in str(a['入荷No'])]+[0])+1):04d}"

def load_brewing():
    rows = _read("仕込み記録", COLS_BRW)
    for r in rows:
        for c in ["仕込量(kg)","こんにゃく精粉(kg)","海藻粉(kg)","デンプン(kg)","石灰(kg)","石灰水(L)"]: r[c]=_f(r.get(c))
        r["仕込No"] = _i(r.get("仕込No"))
    return rows
def append_brewing(r): _append("仕込み記録", COLS_BRW, r)
def update_brewing(no, r): _update("仕込み記録", COLS_BRW, "仕込No", str(no), r)
def next_brewing_no(brw): return max([_i(b.get("仕込No")) for b in brw]+[0])+1

def load_adjustments():
    rows = _read("在庫調整", COLS_ADJ)
    for r in rows: r["調整袋数"] = _f(r.get("調整袋数"))
    return rows
def append_adjustment(r): _append("在庫調整", COLS_ADJ, r)

def load_supplies():
    rows = _read("資材マスター", COLS_SUP)
    for r in rows: r["初期在庫"] = _f(r.get("初期在庫"))
    return rows
def save_supplies(rs): _over("資材マスター", COLS_SUP, rs)

def load_supply_logs():
    rows = _read("資材入出庫", COLS_LOG)
    for r in rows: r["数量"] = _f(r.get("数量"))
    return rows
def append_supply_log(r): _append("資材入出庫", COLS_LOG, r)

def _lcol(n, d):
    try: return [v for v in _ws(n, ["name"]).col_values(1)[1:] if v] or d
    except: return d
def _scol(n, vs):
    w = _ws(n, ["name"]); w.clear()
    w.update(range_name="A1", values=[["name"]] + [[v] for v in vs])

def load_materials(): return _lcol("原料マスター", ["こんにゃく精粉（国産）","海藻粉","加工デンプン","石灰","食塩"])
def save_materials(v): _scol("原料マスター", v)
def load_makers(): return _lcol("メーカーマスター", ["滝田商店","荻野","オリヒロ","その他"])
def save_makers(v): _scol("メーカーマスター", v)
def load_inspectors(): return _lcol("担当者マスター", ["若槻","志村","斎藤"])
def save_inspectors(v): _scol("担当者マスター", v)

def load_order_points():
    try: return {r["material"]: _f(r.get("order_point")) for r in _ws("発注点マスター", ["material","order_point"]).get_all_records(default_blank="")}
    except: return {}
def save_order_points(d):
    w = _ws("発注点マスター", ["material","order_point"]); w.clear()
    w.update(range_name="A1", values=[["material","order_point"]] + [[k,str(v)] for k,v in d.items()])
# --- END OF FILE sheets.py ---
