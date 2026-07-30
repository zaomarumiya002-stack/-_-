# app.py
import streamlit as st
import pandas as pd
import json
import time
import base64
import re
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
#  【視認性・現場モバイル操作 究極特化版】 UI/UX CSS
# ════════════════════════════════════════════════════════════════
st.markdown("""
<style>
:root {
    --c-bg: #e2e8f0;            
    --c-surface: #ffffff;       
    --c-primary: #ea580c;       
    --c-primary-hover: #c2410c;
    --c-secondary: #0f172a;     
    --c-input-border: #64748b;  
}
.stApp { background-color: var(--c-bg); font-family: 'Helvetica Neue', Arial, sans-serif; }
h1, h2, h3, h4, h5, h6, p, span, div, label { color: var(--c-secondary); }

/* ヘッダー・カード */
.main-header {
    background: var(--c-surface); padding: 18px 24px; border-radius: 12px; margin-bottom: 24px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.08); border-left: 8px solid var(--c-primary);
}
.main-header h1 { font-size: 1.6rem !important; margin: 0 0 6px 0 !important; font-weight: 900 !important; color: var(--c-secondary) !important; }
.main-header p { color: #475569 !important; font-size: 0.95rem !important; margin: 0 !important; font-weight: 700; }
.form-card { background: var(--c-surface); border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
.section-title { font-size: 1.25rem; font-weight: 900; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; color: var(--c-secondary) !important; }
.section-title::before { content: ''; display: block; width: 6px; height: 22px; background-color: var(--c-primary); border-radius: 4px; }

/* 入力フィールド */
div[data-baseweb="input"], div[data-baseweb="select"] > div, div[data-testid="stDateInput"] > div {
    background-color: #ffffff !important; border: 2px solid var(--c-input-border) !important;
    border-radius: 8px !important; min-height: 56px !important; box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
}
div[data-baseweb="input"]:focus-within, div[data-baseweb="select"] > div:focus-within, div[data-testid="stDateInput"] > div:focus-within {
    border-color: var(--c-primary) !important; box-shadow: 0 0 0 3px rgba(234, 88, 12, 0.25) !important;
}
div[data-baseweb="input"] input, div[data-baseweb="select"], div[data-testid="stDateInput"] input { 
    font-size: 1.2rem !important; font-weight: 900 !important; color: #000000 !important; padding: 0 14px !important; text-align: center !important;
}
button[data-testid="stNumberInputStepUp"], button[data-testid="stNumberInputStepDown"] {
    min-width: 65px !important; min-height: 56px !important; border-radius: 8px !important; 
    background-color: #f1f5f9 !important; color: #000000 !important; 
    border-left: 2px solid var(--c-input-border) !important; border-right: 2px solid var(--c-input-border) !important;
}
::placeholder { color: #94a3b8 !important; opacity: 1 !important; font-weight: 600 !important; }

/* ラジオボタンのタイル化 */
div[data-testid="stRadio"] > div { display: flex; flex-wrap: wrap; gap: 10px !important; }
div[data-testid="stRadio"] label {
    background-color: #f8fafc; padding: 14px 16px !important; border-radius: 10px;
    border: 2px solid var(--c-input-border) !important; font-weight: 800 !important; cursor: pointer;
    text-align: center; flex: 1 1 auto; justify-content: center; min-width: 120px; transition: all 0.2s ease;
}
div[data-testid="stRadio"] label p { font-size: 1.1rem !important; font-weight: 900 !important; color: var(--c-secondary) !important; }
div[data-testid="stRadio"] label[data-baseweb="radio"] input:checked + div {
    background-color: var(--c-primary) !important; border-color: var(--c-primary) !important; 
    box-shadow: 0 6px 12px rgba(234, 88, 12, 0.3); transform: translateY(-2px);
}
div[data-testid="stRadio"] label[data-baseweb="radio"] input:checked + div p { color: #ffffff !important; }

/* ボタン */
.stButton button {
    border-radius: 10px !important; font-weight: 900 !important; font-size: 1.1rem !important; padding: 12px 16px !important;
    min-height: 56px !important; transition: all 0.1s; border: 2px solid var(--c-input-border) !important; 
    background: #ffffff !important; color: var(--c-secondary) !important;
}
.stButton button[kind="primary"] {
    background: linear-gradient(135deg, var(--c-primary), var(--c-primary-hover)) !important; 
    color: #ffffff !important; border: none !important; box-shadow: 0 4px 12px rgba(234, 88, 12, 0.35) !important;
}
.stButton button:active { transform: scale(0.96) !important; }

/* サイドバー */
[data-testid="stSidebar"] { background-color: var(--c-secondary) !important; padding-top: 1rem; }
[data-testid="stSidebar"], [data-testid="stSidebar"] div, [data-testid="stSidebar"] span { color: #ffffff !important; }
[data-testid="stSidebar"] div[role="radiogroup"] label {
    background: rgba(255,255,255,0.08) !important; border: 1px solid rgba(255,255,255,0.15) !important;
    padding: 12px 16px !important; border-radius: 8px !important; margin-bottom: 8px !important; transition: all 0.2s ease;
}
[data-testid="stSidebar"] div[role="radiogroup"] label p { font-size: 1.1rem !important; font-weight: 900 !important; color: #ffffff !important; }
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
    background: var(--c-primary) !important; border-color: var(--c-primary-hover) !important; box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}
[data-testid="stSidebar"] .stButton button {
    background: #f8fafc !important; border: none !important; margin-top: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important;
}
[data-testid="stSidebar"] .stButton button p { color: #0f172a !important; font-weight: 900 !important; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
#  ユーティリティ & データロード
# ════════════════════════════════════════════════════════════════
def lot_popover(label):
    return st.popover(label, use_container_width=True) if hasattr(st, "popover") else st.expander(label)

def refresh():
    st.cache_data.clear()
    st.rerun()

@st.cache_data(ttl=60)
def load_all_datasets():
    import sheets
    return {
        "arrivals": sheets.load_arrivals(), "brewing": sheets.load_brewing(), "adjustments": sheets.load_adjustments(),
        "supplies": sheets.load_supplies(), "supply_logs": sheets.load_supply_logs(),
        "materials": sheets.load_materials(), "makers": sheets.load_makers(), "inspectors": sheets.load_inspectors(),
        "order_points": sheets.load_order_points(), "recipes": sheets.load_recipes(), "recipe_logs": sheets.load_recipe_logs()
    }

try:
    import sheets
    dataset = load_all_datasets()
    arrivals, brewing, adjustments = dataset.get("arrivals", []), dataset.get("brewing", []), dataset.get("adjustments", [])
    supplies, supply_logs = dataset.get("supplies", []), dataset.get("supply_logs", [])
    materials, makers, inspectors = dataset.get("materials", []), dataset.get("makers", []), dataset.get("inspectors", [])
    order_points, recipes_raw, recipe_logs = dataset.get("order_points", {}), dataset.get("recipes", []), dataset.get("recipe_logs", [])
except Exception as e:
    st.error("🚨 データの読み込みに失敗しました。Google Sheetsの接続設定を確認してください。")
    st.stop()

# 1枠に「発注点」と「1袋重量」をJSONで同居させるハック
def parse_op_data(raw_val):
    pt, wt = 0.0, 20.0
    try:
        if isinstance(raw_val, str) and raw_val.startswith("{"):
            data = json.loads(raw_val)
            pt, wt = float(data.get("pt", 0.0)), float(data.get("wt", 20.0))
        else:
            pt = float(raw_val)
    except: pass
    return pt, wt

BIG_CAT_ICONS = {"プラント": "🏭", "OKM": "🟦"}
SUB_CAT_ICONS = {"白": "⚪", "黒": "⚫", "耐冷": "❄️", "ショクカイ": "🍽️", "めん": "🍜", "おでん": "🍢", "その他": "📦"}
_ICON_POOL = ["🔵", "🟢", "🟡", "🟣", "🟠", "🔴", "🟤", "🔷", "🔶", "🔹", "🔸", "⬛", "⬜", "🟥", "🟩", "🟦"]
_PRODUCT_ICON_POOL = ["🍥", "🥢", "🌿", "🎍", "🧊", "🍡", "🧵", "🏷️", "📌", "🧺", "🔖", "🧫"]

def _deterministic_icon(name, pool): return pool[sum(ord(ch) for ch in str(name)) % len(pool)]
def big_cat_icon(name): return BIG_CAT_ICONS.get(name, _deterministic_icon(name, _ICON_POOL))
def sub_cat_icon(name): return SUB_CAT_ICONS.get(name, _deterministic_icon(name, _ICON_POOL))
def product_icon(name): return _deterministic_icon(name, _PRODUCT_ICON_POOL)

def fmt_kg(val):
    if val is None or val == "": return "0"
    try:
        val = float(val)
        if val.is_integer(): return f"{int(val)}"
        return f"{val:.3f}".rstrip('0').rstrip('.')
    except: return str(val)

def safe_parse_recipe(recipe_val):
    if not recipe_val: return []
    data = recipe_val
    if not isinstance(data, (dict, list)):
        try:
            for _ in range(3):
                if isinstance(data, str): data = json.loads(data)
                else: break
        except: data = []
    if isinstance(data, dict): data = [data]
    if not isinstance(data, list): data = []
    return [{"原料名": str(i.get("原料名", "")).strip(), "比率": float(i.get("比率", 0.0))} for i in data if isinstance(i, dict) and str(i.get("原料名", "")).strip()]

# ════════════════════════════════════════════════════════════════
#  在庫・ロット計算
# ════════════════════════════════════════════════════════════════
def get_inventory():
    inv = {}
    for a in arrivals:
        ano = str(a.get("入荷No", "")).strip()
        if not ano: continue
        inv[ano] = {
            "入荷No": ano, "ロットNo": str(a.get("ロットNo", "")).strip(), "原料種別": str(a.get("原料種別", "")).strip(), 
            "1袋重量": float(a.get("1袋重量(kg)") or 20.0), "入荷袋数": float(a.get("袋数") or 0.0), "使用量(kg)": 0.0, "調整袋数": 0.0
        }
    for b in brewing:
        oa = b.get("その他添加物", "")
        if oa:
            try:
                items = json.loads(oa)
                for item in items:
                    t_lot = str(item.get("lot", "")).strip()
                    t_kg = float(item.get("kg", 0.0))
                    # ブレンド時の(40%)表記を安全に消去
                    valid_lots = [l for l in [re.sub(r'\(\d+%\)', '', l_raw).strip() for l_raw in t_lot.split(",")] if l and l != "─"]
                    if valid_lots:
                        kg_per_lot = t_kg / len(valid_lots)
                        for l in valid_lots:
                            for v in inv.values():
                                if v["ロットNo"] == l: v["使用量(kg)"] += kg_per_lot
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
type_totals_kg = {}
type_totals_bag = {}
for v in inventory_data.values():
    m_type = v["原料種別"]
    type_totals_kg[m_type] = type_totals_kg.get(m_type, 0.0) + v["現在庫(kg)"]
    type_totals_bag[m_type] = type_totals_bag.get(m_type, 0.0) + v["現在庫(袋)"]

def _get_active_lots(mat_name):
    opts = []
    for v in inventory_data.values():
        if v["原料種別"] == mat_name and v["現在庫(kg)"] > 0.01:
            if v["ロットNo"] not in opts: opts.append(v["ロットNo"])
    if not opts:
        recent = sorted(arrivals, key=lambda x: x.get("入荷日", ""), reverse=True)
        for a in recent:
            if str(a.get("原料種別", "")).strip() == mat_name:
                l = str(a.get("ロットNo", "")).strip()
                if l and l not in opts: opts.append(l)
                if len(opts) >= 5: break
    return opts

# ════════════════════════════════════════════════════════════════
#  カスタムUIコンポーネント (現場特化)
# ════════════════════════════════════════════════════════════════
def _change_adj(key, val):
    st.session_state[key] = st.session_state.get(key, 0.0) + val

def render_amount_adjuster(title, base_val, adj_key):
    if adj_key not in st.session_state: st.session_state[adj_key] = 0.0
    act_val = round(base_val + st.session_state[adj_key], 2)
    if act_val < 0: act_val = 0.0
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1: st.button("➖ 0.1", key=f"dec_{adj_key}", on_click=_change_adj, args=(adj_key, -0.1), use_container_width=True)
    with col2:
        st.markdown(f"""
        <div style='text-align:center; padding:10px 0; background-color:#fff7ed; border-radius:12px; border:2px solid #fdba74;'>
            <div style='color:#c2410c; font-weight:900; font-size:1.1rem; margin-bottom:4px;'>{title}</div>
            <div style='font-size:3.2rem; font-weight:900; color:#ea580c; line-height:1;'>{fmt_kg(act_val)} <span style='font-size:1.4rem; color:#f97316;'>kg</span></div>
        </div>
        """, unsafe_allow_html=True)
    with col3: st.button("➕ 0.1", key=f"inc_{adj_key}", on_click=_change_adj, args=(adj_key, 0.1), use_container_width=True)
    return act_val

def render_lot_selector(mat_name, lot_key):
    active_lots = _get_active_lots(mat_name)
    if lot_key not in st.session_state: st.session_state[lot_key] = active_lots[0] if active_lots else "未選択"
    with lot_popover(f"📦 ロット: {st.session_state[lot_key]} (タップで変更)"):
        st.markdown(f"<h4 style='text-align:center;'>{mat_name} のロット選択</h4>", unsafe_allow_html=True)
        if active_lots:
            for lot in active_lots:
                if st.button(f"{lot} (在庫あり)", key=f"btn_{lot_key}_{lot}", use_container_width=True):
                    st.session_state[lot_key] = lot
                    st.rerun()
        else:
            st.info("在庫のあるロットが見つかりません。下から手入力してください。")
        st.markdown("---")
        man_lot = st.text_input("📝 手入力 (リスト外)", key=f"man_in_{lot_key}")
        if st.button("確定", key=f"man_btn_{lot_key}", type="primary", use_container_width=True):
            if man_lot: st.session_state[lot_key] = man_lot; st.rerun()
    return st.session_state[lot_key]

# 【修正済】ボタンID重複を防ぐため、引数の operator_key をボタンkeyにも組み込んでいます。
def render_operator_selector(operator_key):
    if operator_key not in st.session_state: st.session_state[operator_key] = inspectors[0] if inspectors else "未登録"
    with lot_popover(f"👨‍🏭 担当者: {st.session_state[operator_key]} (タップで変更)"):
        st.write("担当者をタップしてください")
        for insp in inspectors:
            if st.button(insp, key=f"btn_insp_{operator_key}_{insp}", use_container_width=True):
                st.session_state[operator_key] = insp; st.rerun()
    return st.session_state[operator_key]

# ════════════════════════════════════════════════════════════════
#  サイドバー
# ════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div style="font-size:1.5rem; font-weight:900; margin-bottom:1rem; color:white; display:flex; align-items:center; gap:8px;">🏭 <span>製造ERP</span></div>', unsafe_allow_html=True)
    page = st.radio("メニュー", [
        "🏭 製造仕込み", "📊 ダッシュボード", "📥 入荷登録", "📦 在庫・棚卸", 
        "🧹 資材管理", "🔍 トレース", "📋 履歴・帳票", "📈 分析", "⚙️ マスタ設定"
    ], label_visibility="collapsed")
    st.markdown("---")
    if st.button("🔄 最新データに更新", use_container_width=True): refresh()

# ═══════════════════════════════════════════════════════════════
#  🏭 製造仕込み (現場特化UI)
# ═══════════════════════════════════════════════════════════════
if page == "🏭 製造仕込み":
    st.markdown('<div class="main-header"><h1>🏭 製造仕込み記録</h1><p>投入量は特大文字で表示されます。指示通りに計量してください。</p></div>', unsafe_allow_html=True)

    st.markdown('<div class="form-card">', unsafe_allow_html=True)
    col_d, _ = st.columns([1, 2])
    with col_d: brew_date = st.date_input("📅 仕込日", value=date.today())
    st.markdown("<br>", unsafe_allow_html=True)

    p_recipes = {r.get("品名", "未定義"): {"大カテゴリ": r.get("大カテゴリ", "その他"), "中カテゴリ": r.get("中カテゴリ", "その他"), "成分": safe_parse_recipe(r.get("配合JSON"))} for r in recipes_raw}

    st.markdown('<div style="font-weight:900; margin-bottom:8px;">① ラインを選択</div>', unsafe_allow_html=True)
    big_cats = sorted({v["大カテゴリ"] for v in p_recipes.values() if v.get("大カテゴリ")})
    big_cat_labels = [f"{big_cat_icon(c)} {c}" for c in big_cats]
    sel_big_label = st.radio("ライン", big_cat_labels, horizontal=True, label_visibility="collapsed") if big_cats else None
    big_cat = big_cats[big_cat_labels.index(sel_big_label)] if sel_big_label else None

    SUB_CAT_ORDER = ["黒", "白", "耐冷", "ショクカイ", "めん", "その他"]
    sub_cats_set = {v["中カテゴリ"] for v in p_recipes.values() if v.get("大カテゴリ") == big_cat and v.get("中カテゴリ")} if big_cat else set()
    sub_cats = sorted(sub_cats_set, key=lambda c: (SUB_CAT_ORDER.index(c) if c in SUB_CAT_ORDER else len(SUB_CAT_ORDER), c))
    sub_str = None
    if big_cat and len(sub_cats) > 1:
        st.markdown('<div style="font-weight:900; margin:20px 0 8px 0;">② 種別を選択</div>', unsafe_allow_html=True)
        sub_cat_labels = [f"{sub_cat_icon(c)} {c}" for c in sub_cats]
        sel_sub_label = st.radio("種別", sub_cat_labels, horizontal=True, label_visibility="collapsed")
        sub_str = sub_cats[sub_cat_labels.index(sel_sub_label)]
    elif sub_cats:
        sub_str = sub_cats[0]

    st.markdown('<div style="font-weight:900; margin:20px 0 8px 0;">③ 製品品番を選択</div>', unsafe_allow_html=True)
    filtered_opts = [k for k, v in p_recipes.items() if v.get("大カテゴリ") == big_cat and v.get("中カテゴリ") == sub_str] if big_cat and sub_str else []
    selected_p = None
    active_recipe = []
    if filtered_opts:
        opt_labels = [f"{product_icon(k)} {k}" for k in filtered_opts]
        sel_label = st.radio("製品", opt_labels, horizontal=True, label_visibility="collapsed")
        selected_p = filtered_opts[opt_labels.index(sel_label)]
        active_recipe = p_recipes.get(selected_p, {}).get("成分", [])

    st.markdown('</div>', unsafe_allow_html=True)

    if not active_recipe:
        st.info("👆 製品を選択してください。")
    else:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">④ 希望仕込量と石灰水量の入力</div>', unsafe_allow_html=True)

        def _add_to_field(key, amt): st.session_state[key] = float(st.session_state.get(key) or 0.0) + float(amt)
        def _clear_field(key): st.session_state[key] = None

        col_in1, col_in2 = st.columns(2)
        with col_in1:
            st.caption("👆 タップで加算（押し間違えたら✖0）")
            btns1 = st.columns(5)
            for pi, pv in enumerate([1, 10, 100, 1000]):
                btns1[pi].button(f"+{pv}", key=f"ts_{pv}", use_container_width=True, on_click=_add_to_field, args=("t_size", pv))
            btns1[4].button("✖0", key="tc", use_container_width=True, on_click=_clear_field, args=("t_size",))
            target_size = st.number_input("🏭 希望仕込製品量 (kg)", min_value=1.0, step=1.0, value=None, format="%.0f", key="t_size")

        with col_in2:
            st.caption("👆 タップで加算（押し間違えたら✖0）")
            btns2 = st.columns(5)
            for pi, pv in enumerate([1, 10, 100, 1000]):
                btns2[pi].button(f"+{pv}", key=f"lw_{pv}", use_container_width=True, on_click=_add_to_field, args=("l_size", pv))
            btns2[4].button("✖0", key="lc", use_container_width=True, on_click=_clear_field, args=("l_size",))
            lime_water_size = st.number_input("💧 石灰水作成量 (kg)", min_value=0.0, step=1.0, value=None, format="%.0f", key="l_size")
        
        st.markdown("<br>", unsafe_allow_html=True)
        c_op1, c_op2 = st.columns(2)
        with c_op1: operator = render_operator_selector("op_key")
        with c_op2: brew_remarks = st.text_input("📝 備考（任意）", placeholder="特記事項があれば入力")
        st.markdown('</div>', unsafe_allow_html=True)

        if target_size is None or lime_water_size is None:
            st.info("💡 仕込量と石灰水量を入力すると、下に準備リストが表示されます。")
        else:
            st.markdown('<div class="section-title" style="margin-top:32px;">📦 準備する原料・ロット</div>', unsafe_allow_html=True)
            submitted_ingredients = []
            is_summer = 6 <= date.today().month <= 9

            for i, item in enumerate(active_recipe[:10]):
                r_name = str(item.get("原料名", "")).strip()
                base_ratio = float(item.get("比率", 0.0))
                is_water, is_lime, is_konjac = ("水" in r_name or "お湯" in r_name), ("石灰" in r_name or "カルシウム" in r_name), ("こんにゃく" in r_name)
                icon = "💧" if is_water else ("🧂" if is_lime else ("📦" if is_konjac else "🔹"))

                if is_water: calc_kg = max(0.0, target_size * (base_ratio / 100.0) - lime_water_size)
                elif is_lime: calc_kg = lime_water_size * ((base_ratio + 0.01 if is_summer else base_ratio) / 10.0)
                else: calc_kg = target_size * (base_ratio / 100.0)

                with st.container(border=True):
                    st.markdown(f"<div style='font-size:1.3rem; font-weight:900;'>{icon} {r_name}</div>", unsafe_allow_html=True)
                    
                    if is_water:
                        st.markdown(f"<div style='color:#3b82f6; font-weight:900; font-size:1.6rem; text-align:center; padding:10px 0;'>必要量: {fmt_kg(calc_kg)} kg <br><span style='font-size:1rem;color:#64748b;'>(石灰水除く)</span></div>", unsafe_allow_html=True)
                        submitted_ingredients.append({"原料名": r_name, "kg": round(calc_kg, 2), "lot": "─"})
                    
                    elif is_konjac:
                        blend_key = f"kb_{selected_p}_{i}"
                        blend_on = st.checkbox("🧪 2種類のこんにゃく粉をブレンドする", key=blend_key)
                        konjac_mats = [m for m in materials if "こんにゃく" in m] or [r_name]
                        
                        if blend_on:
                            ratio_key = f"kr_{selected_p}_{i}"
                            if ratio_key not in st.session_state: st.session_state[ratio_key] = 50
                            
                            st.markdown("<div style='margin-bottom:8px; font-weight:900; color:#475569;'>👇 🅰️の配合比率(%)をタップして選択</div>", unsafe_allow_html=True)
                            btn_cols = st.columns(9)
                            for pidx, pv in enumerate(range(10, 100, 10)):
                                is_sel = (st.session_state[ratio_key] == pv)
                                btn_cols[pidx].button(f"{pv}%", key=f"rbtn_{ratio_key}_{pv}", on_click=lambda k, v: st.session_state.update({k: v}), args=(ratio_key, pv), type="primary" if is_sel else "secondary", use_container_width=True)
                            
                            ratio_a = st.session_state[ratio_key]
                            ratio_b = 100 - ratio_a
                            
                            st.markdown("---")
                            mat_a = st.radio("🅰️ 原料種別", konjac_mats, key=f"kma_{selected_p}_{i}", horizontal=True)
                            act_a = render_amount_adjuster(f"🅰️ 投入量 ({ratio_a}%)", calc_kg * ratio_a / 100.0, f"adj_a_{selected_p}_{i}")
                            lot_a = render_lot_selector(mat_a, f"lot_a_{selected_p}_{i}")
                            
                            st.markdown("---")
                            mat_b = st.radio("🅱️ 原料種別", konjac_mats, index=1 if len(konjac_mats)>1 else 0, key=f"kmb_{selected_p}_{i}", horizontal=True)
                            act_b = render_amount_adjuster(f"🅱️ 投入量 ({ratio_b}%)", calc_kg * ratio_b / 100.0, f"adj_b_{selected_p}_{i}")
                            lot_b = render_lot_selector(mat_b, f"lot_b_{selected_p}_{i}")

                            submitted_ingredients.append({"原料名": mat_a, "kg": act_a, "lot": f"{lot_a}({ratio_a}%)"})
                            submitted_ingredients.append({"原料名": mat_b, "kg": act_b, "lot": f"{lot_b}({ratio_b}%)"})
                            
                            st.markdown(f"<div style='text-align:center; padding:12px; margin-top:20px; background:#fef3c7; border:2px solid #f59e0b; border-radius:12px;'><div style='color:#b45309; font-weight:900;'>🧪 ブレンド合計投入量</div><div style='font-size:2.4rem; font-weight:900; color:#d97706;'>{fmt_kg(act_a + act_b)} <span style='font-size:1.2rem'>kg</span></div></div>", unsafe_allow_html=True)
                        else:
                            act_kg = render_amount_adjuster("投入量", calc_kg, f"adj_{selected_p}_{i}")
                            final_lot = render_lot_selector(r_name, f"lot_{selected_p}_{i}")
                            submitted_ingredients.append({"原料名": r_name, "kg": act_kg, "lot": final_lot})
                    
                    else:
                        act_kg = render_amount_adjuster("投入量", calc_kg, f"adj_{selected_p}_{i}")
                        final_lot = render_lot_selector(r_name, f"lot_{selected_p}_{i}")
                        submitted_ingredients.append({"原料名": r_name, "kg": act_kg, "lot": final_lot})

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("💾 この内容で製造記録を保存する", type="primary", use_container_width=True):
                k_kg = s_kg = st_kg = lime_kg = 0.0
                k_lot = s_lot = st_lot = "─"
                for ing in submitted_ingredients:
                    n, amt, lot = ing["原料名"], ing["kg"], ing["lot"]
                    if "こんにゃく" in n: k_kg += amt; k_lot = lot if k_lot == "─" else (k_lot if lot in k_lot else f"{k_lot} / {lot}")
                    elif "海藻" in n: s_kg += amt; s_lot = lot if s_lot == "─" else (s_lot if lot in s_lot else f"{s_lot} / {lot}")
                    elif "デンプン" in n or "でんぷん" in n: st_kg += amt; st_lot = lot if st_lot == "─" else (st_lot if lot in st_lot else f"{st_lot} / {lot}")
                    elif "石灰" in n or "カルシウム" in n: lime_kg += amt

                sheets.append_brewing({
                    "仕込No": sheets.next_brewing_no(brewing), "仕込日": str(brew_date), "品名": selected_p,
                    "メーカー": operator, "主原料ロット": k_lot, "仕込量(kg)": round(target_size, 2),
                    "こんにゃく精粉(kg)": round(k_kg, 2), "海藻粉(kg)": round(s_kg, 2), "海藻粉ロット": s_lot,
                    "デンプン(kg)": round(st_kg, 2), "デンプンロット": st_lot, "デンプン種別": "-",
                    "石灰(kg)": round(lime_kg, 2), "石灰水(L)": round(lime_water_size, 2),
                    "その他添加物": json.dumps(submitted_ingredients, ensure_ascii=False),
                    "備考": f"{brew_remarks}", "登録日時": datetime.now().isoformat()
                })
                
                # 入力状態をリセット
                for key in list(st.session_state.keys()):
                    if any(key.startswith(p) for p in ["adj_", "ts_", "lw_", "lot_", "t_size", "l_size", "kr_", "kb_"]):
                        del st.session_state[key]
                
                st.balloons()
                st.success(f"✅ 【{selected_p}】の製造記録を保存しました！画面をリセットします...")
                time.sleep(2.0)
                refresh()

# ═══════════════════════════════════════════════════════════════
#  📊 ダッシュボード (超リッチカスタムデザイン)
# ═══════════════════════════════════════════════════════════════
elif page == "📊 ダッシュボード":
    st.markdown('<div class="main-header"><h1>📊 サマリーと在庫モニター</h1></div>', unsafe_allow_html=True)
    
    # --- サマリー ---
    df_brw_global = pd.DataFrame(brewing)
    if not df_brw_global.empty:
        df_brw_global["仕込日_dt"] = pd.to_datetime(df_brw_global["仕込日"], errors="coerce")
        df_brw_today = df_brw_global[df_brw_global["仕込日_dt"].dt.strftime("%Y-%m-%d") == date.today().strftime("%Y-%m-%d")]
        today_total_kg = pd.to_numeric(df_brw_today["仕込量(kg)"], errors="coerce").fillna(0).sum()
        today_count = len(df_brw_today)
    else: today_total_kg = today_count = 0

    c1, c2 = st.columns(2)
    with c1: st.metric("📦 本日の総製造量", f"{fmt_kg(today_total_kg)} kg", f"{today_count} 件製造")
    with c2:
        alert_count = sum(1 for m in materials if parse_op_data(order_points.get(m, 0.0))[0] > 0 and type_totals_bag.get(m, 0.0) < parse_op_data(order_points.get(m, 0.0))[0])
        st.metric("⚠️ 在庫不足原料", f"{alert_count} 品目")

    st.markdown("---")
    st.markdown('<div class="section-title">📦 主要原料 現在庫とアラート</div>', unsafe_allow_html=True)
    cols = st.columns(min(3, len(materials) if materials else 1))
    
    for idx, m in enumerate(materials):
        pt, wt = parse_op_data(order_points.get(m, 0.0))
        curr_kg = type_totals_kg.get(m, 0.0)
        curr_bag = curr_kg / wt if wt > 0 else 0
        is_alert = (pt > 0 and curr_bag < pt)
        
        # 枠色・背景色をアラート状態によって変更
        border_col = "#ef4444" if is_alert else "#cbd5e1"
        bg_col = "#fef2f2" if is_alert else "#ffffff"
        alert_msg = f"<div style='font-size:0.9rem; color:#ef4444; font-weight:bold; margin-top:8px;'>⚠️ 発注点({fmt_kg(pt)}袋) を下回っています</div>" if is_alert else f"<div style='font-size:0.9rem; color:#64748b; font-weight:bold; margin-top:8px;'>✅ 発注点: {fmt_kg(pt)}袋</div>"

        with cols[idx % 3]:
            st.markdown(f"""
            <div style="background:{bg_col}; border:2px solid {border_col}; border-radius:12px; padding:18px; margin-bottom:16px;">
                <div style="font-weight:900; color:#0f172a; font-size:1.15rem;">{m}</div>
                <div style="font-size:2.2rem; font-weight:900; color:#ea580c; margin:6px 0 2px 0;">
                    {fmt_kg(curr_kg)}<span style="font-size:1.1rem; color:#64748b; margin-right:8px;">kg</span> 
                    <span style="font-size:1.6rem; color:#0f172a;">({fmt_kg(curr_bag)}袋)</span>
                </div>
                <div style="font-size:0.85rem; color:#64748b; margin-bottom:4px;">1袋 = {fmt_kg(wt)} kg 設定</div>
                {alert_msg}
            </div>
            """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
#  📥 入荷登録
# ═══════════════════════════════════════════════════════════════
elif page == "📥 入荷登録":
    st.markdown('<div class="main-header"><h1>📥 原料入荷品質記録</h1><p>原料を選ぶと、マスタで設定した「1袋重量」が自動セットされます。</p></div>', unsafe_allow_html=True)
    
    t_in, t_hist = st.tabs(["➕ 新規入荷登録", "📋 入荷履歴"])
    
    with t_in:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📦 基本入荷情報</div>', unsafe_allow_html=True)
        new_no = sheets.next_arrival_no(arrivals)
        
        arr_date = st.date_input("入荷日", value=date.today())
        maker_sel = st.selectbox("メーカー", makers if makers else ["未登録"])
        lot_val = st.text_input("ロットNo ＊必須", placeholder="例: L12345 (バーコードリーダー可)")
        
        m_type = st.selectbox("原料種別", materials if materials else ["未登録"])
        _, default_wt = parse_op_data(order_points.get(m_type, 0.0))
        
        c1, c2 = st.columns(2)
        bags_qty = c1.number_input("入荷袋数", min_value=1.0, value=10.0, step=1.0)
        weight_per_bag = c2.number_input("1袋重量 (kg) ※自動セット済", min_value=1.0, value=float(default_wt), step=1.0)
        st.info(f"💡 合計入荷重量: **{fmt_kg(bags_qty * weight_per_bag)} kg**")
        
        st.markdown('<div class="section-title" style="margin-top:20px;">🔍 受入品質検査</div>', unsafe_allow_html=True)
        chk_app = st.selectbox("外観・規格・賞味期限・異物 総合評価", ["OK（すべて正常）", "NG（異常あり）"])
        operator = render_operator_selector("arr_op")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 入荷記録を登録する", type="primary", use_container_width=True):
            if not lot_val: st.error("ロットNoは必須項目です。")
            else:
                sheets.append_arrival({
                    "入荷No": new_no, "入荷日": str(arr_date), "メーカー": maker_sel, "ロットNo": lot_val,
                    "原料種別": m_type, "袋数": bags_qty, "1袋重量(kg)": weight_per_bag, "総量(kg)": bags_qty * weight_per_bag,
                    "外観": chk_app, "品名・規格確認": chk_app, "賞味期限": chk_app, "異物": chk_app,
                    "担当者": operator, "備考": "", "登録日時": datetime.now().isoformat()
                })
                st.success("入荷記録を保存しました。")
                time.sleep(1.5)
                refresh()
        st.markdown('</div>', unsafe_allow_html=True)
        
    with t_hist:
        if arrivals:
            df_arr = pd.DataFrame(arrivals)[["入荷日", "原料種別", "ロットNo", "メーカー", "総量(kg)"]][::-1]
            st.dataframe(df_arr.head(50), use_container_width=True, hide_index=True)
        else: st.info("入荷履歴はありません。")

# ═══════════════════════════════════════════════════════════════
#  📦 在庫・棚卸
# ═══════════════════════════════════════════════════════════════
elif page == "📦 在庫・棚卸":
    st.markdown('<div class="main-header"><h1>📦 在庫・棚卸管理</h1></div>', unsafe_allow_html=True)
    t_inv, t_adj = st.tabs(["📋 ロット別 現在庫", "⚖️ 棚卸し (在庫調整)"])
    
    with t_inv:
        active_inv = [v for v in inventory_data.values() if v["現在庫(袋)"] > 0.0]
        if active_inv:
            st.dataframe(pd.DataFrame(active_inv)[["原料種別", "ロットNo", "入荷袋数", "使用袋数", "調整袋数", "現在庫(袋)", "現在庫(kg)"]], use_container_width=True, hide_index=True)
        else: st.info("在庫データがありません。")
        
    with t_adj:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        if inventory_data:
            tgt_list = {f"{v['原料種別']} (ロット:{v['ロットNo']}) - 現在:{v['現在庫(袋)']}袋": v["入荷No"] for v in inventory_data.values()}
            selected_tgt = st.selectbox("調整対象ロット", list(tgt_list.keys()))
            diff_bags = st.number_input("理論在庫との差分（袋数） ※増やす場合はプラス、減らす場合はマイナス", value=0.0, step=1.0)
            reason_txt = st.text_input("調整理由")
            op = render_operator_selector("adj_op")
            if st.button("💾 在庫を調整する", type="primary"):
                sheets.append_adjustment({
                    "調整ID": f"ADJ-{datetime.now().strftime('%Y%m%d%H%M%S')}", "入荷No": tgt_list[selected_tgt],
                    "調整日": str(date.today()), "調整袋数": diff_bags, "理由": reason_txt, "担当者": op, "登録日時": datetime.now().isoformat()
                })
                st.success("調整を保存しました。")
                time.sleep(1.5)
                refresh()
        st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
#  🧹 資材管理
# ═══════════════════════════════════════════════════════════════
elif page == "🧹 資材管理":
    st.markdown('<div class="main-header"><h1>🧹 資材・消耗品管理</h1></div>', unsafe_allow_html=True)
    t_s1, t_s2 = st.tabs(["📋 在庫一覧・入出庫", "🕒 ログ管理"])
    
    with t_s1:
        if not supplies: st.warning("資材が未登録です。マスタ設定よりご登録ください。")
        else:
            supply_inventory = {s.get("資材ID"): float(s.get("初期在庫") or 0.0) for s in supplies}
            for log in supply_logs:
                sid = log.get("資材ID")
                if sid in supply_inventory:
                    qty = float(log.get("数量") or 0.0)
                    if log.get("処理") == "入荷": supply_inventory[sid] += qty
                    elif log.get("処理") == "使用": supply_inventory[sid] -= qty

            cols_grid = st.columns(min(3, len(supplies)))
            for idx, s in enumerate(supplies):
                sid = s.get("資材ID")
                with cols_grid[idx % 3]:
                    with st.container(border=True):
                        if s.get("画像URL"): st.image(s.get("画像URL"), width=60)
                        st.markdown(f"**{s.get('資材名')}**")
                        st.metric("現在庫", fmt_kg(supply_inventory.get(sid, 0.0)))
                        with lot_popover("🔄 入出庫"):
                            action = st.radio("処理", ["➖ 使用", "➕ 補充"], key=f"act_{sid}", horizontal=True)
                            qty = st.number_input("数量", min_value=1.0, value=1.0, step=1.0, key=f"qty_{sid}")
                            op = render_operator_selector(f"op_{sid}")
                            if st.button("💾 保存", key=f"btn_{sid}", type="primary", use_container_width=True):
                                sheets.append_supply_log({
                                    "ログID": f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                                    "登録日": str(date.today()), "資材ID": sid, "処理": "使用" if "使用" in action else "入荷", 
                                    "数量": qty, "作業者": op, "備考": "", "登録日時": datetime.now().isoformat()
                                })
                                st.success("記録しました")
                                time.sleep(1.0)
                                refresh()
                                
    with t_s2:
        if supply_logs:
            id_name_map = {s.get("資材ID"): s.get("資材名") for s in supplies}
            df_logs = pd.DataFrame(supply_logs)
            df_logs["資材名"] = df_logs["資材ID"].map(id_name_map)
            df_logs_sorted = df_logs.sort_values("登録日", ascending=False)
            st.dataframe(df_logs_sorted[["登録日", "資材名", "処理", "数量", "作業者"]].head(50), use_container_width=True, hide_index=True)
            
            st.markdown('<div class="section-title">🚨 ログの取り消し・削除</div>', unsafe_allow_html=True)
            log_options = {f"{r.get('登録日','')} / {r.get('資材名','')} / {r.get('処理','')} {fmt_kg(r.get('数量',0))}": r.get("ログID", "") for _, r in df_logs_sorted.head(30).iterrows()}
            if log_options:
                sel_log = st.selectbox("削除するログを選択", list(log_options.keys()))
                if st.button("🗑️ このログを削除", type="primary"):
                    sheets.delete_supply_log(log_options[sel_log])
                    st.success("削除しました。"); time.sleep(1); refresh()

# ═══════════════════════════════════════════════════════════════
#  🔍 トレース
# ═══════════════════════════════════════════════════════════════
elif page == "🔍 トレース":
    st.markdown('<div class="main-header"><h1>🔍 双方向原料トレース</h1></div>', unsafe_allow_html=True)
    trace_dir = st.radio("トレース方向", ["➡️ 原料ロットから製品を追跡（フォワード）", "⬅️ 製品から原料を遡及（バックワード）"])
    
    st.markdown('<div class="form-card">', unsafe_allow_html=True)
    if "フォワード" in trace_dir:
        lot_list = sorted(list(set([str(a.get("ロットNo", "")).strip() for a in arrivals if a.get("ロットNo")])), reverse=True)
        tgt_lot = st.selectbox("検索する原料ロット", lot_list if lot_list else ["なし"])
        if st.button("➡️ 追跡開始", type="primary", use_container_width=True):
            match_brw = [b for b in brewing if tgt_lot in b.get("その他添加物", "")]
            if match_brw: st.dataframe(pd.DataFrame(match_brw)[["仕込日", "品名", "仕込量(kg)"]], use_container_width=True, hide_index=True)
            else: st.warning("履歴がありません。")
    else:
        brw_opts = {f"No.{b.get('仕込No')} - {b.get('品名')} ({b.get('仕込日')})": b for b in brewing}
        if brw_opts:
            sel_b = st.selectbox("対象の製造記録", list(brw_opts.keys()))
            b_data = brw_opts[sel_b]
            if st.button("⬅️ 遡及開始", type="primary", use_container_width=True):
                used_lots = []
                try:
                    for ing in json.loads(b_data.get("その他添加物", "[]")):
                        l_nums = str(ing.get("lot", "")).strip().split(",")
                        for l in [re.sub(r'\(\d+%\)', '', x).strip() for x in l_nums]:
                            if l and l != "─": used_lots.append({"原料種別": ing.get("原料名"), "ロットNo": l})
                except: pass
                if used_lots:
                    details = []
                    for u in used_lots:
                        arr = next((a for a in arrivals if str(a.get("ロットNo", "")).strip() == u["ロットNo"]), None)
                        if arr: details.append({"原料種別": u["原料種別"], "ロットNo": u["ロットNo"], "入荷日": arr.get("入荷日"), "メーカー": arr.get("メーカー")})
                        else: details.append({"原料種別": u["原料種別"], "ロットNo": u["ロットNo"], "入荷日": "不明", "メーカー": "不明"})
                    st.dataframe(pd.DataFrame(details), use_container_width=True, hide_index=True)
                else: st.warning("原料ロットの記録はありません。")
    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
#  📋 履歴・帳票
# ═══════════════════════════════════════════════════════════════
elif page == "📋 履歴・帳票":
    st.markdown('<div class="main-header"><h1>📋 製造履歴・帳票出力</h1></div>', unsafe_allow_html=True)
    if not brewing: st.info("データがありません。")
    else:
        df_brw = pd.DataFrame(brewing)
        df_brw["仕込日_dt"] = pd.to_datetime(df_brw["仕込日"], errors="coerce")
        
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        s_date = c1.date_input("開始日", value=date.today().replace(day=1))
        e_date = c2.date_input("終了日", value=date.today())
        
        mask = (df_brw["仕込日_dt"].dt.date >= s_date) & (df_brw["仕込日_dt"].dt.date <= e_date)
        filtered_df = df_brw[mask].copy().sort_values("仕込日", ascending=False)
        
        if HAS_OPENPYXL and not filtered_df.empty:
            def generate_excel_report(df, start_d, end_d):
                wb = Workbook()
                ws = wb.active
                ws.title = "製造記録"
                headers = ["製造日", "仕込No", "製品名", "担当者", "製造量(kg)", "石灰水(L)", "備考"]
                for col_idx, h in enumerate(headers, 1): ws.cell(row=1, column=col_idx, value=h)
                for r_idx, row in enumerate(df.itertuples(), 2):
                    ws.cell(row=r_idx, column=1, value=str(getattr(row, "仕込日", "")))
                    ws.cell(row=r_idx, column=2, value=str(getattr(row, "仕込No", "")))
                    ws.cell(row=r_idx, column=3, value=str(getattr(row, "品名", "")))
                    ws.cell(row=r_idx, column=4, value=str(getattr(row, "メーカー", "")))
                    ws.cell(row=r_idx, column=5, value=float(getattr(row, "_6", 0) or 0))
                    ws.cell(row=r_idx, column=6, value=float(getattr(row, "_14", 0) or 0))
                    ws.cell(row=r_idx, column=7, value=str(getattr(row, "備考", "")))
                return wb
                
            wb = generate_excel_report(filtered_df, s_date.strftime("%Y/%m/%d"), e_date.strftime("%Y/%m/%d"))
            excel_buffer = BytesIO()
            wb.save(excel_buffer)
            st.download_button("🖨️ Excel帳票をダウンロード", data=excel_buffer.getvalue(), file_name=f"製造記録_{s_date}_{e_date}.xlsx", type="primary")
        
        st.dataframe(filtered_df[["仕込日", "仕込No", "品名", "仕込量(kg)", "主原料ロット", "備考"]], use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="form-card"><div class="section-title">✏️ インライン編集・削除</div>', unsafe_allow_html=True)
        brw_opts = {f"No.{r.get('仕込No','')} - {r.get('品名','')} ({r.get('仕込日','')})": r for _, r in filtered_df.iterrows()}
        if brw_opts:
            sel_rec = brw_opts[st.selectbox("操作する記録を選択", list(brw_opts.keys()))]
            with st.form("edit_form"):
                e_date = st.text_input("製造日", value=str(sel_rec.get("仕込日", "")))
                e_name = st.text_input("品名", value=str(sel_rec.get("品名", "")))
                e_size = st.number_input("製造量(kg)", value=float(sel_rec.get("仕込量(kg)", 100) or 100))
                e_note = st.text_area("備考", value=str(sel_rec.get("備考", "")))
                
                c_s, c_d = st.columns(2)
                do_save = c_s.form_submit_button("💾 上書き保存", type="primary", use_container_width=True)
                do_del = c_d.form_submit_button("🗑️ 削除", use_container_width=True)
                
                if do_save or do_del:
                    updated_brewing = [b for b in brewing if b.get("仕込No") != sel_rec.get("仕込No")]
                    if do_save:
                        new_rec = dict(sel_rec)
                        new_rec.update({"仕込日": e_date, "品名": e_name, "仕込量(kg)": e_size, "備考": e_note + f" 【修正:{date.today()}】"})
                        updated_brewing.append(new_rec)
                        sheets.save_brewing(updated_brewing)
                        st.success("更新しました。")
                    else:
                        sheets.save_brewing(updated_brewing)
                        st.success("削除しました。")
                    time.sleep(1.5); refresh()
        st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
#  📈 分析
# ═══════════════════════════════════════════════════════════════
elif page == "📈 分析":
    st.markdown('<div class="main-header"><h1>📈 製造・原料 分析</h1></div>', unsafe_allow_html=True)
    df_brw_global = pd.DataFrame(brewing)
    if df_brw_global.empty: st.info("データがありません。")
    else:
        df_brw_global["仕込日_dt"] = pd.to_datetime(df_brw_global["仕込日"], errors="coerce")
        df_brw_global["month"] = df_brw_global["仕込日_dt"].dt.to_period("M").astype(str)
        df_brw_global["仕込量(kg)"] = pd.to_numeric(df_brw_global["仕込量(kg)"], errors="coerce").fillna(0)
        
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        monthly_trend = df_brw_global.groupby("month")["仕込量(kg)"].sum().reset_index().sort_values("month")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=monthly_trend["month"], y=monthly_trend["仕込量(kg)"], name="製造量", marker_color="#ea580c"))
        fig.update_layout(title="月間生産推移 (kg)", xaxis_title="年月", yaxis_title="総製造量", plot_bgcolor="#f8fafc")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="form-card">', unsafe_allow_html=True)
            pie_data = df_brw_global.groupby("品名")["仕込量(kg)"].sum().reset_index()
            st.plotly_chart(px.pie(pie_data, names="品名", values="仕込量(kg)", title="製品構成比", hole=0.4), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="form-card">', unsafe_allow_html=True)
            top10 = pie_data.sort_values("仕込量(kg)", ascending=True).tail(10)
            st.plotly_chart(px.bar(top10, x="仕込量(kg)", y="品名", orientation='h', title="製造量 TOP10"), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
#  ⚙️ マスタ設定
# ═══════════════════════════════════════════════════════════════
elif page == "⚙️ マスタ設定":
    st.markdown('<div class="main-header"><h1>⚙️ マスターデータ管理</h1></div>', unsafe_allow_html=True)
    t1, t2, t3, t4, t5 = st.tabs(["⚗️ 原料", "🏢 担当者", "🚨 発注点・重量", "🧪 レシピ", "📦 資材"])
    
    with t1:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        ed_m = st.data_editor(pd.DataFrame({"原料名": materials}), num_rows="dynamic", use_container_width=True)
        if st.button("💾 原料マスタ保存", type="primary"):
            sheets.save_materials([str(x).strip() for x in ed_m["原料名"].tolist() if str(x).strip()])
            st.success("保存しました。"); time.sleep(1); refresh()
        st.markdown('</div>', unsafe_allow_html=True)
            
    with t2:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        ed_u = st.data_editor(pd.DataFrame({"担当者名": inspectors}), num_rows="dynamic", use_container_width=True)
        if st.button("💾 担当者保存", type="primary"):
            sheets.save_inspectors([str(x).strip() for x in ed_u["担当者名"].tolist() if str(x).strip()])
            st.success("保存しました。"); time.sleep(1); refresh()
        st.markdown('</div>', unsafe_allow_html=True)

    with t3:
        st.markdown('<div class="form-card"><p>💡 入荷登録時にここで設定した「1袋重量」が自動で入力されます。</p>', unsafe_allow_html=True)
        op_rows = []
        for m in materials:
            pt, wt = parse_op_data(order_points.get(m, 0.0))
            op_rows.append({"原料名": m, "発注点(袋)": pt, "1袋重量(kg)": wt})
            
        edited_op = st.data_editor(pd.DataFrame(op_rows), use_container_width=True)
        if st.button("💾 発注点・重量保存", type="primary"):
            new_dict = {}
            for _, r in edited_op.iterrows():
                if str(r["原料名"]).strip():
                    new_dict[str(r["原料名"]).strip()] = json.dumps({"pt": float(r["発注点(袋)"]), "wt": float(r["1袋重量(kg)"])})
            sheets.save_order_points(new_dict)
            st.success("保存しました。"); time.sleep(1); refresh()
        st.markdown('</div>', unsafe_allow_html=True)

    with t4:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        edit_mode = st.radio("操作を選択", ["新規作成", "既存レシピの編集"], horizontal=True)
        target_recipe, old_json = None, "[]"
        if edit_mode == "既存レシピの編集" and recipes_raw:
            target_name = st.selectbox("編集するレシピ", [r["品名"] for r in recipes_raw])
            target_recipe = next((r for r in recipes_raw if r["品名"] == target_name), None)
            if target_recipe: old_json = target_recipe.get("配合JSON", "[]")
        
        init_name = target_recipe["品名"] if target_recipe else ""
        init_cat_m = "OKM" if target_recipe and target_recipe.get("大カテゴリ") == "OKM" else "プラント"
        init_cat_s = target_recipe.get("中カテゴリ", "黒") if target_recipe else "黒"
        try: init_items = json.loads(old_json) if isinstance(old_json, str) else old_json
        except: init_items = []
        def_mats = ["(未設定)", "水"] + materials
        
        with st.form("recipe_form"):
            cat_main = st.radio("大カテゴリ", ["🏭 プラント", "🟦 OKM"], index=0 if init_cat_m == "プラント" else 1, horizontal=True)
            cat_sub = st.radio("中カテゴリ", ["⚪ 白", "⚫ 黒", "❄️ 耐冷", "🍽️ ショクカイ", "🍜 めん", "📦 その他"], 
                               index=["白","黒","耐冷","ショクカイ","めん","その他"].index(init_cat_s) if init_cat_s in ["白","黒","耐冷","ショクカイ","めん","その他"] else 1, horizontal=True)
            new_p_name = st.text_input("製品名", value=init_name, disabled=(target_recipe is not None))
            
            cols_recipe = []
            for j in range(10):
                c_n, c_w = st.columns([2, 1])
                def_mat_val = init_items[j]["原料名"] if j < len(init_items) else "(未設定)"
                def_rat_val = float(init_items[j]["比率"]) if j < len(init_items) else 0.00
                uid = f"{init_name}_{j}" if target_recipe else f"new_{j}"
                ing_mat = c_n.selectbox(f"成分 {j+1}", def_mats, index=def_mats.index(def_mat_val) if def_mat_val in def_mats else 0, key=f"rmat_{uid}")
                ing_ratio = c_w.number_input("比率(％)", min_value=0.00, value=def_rat_val, step=0.01, key=f"rrat_{uid}")
                cols_recipe.append({"name": ing_mat, "ratio": ing_ratio})
            
            if st.form_submit_button("💾 レシピを保存"):
                valid_items = [{"原料名": i["name"], "比率": float(i["ratio"])} for i in cols_recipe if i["name"] != "(未設定)" and i["ratio"] > 0]
                cat_str = "プラント" if "プラント" in cat_main else "OKM"
                sub_str = cat_sub.split(" ")[1] if cat_str == "プラント" else "その他"
                updated_recipes = [r for r in recipes_raw if r["品名"] != new_p_name]
                updated_recipes.append({"品名": new_p_name, "大カテゴリ": cat_str, "中カテゴリ": sub_str, "配合JSON": json.dumps(valid_items, ensure_ascii=False)})
                sheets.save_recipes(updated_recipes)
                st.success("レシピを保存しました。"); time.sleep(1); refresh()
        st.markdown('</div>', unsafe_allow_html=True)

    with t5:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        with st.form("new_sup_form"):
            new_s_name = st.text_input("資材名称 ＊")
            new_s_cat = st.text_input("カテゴリ (例: 包材)")
            uploaded_file = st.file_uploader("📷 画像 (任意)", type=["jpg", "png", "jpeg"])
            if st.form_submit_button("💾 資材を登録"):
                if not new_s_name: st.error("名称は必須です。")
                else:
                    img_str = ""
                    if uploaded_file and HAS_PIL:
                        img = Image.open(uploaded_file)
                        img.thumbnail((150, 150))
                        buffered = BytesIO()
                        img.save(buffered, format="PNG")
                        img_str = f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode('utf-8')}"
                    cur_sup = supplies.copy()
                    cur_sup.append({"資材ID": f"SUP-{datetime.now().strftime('%Y%m%d%H%M%S')}", "資材名": new_s_name, "カテゴリ": new_s_cat, "画像URL": img_str, "初期在庫": 0, "発注点": 10, "登録日": str(date.today())})
                    sheets.save_supplies(cur_sup)
                    st.success("資材を登録しました。"); time.sleep(1); refresh()
        st.markdown('</div>', unsafe_allow_html=True)
