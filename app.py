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
#  【視認性・モバイル操作性 究極特化版】 UI/UX CSS
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
/* メインエリアの基本テキストカラー (サイドバーには影響させない) */
h1, h2, h3, h4, h5, h6, p, span, div, label { color: var(--c-secondary); }

/* --- ヘッダー・カード --- */
.main-header {
    background: var(--c-surface); padding: 18px 24px; border-radius: 12px; margin-bottom: 24px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.08); border-left: 8px solid var(--c-primary);
}
.main-header h1 { font-size: 1.6rem !important; margin: 0 0 6px 0 !important; font-weight: 900 !important; color: var(--c-secondary) !important; }
.main-header p { color: #475569 !important; font-size: 0.95rem !important; margin: 0 !important; font-weight: 700; }
.form-card { background: var(--c-surface); border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
.section-title { font-size: 1.25rem; font-weight: 900; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; color: var(--c-secondary) !important; }
.section-title::before { content: ''; display: block; width: 6px; height: 22px; background-color: var(--c-primary); border-radius: 4px; }

/* 🚨🚨 視認性最大化: 入力フィールドの徹底改善 🚨🚨 */
div[data-baseweb="input"],
div[data-baseweb="select"] > div,
div[data-testid="stDateInput"] > div {
    background-color: #ffffff !important;
    border: 2px solid var(--c-input-border) !important;
    border-radius: 8px !important;
    min-height: 56px !important;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
}
div[data-baseweb="input"]:focus-within,
div[data-baseweb="select"] > div:focus-within,
div[data-testid="stDateInput"] > div:focus-within {
    border-color: var(--c-primary) !important;
    box-shadow: 0 0 0 3px rgba(234, 88, 12, 0.25) !important;
}
div[data-baseweb="input"] input, 
div[data-baseweb="select"],
div[data-testid="stDateInput"] input { 
    font-size: 1.2rem !important; font-weight: 900 !important; color: #000000 !important; padding: 0 14px !important;
}
div[data-baseweb="input"] input[type="number"] { text-align: center !important; }
button[data-testid="stNumberInputStepUp"], button[data-testid="stNumberInputStepDown"] {
    min-width: 65px !important; min-height: 56px !important; border-radius: 8px !important; 
    background-color: #f1f5f9 !important; color: #000000 !important; 
    border-left: 2px solid var(--c-input-border) !important; border-right: 2px solid var(--c-input-border) !important;
}
::placeholder { color: #94a3b8 !important; opacity: 1 !important; font-weight: 600 !important; }

/* --- ラジオボタンのタイル化 (ライン・製品選択等) --- */
div[data-testid="stRadio"] > div { display: flex; flex-wrap: wrap; gap: 10px !important; }
div[data-testid="stRadio"] label {
    background-color: #f8fafc; padding: 14px 16px !important; border-radius: 10px;
    border: 2px solid var(--c-input-border) !important; font-weight: 800 !important; cursor: pointer;
    text-align: center; flex: 1 1 auto; justify-content: center; min-width: 120px;
    transition: all 0.2s ease; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
div[data-testid="stRadio"] label p { font-size: 1.1rem !important; font-weight: 900 !important; color: var(--c-secondary) !important; }
div[data-testid="stRadio"] label[data-baseweb="radio"] input:checked + div {
    background-color: var(--c-primary) !important; border-color: var(--c-primary) !important; 
    box-shadow: 0 6px 12px rgba(234, 88, 12, 0.3); transform: translateY(-2px);
}
div[data-testid="stRadio"] label[data-baseweb="radio"] input:checked + div p { color: #ffffff !important; }

/* --- ボタン群 --- */
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

/* 🚨🚨 サイドバーの視認性完全修正 (純白文字を強制) 🚨🚨 */
[data-testid="stSidebar"] { background-color: var(--c-secondary) !important; padding-top: 1rem; }
[data-testid="stSidebar"], [data-testid="stSidebar"] div, [data-testid="stSidebar"] span { color: #ffffff !important; }
[data-testid="stSidebar"] div[role="radiogroup"] label {
    background: rgba(255,255,255,0.08) !important; border: 1px solid rgba(255,255,255,0.15) !important;
    padding: 12px 16px !important; border-radius: 8px !important; margin-bottom: 8px !important;
    cursor: pointer; transition: all 0.2s ease;
}
[data-testid="stSidebar"] div[role="radiogroup"] label p { 
    font-size: 1.1rem !important; font-weight: 900 !important; color: #ffffff !important; 
}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
    background: var(--c-primary) !important; border-color: var(--c-primary-hover) !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}
/* 更新ボタン */
[data-testid="stSidebar"] .stButton button {
    background: #f8fafc !important; border: none !important; margin-top: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important;
}
[data-testid="stSidebar"] .stButton button p { color: #0f172a !important; font-weight: 900 !important; }

/* ラベルの文字サイズ */
label p { font-size: 1.05rem !important; font-weight: 800 !important; margin-bottom: 4px !important; color: #1e293b !important;}
[data-testid="column"] { padding: 0 4px !important; }
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

# --- 在庫計算 (ブレンドバグ修正済み) ---
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
                    # ブレンド時の(40%)表記を消去して純粋なロット名でマッチング
                    valid_lots = [l for l in [re.sub(r'\(.*?\)', '', l_raw).strip() for l_raw in t_lot.split(",")] if l and l != "─"]
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
#  🏭 製造仕込み
# ═══════════════════════════════════════════════════════════════
if page == "🏭 製造仕込み":
    st.markdown('<div class="main-header"><h1>🏭 製造仕込み記録</h1><p>製品を選び、仕込量を入力すると必要原料を自動計算します。ブレンドも可能です。</p></div>', unsafe_allow_html=True)

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
        with c_op1: operator = st.selectbox("👨‍🏭 製造担当者", inspectors if inspectors else ["未登録"])
        with c_op2: brew_remarks = st.text_input("📝 備考（任意）", placeholder="特記事項（例: 通常より多め）")
        st.markdown('</div>', unsafe_allow_html=True)

        if target_size is None or lime_water_size is None:
            st.info("💡 仕込量と石灰水量を入力すると、下に準備リストが表示されます。")
        else:
            st.markdown('<div class="section-title" style="margin-top:32px;">📦 準備する原料・ロット選択</div>', unsafe_allow_html=True)
            
            submitted_ingredients = []
            is_summer = 6 <= date.today().month <= 9
            recent_arrivals = sorted(arrivals, key=lambda x: x.get("入荷日", ""), reverse=True)
            def _recent_lot_options(mat_name):
                opts, seen = [], set()
                for a in recent_arrivals:
                    if str(a.get("原料種別", "")).strip() != mat_name: continue
                    l_no = str(a.get("ロットNo", "")).strip()
                    if not l_no or l_no in seen: continue
                    seen.add(l_no); opts.append(l_no)
                    if len(opts) >= 15: break
                return opts

            for i, item in enumerate(active_recipe[:10]):
                r_name = str(item.get("原料名", "")).strip()
                base_ratio = float(item.get("比率", 0.0))
                is_water, is_lime, is_konjac = ("水" in r_name or "お湯" in r_name), ("石灰" in r_name or "カルシウム" in r_name), ("こんにゃく" in r_name)
                icon = "💧" if is_water else ("🧂" if is_lime else ("📦" if is_konjac else "🔹"))

                if is_water: calc_kg = max(0.0, target_size * (base_ratio / 100.0) - lime_water_size)
                elif is_lime: calc_kg = lime_water_size * ((base_ratio + 0.01 if is_summer else base_ratio) / 10.0)
                else: calc_kg = target_size * (base_ratio / 100.0)

                with st.container(border=True):
                    st.markdown(f"<div style='font-size:1.2rem; font-weight:900;'>{icon} {r_name}</div>", unsafe_allow_html=True)
                    
                    if is_water:
                        st.markdown(f"<div style='color:#3b82f6; font-weight:bold; font-size:1.1rem; margin-top:8px;'>必要量: {fmt_kg(calc_kg)} kg (石灰水除く)</div>", unsafe_allow_html=True)
                        submitted_ingredients.append({"原料名": r_name, "kg": round(calc_kg, 2), "lot": "─"})
                    
                    elif is_konjac:
                        with lot_popover("📦 ロット選択 / 🧪 ブレンド設定"):
                            blend_key = f"kb_{selected_p}_{i}"
                            blend_on = st.checkbox("🧪 2種類のこんにゃく粉をブレンドする", key=blend_key)
                            konjac_mats = [m for m in materials if "こんにゃく" in m] or [r_name]
                            
                            if blend_on:
                                act_total = st.number_input("合計投入量(kg)", value=round(calc_kg, 2), step=0.1, key=f"ktot_{selected_p}_{i}")
                                ratio_key = f"kr_{selected_p}_{i}"
                                if ratio_key not in st.session_state: st.session_state[ratio_key] = 50
                                
                                st.caption("👆 手袋でも押しやすい A(%) の比率選択ボタン")
                                btn_cols = st.columns(7)
                                for pidx, pv in enumerate([20, 30, 40, 50, 60, 70, 80]):
                                    is_sel = (st.session_state[ratio_key] == pv)
                                    btn_cols[pidx].button(f"{pv}%", key=f"{ratio_key}_{pv}", use_container_width=True, type="primary" if is_sel else "secondary", on_click=lambda v=pv, k=ratio_key: st.session_state.update({k: v}))
                                
                                ratio_a = st.number_input("こんにゃく粉A 配合比率(%) 微調整", min_value=0, max_value=100, step=1, key=ratio_key)
                                ratio_b, kg_a = 100 - ratio_a, round(act_total * ratio_a / 100.0, 2)
                                kg_b = round(act_total - kg_a, 2)

                                st.markdown("---")
                                st.markdown(f"**🅰️ こんにゃく粉A（{ratio_a}%・{fmt_kg(kg_a)}kg）**")
                                mat_a = st.selectbox("原料(A)", konjac_mats, key=f"kma_{selected_p}_{i}")
                                sel_a = st.radio("ロット(A)", ["未選択"] + _recent_lot_options(mat_a) + ["手入力"], key=f"kla_{selected_p}_{i}", label_visibility="collapsed")
                                lot_a = st.text_input("手入力(A)", placeholder="ロット番号を入力", key=f"mla_{selected_p}_{i}") if sel_a == "手入力" else (sel_a if sel_a != "未選択" else "─")
                                
                                st.markdown(f"**🅱️ こんにゃく粉B（{ratio_b}%・{fmt_kg(kg_b)}kg）**")
                                mat_b = st.selectbox("原料(B)", konjac_mats, index=1 if len(konjac_mats)>1 else 0, key=f"kmb_{selected_p}_{i}")
                                sel_b = st.radio("ロット(B)", ["未選択"] + _recent_lot_options(mat_b) + ["手入力"], key=f"klb_{selected_p}_{i}", label_visibility="collapsed")
                                lot_b = st.text_input("手入力(B)", placeholder="ロット番号を入力", key=f"mlb_{selected_p}_{i}") if sel_b == "手入力" else (sel_b if sel_b != "未選択" else "─")

                                submitted_ingredients.append({"原料名": mat_a, "kg": kg_a, "lot": f"{lot_a}({ratio_a}%)"})
                                submitted_ingredients.append({"原料名": mat_b, "kg": kg_b, "lot": f"{lot_b}({ratio_b}%)"})
                            else:
                                act_kg = st.number_input("投入量(kg)", value=round(calc_kg, 2), step=0.1, key=f"kamt_{selected_p}_{i}")
                                sel_lot = st.radio("ロット選択", ["未選択"] + _recent_lot_options(r_name) + ["手入力"], key=f"klot_{selected_p}_{i}", label_visibility="collapsed")
                                final_lot = st.text_input("手入力", placeholder="ロット番号を入力", key=f"kman_{selected_p}_{i}") if sel_lot == "手入力" else (sel_lot if sel_lot != "未選択" else "─")
                                submitted_ingredients.append({"原料名": r_name, "kg": act_kg, "lot": final_lot})
                                
                        if blend_on: st.markdown(f"<div style='margin-top:10px; font-weight:900; font-size:1.1rem; color:#ea580c;'>🧪 ブレンド: A {fmt_kg(kg_a)}kg / B {fmt_kg(kg_b)}kg</div>", unsafe_allow_html=True)
                        else: st.markdown(f"<div style='margin-top:10px; font-weight:900; font-size:1.1rem; color:#ea580c;'>投入量: {fmt_kg(act_kg)} kg ｜ ロット: {final_lot}</div>", unsafe_allow_html=True)
                    
                    else:
                        with lot_popover("📦 投入量・ロット入力"):
                            act_kg = st.number_input("投入量(kg)", value=round(calc_kg, 2), step=0.1, key=f"amt_{selected_p}_{i}")
                            sel_lot = st.radio("ロット選択", ["未選択"] + _recent_lot_options(r_name) + ["手入力"], key=f"lot_{selected_p}_{i}", label_visibility="collapsed")
                            final_lot = st.text_input("手入力", placeholder="ロット番号を入力", key=f"man_{selected_p}_{i}") if sel_lot == "手入力" else (sel_lot if sel_lot != "未選択" else "─")
                        
                        st.markdown(f"<div style='margin-top:10px; font-weight:900; font-size:1.1rem; color:#ea580c;'>投入量: {fmt_kg(act_kg)} kg ｜ ロット: {final_lot}</div>", unsafe_allow_html=True)
                        submitted_ingredients.append({"原料名": r_name, "kg": round(act_kg, 2), "lot": final_lot})

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
                st.session_state["t_size"] = None
                st.session_state["l_size"] = None
                st.balloons()
                st.success(f"✅ 【{selected_p}】の製造記録を保存しました！画面を更新します...")
                time.sleep(2.0)
                refresh()

# ═══════════════════════════════════════════════════════════════
#  📊 ダッシュボード
# ═══════════════════════════════════════════════════════════════
elif page == "📊 ダッシュボード":
    st.markdown('<div class="main-header"><h1>📊 サマリーと在庫モニター</h1></div>', unsafe_allow_html=True)
    
    alert_count = sum(1 for m in materials if order_points.get(m, 0.0) > 0 and type_totals_bag.get(m, 0.0) < order_points.get(m, 0.0))
    st.metric("⚠️ 在庫不足原料", f"{alert_count} 品目")

    st.markdown('<div class="section-title">📦 主要原料 現在庫</div>', unsafe_allow_html=True)
    cols = st.columns(min(3, len(materials) if materials else 1))
    for idx, m in enumerate(materials):
        curr_kg = type_totals_kg.get(m, 0.0)
        curr_bag = type_totals_bag.get(m, 0.0)
        pt = order_points.get(m, 0.0)
        is_alert = (pt > 0 and curr_bag < pt)
        with cols[idx % 3]:
            with st.container(border=True):
                st.markdown(f"**{m}**")
                st.metric("現在庫", f"{fmt_kg(curr_kg)} kg", f"発注点: {fmt_kg(pt)}袋", delta_color="inverse" if is_alert else "normal")

# ═══════════════════════════════════════════════════════════════
#  📥 入荷登録
# ═══════════════════════════════════════════════════════════════
elif page == "📥 入荷登録":
    st.markdown('<div class="main-header"><h1>📥 原料入荷品質記録</h1><p>入荷時のロット情報と重量を正確に記録します。</p></div>', unsafe_allow_html=True)
    
    with st.form("arrival_form"):
        st.markdown('<div class="section-title">📦 基本入荷情報</div>', unsafe_allow_html=True)
        new_no = sheets.next_arrival_no(arrivals)
        
        arr_date = st.date_input("入荷日", value=date.today())
        maker_sel = st.selectbox("メーカー", makers if makers else ["未登録"])
        lot_val = st.text_input("ロットNo ＊必須", placeholder="例: L12345 (バーコードリーダー可)")
        
        c1, c2 = st.columns(2)
        m_type = c1.selectbox("原料種別", materials if materials else ["未登録"])
        bags_qty = c2.number_input("入荷袋数", min_value=1.0, value=10.0, step=1.0)
        weight_per_bag = st.number_input("1袋重量 (kg)", min_value=1.0, value=20.0, step=1.0)
        st.info(f"💡 合計入荷重量: **{fmt_kg(bags_qty * weight_per_bag)} kg**")
        
        st.markdown('<div class="section-title" style="margin-top:20px;">🔍 受入品質検査</div>', unsafe_allow_html=True)
        chk_app = st.selectbox("外観・規格・賞味期限・異物 総合評価", ["OK（すべて正常）", "NG（異常あり）"])
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("💾 入荷記録を登録する", type="primary"):
            if not lot_val: st.error("ロットNoは必須項目です。")
            else:
                sheets.append_arrival({
                    "入荷No": new_no, "入荷日": str(arr_date), "メーカー": maker_sel, "ロットNo": lot_val,
                    "原料種別": m_type, "袋数": bags_qty, "1袋重量(kg)": weight_per_bag, "総量(kg)": bags_qty * weight_per_bag,
                    "外観": chk_app, "品名・規格確認": chk_app, "賞味期限": chk_app, "異物": chk_app,
                    "担当者": "現場", "備考": "", "登録日時": datetime.now().isoformat()
                })
                st.success("入荷記録を保存しました。")
                time.sleep(1.5)
                refresh()

# ═══════════════════════════════════════════════════════════════
#  🧹 資材管理
# ═══════════════════════════════════════════════════════════════
elif page == "🧹 資材管理":
    st.markdown('<div class="main-header"><h1>🧹 資材・消耗品管理</h1><p>カード内の「🔄 入出庫」から直接操作できます。</p></div>', unsafe_allow_html=True)
    if not supplies: st.warning("資材が未登録です。マスタ設定よりご登録ください。")
    else:
        supply_inventory = {}
        for s in supplies: supply_inventory[s.get("資材ID")] = float(s.get("初期在庫") or 0.0)
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
                        if st.button("💾 保存", key=f"btn_{sid}", type="primary", use_container_width=True):
                            sheets.append_supply_log({
                                "ログID": f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                                "登録日": str(date.today()), "資材ID": sid,
                                "処理": "使用" if "使用" in action else "入荷", "数量": qty,
                                "作業者": "現場", "備考": "", "登録日時": datetime.now().isoformat()
                            })
                            st.success("記録しました")
                            time.sleep(1.0)
                            refresh()

# ═══════════════════════════════════════════════════════════════
#  ⚙️ マスタ設定
# ═══════════════════════════════════════════════════════════════
elif page == "⚙️ マスタ設定":
    st.markdown('<div class="main-header"><h1>⚙️ マスターデータ管理</h1></div>', unsafe_allow_html=True)
    t1, t2, t3, t4, t5 = st.tabs(["⚗️ 原料", "🏢 担当者", "🚨 発注点", "🧪 レシピ", "📦 資材"])
    
    with t1:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        df_m = pd.DataFrame({"原料名": materials})
        ed_m = st.data_editor(df_m, num_rows="dynamic", use_container_width=True)
        if st.button("💾 原料マスタ保存", type="primary"):
            sheets.save_materials([str(x).strip() for x in ed_m["原料名"].tolist() if str(x).strip()])
            st.success("保存しました。")
            time.sleep(1)
            refresh()
        st.markdown('</div>', unsafe_allow_html=True)
            
    with t2:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        df_u = pd.DataFrame({"担当者名": inspectors})
        ed_u = st.data_editor(df_u, num_rows="dynamic", use_container_width=True)
        if st.button("💾 担当者保存", type="primary"):
            sheets.save_inspectors([str(x).strip() for x in ed_u["担当者名"].tolist() if str(x).strip()])
            st.success("保存しました。")
            time.sleep(1)
            refresh()
        st.markdown('</div>', unsafe_allow_html=True)

    with t3:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        op_rows = [{"原料名": m, "発注点(袋)": float(order_points.get(m, 0.0))} for m in materials]
        edited_op = st.data_editor(pd.DataFrame(op_rows), use_container_width=True)
        if st.button("💾 発注点保存", type="primary"):
            new_op_dict = {str(r["原料名"]).strip(): float(r["発注点(袋)"] or 0.0) for _, r in edited_op.iterrows() if str(r["原料名"]).strip()}
            sheets.save_order_points(new_op_dict)
            st.success("保存しました。")
            time.sleep(1)
            refresh()
        st.markdown('</div>', unsafe_allow_html=True)

    with t4:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        st.write("🧪 **配合レシピの新規登録・編集**")
        edit_mode = st.radio("操作を選択", ["新規作成", "既存レシピの編集"], horizontal=True)
        target_recipe = None
        old_json = "[]"
        if edit_mode == "既存レシピの編集":
            if recipes_raw:
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
                mat_idx = def_mats.index(def_mat_val) if def_mat_val in def_mats else 0
                
                uid = f"{init_name}_{j}" if target_recipe else f"new_{j}"
                ing_mat = c_n.selectbox(f"成分 {j+1}", def_mats, index=mat_idx, key=f"rmat_{uid}")
                ing_ratio = c_w.number_input("比率(％)", min_value=0.00, value=def_rat_val, step=0.01, key=f"rrat_{uid}")
                cols_recipe.append({"name": ing_mat, "ratio": ing_ratio})
            
            if st.form_submit_button("💾 レシピを保存"):
                valid_items = [{"原料名": i["name"], "比率": float(i["ratio"])} for i in cols_recipe if i["name"] != "(未設定)" and i["ratio"] > 0]
                cat_str = "プラント" if "プラント" in cat_main else "OKM"
                sub_str = cat_sub.split(" ")[1] if cat_str == "プラント" else "その他"
                
                new_recipe_entry = {"品名": new_p_name, "大カテゴリ": cat_str, "中カテゴリ": sub_str, "配合JSON": json.dumps(valid_items, ensure_ascii=False)}
                updated_recipes = [r for r in recipes_raw if r["品名"] != new_p_name]
                updated_recipes.append(new_recipe_entry)
                
                sheets.save_recipes(updated_recipes)
                st.success("レシピを保存しました。")
                time.sleep(1)
                refresh()
        st.markdown('</div>', unsafe_allow_html=True)

    with t5:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        st.write("➕ **新規資材の登録**")
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
                    cur_sup.append({
                        "資材ID": f"SUP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "資材名": new_s_name, "カテゴリ": new_s_cat, "画像URL": img_str,
                        "初期在庫": 0, "発注点": 10, "登録日": str(date.today())
                    })
                    sheets.save_supplies(cur_sup)
                    st.success("資材を登録しました。")
                    time.sleep(1)
                    refresh()
        st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
#  その他のタブ
# ═══════════════════════════════════════════════════════════════
else:
    st.markdown(f'<div class="main-header"><h1>{page}</h1></div>', unsafe_allow_html=True)
    if page == "📋 履歴・帳票":
        if brewing:
            df_b = pd.DataFrame(brewing)[::-1]
            st.dataframe(df_b[["仕込日", "品名", "仕込量(kg)", "主原料ロット", "備考"]].head(50), use_container_width=True, hide_index=True)
    elif page == "📦 在庫・棚卸":
        st.markdown('<div class="section-title">⚖️ 棚卸し (在庫調整)</div>', unsafe_allow_html=True)
        if inventory_data:
            tgt_list = {f"{v['原料種別']} (ロット:{v['ロットNo']})": v["入荷No"] for v in inventory_data.values()}
            selected_tgt = st.selectbox("調整対象", list(tgt_list.keys()))
            diff_bags = st.number_input("理論在庫との差分（袋数） ※増やす場合はプラス、減らす場合はマイナス", value=0.0, step=1.0)
            reason_txt = st.text_input("調整理由")
            if st.button("💾 在庫を調整する", type="primary"):
                sheets.append_adjustment({
                    "調整ID": f"ADJ-{datetime.now().strftime('%Y%m%d%H%M%S')}", "入荷No": tgt_list[selected_tgt],
                    "調整日": str(date.today()), "調整袋数": diff_bags, "理由": reason_txt, "担当者": "担当者", 
                    "登録日時": datetime.now().isoformat()
                })
                st.success("調整を保存しました。")
                time.sleep(1.5)
                refresh()
        st.markdown('<div class="section-title">📋 現在庫一覧</div>', unsafe_allow_html=True)
        active_inv = [v for v in inventory_data.values() if v["現在庫(袋)"] > 0.0]
        if active_inv:
            st.dataframe(pd.DataFrame(active_inv)[["原料種別", "ロットNo", "入荷袋数", "使用袋数", "調整袋数", "現在庫(袋)"]], use_container_width=True, hide_index=True)
    elif page == "🔍 トレース":
        lot_list = sorted(list(set([str(a.get("ロットNo", "")).strip() for a in arrivals if a.get("ロットNo")])), reverse=True)
        tgt_lot = st.selectbox("検索する原料ロット", lot_list if lot_list else ["なし"])
        if st.button("➡️ このロットを使った製品を追跡", type="primary"):
            match_brw = [b for b in brewing if tgt_lot in b.get("その他添加物", "")]
            if match_brw:
                st.dataframe(pd.DataFrame(match_brw)[["仕込日", "品名", "仕込量(kg)"]], use_container_width=True, hide_index=True)
            else:
                st.warning("履歴がありません。")
