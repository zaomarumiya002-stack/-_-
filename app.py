# app.py
import streamlit as st
import pandas as pd
import json
from datetime import datetime, date
import traceback
import plotly.graph_objects as go

try:
    from PIL import Image
    import base64
    from io import BytesIO
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

st.set_page_config(
    page_title="製造ERPシステム",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ════════════════════════════════════════════════════════════════
#  クリーン＆モダン UI/UX CSS
# ════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* 全体テーマ設定 */
:root {
    --c-bg: #f8fafc;
    --c-surface: #ffffff;
    --c-primary: #3b82f6;
    --c-primary-hover: #2563eb;
    --c-secondary: #1e293b;
    --c-border: #e2e8f0;
    --c-text: #334155;
}
.stApp { background-color: var(--c-bg); color: var(--c-text); }

/* サイドバー */
[data-testid="stSidebar"] {
    background-color: var(--c-secondary) !important;
}
[data-testid="stSidebar"] * { color: #f8fafc !important; }
[data-testid="stSidebar"] div[role="radiogroup"] label {
    padding: 14px 18px !important;
    border-radius: 8px !important;
    margin-bottom: 8px !important;
    background: #334155 !important;
    border: none !important;
    cursor: pointer;
    font-size: 1.05rem !important;
    font-weight: 600 !important;
}
[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    background: #475569 !important;
}

/* メインヘッダー */
.main-header {
    background: var(--c-surface);
    padding: 20px 24px;
    border-radius: 12px;
    margin-bottom: 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    border-left: 6px solid var(--c-primary);
}
.main-header h1 {
    color: var(--c-secondary) !important;
    font-size: 1.6rem !important;
    margin: 0 0 4px 0 !important;
    font-weight: 800 !important;
}

/* フォームとカード */
.form-card {
    background: var(--c-surface);
    border: 1px solid var(--c-border);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}
.section-title {
    font-size: 1.15rem;
    font-weight: 800;
    color: var(--c-secondary);
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 8px;
    border-bottom: 2px solid #f1f5f9;
    padding-bottom: 8px;
}

/* 入力フィールド */
.stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"], .stDateInput input {
    background-color: #f1f5f9 !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 8px !important;
    color: var(--c-text) !important;
    font-size: 1.05rem !important;
    font-weight: 600 !important;
    padding: 12px !important;
    min-height: 48px;
}
.stTextInput input:focus, .stNumberInput input:focus, .stSelectbox div[data-baseweb="select"]:focus-within {
    border-color: var(--c-primary) !important;
    background-color: var(--c-surface) !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15) !important;
}
label { color: #64748b !important; font-weight: 700 !important; font-size: 0.9rem !important; margin-bottom: 4px;}

/* メインアクションボタン */
.stButton button[kind="primary"] {
    background: var(--c-primary) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    padding: 14px !important;
    min-height: 52px !important;
    width: 100% !important;
    box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2) !important;
}
.stButton button[kind="primary"]:hover {
    background: var(--c-primary-hover) !important;
}

/* トグルやラジオ等のカスタマイズ */
div[data-testid="stRadio"] > div {
    gap: 12px;
}
.stRadio > label { font-size: 1rem !important; color: var(--c-primary) !important; }

/* Metrics (結果表示) */
[data-testid="stMetricValue"] {
    font-size: 1.8rem !important;
    font-weight: 800 !important;
    color: var(--c-secondary) !important;
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
#  データロード
# ════════════════════════════════════════════════════════════════
try:
    import sheets
except:
    st.error("🚨 `sheets.py` のインポートエラー")
    st.stop()

try:
    import report_generator
    HAS_REPORT_GEN = True
except Exception:
    HAS_REPORT_GEN = False

def refresh():
    st.cache_data.clear()
    st.rerun()

@st.cache_data(ttl=60)
def load_all_datasets():
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
        "recipes": sheets.load_recipes()
    }

try:
    dataset = load_all_datasets()
    arrivals, brewing, adjustments = dataset["arrivals"], dataset["brewing"], dataset["adjustments"]
    supplies, supply_logs = dataset["supplies"], dataset["supply_logs"]
    materials, makers, inspectors = dataset["materials"], dataset["makers"], dataset["inspectors"]
    order_points, recipes_raw = dataset["order_points"], dataset["recipes"]
except Exception as e:
    st.error("🚨 データの読み込みに失敗しました。")
    st.stop()

# ════════════════════════════════════════════════════════════════
#  現在庫算出
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
            except:
                pass

    for adj in adjustments:
        ano = str(adj.get("入荷No", "")).strip()
        if ano in inv:
            inv[ano]["調整袋数"] += float(adj.get("調整袋数") or 0.0)

    for v in inv.values():
        bpk = v["1袋重量"] if v["1袋重量"] > 0 else 20.0
        v["使用袋数"] = v["使用量(kg)"] / bpk
        v["現在庫(袋)"] = max(v["入荷袋数"] - v["使用袋数"] + v["調整袋数"], 0.0)
        v["現在庫(kg)"] = v["現在庫(袋)"] * bpk
    return inv

inventory_data = get_inventory()
type_totals = {}
for v in inventory_data.values():
    m_type = v["原料種別"]
    type_totals[m_type] = type_totals.get(m_type, 0.0) + v["現在庫(袋)"]

# ════════════════════════════════════════════════════════════════
#  サイドバー
# ════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div style="font-size:1.5rem; font-weight:900; margin-bottom:1rem; color:white;">🏭 製造管理 ERP</div>', unsafe_allow_html=True)
    page = st.radio("", [
        "📊 ダッシュボード", 
        "📥 原料入荷登録", 
        "🧪 仕込み・配合計算", 
        "📦 原料在庫・棚卸", 
        "🧹 資材・消耗品管理", 
        "🔍 履歴トレース", 
        "⚙️ マスタ設定"
    ], label_visibility="collapsed")
    if st.button("🔄 データを最新に更新"): refresh()

# ════════════════════════════════════════════════════════════════
#  1. ダッシュボード
# ════════════════════════════════════════════════════════════════
if page == "📊 ダッシュボード":
    st.markdown('<div class="main-header"><h1>📊 生産・在庫ダッシュボード</h1><p>工場の在庫状況およびアラート監視をリアルタイムに行います。</p></div>', unsafe_allow_html=True)
    
    alerts = [{"name": m, "current": type_totals.get(m, 0.0), "point": order_points.get(m, 0.0)} for m in materials if order_points.get(m, 0.0) > 0 and type_totals.get(m, 0.0) < order_points.get(m, 0.0)]
    if alerts:
        for al in alerts:
            st.markdown(f'<div style="background:#fef2f2; border-left:6px solid #ef4444; padding:16px; border-radius:8px; margin-bottom:12px; color:#991b1b; font-weight:bold;">🚨 【発注警告】 {al["name"]} の在庫（{al["current"]:.2f} 袋）が発注点（{al["point"]:.2f} 袋）を下回っています！</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="background:#f0fdf4; border-left:6px solid #10b981; padding:16px; border-radius:8px; margin-bottom:12px; color:#065f46; font-weight:bold;">🟢 すべての原料在庫は発注基準値を満たし、安全な状態です。</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">📦 主要原料 在庫モニター</div>', unsafe_allow_html=True)
    cols = st.columns(min(4, len(materials) if materials else 1))
    for idx, m in enumerate(materials):
        curr = type_totals.get(m, 0.0)
        pt = order_points.get(m, 0.0)
        with cols[idx % 4]:
            st.markdown(f"""
            <div style="background:#fff; border:1px solid #e2e8f0; border-radius:12px; padding:20px; text-align:center; margin-bottom:16px; box-shadow:0 1px 3px rgba(0,0,0,0.05); { 'border-color:#ef4444; background:#fef2f2;' if pt > 0 and curr < pt else '' }">
                <div style="font-size:1rem; color:#64748b; font-weight:700; margin-bottom:8px;">{m}</div>
                <div style="font-size:1.8rem; font-weight:900; color:{'#ef4444' if pt > 0 and curr < pt else '#0f172a'};">{curr:,.2f} <span style="font-size:1rem;">袋</span></div>
                <div style="font-size:0.85rem; color:#94a3b8; font-weight:600; margin-top:4px;">発注基準: {pt:,.2f} 袋</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">⏱️ 直近の製造仕込み履歴（最新5件）</div>', unsafe_allow_html=True)
    if brewing:
        df_brw = pd.DataFrame(brewing)[["仕込No", "仕込日", "品名", "仕込量(kg)", "主原料ロット"]]
        st.dataframe(df_brw.tail(5)[::-1], use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════════════
#  2. 原料入荷登録
# ═══════════════════════════════════════════════════════════════
elif page == "📥 原料入荷登録":
    st.markdown('<div class="main-header"><h1>📥 原料入荷品質記録</h1><p>現場での素早い入荷検品と情報登録を行います。</p></div>', unsafe_allow_html=True)
    tab_a, tab_b = st.tabs(["➕ 新規入荷検品", "📋 入荷履歴"])
    
    with tab_a:
        st.markdown('<div class="form-card"><div class="section-title">🚛 基本入荷情報</div>', unsafe_allow_html=True)
        new_no = sheets.next_arrival_no(arrivals)
        c1, c2 = st.columns(2)
        c1.text_input("入荷No", value=new_no, disabled=True)
        arr_date = c2.date_input("入荷日", value=date.today())
        
        c3, c4 = st.columns(2)
        maker_sel = c3.selectbox("メーカー", makers + ["その他"])
        maker_val = st.text_input("メーカー名を入力") if maker_sel == "その他" else maker_sel
        lot_val = c4.text_input("ロットNo ＊")

        c5, c6 = st.columns(2)
        m_type = c5.selectbox("原料種別", materials)
        bags_qty = c6.number_input("入荷袋数", min_value=1, step=1, value=10)
        weight_per_bag = st.number_input("1袋重量 (kg)", min_value=1.0, value=20.0, step=0.5)
        st.info(f"💡 自動算出 合計重量: **{bags_qty * weight_per_bag:,.2f} kg**")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="form-card"><div class="section-title">🔍 受入品質検査</div>', unsafe_allow_html=True)
        cc1, cc2 = st.columns(2)
        chk_app = cc1.selectbox("① 外観検査", ["OK（正常）", "NG（異常あり）"])
        chk_spec = cc2.selectbox("② 品名・規格", ["OK（一致）", "NG（不一致）"])
        chk_exp = cc1.selectbox("③ 賞味期限", ["OK（期限内）", "NG（期限切れ）"])
        chk_dmg = cc2.selectbox("④ 異物・破損", ["OK（なし）", "NG（あり）"])
        
        abn_desc = st.text_input("⚠️ 異常内容の詳細", placeholder="異常詳細を入力してください") if "NG" in [chk_app, chk_spec, chk_exp, chk_dmg] else ""
        inspector_val = st.selectbox("受入検査担当者", inspectors)
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
                st.success("入荷品質検査記録を保存しました。")
                refresh()

    with tab_b:
        if arrivals:
            df_arr = pd.DataFrame(arrivals)[["入荷No", "入荷日", "メーカー", "ロットNo", "原料種別", "袋数", "外観", "担当者"]]
            st.dataframe(df_arr[::-1], use_container_width=True, hide_index=True, column_config={"袋数": st.column_config.NumberColumn(format="%.2f")})

# ═══════════════════════════════════════════════════════════════
#  3. 仕込み・配合記録（カテゴリ階層UI、％逆算、こんにゃく粉ブレンド対応）
# ═══════════════════════════════════════════════════════════════
elif page == "🧪 仕込み・配合計算":
    st.markdown('<div class="main-header"><h1>🧪 製造仕込み・配合計算</h1><p>カテゴリから製品を選択し、割合(%)を入力すると実投入量(kg)が自動算出されます。</p></div>', unsafe_allow_html=True)
    
    tab_brw1, tab_brw2, tab_brw3 = st.tabs(["➕ 新規配合・登録", "📋 履歴一覧・Excel出力", "✏️ 履歴の編集・削除"])
    
    # 登録済みレシピのパース
    p_recipes = {}
    for r in recipes_raw:
        try:
            p_recipes[r["品名"]] = {
                "大カテゴリ": r.get("大カテゴリ", "その他"),
                "中カテゴリ": r.get("中カテゴリ", "その他"),
                "成分": json.loads(r["配合JSON"])
            }
        except:
            p_recipes[r["品名"]] = {"大カテゴリ": "その他", "中カテゴリ": "その他", "成分": []}

    with tab_brw1:
        st.markdown('<div class="form-card"><div class="section-title">📝 製造製品のカテゴリと仕込み量の指定</div>', unsafe_allow_html=True)
        
        # 1. 大カテゴリ選択
        st.write("##### **1. 大カテゴリを選択**")
        cat_main = st.radio("", ["🏭 プラント", "🟦 OKM", "📝 直接入力（マスタ外）"], horizontal=True, label_visibility="collapsed")
        
        selected_p = None
        active_recipe = []

        if "直接入力" in cat_main:
            p_name = st.text_input("品名を手動入力してください")
            active_recipe = [{"原料名": "こんにゃく粉（国産）", "比率": 2.50}, {"原料名": "石灰", "比率": 0.14}, {"原料名": "水", "比率": 97.36}]
        else:
            cat_str = "プラント" if "プラント" in cat_main else "OKM"
            
            # 2. 中カテゴリ選択（プラントの場合のみ）
            if cat_str == "プラント":
                st.write("##### **2. ライン（中カテゴリ）を選択**")
                cat_sub = st.radio("", ["⚪ 白", "⚫ 黒", "❄️ 耐冷", "🍽️ ショクカイ", "🍜 めん", "📦 その他"], horizontal=True, label_visibility="collapsed")
                sub_str = cat_sub.split(" ")[1] # アイコン以降の文字を取得
            else:
                sub_str = None
                
            # 3. 製品プルダウンのフィルタリング
            filtered_opts = []
            for k, v in p_recipes.items():
                if v["大カテゴリ"] == cat_str:
                    if cat_str == "プラント" and v["中カテゴリ"] != sub_str:
                        continue
                    filtered_opts.append(k)
            
            st.write("##### **3. 製造する製品名を選択**")
            if not filtered_opts:
                st.warning("選択したカテゴリに紐づく製品マスタがありません。")
            else:
                selected_p = st.selectbox("", filtered_opts, label_visibility="collapsed")
                p_name = selected_p
                active_recipe = p_recipes.get(selected_p, {}).get("成分", [])

        st.markdown("---")
        target_size = st.number_input("希望仕込製品量 (調合全体重量 kg)", min_value=1.0, value=100.0, step=10.0, format="%.2f")
        st.markdown('</div>', unsafe_allow_html=True)

        if not active_recipe:
            st.info("製品を選択してください。")
        else:
            st.markdown('<div class="form-card"><div class="section-title">⚖️ 投入原料の算出と入力</div>', unsafe_allow_html=True)
            st.write("各原料の「割合(%)」を変更すると、実投入量(kg)が自動で再計算されます。")
            
            current_month = date.today().month
            is_summer = 6 <= current_month <= 9
            
            submitted_ingredients = []
            recent_arrivals = sorted(arrivals, key=lambda x: x.get("入荷日", ""), reverse=True)

            for i, item in enumerate(active_recipe[:10]):
                if not isinstance(item, dict): continue
                r_name = item.get("原料名", "未定義原料")
                base_ratio = float(item.get("比率", 0.0))

                # 1. 水（追跡対象外）
                if "水" == r_name.strip() or "お湯" in r_name:
                    water_weight = target_size * (base_ratio / 100.0)
                    st.markdown(f'<div style="background:#e0f2fe; padding:12px; border-radius:8px; margin-bottom:16px; border:1px solid #bae6fd; color:#0369a1; font-weight:bold;">💧 [参考] 配合加水量: {water_weight:.2f} kg (マスタ比率: {base_ratio:.2f}%)</div>', unsafe_allow_html=True)
                    continue

                # 2. 石灰水（夏季増量＋粉末逆算）
                if "石灰" in r_name or "カルシウム" in r_name:
                    if is_summer:
                        orig_ratio = base_ratio
                        base_ratio += 0.1
                        st.markdown(f'<div style="background:#fefce8; padding:8px 12px; border-radius:6px; color:#a16207; font-weight:bold; margin-bottom:8px; border-left:4px solid #eab308;">☀️ 夏季自動調整: 石灰比率を +0.1% 増量 ({orig_ratio:.2f}% → {base_ratio:.2f}%)</div>', unsafe_allow_html=True)
                    
                    st.markdown(f"#### 🧪 {r_name}")
                    col_l1, col_l2 = st.columns(2)
                    act_ratio = col_l1.number_input("適用比率 (%)", value=base_ratio, step=0.01, format="%.2f", key=f"ratio_{i}")
                    lime_water_l = col_l2.number_input("作りたい石灰水の量 (L)", min_value=0.0, value=float(target_size), step=1.0, format="%.2f", key=f"lime_l_{i}")
                    
                    # 逆算
                    calc_kg = lime_water_l * (act_ratio / 100.0)
                    st.metric("✅ 必要な石灰粉末 (自動計算)", f"{calc_kg:.3f} kg")
                    
                    raw_arr_matches = [a for a in recent_arrivals if str(a.get("原料種別", "")).strip() == r_name.strip()]
                    recent_filtered_lots = []
                    for a in raw_arr_matches:
                        l_no = str(a.get("ロットNo", "")).strip()
                        if l_no and l_no not in recent_filtered_lots: recent_filtered_lots.append(l_no)
                        if len(recent_filtered_lots) >= 5: break
                    
                    lots_choices = ["手入力する"] + recent_filtered_lots + ["─"]
                    col_l_sel, col_l_txt = st.columns(2)
                    lot_sel = col_l_sel.selectbox("直近5件ロット", lots_choices, key=f"lot_sel_{i}")
                    lot_txt = col_l_txt.text_input("ロット手入力", value="" if lot_sel == "手入力する" else lot_sel, disabled=(lot_sel != "手入力する"), key=f"lot_txt_{i}")
                    
                    final_lot = lot_txt if lot_sel == "手入力する" else lot_sel
                    submitted_ingredients.append({"原料名": r_name, "kg": calc_kg, "lot": final_lot})
                    st.markdown("<hr style='margin:20px 0;'>", unsafe_allow_html=True)
                    continue

                # 3. 通常の粉体原料（割合からの重量計算）
                st.markdown(f"#### 🍏 {r_name}")
                col_rat, col_kg_show = st.columns(2)
                act_ratio = col_rat.number_input("適用割合 (%)", value=base_ratio, step=0.01, format="%.2f", key=f"ratio_{i}")
                
                # 自動計算
                calc_kg = target_size * (act_ratio / 100.0)
                col_kg_show.metric("✅ 実投入量 (自動計算)", f"{calc_kg:.3f} kg")
                
                raw_arr_matches = [a for a in recent_arrivals if str(a.get("原料種別", "")).strip() == r_name.strip()]
                recent_filtered_lots = []
                for a in raw_arr_matches:
                    l_no = str(a.get("ロットNo", "")).strip()
                    if l_no and l_no not in recent_filtered_lots: recent_filtered_lots.append(l_no)
                    if len(recent_filtered_lots) >= 5: break
                lots_choices = ["手入力する"] + recent_filtered_lots + ["─"]

                # --- ブレンド機能（こんにゃく粉限定） ---
                if "こんにゃく" in r_name:
                    use_blend = st.toggle("🔀 こんにゃく粉をブレンドする（複数ロット入力）", key=f"blend_{i}")
                    if use_blend:
                        st.markdown('<div style="background:#f8fafc; padding:16px; border-radius:8px; border:2px dashed #cbd5e1; margin-bottom:10px;">', unsafe_allow_html=True)
                        st.write(f"**ブレンド内訳**（合計が {calc_kg:.3f} kg になるよう割り振ってください）")
                        col_b1, col_b2 = st.columns(2)
                        
                        st.write("▼ ロット A")
                        act_kg_1 = col_b1.number_input("投入量 A (kg)", min_value=0.0, value=calc_kg/2, step=0.1, format="%.3f", key=f"kg_{i}_b1")
                        lot_sel_1 = col_b2.selectbox("ロット選択 A", lots_choices, key=f"lot_sel_{i}_b1")
                        lot_txt_1 = col_b2.text_input("ロット手入力 A", value="" if lot_sel_1 == "手入力する" else lot_sel_1, disabled=(lot_sel_1 != "手入力する"), key=f"lot_txt_{i}_b1")
                        final_lot_1 = lot_txt_1 if lot_sel_1 == "手入力する" else lot_sel_1

                        st.write("▼ ロット B")
                        act_kg_2 = col_b1.number_input("投入量 B (kg)", min_value=0.0, value=calc_kg/2, step=0.1, format="%.3f", key=f"kg_{i}_b2")
                        lot_sel_2 = col_b2.selectbox("ロット選択 B", lots_choices, key=f"lot_sel_{i}_b2")
                        lot_txt_2 = col_b2.text_input("ロット手入力 B", value="" if lot_sel_2 == "手入力する" else lot_sel_2, disabled=(lot_sel_2 != "手入力する"), key=f"lot_txt_{i}_b2")
                        final_lot_2 = lot_txt_2 if lot_sel_2 == "手入力する" else lot_sel_2
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        if act_kg_1 > 0: submitted_ingredients.append({"原料名": r_name, "kg": act_kg_1, "lot": final_lot_1})
                        if act_kg_2 > 0: submitted_ingredients.append({"原料名": r_name, "kg": act_kg_2, "lot": final_lot_2})
                        
                        if abs((act_kg_1 + act_kg_2) - calc_kg) > 0.05:
                            st.warning(f"⚠️ 投入量の合計（{act_kg_1 + act_kg_2:.2f} kg）が、算出された実投入量（{calc_kg:.2f} kg）と一致していません。")
                        
                    else:
                        col_s, col_t = st.columns(2)
                        lot_sel = col_s.selectbox("直近5件ロット", lots_choices, key=f"lot_sel_{i}")
                        lot_txt = col_t.text_input("ロット手入力", value="" if lot_sel == "手入力する" else lot_sel, disabled=(lot_sel != "手入力する"), key=f"lot_txt_{i}")
                        final_lot = lot_txt if lot_sel == "手入力する" else lot_sel
                        submitted_ingredients.append({"原料名": r_name, "kg": calc_kg, "lot": final_lot})
                else:
                    # こんにゃく以外は単一ロット
                    col_s, col_t = st.columns(2)
                    lot_sel = col_s.selectbox("直近5件ロット", lots_choices, key=f"lot_sel_{i}")
                    lot_txt = col_t.text_input("ロット手入力", value="" if lot_sel == "手入力する" else lot_sel, disabled=(lot_sel != "手入力する"), key=f"lot_txt_{i}")
                    final_lot = lot_txt if lot_sel == "手入力する" else lot_sel
                    submitted_ingredients.append({"原料名": r_name, "kg": calc_kg, "lot": final_lot})

                st.markdown("<hr style='margin:20px 0;'>", unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

            if st.button("💾 この実績で製造記録を保存する", type="primary", use_container_width=True):
                k_kg = s_kg = st_kg = lime_kg = 0.0
                k_lot = s_lot = st_lot = "─"
                
                for ing in submitted_ingredients:
                    n = ing["原料名"]
                    if "こんにゃく" in n:
                        k_kg += ing["kg"]
                        if k_lot == "─": k_lot = ing["lot"]
                        elif ing["lot"] not in k_lot: k_lot += f", {ing['lot']}"
                    elif "海藻" in n:
                        s_kg += ing["kg"]
                        if s_lot == "─": s_lot = ing["lot"]
                        elif ing["lot"] not in s_lot: s_lot += f", {ing['lot']}"
                    elif "デンプン" in n or "でんぷん" in n:
                        st_kg += ing["kg"]
                        if st_lot == "─": st_lot = ing["lot"]
                        elif ing["lot"] not in st_lot: st_lot += f", {ing['lot']}"
                    elif "石灰" in n or "カルシウム" in n:
                        lime_kg += ing["kg"]

                sheets.append_brewing({
                    "仕込No": sheets.next_brewing_no(brewing), "仕込日": str(date.today()), "品名": p_name,
                    "メーカー": "自社", "主原料ロット": k_lot, "仕込量(kg)": target_size,
                    "こんにゃく精粉(kg)": k_kg, "海藻粉(kg)": s_kg, "海藻粉ロット": s_lot,
                    "デンプン(kg)": st_kg, "デンプンロット": st_lot, "デンプン種別": "-",
                    "石灰(kg)": lime_kg, "石灰水(L)": 0, 
                    "その他添加物": json.dumps(submitted_ingredients, ensure_ascii=False),
                    "備考": "割合ベース動的登録", "登録日時": datetime.now().isoformat()
                })
                st.success("仕込み・製造実績を登録しました。")
                refresh()

    with tab_brw2:
        st.markdown('<div class="section-title">📋 過去の製造記録</div>', unsafe_allow_html=True)
        if brewing:
            df_brw_all = pd.DataFrame(brewing)[["仕込No", "仕込日", "品名", "仕込量(kg)", "こんにゃく精粉(kg)", "主原料ロット"]]
            st.dataframe(df_brw_all[::-1], use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown('<div class="section-title">🖨️ 管理帳票の範囲指定ダウンロード</div>', unsafe_allow_html=True)
            col_d1, col_d2 = st.columns(2)
            today = date.today()
            start_val = date(today.year, today.month, 1)
            date_from = col_d1.date_input("開始日", value=start_val)
            date_to = col_d2.date_input("終了日", value=today)

            if HAS_REPORT_GEN:
                filtered_brewing = []
                for b in brewing:
                    try:
                        b_date = datetime.strptime(b.get("仕込日", "").replace("/","-"), "%Y-%m-%d").date()
                        if date_from <= b_date <= date_to:
                            filtered_brewing.append(b)
                    except:
                        pass
                
                if not filtered_brewing:
                    st.warning("指定された期間の製造記録が見つかりません。")
                else:
                    try:
                        file_path = report_generator.generate_brewing_report(filtered_brewing)
                        with open(file_path, "rb") as f:
                            st.download_button(
                                label=f"📊 指定範囲の帳票をダウンロード ({len(filtered_brewing)}件)",
                                data=f, file_name=file_path.name,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    except Exception as e:
                        st.error("帳票の生成に失敗しました。")
            else:
                st.warning("帳票モジュールがありません。")

    with tab_brw3:
        st.markdown('<div class="form-card"><div class="section-title">✏️ 登録済み記録の編集と削除</div>', unsafe_allow_html=True)
        if not brewing:
            st.info("編集可能な履歴がありません。")
        else:
            brw_opts = {f"No.{b.get('仕込No')} - {b.get('品名')} ({b.get('仕込日')})": b for b in reversed(brewing)}
            selected_brw_label = st.selectbox("対象の製造記録を選択してください", list(brw_opts.keys()))
            target_b = brw_opts[selected_brw_label]
            
            col_e1, col_e2 = st.columns(2)
            edit_date = col_e1.date_input("製造日", value=datetime.strptime(target_b.get("仕込日", date.today().strftime("%Y-%m-%d")).replace("/","-"), "%Y-%m-%d").date())
            edit_name = col_e2.text_input("品名", value=target_b.get("品名", ""))
            edit_target_kg = col_e1.number_input("仕込量 (kg)", min_value=0.0, value=float(target_b.get("仕込量(kg)", 0)), step=1.0)
            edit_remarks = col_e2.text_input("備考（修正理由など）", value=target_b.get("備考", ""))
            
            st.markdown("<br>", unsafe_allow_html=True)
            col_eb1, col_eb2 = st.columns(2)
            if col_eb1.button("💾 この内容で上書き更新する", type="primary", use_container_width=True):
                target_b["仕込日"] = str(edit_date)
                target_b["品名"] = edit_name
                target_b["仕込量(kg)"] = edit_target_kg
                target_b["備考"] = edit_remarks
                sheets.update_brewing(target_b["仕込No"], target_b)
                st.success("更新しました。")
                refresh()
            if col_eb2.button("🗑️ この製造記録を完全に削除する", use_container_width=True):
                sheets.delete_brewing(target_b["仕込No"])
                st.success("削除しました。")
                refresh()
        st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
#  4. 原料在庫・棚卸（入出庫トレンドグラフ追加＆小数第二位ガード）
# ═══════════════════════════════════════════════════════════════
elif page == "📦 原料在庫・棚卸":
    st.markdown('<div class="main-header"><h1>📦 原料在庫・棚卸管理</h1><p>ロット別現在庫の確認、入出庫トレンドのグラフ化、棚卸し調整を行います。</p></div>', unsafe_allow_html=True)
    tab_inv1, tab_inv_trend, tab_inv2 = st.tabs(["📋 ロット別現在庫一覧", "📈 入出庫トレンド推移", "⚖️ 棚卸し在庫調整"])
    
    with tab_inv1:
        active_inv = [v for v in inventory_data.values() if v["現在庫(袋)"] > 0.0]
        if active_inv:
            df_curr_inv = pd.DataFrame(active_inv)[["入荷No", "原料種別", "ロットNo", "入荷袋数", "使用袋数", "調整袋数", "現在庫(袋)"]]
            st.dataframe(
                df_curr_inv, 
                use_container_width=True, hide_index=True,
                column_config={"入荷袋数": st.column_config.NumberColumn(format="%.2f"), "使用袋数": st.column_config.NumberColumn(format="%.2f"), "調整袋数": st.column_config.NumberColumn(format="%.2f"), "現在庫(袋)": st.column_config.NumberColumn(format="%.2f")}
            )

    with tab_inv_trend:
        st.markdown('<div class="form-card"><div class="section-title">📊 原料種別 月別入出庫トレンド</div>', unsafe_allow_html=True)
        target_mat = st.selectbox("グラフ表示する原料種別", materials)
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
                fig.add_trace(go.Bar(x=df_trend["month"], y=df_trend["消費量(kg)"], name="消費量 (kg)", marker_color="#f43f5e"))
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
            operator = st.selectbox("調整実施者", inspectors)

            if st.button("💾 在庫データを上書き調整する", type="primary", use_container_width=True):
                sheets.append_adjustment({"調整ID": f"ADJ-{datetime.now().strftime('%Y%m%d%H%M%S')}", "入荷No": tgt_list[selected_tgt], "調整日": str(date.today()), "調整袋数": diff_bags, "理由": reason_txt, "担当者": operator, "登録日時": datetime.now().isoformat()})
                st.success("調整情報を書き込みました。")
                refresh()
        st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
#  5. 資材・消耗品管理
# ═══════════════════════════════════════════════════════════════
elif page == "🧹 資材・消耗品管理":
    st.markdown('<div class="main-header"><h1>🧹 資材・消耗品管理</h1><p>資材の残量確認および入出庫操作を行います。</p></div>', unsafe_allow_html=True)
    tab_s1, tab_s2 = st.tabs(["📋 在庫一覧・入出庫", "🕒 ログ管理"])
    
    with tab_s1:
        if supplies:
            st.markdown('<div class="section-title">🚦 資材モニター</div>', unsafe_allow_html=True)
            cols_grid = st.columns(max(2, min(4, len(supplies))))
            for idx, s in enumerate(supplies):
                with cols_grid[idx % len(cols_grid)]:
                    st.markdown(f"**{s.get('資材名')}** ({s.get('カテゴリ')})")
                    img_data = s.get("画像URL", "")
                    if img_data and img_data.startswith("data:image"): st.image(img_data, width=100)
                    else: st.caption("📷 画像なし")
                    st.write(f"初期: {s.get('初期在庫')} / 発注点: {s.get('発注点')}")
                    st.markdown("---")
            
            st.markdown('<div class="form-card"><div class="section-title">📥 資材入出庫の記録</div>', unsafe_allow_html=True)
            col_sc1, col_sc2 = st.columns(2)
            sup_name = col_sc1.selectbox("資材名", [s.get("資材名") for s in supplies])
            action_type = col_sc2.selectbox("処理内容", ["➕ 補充する (入荷)", "➖ 使用する (出庫)"])
            qty_val = st.number_input("数量", min_value=1.0, value=1.0, step=1.0, format="%.2f")
            operator_val = st.selectbox("作業担当者", inspectors, key="op_sup")
            notes_val = st.text_input("備考情報")
            
            if st.button("💾 資材変動を保存する", type="primary", use_container_width=True):
                target_sup = next(s for s in supplies if s.get("資材名") == sup_name)
                sheets.append_supply_log({
                    "ログID": f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                    "登録日": str(date.today()), "資材ID": target_sup.get("資材ID"),
                    "処理": "入荷" if "補充" in action_type else "使用", "数量": qty_val,
                    "作業者": operator_val, "備考": notes_val, "登録日時": datetime.now().isoformat()
                })
                st.success("資材情報を記録しました。")
                refresh()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("資材が未登録です。マスタ設定よりご登録ください。")

    with tab_s2:
        if supply_logs:
            id_name_map = {s.get("資材ID"): s.get("資材名") for s in supplies}
            df_logs = pd.DataFrame(supply_logs).copy()
            df_logs["資材名"] = df_logs["資材ID"].map(id_name_map)
            st.dataframe(df_logs.tail(20)[::-1], use_container_width=True, hide_index=True)
            
            st.markdown('<div class="section-title">🚨 ログの取り消し・削除</div>', unsafe_allow_html=True)
            log_id_to_del = st.text_input("削除するログIDを入力してください")
            if st.button("🗑️ このログIDを完全に削除する"):
                if log_id_to_del:
                    sheets.delete_supply_log(log_id_to_del)
                    st.success("ログを削除しました。")
                    refresh()

# ═══════════════════════════════════════════════════════════════
#  6. 履歴トレース
# ═══════════════════════════════════════════════════════════════
elif page == "🔍 履歴トレース":
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
                    except:
                        pass
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
                        <p style="margin-bottom:0; font-size:1.1rem;"><strong>製造量:</strong> <span style="color:#2563eb; font-weight:bold;">{selected_b.get('仕込量(kg)')} kg</span></p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                used_lots = []
                try:
                    items = json.loads(selected_b.get("その他添加物", "[]"))
                    for ing in items:
                        l_num = str(ing.get("lot", "")).strip()
                        if l_num and l_num != "─" and l_num != "":
                            used_lots.append({"原料種別": ing.get("原料名", "副資材"), "ロットNo": l_num})
                except:
                    pass
                
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

# ═══════════════════════════════════════════════════════════════
#  7. マスタ設定（大カテゴリ・中カテゴリ対応）
# ═══════════════════════════════════════════════════════════════
elif page == "⚙️ マスタ設定":
    st.markdown('<div class="main-header"><h1>⚙️ マスターデータ管理</h1><p>システム全体で共有されるリストや配合基準、資材の定義を行います。</p></div>', unsafe_allow_html=True)
    m_tab1, m_tab2, m_tab3, m_tab4, m_tab5 = st.tabs(["⚗️ 原料", "🏢 メーカー・担当", "🚨 発注点", "🧪 配合レシピ", "📦 資材・消耗品"])
    
    with m_tab1:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        df_materials = pd.DataFrame({"原料名": materials})
        edited_materials = st.data_editor(df_materials, num_rows="dynamic", use_container_width=True, key="mat_ed_k")
        if st.button("💾 原料マスタを更新する", type="primary"):
            sheets.save_materials([str(x).strip() for x in edited_materials["原料名"].tolist() if str(x).strip()])
            st.success("原料マスター情報を保存しました。")
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
                refresh()
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col_sub2:
            st.markdown('<div class="form-card"><div class="section-title">担当者</div>', unsafe_allow_html=True)
            df_inspectors = pd.DataFrame({"担当者名": inspectors})
            edited_inspectors = st.data_editor(df_inspectors, num_rows="dynamic", use_container_width=True, key="inspector_ed_k")
            if st.button("💾 担当者を保存", type="primary"):
                sheets.save_inspectors([str(x).strip() for x in edited_inspectors["担当者名"].tolist() if str(x).strip()])
                st.success("保存しました。")
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
            refresh()
        st.markdown('</div>', unsafe_allow_html=True)

    with m_tab4:
        st.markdown('<div class="form-card"><div class="section-title">➕ 配合レシピの新規登録</div>', unsafe_allow_html=True)
        with st.form("new_recipe_builder_pct"):
            st.write("##### **1. カテゴリの選択**")
            cat_main = st.radio("大カテゴリ", ["🏭 プラント", "🟦 OKM"], horizontal=True)
            cat_sub = st.radio("中カテゴリ（プラントの場合のみ）", ["⚪ 白", "⚫ 黒", "❄️ 耐冷", "🍽️ ショクカイ", "🍜 めん", "📦 その他"], horizontal=True)
            
            st.write("##### **2. 製品名と成分の登録**")
            new_p_name = st.text_input("製品の名称 (例: こんにゃく極細白)")
            cols_recipe_inputs = []
            for j in range(10):
                c_n, c_w = st.columns([2, 1])
                ing_mat = c_n.selectbox(f"配合成分 {j+1}", ["(未設定)", "水"] + materials, key=f"rec_builder_mat_{j}_val")
                ing_ratio = c_w.number_input("比率 (％)", min_value=0.00, max_value=100.00, step=0.01, key=f"rec_builder_ratio_{j}_val", format="%.2f")
                cols_recipe_inputs.append({"name": ing_mat, "ratio": ing_ratio})
            
            if st.form_submit_button("➕ この配合レシピを登録/更新する"):
                if not new_p_name:
                    st.error("製品の名称は必須です。")
                else:
                    valid_items = []
                    for ing in cols_recipe_inputs:
                        if ing["name"] != "(未設定)" and ing["ratio"] > 0:
                            valid_items.append({"原料名": ing["name"], "比率": float(ing["ratio"])})
                    
                    if not valid_items:
                        st.error("有効な配合成分がありません。")
                    else:
                        cat_str = "プラント" if "プラント" in cat_main else "OKM"
                        sub_str = cat_sub.split(" ")[1] if cat_str == "プラント" else "その他"

                        new_recipe_entry = {
                            "品名": new_p_name, 
                            "大カテゴリ": cat_str,
                            "中カテゴリ": sub_str,
                            "配合JSON": json.dumps(valid_items, ensure_ascii=False)
                        }
                        updated_recipes = [r for r in recipes_raw if r["品名"] != new_p_name]
                        updated_recipes.append(new_recipe_entry)
                        sheets.save_recipes(updated_recipes)
                        st.success(f"配合レシピ: {new_p_name} を保存しました。")
                        refresh()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="form-card"><div class="section-title">📋 登録済み配合レシピ一覧と削除</div>', unsafe_allow_html=True)
        if recipes_raw:
            for idx, rec in enumerate(recipes_raw):
                with st.expander(f"📦 {rec.get('品名')} (【{rec.get('大カテゴリ','')}】 {rec.get('中カテゴリ','')})"):
                    try:
                        comp_list = json.loads(rec["配合JSON"])
                        st.dataframe(pd.DataFrame(comp_list), use_container_width=True, hide_index=True)
                    except:
                        st.write("読出しエラー")
            
            st.markdown("---")
            del_recipe_name = st.selectbox("削除するレシピを選択してください", [r["品名"] for r in recipes_raw])
            if st.button("🗑️ 選択したレシピを完全に削除する", type="primary"):
                updated_recipes = [r for r in recipes_raw if r["品名"] != del_recipe_name]
                sheets.save_recipes(updated_recipes)
                st.success(f"{del_recipe_name} を削除しました。")
                refresh()
        else:
            st.info("登録済みの配合レシピはありません。")
        st.markdown('</div>', unsafe_allow_html=True)

    with m_tab5:
        st.markdown('<div class="form-card"><div class="section-title">📋 登録済み資材の管理・編集</div>', unsafe_allow_html=True)
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
                            "資材名": str(r.get("資材名")),
                            "カテゴリ": str(r.get("カテゴリ")),
                            "画像URL": orig.get("画像URL", ""),
                            "初期在庫": float(r.get("初期在庫", 0)),
                            "発注点": float(r.get("発注点", 0)),
                            "登録日": orig.get("登録日", str(date.today()))
                        })
                sheets.save_supplies(new_supplies)
                st.success("資材マスタを更新しました。")
                refresh()
        else:
            st.info("登録済みの資材はありません。")
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
                if not new_s_name:
                    st.error("資材名称は必須入力項目です。")
                else:
                    img_base64_str = ""
                    if uploaded_file and HAS_PIL:
                        try:
                            img = Image.open(uploaded_file)
                            img.thumbnail((150, 150))
                            buffered = BytesIO()
                            img.save(buffered, format="PNG", optimize=True)
                            img_base64_str = f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode('utf-8')}"
                        except Exception as e:
                            st.warning(f"画像の処理に失敗しました。: {e}")
                    
                    current_supplies = supplies.copy()
                    current_supplies.append({
                        "資材ID": f"SUP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "資材名": new_s_name, "カテゴリ": new_s_cat, "画像URL": img_base64_str,
                        "初期在庫": new_s_stock, "発注点": new_s_point, "登録日": str(date.today())
                    })
                    sheets.save_supplies(current_supplies)
                    st.success(f"資材: {new_s_name} を登録しました。")
                    refresh()
        st.markdown('</div>', unsafe_allow_html=True)
