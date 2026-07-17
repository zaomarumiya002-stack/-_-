# app.py
import streamlit as st
import pandas as pd
import json
import time
import base64
from io import BytesIO
from datetime import datetime, date
import traceback
import plotly.graph_objects as go
import plotly.express as px

# Excel出力用 (HACCP/ISO監査対応)
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

# 資材画像アップロード用
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

st.set_page_config(
    page_title="食品工場 製造ERP",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ════════════════════════════════════════════════════════════════
#  モバイル・現場特化型 UI/UX CSS (ネイビー/オレンジ/グレー)
# ════════════════════════════════════════════════════════════════
st.markdown("""
<style>
:root {
    --c-bg: #f8fafc;
    --c-surface: #ffffff;
    --c-primary: #ea580c;
    --c-primary-hover: #c2410c;
    --c-secondary: #1e293b;
    --c-border: #94a3b8;
    --c-text: #334155;
}
.stApp { background-color: var(--c-bg); color: var(--c-text); font-family: 'Helvetica Neue', Arial, sans-serif; }

/* --- 全体ボタン タップ領域拡大 --- */
.stButton button {
    background-color: var(--c-surface) !important; 
    border: 1px solid var(--c-border) !important; 
    color: var(--c-secondary) !important;
    border-radius: 10px !important; 
    font-size: 1.1rem !important; 
    font-weight: 800 !important; 
    min-height: 56px !important; 
    transition: all 0.2s;
}
.stButton button[kind="primary"] {
    background: linear-gradient(135deg, var(--c-primary), var(--c-primary-hover)) !important; 
    border: none !important; 
    color: white !important; 
    box-shadow: 0 4px 10px rgba(234, 88, 12, 0.3) !important;
}
.stButton button:active { transform: scale(0.96) !important; }

/* ボタン内テキスト折り返し */
.stButton button p { white-space: normal !important; word-break: break-all !important; line-height: 1.3 !important; }

/* --- サイドバー --- */
[data-testid="stSidebar"] { background-color: var(--c-secondary) !important; padding-top: 0.4rem; }
[data-testid="stSidebar"] * { color: #ffffff !important; }
[data-testid="stSidebar"] div[role="radiogroup"] label {
    padding: 10px 12px !important; border-radius: 8px !important; margin-bottom: 5px !important;
    background: rgba(255,255,255,0.06) !important; border: 1px solid rgba(255,255,255,0.12) !important;
    font-weight: 700 !important; min-height: 48px; display: flex; align-items: center;
}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
    background: var(--c-primary) !important; border-color: var(--c-primary-hover) !important;
}

/* --- タイル型ラジオボタン (ライン・製品選択) --- */
div[data-testid="stRadio"] > div { display: flex; flex-wrap: wrap; gap: 8px !important; }
div[data-testid="stRadio"] label {
    font-size: 1.05rem !important; color: var(--c-secondary) !important; background-color: #f1f5f9;
    padding: 14px 16px !important; border-radius: 14px; border: 2px solid var(--c-border);
    font-weight: 900 !important; cursor: pointer; text-align: center; flex: 1 1 auto;
    white-space: nowrap; justify-content: center; box-shadow: 0 4px 6px rgba(0,0,0,0.05); min-height: 54px;
}
div[data-testid="stRadio"] label[data-baseweb="radio"] input:checked + div {
    background-color: var(--c-primary) !important; color: white !important;
    border-color: var(--c-primary) !important; transform: scale(1.02);
}

/* --- 汎用カード --- */
.form-card { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: 12px; padding: 16px; margin-bottom: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.03); }
.section-title { font-size: 1.15rem; font-weight: 900; color: var(--c-secondary); margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
.section-title::before { content: ''; display: block; width: 6px; height: 18px; background-color: var(--c-primary); border-radius: 4px; }

/* 🔴【最重要】入力ウィジェットとプルダウンの文字を「太字＆拡大」化 🔴 */
div[data-baseweb="input"] { border-radius: 10px !important; border: 1px solid var(--c-border) !important; min-height: 54px !important; }
div[data-baseweb="input"] input { 
    font-size: 1.25rem !important; 
    font-weight: 900 !important; 
    color: var(--c-secondary) !important;
    text-align: center !important; 
}
div[data-baseweb="select"] > div {
    font-size: 1.15rem !important;
    font-weight: 900 !important; 
    color: var(--c-secondary) !important;
    min-height: 54px !important;
}
div[data-baseweb="popover"] li {
    font-size: 1.1rem !important;
    font-weight: 800 !important;
    padding-top: 14px !important;
    padding-bottom: 14px !important;
}

/* 仕込量など特大入力用 */
.giant-input div[data-baseweb="input"] { border-width: 3px !important; min-height: 72px !important; }
.giant-input div[data-baseweb="input"] input { font-size: 2.2rem !important; font-weight: 900 !important; color: var(--c-primary) !important; }

/* モバイル向け余白調整 */
@media (max-width: 768px) {
    .block-container { padding-top: 1.5rem !important; padding-left: 0.5rem !important; padding-right: 0.5rem !important; }
    .stApp > header { display: none; }
}

.status-badge { display: inline-block; padding: 5px 12px; border-radius: 8px; font-size: 0.9rem; font-weight: 900; border: 2px solid; }
.status-badge.danger { background-color: #fef2f2; color: #b91c1c; border-color: #fca5a5; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
#  データロード・ユーティリティ
# ════════════════════════════════════════════════════════════════
try:
    import sheets
except Exception as e:
    st.error("🚨 `sheets.py` のインポート時にエラーが発生しました。")
    st.stop()

def refresh():
    st.cache_data.clear()
    st.rerun()

@st.cache_data(ttl=60)
def load_all_datasets():
    return {
        "arrivals": sheets.load_arrivals(), "brewing": sheets.load_brewing(), "adjustments": sheets.load_adjustments(),
        "supplies": sheets.load_supplies(), "supply_logs": sheets.load_supply_logs(), "materials": sheets.load_materials(),
        "makers": sheets.load_makers(), "inspectors": sheets.load_inspectors(), "order_points": sheets.load_order_points(),
        "recipes": sheets.load_recipes(), "recipe_logs": sheets.load_recipe_logs()
    }

try:
    dataset = load_all_datasets()
    arrivals, brewing, adjustments = dataset.get("arrivals", []), dataset.get("brewing", []), dataset.get("adjustments", [])
    supplies, supply_logs = dataset.get("supplies", []), dataset.get("supply_logs", [])
    materials, makers, inspectors = dataset.get("materials", []), dataset.get("makers", []), dataset.get("inspectors", [])
    order_points, recipes_raw, recipe_logs = dataset.get("order_points", {}), dataset.get("recipes", []), dataset.get("recipe_logs", [])
except Exception as e:
    st.error("🚨 データの読み込みに失敗しました。")
    st.stop()

BIG_CAT_ICONS = {"プラント": "🏭", "OKM": "🟦"}
SUB_CAT_ICONS = {"白": "⚪", "黒": "⚫", "耐冷": "❄️", "ショクカイ": "🍽️", "めん": "🍜", "おでん": "🍢", "その他": "📦"}
_ICON_POOL = ["🔵", "🟢", "🟡", "🟣", "🟠", "🔴", "🟤", "🔷", "🔶", "🔹", "🔸", "⬛", "⬜", "🟥", "🟩", "🟦"]
_PRODUCT_ICON_POOL = ["🍥", "🥢", "🌿", "🎍", "🧊", "🍡", "🧵", "🏷️", "📌", "🧺", "🔖", "🧫"]

def _deterministic_icon(name, pool):
    idx = sum(ord(ch) for ch in str(name)) % len(pool)
    return pool[idx]

def big_cat_icon(name): return BIG_CAT_ICONS.get(name, _deterministic_icon(name, _ICON_POOL))
def sub_cat_icon(name): return SUB_CAT_ICONS.get(name, _deterministic_icon(name, _ICON_POOL))
def product_icon(name): return _deterministic_icon(name, _PRODUCT_ICON_POOL)

def is_corrupted_name(name):
    name = str(name).strip()
    return len(name) > 30 or name.startswith("[") or name.startswith("{") if name else False

def safe_parse_recipe(recipe_val):
    if not recipe_val: return []
    data = recipe_val
    if not isinstance(data, (dict, list)):
        try:
            for _ in range(3):
                if isinstance(data, str): data = json.loads(data)
                else: break
        except Exception: data = []
    if isinstance(data, dict): data = [data]
    if not isinstance(data, list): data = []
    cleaned = []
    for item in data:
        if not isinstance(item, dict): continue
        name = str(item.get("原料名", "")).strip()
        if not name or is_corrupted_name(name): continue
        try: cleaned.append({"原料名": name, "比率": float(item.get("比率", 0.0))})
        except Exception: continue
    return cleaned

def fmt_kg(val):
    if val is None or val == "": return "0"
    try:
        val = float(val)
        if val.is_integer(): return f"{int(val)}"
        s = f"{val:.3f}".rstrip('0')
        if s.endswith('.'): s = s[:-1]
        return s
    except: return str(val)

def get_inventory():
    inv = {}
    for a in arrivals:
        ano = str(a.get("入荷No", "")).strip()
        if not ano: continue
        inv[ano] = {"入荷No": ano, "ロットNo": str(a.get("ロットNo", "")).strip(), "メーカー": str(a.get("メーカー", "")).strip(), "原料種別": str(a.get("原料種別", "")).strip(), "1袋重量": float(a.get("1袋重量(kg)") or 20.0), "入荷袋数": float(a.get("袋数") or 0.0), "使用量(kg)": 0.0, "調整袋数": 0.0}
    for b in brewing:
        oa = b.get("その他添加物", "")
        if oa:
            try:
                items = json.loads(oa)
                for item in items:
                    t_lot = str(item.get("lot", "")).strip()
                    t_kg = float(item.get("kg", 0.0))
                    if "," in t_lot:
                        lots = [l.strip() for l in t_lot.split(",")]
                        kg_per_lot = t_kg / len(lots)
                        for l in lots:
                            for v in inv.values():
                                if l and v["ロットNo"] == l: v["使用量(kg)"] += kg_per_lot
                    else:
                        for v in inv.values():
                            if t_lot and v["ロットNo"] == t_lot: v["使用量(kg)"] += t_kg
            except: pass
    for adj in adjustments:
        ano = str(adj.get("入荷No", "")).strip()
        if ano in inv: inv[ano]["調整袋数"] += float(adj.get("調整袋数") or 0.0)
    for v in inv.values():
        bpk = v["1袋重量"] if v["1袋重量"] > 0 else 20.0
        v["使用袋数"] = v["使用量(kg)"] / bpk
        v["現在庫(袋)"] = max(v["入荷袋数"] - v["使用袋数"] + v["調整袋数"], 0.0)
        v["現在庫(kg)"] = v["現在庫(袋)"] * bpk
    return inv

inventory_data = get_inventory()
type_totals = {}       
type_totals_kg = {}    
for v in inventory_data.values():
    m_type = v["原料種別"]
    type_totals[m_type] = type_totals.get(m_type, 0.0) + v["現在庫(袋)"]
    type_totals_kg[m_type] = type_totals_kg.get(m_type, 0.0) + v["現在庫(kg)"]

def get_supply_inventory():
    inv = {}
    for s in supplies:
        sid = str(s.get("資材ID", "")).strip()
        if not sid: continue
        inv[sid] = {"資材ID": sid, "資材名": s.get("資材名", ""), "カテゴリ": s.get("カテゴリ", ""), "画像URL": s.get("画像URL", ""), "初期在庫": float(s.get("初期在庫") or 0.0), "発注点": float(s.get("発注点") or 0.0), "入庫累計": 0.0, "出庫累計": 0.0}
    for log in supply_logs:
        sid = str(log.get("資材ID", "")).strip()
        if sid not in inv: continue
        try: qty = float(log.get("数量") or 0.0)
        except Exception: qty = 0.0
        if log.get("処理") == "入荷": inv[sid]["入庫累計"] += qty
        elif log.get("処理") == "使用": inv[sid]["出庫累計"] += qty
    for v in inv.values():
        v["現在庫"] = v["初期在庫"] + v["入庫累計"] - v["出庫累計"]
    return inv

supply_inventory = get_supply_inventory()

df_brw_global = pd.DataFrame(brewing)
if not df_brw_global.empty:
    df_brw_global["仕込日_dt"] = pd.to_datetime(df_brw_global["仕込日"], errors="coerce")
    df_brw_global["month"] = df_brw_global["仕込日_dt"].dt.to_period("M").astype(str)
    df_brw_global["date_str"] = df_brw_global["仕込日_dt"].dt.strftime("%Y-%m-%d")
    df_brw_global["仕込量(kg)"] = pd.to_numeric(df_brw_global["仕込量(kg)"], errors="coerce").fillna(0)
    df_brw_global["こんにゃく精粉(kg)"] = pd.to_numeric(df_brw_global["こんにゃく精粉(kg)"], errors="coerce").fillna(0)
    df_brw_global["石灰(kg)"] = pd.to_numeric(df_brw_global["石灰(kg)"], errors="coerce").fillna(0)
    today_str = date.today().strftime("%Y-%m-%d")
    df_brw_today = df_brw_global[df_brw_global["date_str"] == today_str]
    today_total_kg = df_brw_today["仕込量(kg)"].sum()
    today_count = len(df_brw_today)
    today_konjac_kg = df_brw_today["こんにゃく精粉(kg)"].sum()
    today_lime_kg = df_brw_today["石灰(kg)"].sum()
else:
    today_total_kg = today_count = today_konjac_kg = today_lime_kg = 0

def generate_excel_report(df, start_d, end_d, report_title="製造記録一覧"):
    if not HAS_OPENPYXL: return None
    wb = Workbook()
    ws = wb.active
    ws.title = "製造記録"
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.oddHeader.center.text = f"&16&B【 {report_title} 】"
    ws.oddFooter.center.text = "&10Page &P of &N"
    ws.oddFooter.right.text = f"出力日時: {datetime.now().strftime('%Y/%m/%d %H:%M')}"
    ws["A1"] = "会社名: 株式会社○○○○"
    ws["A2"] = "工場名: 本社第一工場"
    ws["A1"].font = ws["A2"].font = Font(bold=True)
    ws["J1"] = f"出力日時: {datetime.now().strftime('%Y/%m/%d %H:%M')}"
    ws["J2"] = f"対象期間: {start_d} ～ {end_d}"
    headers = ["製造日", "仕込No", "製品名", "担当者", "製造量(kg)", "石灰水(L)", "こんにゃく精粉", "海藻粉", "石灰", "使用ロット", "備考・監査履歴"]
    for col_idx, h in enumerate(headers, 1):
        c = ws.cell(row=5, column=col_idx, value=h)
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="DDEBF7")
        c.border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='medium'), bottom=Side(style='medium'))
        c.alignment = Alignment(horizontal="center", vertical="center")
    row_idx = 6
    total_qty = 0.0
    for _, row in df.iterrows():
        ws.cell(row=row_idx, column=1, value=str(row.get("仕込日", "")))
        ws.cell(row=row_idx, column=2, value=str(row.get("仕込No", "")))
        ws.cell(row=row_idx, column=3, value=str(row.get("品名", "")))
        ws.cell(row=row_idx, column=4, value=str(row.get("メーカー", "自社")))
        qty = float(row.get("仕込量(kg)", 0) or 0)
        total_qty += qty
        ws.cell(row=row_idx, column=5, value=qty).number_format = '#,##0.0'
        ws.cell(row=row_idx, column=6, value=float(row.get("石灰水(L)", 0) or 0)).number_format = '#,##0.0'
        ws.cell(row=row_idx, column=7, value=float(row.get("こんにゃく精粉(kg)", 0) or 0)).number_format = '#,##0.00'
        ws.cell(row=row_idx, column=8, value=float(row.get("海藻粉(kg)", 0) or 0)).number_format = '#,##0.00'
        ws.cell(row=row_idx, column=9, value=float(row.get("石灰(kg)", 0) or 0)).number_format = '#,##0.00'
        lot_str = str(row.get("主原料ロット", ""))
        try:
            oa = json.loads(row.get("その他添加物", "[]"))
            for item in oa:
                if "lot" in item and item["lot"] != "─" and item["lot"] not in lot_str:
                    lot_str += f" / {item['原料名']}:{item['lot']}"
        except: pass
        ws.cell(row=row_idx, column=10, value=lot_str)
        ws.cell(row=row_idx, column=11, value=str(row.get("備考", "")))
        for c in range(1, 12): ws.cell(row=row_idx, column=c).border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        row_idx += 1
    ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=4)
    c_tot = ws.cell(row=row_idx, column=1, value="合計 / 総合計")
    c_tot.font = Font(bold=True)
    c_tot.alignment = Alignment(horizontal="right", vertical="center")
    ws.cell(row=row_idx, column=5, value=total_qty).number_format = '#,##0.0'
    ws.cell(row=row_idx, column=11, value=f"製造件数: {len(df)} 件")
    for c in range(1, 12):
         cell = ws.cell(row=row_idx, column=c)
         cell.font = Font(bold=True)
         cell.fill = PatternFill("solid", fgColor="E2EFDA")
         cell.border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='medium'), bottom=Side(style='medium'))
    ws.auto_filter.ref = f"A5:K{row_idx-1}"
    for i, w in enumerate([12, 14, 25, 14, 12, 10, 15, 10, 10, 30, 40], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    return wb

# ════════════════════════════════════════════════════════════════
#  サイドバー
# ════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div style="font-size:1.2rem; font-weight:900; margin-bottom:0.8rem; color:white; display:flex; align-items:center; gap:8px;">🏭 <span>製造ERP</span></div>', unsafe_allow_html=True)
    page = st.radio("メニュー", [
        "🏭 製造仕込み", 
        "📥 入荷登録", 
        "🧹 資材管理", 
        "📊 経営ダッシュボード", 
        "📦 在庫・棚卸", 
        "🔍 トレース", 
        "📋 履歴・帳票",
        "📈 分析",
        "⚙️ マスタ設定"
    ], label_visibility="collapsed")
    st.markdown("---")
    if st.button("🔄 最新データに更新"): refresh()

# ==============================================================================
#  [1] 製造仕込み (モバイル特化・プルダウンUI版)
# ==============================================================================
if page == "🏭 製造仕込み":
    st.markdown('<div style="background:#fff; padding:12px; border-radius:12px; margin-bottom:12px; border-left:6px solid #ea580c; box-shadow:0 2px 4px rgba(0,0,0,0.05);"><h2 style="margin:0; font-size:1.4rem; color:#1e293b;">🏭 製造仕込み</h2></div>', unsafe_allow_html=True)

    st.markdown('<div class="form-card"><div style="font-size:1.1rem; font-weight:900; color:#1e293b; margin-bottom:8px;">📅 仕込日</div>', unsafe_allow_html=True)
    brew_date = st.date_input("仕込日", value=date.today(), label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    p_recipes = {}
    for r in recipes_raw:
        p_name = r.get("品名", "未定義")
        p_recipes[p_name] = {"大カテゴリ": r.get("大カテゴリ", "その他"), "中カテゴリ": r.get("中カテゴリ", "その他"), "成分": safe_parse_recipe(r.get("配合JSON"))}

    st.markdown('<div class="form-card"><div style="font-size:1.1rem; font-weight:900; color:#1e293b; margin-bottom:8px;">① ライン選択</div>', unsafe_allow_html=True)
    big_cats = sorted({v["大カテゴリ"] for v in p_recipes.values() if v.get("大カテゴリ")})
    if not big_cats:
        st.warning("ラインが登録されている製品マスタがありません。")
        big_cat = None
    else:
        big_cat_labels = [f"{big_cat_icon(c)} {c}" for c in big_cats]
        sel_big_label = st.radio("ライン", big_cat_labels, horizontal=True, label_visibility="collapsed")
        big_cat = big_cats[big_cat_labels.index(sel_big_label)]

    SUB_CAT_ORDER = ["黒", "白", "耐冷", "ショクカイ", "めん", "その他"]
    sub_cats_set = {v["中カテゴリ"] for v in p_recipes.values() if v.get("大カテゴリ") == big_cat and v.get("中カテゴリ")} if big_cat else set()
    sub_cats = sorted(sub_cats_set, key=lambda c: (SUB_CAT_ORDER.index(c) if c in SUB_CAT_ORDER else len(SUB_CAT_ORDER), c))
    sub_str = None
    if big_cat and len(sub_cats) > 1:
        st.markdown('<div style="font-size:1.1rem; font-weight:900; color:#1e293b; margin:16px 0 8px 0;">② 製品種別</div>', unsafe_allow_html=True)
        sub_cat_labels = [f"{sub_cat_icon(c)} {c}" for c in sub_cats]
        sel_sub_label = st.radio("製品", sub_cat_labels, horizontal=True, label_visibility="collapsed")
        sub_str = sub_cats[sub_cat_labels.index(sel_sub_label)]
    elif sub_cats:
        sub_str = sub_cats[0]
    
    st.markdown('<div style="font-size:1.1rem; font-weight:900; color:#1e293b; margin:16px 0 8px 0;">③ 品番を選択</div>', unsafe_allow_html=True)
    filtered_opts = [k for k, v in p_recipes.items() if v.get("大カテゴリ") == big_cat and v.get("中カテゴリ") == sub_str] if big_cat and sub_str else []
    
    selected_p = None
    active_recipe = []
    
    if not filtered_opts:
        st.warning("このラインに登録されている製品マスタがありません。")
        p_name = ""
    else:
        opt_labels = [f"{product_icon(k)} {k}" for k in filtered_opts]
        sel_label = st.radio("製品", opt_labels, horizontal=True, label_visibility="collapsed")
        selected_p = filtered_opts[opt_labels.index(sel_label)]
        p_name = selected_p
        active_recipe = p_recipes.get(selected_p, {}).get("成分", [])
    st.markdown('</div>', unsafe_allow_html=True)

    # 🔴 仕込量・石灰水のUI (縦積み＋大きな3列ボタン) 🔴
    st.markdown('<div class="form-card"><div style="font-size:1.2rem; font-weight:900; color:#ea580c; margin-bottom:16px;">④ 仕込量・石灰水を入力</div>', unsafe_allow_html=True)

    def _add_to_field(key, amt):
        cur = st.session_state.get(key)
        cur = float(cur) if cur not in (None, "") else 0.0
        st.session_state[key] = max(0.0, cur + float(amt))

    def _clear_field(key):
        st.session_state[key] = None

    # ▼ 希望仕込製品量 (縦積み)
    st.markdown("<div style='font-size:1.1rem; font-weight:900; color:#1e293b; margin-bottom:8px;'>🏭 希望仕込製品量 (kg)</div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.button("＋ 100", key="ts_100", use_container_width=True, on_click=_add_to_field, args=("target_size_val", 100))
    c2.button("＋ 500", key="ts_500", use_container_width=True, on_click=_add_to_field, args=("target_size_val", 500))
    c3.button("＋1000", key="ts_1000", use_container_width=True, on_click=_add_to_field, args=("target_size_val", 1000))
    
    c4, c5, c6 = st.columns(3)
    c4.button("リセット(0)", key="ts_0", use_container_width=True, on_click=_clear_field, args=("target_size_val",))
    c5.button("－ 10", key="ts_m10", use_container_width=True, on_click=_add_to_field, args=("target_size_val", -10))
    c6.button("－ 1", key="ts_m1", use_container_width=True, on_click=_add_to_field, args=("target_size_val", -1))
    
    st.markdown("<div class='giant-input'>", unsafe_allow_html=True)
    target_size = st.number_input("仕込量", min_value=1.0, step=1.0, value=None, format="%.0f", placeholder="例: 1000", key="target_size_val", label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)

    # ▼ 石灰水作成量 (縦積み)
    st.markdown("<div style='font-size:1.1rem; font-weight:900; color:#1e293b; margin-bottom:8px;'>💧 石灰水作成量 (kg)</div>", unsafe_allow_html=True)
    lc1, lc2, lc3 = st.columns(3)
    lc1.button("＋ 10", key="lw_10", use_container_width=True, on_click=_add_to_field, args=("lime_water_size_val", 10))
    lc2.button("＋ 50", key="lw_50", use_container_width=True, on_click=_add_to_field, args=("lime_water_size_val", 50))
    lc3.button("＋100", key="lw_100", use_container_width=True, on_click=_add_to_field, args=("lime_water_size_val", 100))
    
    lc4, lc5, lc6 = st.columns(3)
    lc4.button("リセット(0)", key="lw_0", use_container_width=True, on_click=_clear_field, args=("lime_water_size_val",))
    lc5.button("－ 10", key="lw_m10", use_container_width=True, on_click=_add_to_field, args=("lime_water_size_val", -10))
    lc6.button("－ 1", key="lw_m1", use_container_width=True, on_click=_add_to_field, args=("lime_water_size_val", -1))
    
    st.markdown("<div class='giant-input'>", unsafe_allow_html=True)
    lime_water_size = st.number_input("石灰水量", min_value=0.0, step=1.0, value=None, format="%.0f", placeholder="例: 20", key="lime_water_size_val", label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)
            
    st.markdown("<br>", unsafe_allow_html=True)
    operator = st.selectbox("👨‍🏭 製造担当者", inspectors if inspectors else ["未登録"])
    brew_remarks = st.text_input("📝 備考（任意）", placeholder="例: 通常より多め")
    st.markdown('</div>', unsafe_allow_html=True)

    if not active_recipe:
        st.info("製品を選択してください。")
    elif target_size is None or lime_water_size is None:
        st.info("👆 希望仕込量と石灰水量を入力すると、準備する原料が表示されます。")
    else:
        st.markdown('<div style="font-size:1.4rem; font-weight:900; margin:30px 0 16px 0; color:#1e293b;">📦 準備する原料・ロット確定</div>', unsafe_allow_html=True)
        
        submitted_ingredients = []
        key_suffix = f"_{selected_p}_{target_size}_{lime_water_size}"
        is_summer = 6 <= date.today().month <= 9
        recent_arrivals = sorted(arrivals, key=lambda x: x.get("入荷日", ""), reverse=True)

        def _recent_lot_options(mat_name, limit=15):
            opts = []
            seen = set()
            for a in recent_arrivals:
                if str(a.get("原料種別", "")).strip() != mat_name: continue
                l_no = str(a.get("ロットNo", "")).strip()
                if not l_no or l_no in seen: continue
                seen.add(l_no)
                opts.append((l_no, str(a.get("メーカー", "")).strip() or "不明"))
                if len(opts) >= limit: break
            return opts

        # 🔴【改修】ロット選択をシンプルで太字化された「プルダウン (selectbox)」に変更 🔴
        def _lot_selector_dropdown(label, mat_name, session_key):
            st.markdown(f"<div style='font-size:1.0rem; font-weight:900; color:#1e293b; margin:12px 0 4px 0;'>👆 {label}</div>", unsafe_allow_html=True)
            lot_opts = _recent_lot_options(mat_name, limit=15)
            choices = ["─ (未選択)", "✏️ 手入力 (リスト外)"] + [f"{lot} ｜ {maker}" for lot, maker in lot_opts]
            
            sel_val = st.selectbox(label, choices, key=f"sel_{session_key}", label_visibility="collapsed")
            
            if sel_val == "✏️ 手入力 (リスト外)":
                manual_lot = st.text_input("手入力ロット番号", key=f"man_{session_key}", placeholder="ロット番号を入力")
                return manual_lot if manual_lot else "─"
            elif sel_val == "─ (未選択)":
                return "─"
            else:
                return sel_val.split(" ｜ ")[0]

        # 🔴 原料リストの描画 (巨大なkg数とプルダウンUI) 🔴
        for i, item in enumerate(active_recipe[:10]):
            if not isinstance(item, dict): continue
            r_name = str(item.get("原料名", "未定義")).strip()
            base_ratio = float(item.get("比率", 0.0))
            is_water = ("水" == r_name or "お湯" in r_name)
            is_lime = ("石灰" in r_name or "カルシウム" in r_name)
            is_konjac = ("こんにゃく" in r_name)
            icon = "💧" if is_water else ("🧂" if is_lime else ("📦" if is_konjac else "🌿"))

            if is_water:
                calc_kg = max(0.0, (target_size * (base_ratio / 100.0)) - lime_water_size)
            elif is_lime:
                eff_r = base_ratio + (0.01 if is_summer else 0.0)
                calc_kg = lime_water_size * (eff_r / 10.0)
            else:
                calc_kg = target_size * (base_ratio / 100.0)

            inv_kg = type_totals_kg.get(r_name, 0.0)
            is_shortage = (not is_water) and (calc_kg > inv_kg)

            with st.container(border=True):
                if is_shortage:
                    st.markdown(f"<div style='color:#dc2626; font-weight:900; margin-bottom:8px;'>⚠ 在庫不足 (不足 {fmt_kg(calc_kg - inv_kg)}kg)</div>", unsafe_allow_html=True)
                
                # 🔴 kg数を「超特大」で表示 🔴
                clr = "#ea580c" if not is_water else "#3b82f6"
                st.markdown(f"""
                <div style="background-color:#f8fafc; padding:16px; border-radius:10px; margin-bottom:12px; border: 1px solid #e2e8f0;">
                    <div style="font-size:1.3rem; font-weight:900; color:#1e293b; margin-bottom:4px;">{icon} {r_name} <span style="font-size:0.9rem; color:#64748b; font-weight:normal;">({base_ratio}%)</span></div>
                    <div style="text-align:right; font-size:3.2rem; font-weight:900; color:{clr}; line-height:1.0;">
                        {fmt_kg(calc_kg)} <span style="font-size:1.2rem; color:#334155;">kg</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if is_water:
                    st.info("💧 計量・ロット記録は不要です")
                    submitted_ingredients.append({"原料名": r_name, "kg": calc_kg, "lot": "─"})
                
                elif is_konjac:
                    blend_on = st.toggle("🧪 2種類の原料をブレンドする", key=f"blend_on_{i}{key_suffix}")
                    konjac_mats = [m for m in materials if "こんにゃく" in m] or [r_name]
                    
                    if blend_on:
                        st.markdown("<div style='font-size:1.0rem; font-weight:900; margin-bottom:4px;'>⚖️ 合計投入量微調整 (kg)</div>", unsafe_allow_html=True)
                        actual_total_kg = st.number_input("合計投入量", value=float(calc_kg), step=0.01, format="%.2f", key=f"konjac_tot_{i}{key_suffix}", label_visibility="collapsed")
                        
                        ratio_key = f"konjac_ratio_{i}{key_suffix}"
                        if ratio_key not in st.session_state: st.session_state[ratio_key] = 50
                        
                        st.markdown("**【ブレンド比率設定】**")
                        ratio_presets = [20, 30, 40, 50, 60, 70, 80]
                        bc1, bc2, bc3 = st.columns(3)
                        bc1.button("A 20%", key=f"{ratio_key}_20", use_container_width=True, type="primary" if st.session_state[ratio_key]==20 else "secondary", on_click=lambda k=ratio_key: st.session_state.update({k: 20}))
                        bc2.button("A 50%", key=f"{ratio_key}_50", use_container_width=True, type="primary" if st.session_state[ratio_key]==50 else "secondary", on_click=lambda k=ratio_key: st.session_state.update({k: 50}))
                        bc3.button("A 80%", key=f"{ratio_key}_80", use_container_width=True, type="primary" if st.session_state[ratio_key]==80 else "secondary", on_click=lambda k=ratio_key: st.session_state.update({k: 80}))
                        
                        st.markdown("<div style='font-size:1.0rem; font-weight:900; margin-bottom:4px;'>こんにゃく粉A(%) 微調整</div>", unsafe_allow_html=True)
                        ratio_a = st.number_input("こんにゃく粉A(%) 微調整", min_value=0, max_value=100, step=1, key=ratio_key, label_visibility="collapsed")
                        ratio_b = 100 - ratio_a
                        kg_a = round(actual_total_kg * ratio_a / 100.0, 2)
                        kg_b = round(actual_total_kg - kg_a, 2)

                        st.markdown("---")
                        st.markdown(f"<div style='font-size:1.1rem; font-weight:900;'>🅰️ 原料A ({ratio_a}%) - {fmt_kg(kg_a)}kg</div>", unsafe_allow_html=True)
                        mat_a = st.selectbox("原料(A)の種類", konjac_mats, index=0, key=f"k_m_a_{i}{key_suffix}")
                        lot_final_a = _lot_selector_dropdown("📦 原料Aのロット", mat_a, f"lot_a_{i}_{key_suffix}")

                        st.markdown("---")
                        st.markdown(f"<div style='font-size:1.1rem; font-weight:900;'>🅱️ 原料B ({ratio_b}%) - {fmt_kg(kg_b)}kg</div>", unsafe_allow_html=True)
                        mat_b = st.selectbox("原料(B)の種類", konjac_mats, index=1 if len(konjac_mats)>1 else 0, key=f"k_m_b_{i}{key_suffix}")
                        lot_final_b = _lot_selector_dropdown("📦 原料Bのロット", mat_b, f"lot_b_{i}_{key_suffix}")

                        submitted_ingredients.append({"原料名": mat_a, "kg": kg_a, "lot": f"{lot_final_a}({ratio_a}%)"})
                        submitted_ingredients.append({"原料名": mat_b, "kg": kg_b, "lot": f"{lot_final_b}({ratio_b}%)"})
                    else:
                        st.markdown("<div style='font-size:1.0rem; font-weight:900; margin-bottom:4px;'>⚖️ 実投入量微調整 (kg)</div>", unsafe_allow_html=True)
                        actual_total_kg = st.number_input("実投入量微調整 (kg)", value=float(calc_kg), step=0.01, format="%.2f", key=f"act_kg_{i}{key_suffix}", label_visibility="collapsed")
                        final_lot = _lot_selector_dropdown("📦 使用するロット", r_name, f"lot_{i}_{key_suffix}")
                        submitted_ingredients.append({"原料名": r_name, "kg": actual_total_kg, "lot": final_lot})
                
                else:
                    st.markdown("<div style='font-size:1.0rem; font-weight:900; margin-bottom:4px;'>⚖️ 実投入量微調整 (kg)</div>", unsafe_allow_html=True)
                    actual_total_kg = st.number_input("実投入量微調整 (kg)", value=float(calc_kg), step=0.01, format="%.2f", key=f"act_kg_{i}{key_suffix}", label_visibility="collapsed")
                    final_lot = _lot_selector_dropdown("📦 使用するロット", r_name, f"lot_{i}_{key_suffix}")
                    submitted_ingredients.append({"原料名": r_name, "kg": actual_total_kg, "lot": final_lot})

        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("💾 この実績で製造記録を保存する", type="primary", use_container_width=True):
            k_kg = s_kg = st_kg = lime_kg = 0.0
            k_lot = s_lot = st_lot = "─"
            for ing in submitted_ingredients:
                n = ing["原料名"]
                if "こんにゃく" in n:
                    k_kg += ing["kg"]
                    if k_lot == "─": k_lot = ing["lot"]
                    elif ing["lot"] not in k_lot: k_lot += f" / {ing['lot']}"
                elif "海藻" in n:
                    s_kg += ing["kg"]
                    if s_lot == "─": s_lot = ing["lot"]
                    elif ing["lot"] not in s_lot: s_lot += f" / {ing['lot']}"
                elif "デンプン" in n or "でんぷん" in n:
                    st_kg += ing["kg"]
                    if st_lot == "─": st_lot = ing["lot"]
                    elif ing["lot"] not in st_lot: st_lot += f" / {ing['lot']}"
                elif "石灰" in n or "カルシウム" in n:
                    lime_kg += ing["kg"]

            user_note = f"{brew_remarks} " if brew_remarks else ""
            sheets.append_brewing({
                "仕込No": sheets.next_brewing_no(brewing), "仕込日": str(brew_date), "品名": p_name,
                "メーカー": operator, "主原料ロット": k_lot, "仕込量(kg)": target_size,
                "こんにゃく精粉(kg)": k_kg, "海藻粉(kg)": s_kg, "海藻粉ロット": s_lot,
                "デンプン(kg)": st_kg, "デンプンロット": st_lot, "デンプン種別": "-",
                "石灰(kg)": lime_kg, "石灰水(L)": lime_water_size,
                "その他添加物": json.dumps(submitted_ingredients, ensure_ascii=False),
                "備考": f"{user_note}【新規作成: {datetime.now().strftime('%Y/%m/%d %H:%M')} {operator}】", 
                "登録日時": datetime.now().isoformat()
            })
            st.success("🎉 製造実績を登録しました。画面を更新します...")
            time.sleep(1.5)
            refresh()


# ==============================================================================
#  以降のページ処理 (元のコードから一切の機能省略なしで完全復元)
# ==============================================================================
elif page == "📥 入荷登録":
    st.markdown('<div class="main-header"><h1>📥 原料入荷品質記録</h1><p>現場での素早い入荷検品と情報登録を行います。</p></div>', unsafe_allow_html=True)
    tab_a, tab_b = st.tabs(["➕ 新規入荷検品", "📋 入荷履歴"])
    
    with tab_a:
        st.markdown('<div class="form-card"><div class="section-title">🚛 基本入荷情報</div>', unsafe_allow_html=True)
        new_no = sheets.next_arrival_no(arrivals)
        c1, c2 = st.columns(2)
        c1.text_input("入荷No", value=new_no, disabled=True)
        arr_date = c2.date_input("入荷日", value=date.today())
        
        c3, c4 = st.columns(2)
        maker_sel = c3.selectbox("メーカー", makers + ["その他"] if makers else ["その他"])
        maker_val = st.text_input("メーカー名を入力") if maker_sel == "その他" else maker_sel
        lot_val = c4.text_input("ロットNo ＊")

        c5, c6 = st.columns(2)
        m_type = c5.selectbox("原料種別", materials if materials else ["未登録"])
        bags_qty = c6.number_input("入荷袋数", min_value=1, step=1, value=10)
        weight_per_bag = st.number_input("1袋重量 (kg)", min_value=1.0, value=20.0, step=0.5)
        st.info(f"💡 自動算出 合計重量: **{fmt_kg(bags_qty * weight_per_bag)} kg**")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="form-card"><div class="section-title">🔍 受入品質検査</div>', unsafe_allow_html=True)
        cc1, cc2 = st.columns(2)
        chk_app = cc1.selectbox("① 外観検査", ["OK（正常）", "NG（異常あり）"])
        chk_spec = cc2.selectbox("② 品名・規格", ["OK（一致）", "NG（不一致）"])
        chk_exp = cc1.selectbox("③ 賞味期限", ["OK（期限内）", "NG（期限切れ）"])
        chk_dmg = cc2.selectbox("④ 異物・破損", ["OK（なし）", "NG（あり）"])
        
        abn_desc = st.text_input("⚠️ 異常内容の詳細", placeholder="異常詳細を入力してください") if any("NG" in v for v in [chk_app, chk_spec, chk_exp, chk_dmg]) else ""
        inspector_val = st.selectbox("受入検査担当者", inspectors if inspectors else ["未登録"])
        remarks_val = st.text_input("備考")
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("💾 入荷記録を登録する", type="primary", use_container_width=True):
            if not lot_val:
                st.error("ロットNoは必須項目です。")
            else:
                sheets.append_arrival({
                    "入荷No": new_no, "入荷日": str(arr_date), "メーカー": maker_val, "ロットNo": lot_val,
                    "原料種別": m_type, "袋数": bags_qty, "1袋重量(kg)": weight_per_bag, "総量(kg)": bags_qty * weight_per_bag,
                    "外観": chk_app, "品名・規格確認": chk_spec, "賞味期限": chk_exp, "異物": chk_dmg,
                    "搬入温度": "-", "臭い": "OK", "包装": "OK", "色調": "OK", "水分": "OK",
                    "異常内容": abn_desc, "担当者": inspector_val, "備考": remarks_val, "登録日時": datetime.now().isoformat()
                })
                st.success("入荷品質検査記録を保存しました。画面を更新します...")
                time.sleep(1.5)
                refresh()

    with tab_b:
        if arrivals:
            df_arr = pd.DataFrame(arrivals)[["入荷No", "入荷日", "メーカー", "ロットNo", "原料種別", "袋数", "外観", "担当者"]]
            st.dataframe(df_arr[::-1], use_container_width=True, hide_index=True)


elif page == "🧹 資材管理":
    st.markdown('<div class="main-header"><h1>🧹 資材・消耗品管理</h1><p>資材の残量確認および入出庫操作を行います。</p></div>', unsafe_allow_html=True)
    tab_s1, tab_s2 = st.tabs(["📋 在庫一覧・入出庫", "🕒 ログ管理"])
    
    with tab_s1:
        if supplies:
            if "selected_supply_id" not in st.session_state:
                st.session_state.selected_supply_id = supplies[0].get("資材ID")

            id_by_name = {s.get("資材名"): s.get("資材ID") for s in supplies}
            name_by_id = {s.get("資材ID"): s.get("資材名") for s in supplies}

            def _select_supply(sid):
                st.session_state.selected_supply_id = sid

            sel_id = st.session_state.selected_supply_id
            target_sup = next((s for s in supplies if s.get("資材ID") == sel_id), supplies[0])
            sel_inv = supply_inventory.get(sel_id, {})
            sel_curr = sel_inv.get("現在庫", float(target_sup.get("初期在庫") or 0.0))

            st.markdown(f'<div class="form-card"><div class="section-title">📥「{target_sup.get("資材名")}」の入出庫を記録</div>', unsafe_allow_html=True)
            col_img, col_form = st.columns([1, 2])
            with col_img:
                img_data = target_sup.get("画像URL", "")
                if img_data and img_data.startswith("data:image"):
                    st.image(img_data, width=140)
                else:
                    st.info("📷 画像未登録")
                st.metric("現在庫", f"{fmt_kg(sel_curr)}")

            with col_form:
                action_type = st.radio("処理内容", ["➕ 補充する (入荷)", "➖ 使用する (出庫)"], horizontal=True, key="sup_action_type")
                if "sup_qty_val" not in st.session_state:
                    st.session_state.sup_qty_val = 1.0
                st.caption("よく使う数量をワンタップで入力")
                quick_cols = st.columns(4)
                for qi, qv in enumerate([1, 5, 10, 20]):
                    quick_cols[qi].button(f"{qv}", key=f"quick_sup_{qv}", use_container_width=True, on_click=lambda v=float(qv): st.session_state.update(sup_qty_val=v))

                qty_val = st.number_input("数量", min_value=0.01, step=1.0, format="%.2f", key="sup_qty_val")
                operator_val = st.selectbox("作業担当者", inspectors if inspectors else ["未登録"], key="op_sup")
                notes_val = st.text_input("備考情報", key="sup_notes")

                if st.button("💾 資材変動を保存する", type="primary", use_container_width=True):
                    sheets.append_supply_log({
                        "ログID": f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                        "登録日": str(date.today()), "資材ID": target_sup.get("資材ID"),
                        "処理": "入荷" if "補充" in action_type else "使用", "数量": qty_val,
                        "作業者": operator_val, "備考": notes_val, "登録日時": datetime.now().isoformat()
                    })
                    st.success(f"「{target_sup.get('資材名')}」の{'補充' if '補充' in action_type else '使用'}を記録しました。")
                    time.sleep(1.5)
                    refresh()
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="section-title">🚦 資材モニター（タップして選択）</div>', unsafe_allow_html=True)
            sup_names = [s.get("資材名") for s in supplies]
            current_name = name_by_id.get(st.session_state.selected_supply_id, sup_names[0])
            search_key = f"sup_quick_search_{st.session_state.selected_supply_id}"

            def _on_search_change(_key=search_key):
                picked_name = st.session_state.get(_key)
                if picked_name in id_by_name:
                    st.session_state.selected_supply_id = id_by_name[picked_name]

            st.selectbox("🔎 資材名で検索して選択", sup_names, index=sup_names.index(current_name) if current_name in sup_names else 0, key=search_key, on_change=_on_search_change)

            cols_grid = st.columns(max(2, min(4, len(supplies))))
            for idx, s in enumerate(supplies):
                sid = s.get("資材ID")
                sinv = supply_inventory.get(sid, {})
                curr_stock = sinv.get("現在庫", float(s.get("初期在庫") or 0.0))
                order_pt = sinv.get("発注点", float(s.get("発注点") or 0.0))
                is_low = (order_pt > 0 and curr_stock < order_pt)
                is_selected = (st.session_state.selected_supply_id == sid)
                
                with cols_grid[idx % len(cols_grid)]:
                    with st.container(border=True):
                        img_data = s.get("画像URL", "")
                        if img_data and img_data.startswith("data:image"):
                            st.image(img_data, width=90)
                        else:
                            st.markdown("<div style='text-align:center; padding:14px 0; color:#94a3b8; font-size:0.85rem;'>📷 画像なし</div>", unsafe_allow_html=True)
                        st.markdown(f"**{s.get('資材名')}**")
                        st.caption(s.get("カテゴリ", ""))
                        st.metric("現在庫", f"{fmt_kg(curr_stock)}", f"発注点 {fmt_kg(order_pt)}", delta_color="inverse" if is_low else "off")
                        if is_low:
                            st.markdown('<div class="status-badge danger">⚠ 発注点以下</div>', unsafe_allow_html=True)
                        st.button("✅ 選択中" if is_selected else "👆 選択", key=f"sel_sup_{sid}", type="primary" if is_selected else "secondary", use_container_width=True, on_click=_select_supply, args=(sid,))
        else:
            st.warning("資材が未登録です。マスタ設定よりご登録ください。")

    with tab_s2:
        if supply_logs:
            id_name_map = {s.get("資材ID"): s.get("資材名") for s in supplies}
            df_logs = pd.DataFrame(supply_logs).copy()
            df_logs["資材名"] = df_logs["資材ID"].map(id_name_map)
            st.dataframe(df_logs.tail(20)[::-1], use_container_width=True, hide_index=True)
            
            st.markdown('<div class="section-title">🚨 ログの取り消し・削除</div>', unsafe_allow_html=True)
            df_logs_sorted = df_logs.sort_values("登録日", ascending=False) if "登録日" in df_logs.columns else df_logs
            log_options = { f"{r.get('登録日','')} / {r.get('資材名','')} / {r.get('処理','')} {fmt_kg(r.get('数量',0))} (ID:{r.get('ログID','')})": r.get("ログID", "") for _, r in df_logs_sorted.iterrows() }
            if log_options:
                sel_log_label = st.selectbox("削除するログを選択してください", list(log_options.keys()))
                if st.button("🗑️ このログを完全に削除する", type="primary"):
                    sheets.delete_supply_log(log_options[sel_log_label])
                    st.success("ログを削除しました。")
                    time.sleep(1.5)
                    refresh()
        else:
            st.info("入出庫ログはまだありません。")


elif page == "📊 経営ダッシュボード":
    st.markdown('<div class="main-header"><h1>📊 工場長ダッシュボード</h1><p>工場の本日の稼働状況と在庫アラートを即座に把握します。</p></div>', unsafe_allow_html=True)
    
    st.markdown(f'<div class="section-title">📅 本日の製造サマリー ({date.today().strftime("%Y/%m/%d")})</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("📦 今日の総製造量", f"{fmt_kg(today_total_kg)} kg", f"{today_count} 件")
    with c2: st.metric("📦 粉使用量", f"{fmt_kg(today_konjac_kg)} kg")
    with c3: st.metric("🧂 石灰使用量", f"{fmt_kg(today_lime_kg)} kg")
    with c4:
        alert_count = sum(1 for m in materials if order_points.get(m, 0.0) > 0 and type_totals.get(m, 0.0) < order_points.get(m, 0.0))
        st.metric("⚠️ 在庫不足原料", f"{alert_count} 品目")

    st.markdown("---")
    st.markdown('<div class="section-title">📦 主要原料 在庫モニター</div>', unsafe_allow_html=True)
    if alert_count > 0:
        st.markdown('<div class="alert-box danger" style="padding:10px; background:#fef2f2; color:#b91c1c; border-radius:8px; margin-bottom:16px;">🚨 以下の原料が発注点を下回っています。至急確認してください。</div>', unsafe_allow_html=True)
    
    cols = st.columns(min(4, len(materials) if materials else 1))
    for idx, m in enumerate(materials):
        curr = type_totals.get(m, 0.0)
        pt = order_points.get(m, 0.0)
        is_alert = (pt > 0 and curr < pt)
        with cols[idx % 4]:
            with st.container(border=True):
                st.markdown(f"<h4 style='color:#1e293b; font-weight:900;'>{m}</h4>", unsafe_allow_html=True)
                st.metric("現在庫", f"{fmt_kg(curr)} 袋", f"発注点: {fmt_kg(pt)} 袋", delta_color="inverse" if is_alert else "normal")
                if is_alert:
                    st.markdown('<div class="status-badge danger" style="margin-top:10px;">⚠ 在庫不足</div>', unsafe_allow_html=True)


elif page == "📦 在庫・棚卸":
    st.markdown('<div class="main-header"><h1>📦 原料在庫・棚卸管理</h1><p>ロット別現在庫の確認、入出庫トレンドのグラフ化、棚卸し調整を行います。</p></div>', unsafe_allow_html=True)
    tab_inv1, tab_inv_trend, tab_inv2 = st.tabs(["📋 ロット別現在庫", "📈 入出庫トレンド", "⚖️ 棚卸し在庫調整"])
    
    with tab_inv1:
        active_inv = [v for v in inventory_data.values() if v["現在庫(袋)"] > 0.0]
        if active_inv:
            df_curr_inv = pd.DataFrame(active_inv)[["入荷No", "原料種別", "ロットNo", "入荷袋数", "使用袋数", "調整袋数", "現在庫(袋)"]]
            st.dataframe(df_curr_inv, use_container_width=True, hide_index=True)

    with tab_inv_trend:
        st.markdown('<div class="form-card"><div class="section-title">📊 原料種別 月別入出庫トレンド</div>', unsafe_allow_html=True)
        target_mat = st.selectbox("グラフ表示する原料種別", materials if materials else ["未登録"])
        df_a = pd.DataFrame(arrivals)
        df_b = pd.DataFrame(brewing)
        if not df_a.empty and not df_b.empty:
            df_a["date"] = pd.to_datetime(df_a["入荷日"], errors="coerce")
            df_a = df_a.dropna(subset=["date"])
            df_a["month"] = df_a["date"].dt.to_period("M").astype(str)
            df_a["総量(kg)"] = pd.to_numeric(df_a["総量(kg)"], errors="coerce").fillna(0)
            in_trend = df_a[df_a["原料種別"] == target_mat].groupby("month")["総量(kg)"].sum().reset_index()
            in_trend.rename(columns={"総量(kg)": "入荷量(kg)"}, inplace=True)
            
            out_records = []
            for _, r in df_b.iterrows():
                try:
                    b_date = pd.to_datetime(r["仕込日"], errors="coerce")
                    if pd.isna(b_date): continue
                    m_str = b_date.to_period("M").astype(str)
                    oa = r.get("その他添加物", "")
                    if oa:
                        items = json.loads(oa)
                        for item in items:
                            if item.get("原料名", "").strip() == target_mat: out_records.append({"month": m_str, "消費量(kg)": float(item.get("kg", 0))})
                except: pass
            
            df_out = pd.DataFrame(out_records)
            out_trend = df_out.groupby("month")["消費量(kg)"].sum().reset_index() if not df_out.empty else pd.DataFrame(columns=["month", "消費量(kg)"])

            df_trend = pd.merge(in_trend, out_trend, on="month", how="outer").fillna(0).sort_values("month")
            if not df_trend.empty:
                fig = go.Figure()
                fig.add_trace(go.Bar(x=df_trend["month"], y=df_trend["入荷量(kg)"], name="入荷量 (kg)", marker_color="#10b981"))
                fig.add_trace(go.Bar(x=df_trend["month"], y=df_trend["消費量(kg)"], name="消費量 (kg)", marker_color="#ef4444"))
                fig.update_layout(barmode="group", xaxis_title="年月", yaxis_title="重量 (kg)", plot_bgcolor="#f8fafc")
                st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with tab_inv2:
        st.markdown('<div class="form-card"><div class="section-title">⚖️ 棚卸による理論在庫ズレ調整</div>', unsafe_allow_html=True)
        if inventory_data:
            tgt_list = {f"{v['入荷No']} - {v['原料種別']} (ロット:{v['ロットNo']})": v["入荷No"] for v in inventory_data.values()}
            selected_tgt = st.selectbox("調整対象ロット", list(tgt_list.keys()))
            diff_bags = st.number_input("理論在庫との差分（袋数単位）", step=1.0, value=0.0, format="%.2f")
            reason_txt = st.text_input("調整の理由", placeholder="例: 実地棚卸との差分修正")
            operator = st.selectbox("調整実施者", inspectors if inspectors else ["未登録"])

            if st.button("💾 在庫データを上書き調整する", type="primary", use_container_width=True):
                sheets.append_adjustment({"調整ID": f"ADJ-{datetime.now().strftime('%Y%m%d%H%M%S')}", "入荷No": tgt_list[selected_tgt], "調整日": str(date.today()), "調整袋数": diff_bags, "理由": reason_txt, "担当者": operator, "登録日時": datetime.now().isoformat()})
                st.success("調整情報を書き込みました。")
                time.sleep(1.5)
                refresh()
        st.markdown('</div>', unsafe_allow_html=True)


elif page == "🔍 トレース":
    st.markdown('<div class="main-header"><h1>🔍 双方向原料トレース</h1><p>原料ロットと製品製造ロットの関連付けを完全に追跡します。</p></div>', unsafe_allow_html=True)
    trace_dir = st.radio("トレース方向", ["➡️ 原料ロットから製品を追跡（フォワード）", "⬅️ 製品から原料を遡及（バックワード）"])
    
    if "フォワード" in trace_dir:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        lots_to_search = sorted(list(set([str(a.get("ロットNo", "")).strip() for a in arrivals if a.get("ロットNo")])), reverse=True)
        if not lots_to_search:
            st.info("原料ロット情報がありません。")
        else:
            target_lot = st.selectbox("検索する原料ロット番号", lots_to_search)
            if st.button("➡️ 追跡を開始する", type="primary", use_container_width=True):
                match_arr = [a for a in arrivals if str(a.get("ロットNo", "")).strip() == target_lot]
                if match_arr:
                    st.markdown("##### 📦 入荷・受け入れ情報")
                    st.dataframe(pd.DataFrame(match_arr)[["入荷No", "入荷日", "原料種別", "メーカー", "袋数", "外観", "担当者"]], use_container_width=True, hide_index=True)
                
                match_brw = []
                for b in brewing:
                    matched = False
                    try:
                        items = json.loads(b.get("その他添加物", "[]"))
                        if any(target_lot in str(i.get("lot", "")).strip() for i in items): matched = True
                    except: pass
                    if matched: match_brw.append(b)

                if match_brw:
                    st.markdown("##### 🧪 製造仕込み消費実績")
                    st.dataframe(pd.DataFrame(match_brw)[["仕込No", "仕込日", "品名", "仕込量(kg)", "こんにゃく精粉(kg)", "主原料ロット"]], use_container_width=True, hide_index=True)
                else:
                    st.warning("⚠️ このロットを使用した仕込み履歴は存在しません。")
        st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        if not brewing:
            st.info("製造記録が存在しません。")
        else:
            brw_opts = {f"No.{b.get('仕込No')} - {b.get('品名')} ({b.get('仕込日')})": b for b in brewing}
            selected_brw_label = st.selectbox("対象の製造仕込み記録", list(brw_opts.keys()))
            selected_b = brw_opts[selected_brw_label]
            
            if st.button("⬅️ 遡及を開始する", type="primary", use_container_width=True):
                st.markdown("##### 🧪 製造の基本情報")
                st.markdown(f"""
                <div style="background-color: #f8fafc; padding: 20px; border-radius: 12px; border-left: 6px solid #2563eb; margin-bottom: 20px; border: 1px solid #e2e8f0;">
                    <h3 style="margin-top:0; color:#1e293b;">{selected_b.get('品名')}</h3>
                    <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                        <p style="margin-bottom:0; font-size:1.1rem;"><strong>仕込No:</strong> {selected_b.get('仕込No')}</p>
                        <p style="margin-bottom:0; font-size:1.1rem;"><strong>製造日:</strong> {selected_b.get('仕込日')}</p>
                        <p style="margin-bottom:0; font-size:1.1rem;"><strong>製造量:</strong> <span style="color:#2563eb; font-weight:bold;">{fmt_kg(selected_b.get('仕込量(kg)'))} kg</span></p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                used_lots = []
                try:
                    items = json.loads(selected_b.get("その他添加物", "[]"))
                    for ing in items:
                        l_nums = str(ing.get("lot", "")).strip().split(",")
                        for l in l_nums:
                            if l.strip() and l.strip() != "─":
                                used_lots.append({"原料種別": ing.get("原料名", "副資材"), "ロットNo": l.strip()})
                except: pass
                
                if used_lots:
                    st.markdown("##### 📦 使用原料の入荷元詳細情報")
                    details = []
                    for u in used_lots:
                        arr_match = next((a for a in arrivals if str(a.get("ロットNo", "")).strip() == u["ロットNo"]), None)
                        if arr_match:
                            details.append({"原料種別": u["原料種別"], "ロットNo": u["ロットNo"], "入荷No": arr_match.get("入荷No"), "入荷日": arr_match.get("入荷日"), "メーカー": arr_match.get("メーカー"), "外観検査": arr_match.get("外観")})
                        else:
                            details.append({"原料種別": u["原料種別"], "ロットNo": u["ロットNo"], "入荷No": "不明", "入荷日": "不明", "メーカー": "不明", "外観検査": "不明"})
                    st.dataframe(pd.DataFrame(details), use_container_width=True, hide_index=True)
                else:
                    st.warning("この製造ロットで使用された原料ロットの記録はありません。")
        st.markdown('</div>', unsafe_allow_html=True)


elif page == "📋 履歴・帳票":
    st.markdown('<div class="main-header"><h1>📋 製造履歴・監査帳票</h1><p>過去の製造記録の確認・編集、およびExcel帳票出力を行います。</p></div>', unsafe_allow_html=True)

    if not brewing:
        st.info("まだ製造記録がありません。")
    else:
        df_brw = pd.DataFrame(brewing)
        df_brw["仕込日_dt"] = pd.to_datetime(df_brw["仕込日"], errors="coerce")
        
        st.markdown('<div class="form-card"><div class="section-title">🔍 履歴の絞り込み検索</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        s_date = c1.date_input("開始日", value=date.today().replace(day=1))
        e_date = c2.date_input("終了日", value=date.today())
        
        unique_names = ["すべて"] + list(df_brw["品名"].dropna().unique()) if "品名" in df_brw.columns else ["すべて"]
        unique_users = ["すべて"] + list(df_brw["メーカー"].dropna().unique()) if "メーカー" in df_brw.columns else ["すべて"]
        
        s_name = c3.selectbox("製品名", unique_names)
        s_user = c4.selectbox("担当者", unique_users)
        
        mask = (df_brw["仕込日_dt"].dt.date >= s_date) & (df_brw["仕込日_dt"].dt.date <= e_date)
        if s_name != "すべて": mask &= (df_brw["品名"] == s_name)
        if s_user != "すべて": mask &= (df_brw["メーカー"] == s_user)
        
        filtered_df = df_brw[mask].copy()
        if "仕込日" in filtered_df.columns:
            filtered_df = filtered_df.sort_values("仕込日", ascending=False)
        
        if HAS_OPENPYXL and not filtered_df.empty:
            wb = generate_excel_report(filtered_df, s_date.strftime("%Y/%m/%d"), e_date.strftime("%Y/%m/%d"))
            excel_buffer = BytesIO()
            wb.save(excel_buffer)
            c1.download_button("🖨️ 期間指定でExcel帳票をダウンロード", data=excel_buffer.getvalue(), file_name=f"製造記録一覧_{s_date.strftime('%Y%m%d')}_{e_date.strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="form-card"><div class="section-title">📋 検索結果一覧</div>', unsafe_allow_html=True)
        target_cols = ["仕込日", "仕込No", "品名", "メーカー", "仕込量(kg)", "石灰水(L)", "主原料ロット", "備考"]
        show_cols = [c for c in target_cols if c in filtered_df.columns]
        st.dataframe(filtered_df[show_cols], use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="form-card"><div class="section-title">✏️ 対象記録のインライン操作 (編集・削除)</div>', unsafe_allow_html=True)
        brw_opts = {f"No.{r.get('仕込No','')} - {r.get('品名','')} ({r.get('仕込日','')})": r for _, r in filtered_df.iterrows()}
        if brw_opts:
            selected_label = st.selectbox("操作する記録を選択", list(brw_opts.keys()))
            sel_rec = brw_opts[selected_label]
            
            with st.container(border=True):
                with st.form("inline_edit_form"):
                    st.markdown("#### 編集パネル")
                    edit_seikomi_date = st.text_input("製造日", value=str(sel_rec.get("仕込日", "")))
                    e_name = st.text_input("品名", value=str(sel_rec.get("品名", "")))
                    c_s1, c_s2 = st.columns(2)
                    e_size = c_s1.number_input("製造量(kg)", min_value=1.0, value=float(sel_rec.get("仕込量(kg)", 100) or 100), step=10.0, format="%.1f")
                    e_lime = c_s2.number_input("石灰水(L)", min_value=0.0, value=float(sel_rec.get("石灰水(L)", 0) or 0), step=1.0, format="%.1f")
                    
                    user_idx = 0
                    if sel_rec.get("メーカー") in inspectors: user_idx = inspectors.index(sel_rec.get("メーカー"))
                    e_user = st.selectbox("担当者", inspectors if inspectors else ["未登録"], index=user_idx)
                    
                    e_note = st.text_area("備考 (自動で編集履歴が追記されます)", value=str(sel_rec.get("備考", "")))

                    col_save, col_del = st.columns(2)
                    do_save = col_save.form_submit_button("💾 変更を上書き保存する", type="primary", use_container_width=True)
                    do_delete = col_del.form_submit_button("🗑️ この記録を削除する", use_container_width=True)

                    if do_save or do_delete:
                        if not hasattr(sheets, "save_brewing"):
                            st.error("この操作には `sheets.py` 側に `save_brewing(list)` 関数が必要です。")
                        else:
                            updated_brewing = [b for b in brewing if b.get("仕込No") != sel_rec.get("仕込No")]
                            if do_save:
                                new_rec = dict(sel_rec)
                                new_note = e_note + f" 【修正: {datetime.now().strftime('%Y/%m/%d %H:%M')} {e_user}】"
                                new_rec.update({"仕込日": edit_seikomi_date, "品名": e_name, "メーカー": e_user, "仕込量(kg)": e_size, "石灰水(L)": e_lime, "備考": new_note})
                                updated_brewing.append(new_rec)
                                sheets.save_brewing(updated_brewing)
                                st.success("製造記録を更新しました。")
                            else:
                                sheets.save_brewing(updated_brewing)
                                st.success("製造記録を削除しました。")
                            time.sleep(1.5)
                            refresh()
        st.markdown('</div>', unsafe_allow_html=True)


elif page == "📈 分析":
    st.markdown('<div class="main-header"><h1>📈 製造・原料消費 分析</h1><p>月別の生産実績や製品構成のトレンドを可視化します。</p></div>', unsafe_allow_html=True)
    
    if df_brw_global.empty:
        st.info("分析可能な製造データがありません。")
    else:
        st.markdown('<div class="form-card"><div class="section-title">📅 月間生産推移 (折れ線・棒グラフ)</div>', unsafe_allow_html=True)
        monthly_trend = df_brw_global.groupby("month")["仕込量(kg)"].sum().reset_index().sort_values("month")
        
        fig = go.Figure()
        fig.add_trace(go.Bar(x=monthly_trend["month"], y=monthly_trend["仕込量(kg)"], name="製造量(kg)", marker_color="#ea580c"))
        fig.add_trace(go.Scatter(x=monthly_trend["month"], y=monthly_trend["仕込量(kg)"], mode="lines+markers", name="推移", line=dict(color="#1e293b", width=3)))
        fig.update_layout(xaxis_title="年月", yaxis_title="総製造量 (kg)", plot_bgcolor="#f8fafc", margin=dict(l=40, r=40, t=40, b=40))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        c_p1, c_p2 = st.columns(2)
        with c_p1:
            st.markdown('<div class="form-card"><div class="section-title">📊 製品構成比 (全期間)</div>', unsafe_allow_html=True)
            pie_data = df_brw_global.groupby("品名")["仕込量(kg)"].sum().reset_index()
            fig_pie = px.pie(pie_data, names="品名", values="仕込量(kg)", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pie.update_layout(margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_pie, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
        with c_p2:
            st.markdown('<div class="form-card"><div class="section-title">🏆 製造量 TOP 10 製品</div>', unsafe_allow_html=True)
            top10 = pie_data.sort_values("仕込量(kg)", ascending=True).tail(10)
            fig_bar = px.bar(top10, x="仕込量(kg)", y="品名", orientation='h', color="仕込量(kg)", color_continuous_scale="Oranges")
            fig_bar.update_layout(margin=dict(l=20, r=20, t=20, b=20), xaxis_title="製造量 (kg)", yaxis_title="")
            st.plotly_chart(fig_bar, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)


elif page == "⚙️ マスタ設定":
    st.markdown('<div class="main-header"><h1>⚙️ マスターデータ管理</h1><p>システム全体で共有されるリストや配合基準、資材の定義を行います。</p></div>', unsafe_allow_html=True)
    m_tab1, m_tab2, m_tab3, m_tab4, m_tab5 = st.tabs(["⚗️ 原料", "🏢 メーカー・担当", "🚨 発注点", "🧪 配合レシピ", "📦 資材・備品"])
    
    with m_tab1:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        df_materials = pd.DataFrame({"原料名": materials})
        edited_materials = st.data_editor(df_materials, num_rows="dynamic", use_container_width=True, key="mat_ed_k")
        if st.button("💾 原料マスタを更新する", type="primary"):
            raw_names = [str(x).strip() for x in edited_materials["原料名"].tolist() if str(x).strip()]
            bad_names = [n for n in raw_names if is_corrupted_name(n)]
            clean_names = [n for n in raw_names if not is_corrupted_name(n)]
            if bad_names:
                st.error(f"⚠️ 原料名として不正な値が {len(bad_names)} 件含まれていたため、保存をスキップしました。短い名称を入力してください。")
            else:
                sheets.save_materials(clean_names)
                st.success("原料マスター情報を保存しました。")
                time.sleep(1.5)
                refresh()
        st.markdown('</div>', unsafe_allow_html=True)

    with m_tab2:
        col_sub1, col_sub2 = st.columns(2)
        with col_sub1:
            st.markdown('<div class="form-card"><div class="section-title">取引先メーカー</div>', unsafe_allow_html=True)
            df_makers = pd.DataFrame({"メーカー名": makers})
            edited_makers = st.data_editor(df_makers, num_rows="dynamic", use_container_width=True, key="maker_ed_k")
            if st.button("💾 メーカーリストを保存", type="primary"):
                sheets.save_makers([str(x).strip() for x in edited_makers["メーカー名"].tolist() if str(x).strip()])
                st.success("保存しました。")
                time.sleep(1.5)
                refresh()
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col_sub2:
            st.markdown('<div class="form-card"><div class="section-title">担当者</div>', unsafe_allow_html=True)
            df_inspectors = pd.DataFrame({"担当者名": inspectors})
            edited_inspectors = st.data_editor(df_inspectors, num_rows="dynamic", use_container_width=True, key="inspector_ed_k")
            if st.button("💾 担当者を保存", type="primary"):
                sheets.save_inspectors([str(x).strip() for x in edited_inspectors["担当者名"].tolist() if str(x).strip()])
                st.success("保存しました。")
                time.sleep(1.5)
                refresh()
            st.markdown('</div>', unsafe_allow_html=True)

    with m_tab3:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        op_rows = [{"原料名": m, "発注点(袋)": float(order_points.get(m, 0.0))} for m in materials]
        df_op = pd.DataFrame(op_rows)
        edited_op = st.data_editor(
            df_op, 
            use_container_width=True, 
            key="op_ed_k",
            column_config={"発注点(袋)": st.column_config.NumberColumn(format="%.2f")}
        )
        if st.button("💾 発注点設定を更新する", type="primary"):
            new_op_dict = {str(r["原料名"]).strip(): float(r["発注点(袋)"] or 0.0) for _, r in edited_op.iterrows() if str(r["原料名"]).strip()}
            sheets.save_order_points(new_op_dict)
            st.success("発注点設定を保存しました。")
            time.sleep(1.5)
            refresh()
        st.markdown('</div>', unsafe_allow_html=True)

    with m_tab4:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        r_tab1, r_tab2, r_tab3 = st.tabs(["📝 新規登録・編集", "📋 登録済み一覧と削除", "🕒 変更履歴"])
        
        def get_recipe_diff(old_json, new_json):
            try:
                old_items = json.loads(old_json) if isinstance(old_json, str) else old_json
                new_items = json.loads(new_json) if isinstance(new_json, str) else new_json
                old_dict = {i["原料名"]: float(i["比率"]) for i in old_items}
                new_dict = {i["原料名"]: float(i["比率"]) for i in new_items}
                changes = []
                for k in set(old_dict.keys()) | set(new_dict.keys()):
                    o_val = old_dict.get(k)
                    n_val = new_dict.get(k)
                    if o_val == n_val: continue
                    if o_val is None: changes.append(f"[{k}] 追加({n_val}%)")
                    elif n_val is None: changes.append(f"[{k}] 削除")
                    else: changes.append(f"[{k}] {o_val}%→{n_val}%")
                return " / ".join(changes) if changes else "変更なし"
            except: return "詳細不明"

        with r_tab1:
            st.write("水を含む各配合原料の全体比率(％)を定義します。")
            edit_mode = st.radio("操作を選択", ["新規作成", "既存レシピの編集"], horizontal=True)
            
            target_recipe = None
            old_json = "[]"
            if edit_mode == "既存レシピの編集":
                if not recipes_raw: st.warning("編集できるレシピがありません。")
                else:
                    target_name = st.selectbox("編集するレシピを選択", [r["品名"] for r in recipes_raw])
                    target_recipe = next((r for r in recipes_raw if r["品名"] == target_name), None)
                    if target_recipe: old_json = target_recipe.get("配合JSON", "[]")
            
            init_name = target_recipe["品名"] if target_recipe else ""
            init_cat_m = "OKM" if target_recipe and target_recipe.get("大カテゴリ") == "OKM" else "プラント"
            init_cat_s = target_recipe.get("中カテゴリ", "黒") if target_recipe else "黒"
            
            try: 
                init_items = json.loads(old_json) if isinstance(old_json, str) else old_json
                if not isinstance(init_items, list): init_items = []
            except: init_items = []
                
            def_mats = ["(未設定)", "水"] + materials

            form_scope = f"edit_{init_name}" if (edit_mode == "既存レシピの編集" and target_recipe) else "new"

            with st.form(f"recipe_builder_form_{form_scope}"):
                cat_main = st.radio("大カテゴリ", ["🏭 プラント", "🟦 OKM"], index=0 if init_cat_m == "プラント" else 1, horizontal=True)
                cat_sub = st.radio("中カテゴリ（プラントの場合のみ）", ["⚪ 白", "⚫ 黒", "❄️ 耐冷", "🍽️ ショクカイ", "🍜 めん", "📦 その他"], 
                                   index=["白","黒","耐冷","ショクカイ","めん","その他"].index(init_cat_s) if init_cat_s in ["白","黒","耐冷","ショクカイ","めん","その他"] else 1, horizontal=True)
                new_p_name = st.text_input("製品の名称 (例: こんにゃく極細白)", value=init_name, disabled=(target_recipe is not None))
                
                st.write("🧪 **各構成原料のパーセンテージ（％）比率**")
                cols_recipe_inputs = []
                for j in range(10):
                    c_n, c_w = st.columns([2, 1])
                    def_mat_val = init_items[j]["原料名"] if j < len(init_items) else "(未設定)"
                    def_rat_val = float(init_items[j]["比率"]) if j < len(init_items) else 0.00
                    try: mat_idx = def_mats.index(def_mat_val)
                    except: mat_idx = 0
                    
                    ing_mat = c_n.selectbox(f"配合成分 {j+1}", def_mats, index=mat_idx, key=f"rec_b_{j}_{form_scope}")
                    ing_ratio = c_w.number_input("比率 (％)", min_value=0.00, max_value=100.00, value=def_rat_val, step=0.01, format="%.2f", key=f"rec_r_{j}_{form_scope}")
                    cols_recipe_inputs.append({"name": ing_mat, "ratio": ing_ratio})
                
                operator = st.selectbox("操作担当者", inspectors if inspectors else ["未登録"])
                
                if st.form_submit_button("💾 配合比率を保存する"):
                    if not new_p_name: st.error("製品の名称は必須です。")
                    elif is_corrupted_name(new_p_name):
                        st.error("⚠️ 製品名として不正な値です。短い製品名を入力してください。")
                    else:
                        valid_items = [
                            {"原料名": i["name"], "比率": float(i["ratio"])}
                            for i in cols_recipe_inputs
                            if i["name"] != "(未設定)" and i["ratio"] > 0 and not is_corrupted_name(i["name"])
                        ]
                        if not valid_items: st.error("有効な配合成分がありません。")
                        else:
                            cat_str = "プラント" if "プラント" in cat_main else "OKM"
                            sub_str = cat_sub.split(" ")[1] if cat_str == "プラント" else "その他"
                            new_json = json.dumps(valid_items, ensure_ascii=False)
                            
                            new_recipe_entry = {"品名": new_p_name, "大カテゴリ": cat_str, "中カテゴリ": sub_str, "配合JSON": new_json}
                            updated_recipes = [r for r in recipes_raw if r["品名"] != new_p_name]
                            updated_recipes.append(new_recipe_entry)
                            
                            action = "新規" if not target_recipe else "更新"
                            diff_str = get_recipe_diff(old_json, new_json) if target_recipe else "新規作成"
                            try:
                                sheets.append_recipe_log({
                                    "ログID": f"RLOG-{datetime.now().strftime('%Y%m%d%H%M%S')}", "変更日時": datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
                                    "品名": new_p_name, "処理": action, "変更内容": diff_str, "作業者": operator
                                })
                            except: pass
                            sheets.save_recipes(updated_recipes)
                            st.success(f"配合レシピ: {new_p_name} を保存しました。")
                            time.sleep(1.5)
                            refresh()

        with r_tab2:
            if recipes_raw:
                for idx, rec in enumerate(recipes_raw):
                    with st.expander(f"📦 {rec.get('品名')} (【{rec.get('大カテゴリ','')}】 {rec.get('中カテゴリ','')})"):
                        try:
                            comp_list = safe_parse_recipe(rec.get("配合JSON"))
                            if comp_list: st.dataframe(pd.DataFrame(comp_list), use_container_width=True, hide_index=True)
                            else: st.write("成分データがありません")
                        except Exception: st.error(f"読み出しエラー")
                
                st.markdown("---")
                del_recipe_name = st.selectbox("削除するレシピを選択", [r["品名"] for r in recipes_raw])
                if st.button("🗑️ 選択したレシピを完全に削除する", type="primary"):
                    updated_recipes = [r for r in recipes_raw if r["品名"] != del_recipe_name]
                    try:
                        sheets.append_recipe_log({
                            "ログID": f"RLOG-{datetime.now().strftime('%Y%m%d%H%M%S')}", "変更日時": datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
                            "品名": del_recipe_name, "処理": "削除", "変更内容": "レシピの完全削除", "作業者": "システム"
                        })
                    except: pass
                    sheets.save_recipes(updated_recipes)
                    st.success(f"{del_recipe_name} を削除しました。")
                    time.sleep(1.5)
                    refresh()
            else: st.info("登録済みの配合レシピはありません。")
                
        with r_tab3:
            try:
                recipe_logs = dataset.get("recipe_logs", [])
                if recipe_logs: st.dataframe(pd.DataFrame(recipe_logs)[::-1], use_container_width=True, hide_index=True)
                else: st.info("変更履歴はまだありません。")
            except: st.warning("履歴データの読み込みに失敗しました。")
        st.markdown('</div>', unsafe_allow_html=True)

    with m_tab5:
        st.markdown('<div class="form-card"><div class="section-title">📋 登録済み資材の管理・編集</div>', unsafe_allow_html=True)
        st.caption("💡「初期在庫」はマスタ登録時の基準値です。実際の現在庫は🧹資材管理タブで自動計算されます。")
        df_sup_list = pd.DataFrame(supplies)
        if not df_sup_list.empty:
            df_sup_edit = df_sup_list[["資材ID", "資材名", "カテゴリ", "初期在庫", "発注点"]]
            edited_sup = st.data_editor(
                df_sup_edit, 
                num_rows="dynamic", 
                use_container_width=True, 
                key="sup_master_ed", 
                disabled=["資材ID"],
                column_config={"初期在庫": st.column_config.NumberColumn(format="%.2f"), "発注点": st.column_config.NumberColumn(format="%.2f")}
            )
            if st.button("💾 資材マスタの変更を保存", type="primary"):
                new_supplies = []
                for _, r in edited_sup.iterrows():
                    sid = str(r.get("資材ID", "")).strip()
                    orig = next((s for s in supplies if s.get("資材ID") == sid), {})
                    if str(r.get("資材名", "")).strip() and str(r.get("資材名", "")) != "nan":
                        new_supplies.append({
                            "資材ID": sid if sid and sid != "nan" else f"SUP-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                            "資材名": str(r.get("資材名")), "カテゴリ": str(r.get("カテゴリ")),
                            "画像URL": orig.get("画像URL", ""), "初期在庫": float(r.get("初期在庫", 0)),
                            "発注点": float(r.get("発注点", 0)), "登録日": orig.get("登録日", str(date.today()))
                        })
                sheets.save_supplies(new_supplies)
                st.success("資材マスタを更新しました。")
                time.sleep(1.5)
                refresh()
        else: st.info("登録済みの資材はありません。")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="form-card"><div class="section-title">➕ 新規資材・衛生消耗品の登録</div>', unsafe_allow_html=True)
        with st.form("new_sup_form_rich"):
            c_s1, c_s2 = st.columns(2)
            new_s_name = c_s1.text_input("資材・備品名称 ＊")
            new_s_cat = c_s2.text_input("カテゴリ (例: 包材, 衛生消耗品)")
            c_s3, c_s4 = st.columns(2)
            new_s_stock = c_s3.number_input("現在の実地在庫数", min_value=0.0, value=0.0, format="%.2f")
            new_s_point = c_s4.number_input("発注注意アラート点", min_value=0.0, value=10.0, format="%.2f")
            uploaded_file = st.file_uploader("📷 写真・画像をアップロード (スマホ対応)", type=["jpg", "png", "jpeg"])
            
            if st.form_submit_button("➕ 画像付きで新規登録する"):
                if not new_s_name: st.error("資材名称は必須入力項目です。")
                else:
                    img_base64_str = ""
                    if uploaded_file and HAS_PIL:
                        try:
                            img = Image.open(uploaded_file)
                            img.thumbnail((150, 150))
                            buffered = BytesIO()
                            img.save(buffered, format="PNG", optimize=True)
                            img_base64_str = f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode('utf-8')}"
                        except Exception as e: st.warning(f"画像の処理に失敗しました。: {e}")
                    
                    current_supplies = supplies.copy()
                    current_supplies.append({
                        "資材ID": f"SUP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "資材名": new_s_name, "カテゴリ": new_s_cat, "画像URL": img_base64_str,
                        "初期在庫": new_s_stock, "発注点": new_s_point, "登録日": str(date.today())
                    })
                    sheets.save_supplies(current_supplies)
                    st.success(f"資材: {new_s_name} を登録しました。")
                    time.sleep(1.5)
                    refresh()
        st.markdown('</div>', unsafe_allow_html=True)
