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
#  シンプルで使いやすい・モバイル特化UI/UX CSS
# ════════════════════════════════════════════════════════════════
st.markdown("""
<style>
:root {
    --c-bg: #f4f6f8;
    --c-surface: #ffffff;
    --c-primary: #ea580c;
    --c-primary-hover: #c2410c;
    --c-secondary: #1e293b;
    --c-border: #cbd5e1;
    --c-text: #334155;
}
.stApp { background-color: var(--c-bg); color: var(--c-text); font-family: 'Helvetica Neue', Arial, sans-serif; }

/* サイドバー */
[data-testid="stSidebar"] { background-color: var(--c-secondary) !important; padding-top: 1rem; }
[data-testid="stSidebar"] * { color: #ffffff !important; }
[data-testid="stSidebar"] div[role="radiogroup"] label {
    padding: 10px 14px !important;
    border-radius: 8px !important;
    margin-bottom: 8px !important;
    background: rgba(255,255,255,0.05) !important;
    cursor: pointer;
    font-weight: 700 !important;
    transition: all 0.2s;
}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
    background: var(--c-primary) !important;
    box-shadow: 0 4px 6px rgba(0,0,0,0.2);
}

/* ヘッダー */
.main-header {
    background: var(--c-surface);
    padding: 16px 24px;
    border-radius: 12px;
    margin-bottom: 20px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    border-left: 6px solid var(--c-primary);
}
.main-header h1 { color: var(--c-secondary) !important; font-size: 1.5rem !important; margin: 0 0 4px 0 !important; font-weight: 800 !important; }
.main-header p { color: #64748b !important; font-size: 0.95rem !important; margin: 0 !important; }

/* ラジオボタンのタイル化 (ライン・製品選択等) */
div[data-testid="stRadio"] > div { display: flex; flex-wrap: wrap; gap: 8px !important; }
div[data-testid="stRadio"] label {
    background-color: #f1f5f9; padding: 12px 16px !important; border-radius: 10px;
    border: 1px solid var(--c-border); font-weight: 700 !important; cursor: pointer;
    text-align: center; flex: 1 1 auto; justify-content: center;
}
div[data-testid="stRadio"] label[data-baseweb="radio"] input:checked + div {
    background-color: var(--c-primary) !important; color: white !important;
    border-color: var(--c-primary) !important; box-shadow: 0 4px 8px rgba(234, 88, 12, 0.2);
}

/* 数値入力フィールドと＋/－ボタンのモバイル特化 (タップ領域特大化) */
div[data-baseweb="input"] { border-radius: 8px !important; min-height: 48px !important; }
div[data-baseweb="input"] input { font-size: 1.1rem !important; font-weight: bold !important; text-align: center !important; }
button[data-testid="stNumberInputStepUp"], button[data-testid="stNumberInputStepDown"] {
    min-width: 54px !important; min-height: 54px !important; border-radius: 8px !important;
    background-color: #e2e8f0 !important; margin: 0 2px;
}

/* ボタン */
.stButton button {
    border-radius: 8px !important; font-weight: 700 !important; padding: 10px 16px !important; min-height: 48px !important;
}
.stButton button[kind="primary"] {
    background: var(--c-primary) !important; color: white !important; border: none !important;
}

/* カードデザイン */
.form-card { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
.section-title { font-size: 1.2rem; font-weight: 800; color: var(--c-secondary); margin-bottom: 16px; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
#  ユーティリティ関数
# ════════════════════════════════════════════════════════════════
def lot_popover(label):
    if hasattr(st, "popover"):
        return st.popover(label, use_container_width=True)
    else:
        return st.expander(label)

def refresh():
    st.cache_data.clear()
    st.rerun()

@st.cache_data(ttl=60)
def load_all_datasets():
    import sheets
    return {
        "arrivals": sheets.load_arrivals(),
        "brewing": sheets.load_brewing(),
        "adjustments": sheets.load_adjustments(),
        "supplies": sheets.load_supplies(),
        "supply_logs": sheets.load_supply_logs(),
        "materials": sheets.load_materials(),
        "makers": sheets.load_makers(),
        "inspectors": sheets.load_inspectors(),
        "order_points": sheets.load_order_points(),
        "recipes": sheets.load_recipes(),
        "recipe_logs": sheets.load_recipe_logs()
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

def is_corrupted_name(name):
    name = str(name).strip()
    return len(name) > 30 or name.startswith("[") or name.startswith("{") if name else False

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
    cleaned = []
    for item in data:
        if not isinstance(item, dict): continue
        name = str(item.get("原料名", "")).strip()
        if not name or is_corrupted_name(name): continue
        try: cleaned.append({"原料名": name, "比率": float(item.get("比率", 0.0))})
        except: continue
    return cleaned

# ════════════════════════════════════════════════════════════════
#  現在庫算出ロジック
# ════════════════════════════════════════════════════════════════
def get_inventory():
    inv = {}
    for a in arrivals:
        ano = str(a.get("入荷No", "")).strip()
        if not ano: continue
        inv[ano] = {
            "入荷No": ano, "ロットNo": str(a.get("ロットNo", "")).strip(), 
            "メーカー": str(a.get("メーカー", "")).strip(), "原料種別": str(a.get("原料種別", "")).strip(), 
            "1袋重量": float(a.get("1袋重量(kg)") or 20.0), "入荷袋数": float(a.get("袋数") or 0.0), 
            "使用量(kg)": 0.0, "調整袋数": 0.0
        }
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
        inv[sid] = {
            "資材ID": sid, "初期在庫": float(s.get("初期在庫") or 0.0), "入庫累計": 0.0, "出庫累計": 0.0
        }
    for log in supply_logs:
        sid = str(log.get("資材ID", "")).strip()
        if sid not in inv: continue
        qty = float(log.get("数量") or 0.0)
        if log.get("処理") == "入荷": inv[sid]["入庫累計"] += qty
        elif log.get("処理") == "使用": inv[sid]["出庫累計"] += qty
    for v in inv.values():
        v["現在庫"] = v["初期在庫"] + v["入庫累計"] - v["出庫累計"]
    return inv

supply_inventory = get_supply_inventory()

def get_material_usage_history():
    usage_by_material = {}
    usage_events = []
    for b in brewing:
        oa = b.get("その他添加物", "")
        if not oa: continue
        b_date = str(b.get("仕込日", "")).strip()
        p_name = str(b.get("品名", "")).strip()
        try: items = json.loads(oa)
        except: continue
        for item in items:
            m_name = str(item.get("原料名", "")).strip()
            kg = float(item.get("kg", 0.0) or 0.0)
            if not m_name or kg <= 0: continue
            usage_by_material.setdefault(m_name, []).append({"日付": b_date, "kg": kg})
            usage_events.append({"日付": b_date, "原料名": m_name, "使用量(kg)": round(kg, 2), "品名": p_name, "ロット": item.get("lot", "")})
    return usage_by_material, usage_events

material_usage_by_name, material_usage_events = get_material_usage_history()

# サマリーデータ
df_brw_global = pd.DataFrame(brewing)
if not df_brw_global.empty:
    df_brw_global["仕込日_dt"] = pd.to_datetime(df_brw_global["仕込日"], errors="coerce")
    df_brw_global["month"] = df_brw_global["仕込日_dt"].dt.to_period("M").astype(str)
    df_brw_global["date_str"] = df_brw_global["仕込日_dt"].dt.strftime("%Y-%m-%d")
    df_brw_today = df_brw_global[df_brw_global["date_str"] == date.today().strftime("%Y-%m-%d")]
    today_total_kg = pd.to_numeric(df_brw_today["仕込量(kg)"], errors="coerce").fillna(0).sum()
    today_count = len(df_brw_today)
else:
    today_total_kg = today_count = 0

# ════════════════════════════════════════════════════════════════
#  サイドバー
# ════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div style="font-size:1.3rem; font-weight:800; margin-bottom:1rem; color:white;">🏭 製造ERP</div>', unsafe_allow_html=True)
    page = st.radio("メニュー", [
        "📊 ダッシュボード", 
        "🏭 製造仕込み", 
        "📥 入荷登録", 
        "📦 在庫・棚卸", 
        "🧹 資材管理", 
        "🔍 トレース", 
        "📋 履歴・帳票",
        "📈 分析",
        "⚙️ マスタ設定"
    ], label_visibility="collapsed")
    st.markdown("---")
    if st.button("🔄 最新データに更新", use_container_width=True): refresh()

# ════════════════════════════════════════════════════════════════
#  1. ダッシュボード
# ════════════════════════════════════════════════════════════════
if page == "📊 ダッシュボード":
    st.markdown('<div class="main-header"><h1>📊 サマリーと在庫モニター</h1><p>現場の稼働状況と原料の在庫アラートを即座に確認できます。</p></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📦 本日の総製造量", f"{fmt_kg(today_total_kg)} kg", f"{today_count} 件製造")
    with col2:
        alert_count = sum(1 for m in materials if order_points.get(m, 0.0) > 0 and type_totals.get(m, 0.0) < order_points.get(m, 0.0))
        st.metric("⚠️ 在庫不足原料", f"{alert_count} 品目")

    st.markdown("---")
    st.markdown('<div class="section-title">📦 主要原料 在庫モニター</div>', unsafe_allow_html=True)
    
    if alert_count > 0:
        st.error("🚨 以下の原料が発注点を下回っています。至急確認してください。")
    
    # スマホでも崩れないようにカラム数を調整
    cols = st.columns(min(3, len(materials) if materials else 1))
    for idx, m in enumerate(materials):
        curr = type_totals.get(m, 0.0)
        pt = order_points.get(m, 0.0)
        is_alert = (pt > 0 and curr < pt)
        with cols[idx % 3]:
            with st.container(border=True):
                st.markdown(f"**{m}**")
                st.metric("現在庫", f"{fmt_kg(curr)} 袋", f"発注点: {fmt_kg(pt)}", delta_color="inverse" if is_alert else "normal")
                if is_alert:
                    st.markdown('<span style="background-color:#fee2e2;color:#ef4444;padding:4px 8px;border-radius:4px;font-weight:bold;font-size:0.8rem;">⚠ 不足</span>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
#  2. 製造仕込み (モバイル特化・シンプル化)
# ═══════════════════════════════════════════════════════════════
elif page == "🏭 製造仕込み":
    st.markdown('<div class="main-header"><h1>🏭 製造仕込み記録</h1><p>製品を選び、仕込量を入力するだけで必要原料を自動計算します。</p></div>', unsafe_allow_html=True)

    # 上から下へ自然な流れで入力させる
    st.markdown('<div class="form-card">', unsafe_allow_html=True)
    
    brew_date = st.date_input("📅 仕込日", value=date.today())
    
    p_recipes = {}
    for r in recipes_raw:
        p_name = r.get("品名", "未定義")
        p_recipes[p_name] = {
            "大カテゴリ": r.get("大カテゴリ", "その他"),
            "中カテゴリ": r.get("中カテゴリ", "その他"),
            "成分": safe_parse_recipe(r.get("配合JSON"))
        }

    big_cats = sorted({v["大カテゴリ"] for v in p_recipes.values() if v.get("大カテゴリ")})
    big_cat = st.radio("① ライン", big_cats, horizontal=True) if big_cats else None

    sub_cats = sorted({v["中カテゴリ"] for v in p_recipes.values() if v.get("大カテゴリ") == big_cat and v.get("中カテゴリ")}) if big_cat else []
    sub_str = st.radio("② 種別", sub_cats, horizontal=True) if len(sub_cats) > 1 else (sub_cats[0] if sub_cats else None)

    filtered_opts = [k for k, v in p_recipes.items() if v.get("大カテゴリ") == big_cat and v.get("中カテゴリ") == sub_str] if big_cat and sub_str else []
    
    selected_p = st.radio("③ 製品", filtered_opts, horizontal=True) if filtered_opts else None
    active_recipe = p_recipes.get(selected_p, {}).get("成分", []) if selected_p else []

    st.markdown('</div>', unsafe_allow_html=True)

    if not active_recipe:
        st.info("👆 製品を選択してください。")
    else:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">④ 仕込量と石灰水量の入力</div>', unsafe_allow_html=True)
        
        # モバイルでも押しやすいように標準の step を調整するのみ。余計な加算ボタンは廃止。
        c1, c2 = st.columns(2)
        with c1:
            target_size = st.number_input("🏭 希望仕込製品量 (kg)", min_value=1.0, value=100.0, step=10.0, format="%.0f")
        with c2:
            lime_water_size = st.number_input("💧 石灰水作成量 (kg)", min_value=0.0, value=10.0, step=1.0, format="%.0f")
        
        operator = st.selectbox("👨‍🏭 製造担当者", inspectors if inspectors else ["未登録"])
        brew_remarks = st.text_input("📝 備考（任意）", placeholder="特記事項があれば入力")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-title">📦 必要原料リストとロット選択</div>', unsafe_allow_html=True)
        
        submitted_ingredients = []
        is_summer = 6 <= date.today().month <= 9
        recent_arrivals = sorted(arrivals, key=lambda x: x.get("入荷日", ""), reverse=True)

        def _recent_lot_options(mat_name):
            opts = []
            seen = set()
            for a in recent_arrivals:
                if str(a.get("原料種別", "")).strip() != mat_name: continue
                l_no = str(a.get("ロットNo", "")).strip()
                if not l_no or l_no in seen: continue
                seen.add(l_no)
                opts.append(l_no)
                if len(opts) >= 15: break
            return opts

        for i, item in enumerate(active_recipe[:10]):
            r_name = str(item.get("原料名", "")).strip()
            base_ratio = float(item.get("比率", 0.0))
            is_water = ("水" == r_name or "お湯" in r_name)
            is_lime = ("石灰" in r_name or "カルシウム" in r_name)

            if is_water:
                calc_kg = max(0.0, target_size * (base_ratio / 100.0) - lime_water_size)
            elif is_lime:
                effective_ratio = base_ratio + 0.01 if is_summer else base_ratio
                calc_kg = lime_water_size * (effective_ratio / 10.0)
            else:
                calc_kg = target_size * (base_ratio / 100.0)

            with st.container(border=True):
                st.markdown(f"<div style='font-weight:bold;font-size:1.1rem;color:#1e293b;'>{r_name}</div>", unsafe_allow_html=True)
                
                if is_water:
                    st.markdown(f"<div style='color:#3b82f6;'>必要量: {fmt_kg(calc_kg)} kg (石灰水除く)</div>", unsafe_allow_html=True)
                    submitted_ingredients.append({"原料名": r_name, "kg": round(calc_kg, 2), "lot": "─"})
                else:
                    c_amt, c_lot = st.columns([1, 1])
                    with c_amt:
                        act_kg = st.number_input("投入量(kg)", value=round(calc_kg, 2), step=0.1, key=f"amt_{i}")
                    with c_lot:
                        # モバイルでキーボードが出ないようにポップオーバー内でタップ選択
                        with lot_popover(f"📦 ロット選択"):
                            st.write("最新ロットをタップして選択")
                            lot_opts = _recent_lot_options(r_name)
                            sel_lot = st.radio("ロット選択", ["未選択"] + lot_opts + ["手入力"], key=f"r_lot_{i}", label_visibility="collapsed")
                            final_lot = "─"
                            if sel_lot == "手入力":
                                final_lot = st.text_input("ロット手入力", key=f"m_lot_{i}")
                            elif sel_lot != "未選択":
                                final_lot = sel_lot
                    
                    st.markdown(f"<div style='color:#15803d;font-weight:bold;margin-top:4px;'>選択ロット: {final_lot}</div>", unsafe_allow_html=True)
                    submitted_ingredients.append({"原料名": r_name, "kg": round(act_kg, 2), "lot": final_lot})

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 この内容で製造記録を保存する", type="primary", use_container_width=True):
            k_kg = s_kg = st_kg = lime_kg = 0.0
            k_lot = s_lot = st_lot = "─"
            for ing in submitted_ingredients:
                n, amt, lot = ing["原料名"], ing["kg"], ing["lot"]
                if "こんにゃく" in n:
                    k_kg += amt
                    k_lot = lot if k_lot == "─" else (k_lot if lot in k_lot else f"{k_lot} / {lot}")
                elif "海藻" in n:
                    s_kg += amt
                    s_lot = lot if s_lot == "─" else (s_lot if lot in s_lot else f"{s_lot} / {lot}")
                elif "デンプン" in n or "でんぷん" in n:
                    st_kg += amt
                    st_lot = lot if st_lot == "─" else (st_lot if lot in st_lot else f"{st_lot} / {lot}")
                elif "石灰" in n or "カルシウム" in n:
                    lime_kg += amt

            sheets.append_brewing({
                "仕込No": sheets.next_brewing_no(brewing), "仕込日": str(brew_date), "品名": selected_p,
                "メーカー": operator, "主原料ロット": k_lot, "仕込量(kg)": round(target_size, 2),
                "こんにゃく精粉(kg)": round(k_kg, 2), "海藻粉(kg)": round(s_kg, 2), "海藻粉ロット": s_lot,
                "デンプン(kg)": round(st_kg, 2), "デンプンロット": st_lot, "デンプン種別": "-",
                "石灰(kg)": round(lime_kg, 2), "石灰水(L)": round(lime_water_size, 2),
                "その他添加物": json.dumps(submitted_ingredients, ensure_ascii=False),
                "備考": f"{brew_remarks}", "登録日時": datetime.now().isoformat()
            })
            st.success("✅ 製造記録を保存しました！")
            time.sleep(1.5)
            refresh()

# ═══════════════════════════════════════════════════════════════
#  3. 入荷登録 (シンプル化)
# ═══════════════════════════════════════════════════════════════
elif page == "📥 入荷登録":
    st.markdown('<div class="main-header"><h1>📥 原料入荷品質記録</h1><p>現場での素早い入荷検品と情報登録を行います。</p></div>', unsafe_allow_html=True)
    
    with st.form("arrival_form"):
        st.markdown('<div class="section-title">🚛 入荷情報</div>', unsafe_allow_html=True)
        new_no = sheets.next_arrival_no(arrivals)
        arr_date = st.date_input("入荷日", value=date.today())
        maker_sel = st.selectbox("メーカー", makers if makers else ["未登録"])
        lot_val = st.text_input("ロットNo ＊必須")
        
        c1, c2 = st.columns(2)
        m_type = c1.selectbox("原料種別", materials if materials else ["未登録"])
        bags_qty = c2.number_input("入荷袋数", min_value=1, value=10, step=1)
        weight_per_bag = st.number_input("1袋重量 (kg)", min_value=1.0, value=20.0, step=1.0)
        
        st.markdown('<div class="section-title">🔍 受入品質検査</div>', unsafe_allow_html=True)
        chk_app = st.selectbox("外観・規格・賞味期限・異物 総合評価", ["OK（すべて正常）", "NG（異常あり）"])
        inspector_val = st.selectbox("受入検査担当者", inspectors if inspectors else ["未登録"])
        remarks_val = st.text_input("備考 / NG詳細")
        
        if st.form_submit_button("💾 入荷記録を登録する", type="primary"):
            if not lot_val:
                st.error("ロットNoは必須項目です。")
            else:
                sheets.append_arrival({
                    "入荷No": new_no, "入荷日": str(arr_date), "メーカー": maker_sel, "ロットNo": lot_val,
                    "原料種別": m_type, "袋数": bags_qty, "1袋重量(kg)": weight_per_bag, "総量(kg)": bags_qty * weight_per_bag,
                    "外観": chk_app, "品名・規格確認": chk_app, "賞味期限": chk_app, "異物": chk_app,
                    "担当者": inspector_val, "備考": remarks_val, "登録日時": datetime.now().isoformat()
                })
                st.success("入荷記録を保存しました。")
                time.sleep(1.5)
                refresh()

    with st.expander("📋 最近の入荷履歴を見る"):
        if arrivals:
            df_arr = pd.DataFrame(arrivals)[["入荷日", "原料種別", "ロットNo", "メーカー", "袋数"]]
            st.dataframe(df_arr[::-1].head(20), use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════
#  4. 在庫・棚卸
# ═══════════════════════════════════════════════════════════════
elif page == "📦 在庫・棚卸":
    st.markdown('<div class="main-header"><h1>📦 原料在庫・棚卸管理</h1><p>ロット別現在庫の確認と、実地棚卸しの調整を行います。</p></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-title">📋 ロット別現在庫一覧</div>', unsafe_allow_html=True)
    active_inv = [v for v in inventory_data.values() if v["現在庫(袋)"] > 0.0]
    if active_inv:
        df_curr_inv = pd.DataFrame(active_inv)[["原料種別", "ロットNo", "入荷袋数", "使用袋数", "調整袋数", "現在庫(袋)"]]
        st.dataframe(df_curr_inv, use_container_width=True, hide_index=True)
    else:
        st.info("在庫のある原料がありません。")

    with st.expander("⚖️ 棚卸による在庫調整を行う"):
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

# ═══════════════════════════════════════════════════════════════
#  5. 資材管理 (直感操作へ超効率化)
# ═══════════════════════════════════════════════════════════════
elif page == "🧹 資材管理":
    st.markdown('<div class="main-header"><h1>🧹 資材・消耗品管理</h1><p>資材の残量確認と入出庫を行います。カード内の「🔄 入出庫」ボタンから直接操作できます。</p></div>', unsafe_allow_html=True)
    
    if not supplies:
        st.warning("資材が未登録です。マスタ設定よりご登録ください。")
    else:
        cols_grid = st.columns(min(3, len(supplies)))
        for idx, s in enumerate(supplies):
            sid = s.get("資材ID")
            curr_stock = supply_inventory.get(sid, {}).get("現在庫", 0.0)
            
            with cols_grid[idx % 3]:
                with st.container(border=True):
                    img_data = s.get("画像URL", "")
                    if img_data and img_data.startswith("data:image"):
                        st.image(img_data, width=80)
                    st.markdown(f"<div style='font-weight:bold;font-size:1.1rem;margin-bottom:8px;'>{s.get('資材名')}</div>", unsafe_allow_html=True)
                    st.metric("現在庫", fmt_kg(curr_stock))
                    
                    # ★ その場で入力できるポップオーバー
                    with lot_popover("🔄 入出庫を記録"):
                        action = st.radio("処理", ["➖ 使用(出庫)", "➕ 補充(入庫)"], key=f"act_{sid}", horizontal=True)
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

    with st.expander("🕒 最近の入出庫ログ"):
        if supply_logs:
            id_name_map = {s.get("資材ID"): s.get("資材名") for s in supplies}
            df_logs = pd.DataFrame(supply_logs)
            df_logs["資材名"] = df_logs["資材ID"].map(id_name_map)
            st.dataframe(df_logs[["登録日", "資材名", "処理", "数量"]][::-1].head(20), use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════
#  その他機能群 (アコーディオン・タブで整理)
# ═══════════════════════════════════════════════════════════════
else:
    if page == "🔍 トレース":
        st.markdown('<div class="main-header"><h1>🔍 トレース</h1></div>', unsafe_allow_html=True)
        st.info("原料ロットと製品ロットの紐付け検索を行います。")
        lot_list = sorted(list(set([str(a.get("ロットNo", "")).strip() for a in arrivals if a.get("ロットNo")])), reverse=True)
        tgt_lot = st.selectbox("検索する原料ロット", lot_list if lot_list else ["なし"])
        if st.button("➡️ このロットを使った製品を追跡", type="primary"):
            match_brw = [b for b in brewing if tgt_lot in b.get("その他添加物", "")]
            if match_brw:
                st.dataframe(pd.DataFrame(match_brw)[["仕込日", "品名", "仕込量(kg)"]], use_container_width=True, hide_index=True)
            else:
                st.warning("履歴がありません。")

    elif page == "📋 履歴・帳票":
        st.markdown('<div class="main-header"><h1>📋 製造履歴・監査帳票</h1></div>', unsafe_allow_html=True)
        if not brewing: st.info("データがありません。")
        else:
            df_b = pd.DataFrame(brewing)[::-1]
            st.dataframe(df_b[["仕込日", "品名", "仕込量(kg)", "主原料ロット", "備考"]].head(50), use_container_width=True, hide_index=True)

    elif page == "📈 分析":
        st.markdown('<div class="main-header"><h1>📈 分析</h1></div>', unsafe_allow_html=True)
        if not df_brw_global.empty:
            pie_data = df_brw_global.groupby("品名")["仕込量(kg)"].sum().reset_index()
            fig_pie = px.pie(pie_data, names="品名", values="仕込量(kg)", title="製品別 製造割合")
            st.plotly_chart(fig_pie, use_container_width=True)

    elif page == "⚙️ マスタ設定":
        st.markdown('<div class="main-header"><h1>⚙️ マスターデータ管理</h1></div>', unsafe_allow_html=True)
        t1, t2 = st.tabs(["⚗️ 原料リスト", "🏢 取引先・担当者"])
        with t1:
            df_m = pd.DataFrame({"原料名": materials})
            ed_m = st.data_editor(df_m, num_rows="dynamic", use_container_width=True)
            if st.button("💾 原料マスタ保存", type="primary"):
                sheets.save_materials([str(x).strip() for x in ed_m["原料名"].tolist() if str(x).strip()])
                st.success("保存しました。")
                time.sleep(1)
                refresh()
        with t2:
            df_u = pd.DataFrame({"担当者名": inspectors})
            ed_u = st.data_editor(df_u, num_rows="dynamic", use_container_width=True)
            if st.button("💾 担当者保存", type="primary"):
                sheets.save_inspectors([str(x).strip() for x in ed_u["担当者名"].tolist() if str(x).strip()])
                st.success("保存しました。")
                time.sleep(1)
                refresh()
