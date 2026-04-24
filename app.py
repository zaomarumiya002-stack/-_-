# --- START OF FILE app.py ---
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
from datetime import datetime, date

st.set_page_config(page_title="原料管理システム", page_icon="🧪", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #0f1724 0%, #1a2744 100%); }
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
.main-header { background: linear-gradient(135deg, #1e3a5f 0%, #0d47a1 100%); padding: 20px 28px; border-radius: 12px; margin-bottom: 24px; }
.main-header h1 { color: #fff; font-size: 1.6rem; margin: 0; }
.main-header p  { color: #90caf9; font-size: 0.85rem; margin: 4px 0 0; }
.kpi-card { background: #fff; border-radius: 12px; padding: 18px 20px; box-shadow: 0 2px 12px rgba(0,0,0,0.07); border-left: 4px solid #1565c0; text-align: center; }
.kpi-value { font-size: 2rem; font-weight: 700; color: #1a237e; }
.kpi-label { font-size: 0.8rem; color: #607d8b; margin-top: 4px; }
.form-card { background: #f8faff; border-radius: 12px; padding: 20px 24px; border: 1px solid #e3eaf5; margin-bottom: 16px; }
.section-title { font-size: 1.1rem; font-weight: 700; color: #1a237e; margin: 20px 0 12px; padding-left: 10px; border-left: 4px solid #1565c0; }
.alert-ng { background:#ffebee; border-left:4px solid #c62828; padding:10px 16px; border-radius:8px; color:#b71c1c; font-weight:600; margin-bottom:10px;}
</style>
""", unsafe_allow_html=True)

try:
    from sheets import (load_arrivals, append_arrival, load_brewing, append_brewing, load_adjustments, append_adjustment,
                        load_materials, save_materials, load_makers, save_makers, load_inspectors, save_inspectors,
                        load_order_points, save_order_points, next_arrival_no, next_brewing_no)
    SHEETS_OK = True
except Exception as e:
    SHEETS_OK = False
    SHEETS_ERROR = str(e)

with st.sidebar:
    st.markdown("## 🧪 原料管理システム")
    if SHEETS_OK: st.success("🟢 接続中")
    else: st.error("🔴 接続エラー")
    st.markdown("---")
    page = st.radio("メニュー", ["🏠 ダッシュボード", "📦 入荷記録", "🧪 仕込み記録", "🏭 在庫管理", "🔍 原料トレース", "📊 集計・分析", "⚙️ マスター設定"], label_visibility="collapsed")

if not SHEETS_OK:
    st.error(f"接続エラー: {SHEETS_ERROR}")
    st.stop()

@st.cache_data(ttl=30)
def fetch_data(): return load_arrivals(), load_brewing(), load_adjustments()
arrivals, brewing, adjustments = fetch_data()

@st.cache_data(ttl=60)
def fetch_masters(): return load_materials(), load_makers(), load_inspectors(), load_order_points()
materials, makers, inspectors, order_points = fetch_masters()

def refresh():
    fetch_data.clear()
    st.rerun()

# --- 在庫計算ロジック ---
def calculate_inventory():
    inv = {}
    for a in arrivals:
        inv[a["arrival_no"]] = {
            "arrival_no": a["arrival_no"], "lot_no": a["lot_no"], "maker": a["maker"],
            "material_type": a["material_type"], "total_in": float(a.get("total_kg") or 0),
            "total_out": 0.0, "adj_kg": 0.0
        }
    for b in brewing:
        if b.get("lot_no"):
            m = [k for k, v in inv.items() if v["lot_no"] == b["lot_no"] and "精粉" in v["material_type"]]
            if m: inv[m[0]]["total_out"] += float(b.get("material_kg") or 0)
        if b.get("seaweed_lot"):
            m = [k for k, v in inv.items() if v["lot_no"] == b["seaweed_lot"]]
            if m: inv[m[0]]["total_out"] += float(b.get("seaweed_kg") or 0)
        if b.get("starch_lot"):
            m = [k for k, v in inv.items() if v["lot_no"] == b["starch_lot"]]
            if m: inv[m[0]]["total_out"] += float(b.get("starch_kg") or 0)
        if b.get("other_additives"):
            try:
                others = json.loads(b["other_additives"])
                for o in others:
                    if o.get("lot"):
                        m = [k for k, v in inv.items() if v["lot_no"] == o["lot"]]
                        if m: inv[m[0]]["total_out"] += float(o.get("kg") or 0)
            except: pass
    for adj in adjustments:
        if adj["arrival_no"] in inv: inv[adj["arrival_no"]]["adj_kg"] += float(adj.get("diff_kg") or 0)
    for v in inv.values(): v["current_kg"] = v["total_in"] - v["total_out"] + v["adj_kg"]
    return inv

inventory_data = calculate_inventory()

# 発注点アラートチェック
alerts = []
type_totals = {}
for v in inventory_data.values():
    type_totals[v["material_type"]] = type_totals.get(v["material_type"], 0) + v["current_kg"]
for mat, current in type_totals.items():
    if mat in order_points and current < order_points[mat]:
        alerts.append(f"⚠️ 【発注アラート】 {mat} の現在庫（{current:,.1f}kg）が発注点（{order_points[mat]:,.1f}kg）を下回っています。")

# ════════════════════════════════════════════════════════════════
if page == "🏠 ダッシュボード":
    st.markdown('<div class="main-header"><h1>🧪 ダッシュボード</h1><p>システム概況</p></div>', unsafe_allow_html=True)
    if alerts:
        for al in alerts: st.markdown(f'<div class="alert-ng">{al}</div>', unsafe_allow_html=True)

    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(f'<div class="kpi-card"><div class="kpi-value">{len(arrivals)}</div><div class="kpi-label">総入荷件数</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-card"><div class="kpi-value">{len(brewing)}</div><div class="kpi-label">総仕込み件数</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-card"><div class="kpi-value">{len([b for b in brewing if b.get("brew_date")==str(date.today())])}</div><div class="kpi-label">本日の仕込み</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi-card"><div class="kpi-value">{sum(v["current_kg"] for v in inventory_data.values()):,.0f}</div><div class="kpi-label">全原料 在庫量(kg)</div></div>', unsafe_allow_html=True)

elif page == "📦 入荷記録":
    st.markdown('<div class="main-header"><h1>📦 入荷記録</h1></div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["➕ 登録", "📋 一覧"])
    with t1:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        c1,c2,c3 = st.columns(3)
        new_no = next_arrival_no(arrivals)
        c1.text_input("入荷No", value=new_no, disabled=True)
        arrival_date = c2.date_input("入荷日")
        maker = c3.selectbox("メーカー", makers + ["その他"])
        if maker == "その他": maker = st.text_input("直接入力")
        
        c4,c5,c6 = st.columns(3)
        lot_no = c4.text_input("ロットNo ＊")
        material_type = c5.selectbox("原料種別", materials)
        bags = c6.number_input("袋数", min_value=0, step=1)
        bags_per = st.number_input("1袋重量(kg)", value=20.0, step=0.5)
        st.info(f"総量: {bags * bags_per:,.1f} kg")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        c7,c8 = st.columns(2)
        appearance = c7.selectbox("外観", ["OK（正常）", "NG（異常あり）"])
        abnormal_detail = st.text_input("異常内容（NG時）") if "NG" in appearance else ""
        inspector = c8.selectbox("担当者 ＊", inspectors)
        remarks = st.text_input("備考")
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("✅ 保存", type="primary"):
            if not lot_no: st.error("ロットNo必須")
            else:
                append_arrival({"arrival_no": new_no, "arrival_date": str(arrival_date), "maker": maker, "lot_no": lot_no,
                                "material_type": material_type, "bags": bags, "bags_per_kg": bags_per, "total_kg": bags * bags_per,
                                "appearance": appearance, "abnormal_detail": abnormal_detail, "inspector": inspector,
                                "remarks": remarks, "registered_at": datetime.now().isoformat()})
                st.success("保存完了"); refresh()

    with t2:
        if arrivals:
            df = pd.DataFrame(arrivals)[["arrival_no", "arrival_date", "maker", "lot_no", "material_type", "total_kg", "appearance", "inspector"]]
            st.dataframe(df[::-1].reset_index(drop=True), use_container_width=True)

elif page == "🧪 仕込み記録":
    st.markdown('<div class="main-header"><h1>🧪 仕込み記録</h1></div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["➕ 登録", "📋 一覧"])
    with t1:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        c1,c2,c3 = st.columns(3)
        brew_date = c1.date_input("仕込日")
        product_name = c2.text_input("品名 ＊")
        brew_maker = c3.selectbox("メーカー", makers)
        active_lots = sorted(list(set(a["lot_no"] for a in arrivals)), reverse=True)
        lot_no_b = st.selectbox("主原料（精粉）ロットNo ＊", ["─"] + active_lots)
        brew_amount = st.number_input("仕込量(kg)", min_value=0.0, value=None, step=10.0)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="form-card"><div class="section-title">⚗️ 基本原料</div>', unsafe_allow_html=True)
        c6,c7,c8 = st.columns(3)
        mat_kg = c6.number_input("精粉(kg)", min_value=0.0, value=None)
        sea_kg = c6.number_input("海藻粉(kg)", min_value=0.0, value=None)
        sea_lot = c6.text_input("海藻ロット")
        
        sta_kg = c7.number_input("デンプン(kg)", min_value=0.0, value=None)
        sta_type = c7.selectbox("デンプン種別", ["─","ゆり8","VA70","その他"])
        sta_lot = c7.text_input("デンプンロット")
        
        lime_kg = c8.number_input("石灰(kg)", min_value=0.0, value=None)
        lime_w = c8.number_input("石灰水(ℓ)", min_value=0.0, value=None)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="form-card"><div class="section-title">🧂 その他添加物</div>', unsafe_allow_html=True)
        st.caption("必要な添加物を表に追加してください。")
        if "other_df" not in st.session_state: st.session_state.other_df = pd.DataFrame(columns=["name", "lot", "kg"])
        edited_df = st.data_editor(
            st.session_state.other_df, num_rows="dynamic",
            column_config={
                "name": st.column_config.SelectboxColumn("添加物名", options=materials),
                "lot": st.column_config.TextColumn("ロットNo（任意）"),
                "kg": st.column_config.NumberColumn("使用量(kg)", min_value=0.0, format="%.2f")
            }, use_container_width=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("✅ 保存", type="primary"):
            if not product_name or lot_no_b == "─": st.error("品名と主ロットNoは必須です")
            else:
                others_json = edited_df.dropna(subset=["name"]).to_json(orient="records")
                append_brewing({
                    "no": next_brewing_no(brewing), "brew_date": str(brew_date), "product_name": product_name,
                    "maker": brew_maker, "lot_no": lot_no_b, "seaweed_lot": sea_lot, "starch_lot": sta_lot,
                    "brew_amount": brew_amount or 0, "material_kg": mat_kg or 0, "seaweed_kg": sea_kg or 0,
                    "starch_kg": sta_kg or 0, "starch_type": sta_type, "lime_kg": lime_kg or 0, "lime_water_l": lime_w or 0,
                    "other_additives": others_json, "registered_at": datetime.now().isoformat()
                })
                st.session_state.other_df = pd.DataFrame(columns=["name", "lot", "kg"]) # リセット
                st.success("保存完了"); refresh()
    with t2:
        if brewing:
            df = pd.DataFrame(brewing)[["no","brew_date","product_name","lot_no","brew_amount","material_kg"]]
            st.dataframe(df[::-1].reset_index(drop=True), use_container_width=True)

elif page == "🏭 在庫管理":
    st.markdown('<div class="main-header"><h1>🏭 在庫管理</h1><p>ロットごとの現在庫と調整</p></div>', unsafe_allow_html=True)
    
    t1, t2 = st.tabs(["📋 現在庫一覧", "⚖️ 在庫ズレ調整"])
    
    inv_list = list(inventory_data.values())
    inv_df = pd.DataFrame(inv_list)[["arrival_no", "material_type", "maker", "lot_no", "total_in", "total_out", "adj_kg", "current_kg"]]
    inv_df.columns = ["入荷No", "原料種別", "メーカー", "ロットNo", "入荷総量", "使用量", "調整量", "現在庫(kg)"]
    
    with t1:
        st.dataframe(inv_df.style.format({"入荷総量":"{:.1f}","使用量":"{:.1f}","調整量":"{:.1f}","現在庫(kg)":"{:.1f}"}), use_container_width=True, height=500)
        
        st.markdown("### 📊 原料種別 合計在庫")
        tot_df = pd.DataFrame(list(type_totals.items()), columns=["原料種別", "現在庫合計(kg)"])
        tot_df["発注点(kg)"] = tot_df["原料種別"].map(lambda x: order_points.get(x, "-"))
        st.dataframe(tot_df, use_container_width=True)

    with t2:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        st.info("棚卸し等で判明した実在庫を入力すると、差分が自動計算されて在庫調整記録に残ります。")
        target_arr = st.selectbox("対象の入荷No・ロット", [f"{v['arrival_no']} ({v['material_type']} / ロット:{v['lot_no']} / 現在:{v['current_kg']:.1f}kg)" for v in inv_list])
        
        if target_arr:
            arr_id = target_arr.split(" ")[0]
            current_val = inventory_data[arr_id]["current_kg"]
            real_val = st.number_input("実在庫 (kg)", value=float(current_val), step=1.0)
            diff = real_val - current_val
            st.write(f"👉 調整量: **{diff:+.1f} kg**")
            reason = st.text_input("調整理由", placeholder="例: 棚卸しによる修正")
            
            if st.button("⚖️ 在庫を調整する", type="primary"):
                append_adjustment({
                    "adj_date": str(date.today()), "arrival_no": arr_id,
                    "lot_no": inventory_data[arr_id]["lot_no"], "material_type": inventory_data[arr_id]["material_type"],
                    "diff_kg": diff, "reason": reason, "registered_at": datetime.now().isoformat()
                })
                st.success("調整を記録しました"); refresh()
        st.markdown('</div>', unsafe_allow_html=True)
        if adjustments:
            st.markdown("##### 過去の調整履歴")
            st.dataframe(pd.DataFrame(adjustments)[::-1].reset_index(drop=True), use_container_width=True)

elif page == "🔍 原料トレース" or page == "📊 集計・分析":
    st.info("※左のメニューからお選びください。（その他の分析機能は既存コードに準拠します）")

elif page == "⚙️ マスター設定":
    st.markdown('<div class="main-header"><h1>⚙️ マスター設定</h1></div>', unsafe_allow_html=True)
    t1, t2, t3, t4 = st.tabs(["🧴 原料", "🏭 メーカー", "👤 担当者", "⚠️ 発注点"])
    with t1:
        mat_text = st.text_area("原料リスト", value="\n".join(materials), height=200)
        if st.button("保存", key="m1"): save_materials([m.strip() for m in mat_text.splitlines() if m.strip()]); fetch_masters.clear(); st.rerun()
    with t2:
        mak_text = st.text_area("メーカーリスト", value="\n".join(makers), height=200)
        if st.button("保存", key="m2"): save_makers([m.strip() for m in mak_text.splitlines() if m.strip()]); fetch_masters.clear(); st.rerun()
    with t3:
        ins_text = st.text_area("担当者リスト", value="\n".join(inspectors), height=200)
        if st.button("保存", key="m3"): save_inspectors([m.strip() for m in ins_text.splitlines() if m.strip()]); fetch_masters.clear(); st.rerun()
    with t4:
        st.info("原料ごとの発注点（安全在庫）を設定します。")
        op_df = pd.DataFrame([{"原料名": m, "発注点(kg)": order_points.get(m, 0.0)} for m in materials])
        edited_op = st.data_editor(op_df, use_container_width=True)
        if st.button("発注点を保存", key="m4"):
            save_order_points({r["原料名"]: r["発注点(kg)"] for _, r in edited_op.iterrows() if float(r["発注点(kg)"]) > 0})
            fetch_masters.clear(); st.rerun()
# --- END OF FILE app.py ---
