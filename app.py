# --- START OF FILE app.py ---
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
from datetime import datetime, date, timedelta

st.set_page_config(page_title="原料管理ERP", page_icon="🧪", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #0f1724 0%, #1a2744 100%); }
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
.main-header { background: linear-gradient(135deg, #1e3a5f 0%, #0d47a1 100%); padding: 20px 28px; border-radius: 12px; margin-bottom: 24px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);}
.main-header h1 { color: #fff; font-size: 1.8rem; margin: 0; font-weight:700;}
.main-header p  { color: #90caf9; font-size: 0.9rem; margin: 4px 0 0; }
.kpi-card { background: #fff; border-radius: 12px; padding: 18px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); border-left: 5px solid #1565c0; text-align: center; }
.kpi-value { font-size: 2.2rem; font-weight: 700; color: #1a237e; line-height: 1.2; }
.kpi-label { font-size: 0.85rem; color: #607d8b; margin-top: 4px; font-weight:500;}
.form-card { background: #fff; border-radius: 12px; padding: 20px; border: 1px solid #e3eaf5; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);}
.section-title { font-size: 1.1rem; font-weight: 700; color: #1a237e; margin: 20px 0 12px; padding-left: 10px; border-left: 4px solid #1565c0; }
.alert-ng { background:#ffebee; border-left:4px solid #c62828; padding:12px 16px; border-radius:8px; color:#b71c1c; font-weight:600; margin-bottom:10px;}
</style>
""", unsafe_allow_html=True)

try:
    from sheets import (load_arrivals, append_arrival, load_brewing, append_brewing, load_adjustments, append_adjustment,
                        load_supplies, save_supplies, load_supply_logs, append_supply_log,
                        load_materials, save_materials, load_makers, save_makers, load_inspectors, save_inspectors,
                        load_order_points, save_order_points, next_arrival_no, next_brewing_no)
    SHEETS_OK = True
except Exception as e:
    SHEETS_OK, SHEETS_ERROR = False, str(e)

with st.sidebar:
    st.markdown("## 🧪 ERP 原料管理")
    if SHEETS_OK: st.success("🟢 データベース接続中")
    else: st.error("🔴 接続エラー")
    st.markdown("---")
    page = st.radio("メニュー", ["🏠 ダッシュボード", "📦 原料入荷記録", "🧪 仕込み記録", "🏭 原料在庫管理", "🧹 資材(備品)在庫管理", "🔍 原料トレース", "📊 集計・分析", "⚙️ マスター設定"], label_visibility="collapsed")
    if st.button("🔄 最新データに更新", use_container_width=True): st.cache_data.clear(); st.rerun()

if not SHEETS_OK: st.error(f"接続エラー: {SHEETS_ERROR}"); st.stop()

@st.cache_data(ttl=60)
def fetch_all(): 
    return (load_arrivals(), load_brewing(), load_adjustments(), load_supplies(), load_supply_logs(), 
            load_materials(), load_makers(), load_inspectors(), load_order_points())

(arrivals, brewing, adjustments, supplies, supply_logs, materials, makers, inspectors, order_points) = fetch_all()

# --- 高速在庫計算（原料） ---
@st.cache_data(ttl=60)
def calc_inventory(arrivals_list, brewing_list, adj_list):
    inv = {a["arrival_no"]: {
        "arrival_no": a["arrival_no"], "lot_no": a["lot_no"], "maker": a["maker"],
        "material_type": a["material_type"], "bags_per_kg": float(a.get("bags_per_kg") or 20.0),
        "total_in_bags": float(a.get("bags") or 0), "total_out_kg": 0.0, "adj_bags": 0.0
    } for a in arrivals_list}
    
    for b in brewing_list:
        for lot_key, kg_key in [("lot_no","material_kg"), ("seaweed_lot","seaweed_kg"), ("starch_lot","starch_kg")]:
            lot_val = b.get(lot_key)
            if lot_val and lot_val != "─":
                m = [k for k, v in inv.items() if v["lot_no"] == lot_val]
                if m: inv[m[0]]["total_out_kg"] += float(b.get(kg_key) or 0)
        
        # ▼ インデントエラー修正箇所 ▼
        if b.get("other_additives"):
            try:
                for o in json.loads(b["other_additives"]):
                    if o.get("lot") and o["lot"] != "─":
                        m = [k for k, v in inv.items() if v["lot_no"] == o["lot"]]
                        if m: inv[m[0]]["total_out_kg"] += float(o.get("kg") or 0)
            except:
                pass
            
    for adj in adj_list:
        if adj["arrival_no"] in inv: 
            inv[adj["arrival_no"]]["adj_bags"] += float(adj.get("diff_bags") or adj.get("diff_kg") or 0)
            
    for v in inv.values(): 
        b_per_kg = v["bags_per_kg"] if v["bags_per_kg"] > 0 else 20.0
        v["total_out_bags"] = v["total_out_kg"] / b_per_kg
        v["current_bags"] = v["total_in_bags"] - v["total_out_bags"] + v["adj_bags"]
    return inv

# --- 資材（備品）の在庫計算 ---
@st.cache_data(ttl=60)
def calc_supply_inventory(sup_list, log_list):
    inv = {s["supply_id"]: {
        "image_url": s.get("image_url", "https://cdn-icons-png.flaticon.com/512/1243/1243324.png"), # 代替画像
        "name": s["name"], "category": s.get("category", ""), 
        "initial": float(s.get("initial_stock") or 0), "in_out": 0.0
    } for s in sup_list if s.get("supply_id")}
    
    for lg in log_list:
        sid = lg.get("supply_id")
        if sid in inv:
            amt = float(lg.get("amount") or 0)
            if "入荷" in lg.get("action_type", ""): inv[sid]["in_out"] += amt
            else: inv[sid]["in_out"] -= amt
            
    res = []
    for sid, v in inv.items():
        v["supply_id"] = sid
        v["current_stock"] = v["initial"] + v["in_out"]
        res.append(v)
    return res

inventory_data = calc_inventory(arrivals, brewing, adjustments)
supply_inventory = calc_supply_inventory(supplies, supply_logs)

type_totals = {}
for v in inventory_data.values(): type_totals[v["material_type"]] = type_totals.get(v["material_type"], 0) + v["current_bags"]
alerts = [f"⚠️ 【原料発注アラート】 {m} の在庫（{c:,.1f}袋）が発注点（{order_points[m]:,.1f}袋）を下回っています！" for m, c in type_totals.items() if m in order_points and c < order_points[m]]

# ════════════════════════════════════════════════════════════════
if page == "🏠 ダッシュボード":
    st.markdown('<div class="main-header"><h1>📊 ERP ダッシュボード</h1><p>工場の稼働状況・在庫・アラートをリアルタイムで把握します</p></div>', unsafe_allow_html=True)
    if alerts:
        for al in alerts: st.markdown(f'<div class="alert-ng">{al}</div>', unsafe_allow_html=True)
    
    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(f'<div class="kpi-card"><div class="kpi-value">{len([b for b in brewing if b.get("brew_date")==str(date.today())])}</div><div class="kpi-label">本日の仕込み回数</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-card"><div class="kpi-value">{sum(float(b.get("brew_amount") or 0) for b in brewing if b.get("brew_date", "") >= str(date.today() - timedelta(days=7))):,.0f}</div><div class="kpi-label">直近7日 仕込量(kg)</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-card"><div class="kpi-value">{sum(v["current_bags"] for v in inventory_data.values()):,.0f}</div><div class="kpi-label">全原料 総在庫(袋)</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi-card"><div class="kpi-value" style="color:#d32f2f;">{len(alerts)}</div><div class="kpi-label">要発注アラート数</div></div>', unsafe_allow_html=True)

elif page == "📦 原料入荷記録":
    st.markdown('<div class="main-header"><h1>📦 原料入荷記録</h1><p>原料の入荷と品質検査の記録</p></div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["➕ 新規入荷登録", "📋 入荷履歴"])
    with t1:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        c1,c2,c3 = st.columns(3)
        new_no = next_arrival_no(arrivals)
        c1.text_input("入荷No", value=new_no, disabled=True)
        a_date = c2.date_input("入荷日")
        maker = c3.selectbox("メーカー", makers + ["その他"])
        if maker == "その他": maker = st.text_input("メーカー直接入力")
        
        c4,c5,c6 = st.columns(3)
        lot_no = c4.text_input("ロットNo ＊")
        m_type = c5.selectbox("原料種別", materials)
        bags = c6.number_input("袋数", min_value=0, step=1)
        b_per = st.number_input("1袋重量(kg)", value=20.0, step=0.5)
        st.info(f"📦 自動計算 総量: **{bags * b_per:,.1f} kg**")
        st.markdown('</div><div class="form-card"><div class="section-title">🔍 品質検査</div>', unsafe_allow_html=True)
        
        # 検査項目の拡張
        ck1, ck2 = st.columns(2)
        app    = ck1.selectbox("① 外観検査", ["OK（正常）", "NG（異常あり）", "要確認"])
        c_name = ck1.selectbox("② 品名・規格確認", ["OK（一致）", "NG（不一致）"])
        c_exp  = ck2.selectbox("③ 賞味・消費期限", ["OK（期限内）", "NG（期限外・不明）"])
        c_dmg  = ck2.selectbox("④ 異物・破損確認", ["OK（なし）", "NG（あり）"])
        
        has_ng = any("NG" in x for x in [app, c_name, c_exp, c_dmg])
        abn = st.text_input("⚠️ 異常内容（NG時）", placeholder="異常があれば詳細を記入") if has_ng else ""
        
        ins = st.selectbox("担当者 ＊", inspectors)
        rem = st.text_input("備考")
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("✅ 入荷記録を保存", type="primary", use_container_width=True):
            if not lot_no: st.error("ロットNoは必須です")
            else:
                append_arrival({"arrival_no": new_no, "arrival_date": str(a_date), "maker": maker, "lot_no": lot_no,
                                "material_type": m_type, "bags": bags, "bags_per_kg": b_per, "total_kg": bags * b_per,
                                "appearance": app, "check_name_std": c_name, "expiry_check": c_exp, "contamination": c_dmg,
                                "abnormal_detail": abn, "inspector": ins, "remarks": rem, "registered_at": datetime.now().isoformat()})
                st.cache_data.clear(); st.rerun()
    with t2:
        if arrivals:
            st.dataframe(pd.DataFrame(arrivals)[["arrival_no", "arrival_date", "maker", "lot_no", "material_type", "bags", "appearance", "inspector"]][::-1].reset_index(drop=True), use_container_width=True, height=500)

elif page == "🧪 仕込み記録":
    # (既存の仕込み記録のコード。省略せずに全て記載)
    st.markdown('<div class="main-header"><h1>🧪 仕込み記録</h1><p>品名と使用した各原料ロットの紐付け</p></div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["➕ 新規仕込み登録", "📋 仕込み履歴"])
    with t1:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        c1,c2,c3 = st.columns(3)
        b_date = c1.date_input("仕込日")
        p_name = c2.text_input("品名 ＊")
        b_maker = c3.selectbox("メーカー", makers)
        all_lots = {a["material_type"]: [] for a in arrivals}
        for a in arrivals: all_lots[a["material_type"]].append(a["lot_no"])
        def get_lots(kw): 
            lts = []
            for k, v in all_lots.items():
                if kw in k: lts.extend(v)
            return ["─"] + sorted(list(set(lts)), reverse=True)
        c4, c5 = st.columns(2)
        lot_no_b = c4.selectbox("主原料（精粉）ロットNo ＊", get_lots("精粉"))
        b_amount = c5.number_input("仕込量(kg) ＊", min_value=0.0, value=None, step=10.0)
        st.markdown('</div><div class="form-card"><div class="section-title">⚗️ 基本原料</div>', unsafe_allow_html=True)
        c6,c7,c8 = st.columns(3)
        mat_kg = c6.number_input("精粉 使用量(kg)", min_value=0.0, value=None, format="%.2f")
        sea_lot = c6.selectbox("海藻粉 ロット", get_lots("海藻"))
        sea_kg = c6.number_input("海藻粉 使用量(kg)", min_value=0.0, value=None, format="%.2f")
        sta_lot = c7.selectbox("加工デンプン ロット", get_lots("デンプン"))
        sta_kg = c7.number_input("デンプン 使用量(kg)", min_value=0.0, value=None, format="%.2f")
        sta_type = c7.selectbox("デンプン種別", ["─","ゆり8","VA70","その他"])
        lime_kg = c8.number_input("石灰(kg)", min_value=0.0, value=None, format="%.2f")
        lime_w = c8.number_input("石灰水(ℓ)", min_value=0.0, value=None, format="%.1f")
        st.markdown('</div><div class="form-card"><div class="section-title">🧂 その他添加物</div>', unsafe_allow_html=True)
        if "other_rows" not in st.session_state: st.session_state.other_rows = []
        for i, row in enumerate(st.session_state.other_rows):
            oc1, oc2, oc3, oc4 = st.columns([3,3,2,1])
            sel_mat = oc1.selectbox("原料名", materials, key=f"mat_{i}", index=materials.index(row["name"]) if row["name"] in materials else 0)
            avail_lots = ["─"] + sorted(list(set([a["lot_no"] for a in arrivals if a["material_type"] == sel_mat])), reverse=True)
            sel_lot = oc2.selectbox("ロットNo", avail_lots, key=f"lot_{i}")
            sel_kg = oc3.number_input("使用量(kg)", min_value=0.0, format="%.2f", key=f"kg_{i}")
            if oc4.button("❌", key=f"del_{i}"): st.session_state.other_rows.pop(i); st.rerun()
            st.session_state.other_rows[i] = {"name": sel_mat, "lot": sel_lot, "kg": sel_kg}
        if st.button("➕ 添加物を追加"): st.session_state.other_rows.append({"name": materials[0], "lot": "─", "kg": 0.0}); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        if st.button("✅ 仕込み記録を保存", type="primary", use_container_width=True):
            if not p_name or lot_no_b == "─" or not b_amount: st.error("品名、主ロット、仕込量は必須です")
            else:
                others_json = json.dumps([r for r in st.session_state.other_rows if r["kg"] > 0], ensure_ascii=False)
                append_brewing({
                    "no": next_brewing_no(brewing), "brew_date": str(b_date), "product_name": p_name,
                    "maker": b_maker, "lot_no": lot_no_b, "seaweed_lot": sea_lot, "starch_lot": sta_lot,
                    "brew_amount": b_amount, "material_kg": mat_kg or 0, "seaweed_kg": sea_kg or 0,
                    "starch_kg": sta_kg or 0, "starch_type": sta_type, "lime_kg": lime_kg or 0, "lime_water_l": lime_w or 0,
                    "other_additives": others_json, "registered_at": datetime.now().isoformat()
                })
                st.session_state.other_rows = []
                st.cache_data.clear(); st.rerun()
    with t2:
        if brewing: st.dataframe(pd.DataFrame(brewing)[["no","brew_date","product_name","lot_no","brew_amount","material_kg"]][::-1].reset_index(drop=True), use_container_width=True, height=500)

elif page == "🏭 原料在庫管理":
    st.markdown('<div class="main-header"><h1>🏭 原料在庫管理</h1><p>自動計算された現在庫（袋単位）と棚卸し調整</p></div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["📋 現在庫一覧", "⚖️ 在庫ズレ調整"])
    with t1:
        inv_df = pd.DataFrame(list(inventory_data.values()))[["arrival_no", "material_type", "lot_no", "total_in_bags", "total_out_bags", "adj_bags", "current_bags"]]
        inv_df.columns = ["入荷No", "原料種別", "ロットNo", "入荷(袋)", "使用(袋)", "調整(袋)", "現在庫(袋)"]
        st.dataframe(inv_df, column_config={"入荷(袋)": st.column_config.NumberColumn(format="%.1f"), "使用(袋)": st.column_config.NumberColumn(format="%.1f"), "調整(袋)": st.column_config.NumberColumn(format="%.1f"), "現在庫(袋)": st.column_config.NumberColumn(format="%.1f")}, use_container_width=True, height=400)
    with t2:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        target_arr = st.selectbox("対象ロット", [f"{v['arrival_no']} ({v['material_type']} / ロット:{v['lot_no']} / 現在庫:{v['current_bags']:.1f}袋)" for v in inventory_data.values()])
        if target_arr:
            arr_id = target_arr.split(" ")[0]
            real_val = st.number_input("実在庫 (袋)", value=float(inventory_data[arr_id]["current_bags"]), step=1.0)
            diff = real_val - inventory_data[arr_id]["current_bags"]
            st.write(f"👉 調整量: **{diff:+.1f} 袋**")
            reason = st.text_input("調整理由")
            if st.button("⚖️ 在庫を調整する", type="primary"):
                append_adjustment({"adj_date": str(date.today()), "arrival_no": arr_id, "lot_no": inventory_data[arr_id]["lot_no"], "material_type": inventory_data[arr_id]["material_type"], "diff_bags": diff, "reason": reason, "registered_at": datetime.now().isoformat()})
                st.cache_data.clear(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

elif page == "🧹 資材(備品)在庫管理":
    st.markdown('<div class="main-header"><h1>🧹 資材・衛生備品 管理</h1><p>スマホ対応：写真を見ながら簡単に入出庫記録ができます</p></div>', unsafe_allow_html=True)
    
    # スマホ向け：一番上に「入力フォーム」を固定配置
    st.markdown('<div class="form-card" style="border-left: 5px solid #ff9800;">', unsafe_allow_html=True)
    st.markdown('#### 📝 入出庫 登録フォーム')
    
    if not supplies:
        st.warning("資材マスターが登録されていません。「⚙️ マスター設定」から追加してください。")
    else:
        sc1, sc2 = st.columns([2, 1])
        sup_sel = sc1.selectbox("資材を選択", [s["name"] for s in supplies])
        act_sel = sc2.selectbox("処理", ["➖ 使用する (出庫)", "➕ 補充する (入荷)"])
        
        sc3, sc4 = st.columns([2, 1])
        amt_val = sc3.number_input("数量（個/セット）", min_value=1, step=1)
        ins_sel = sc4.selectbox("作業者", inspectors)
        
        if st.button("✅ 記録を保存", type="primary", use_container_width=True):
            target_id = next(s["supply_id"] for s in supplies if s["name"] == sup_sel)
            append_supply_log({
                "date": str(date.today()), "supply_id": target_id, "action_type": "入荷" if "➕" in act_sel else "使用",
                "amount": amt_val, "inspector": ins_sel, "note": "", "registered_at": datetime.now().isoformat()
            })
            st.success(f"{sup_sel} を {amt_val}個 {act_sel.split(' ')[1]}しました！")
            st.cache_data.clear(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # スマホ向け：写真付き在庫一覧
    st.markdown('### 📦 写真付き 現在庫一覧')
    if supply_inventory:
        df_sup = pd.DataFrame(supply_inventory)[["image_url", "name", "category", "current_stock"]]
        st.dataframe(
            df_sup,
            column_config={
                "image_url": st.column_config.ImageColumn("画像", help="資材の写真"),
                "name": "資材名",
                "category": "カテゴリ",
                "current_stock": st.column_config.NumberColumn("現在庫", format="%d")
            },
            use_container_width=True, hide_index=True, height=500
        )
    else:
        st.info("データがありません")

elif page == "🔍 原料トレース" or page == "📊 集計・分析":
    st.info("左メニューからお選びください。（トレース・集計は既存機能のまま稼働します）")

elif page == "⚙️ マスター設定":
    st.markdown('<div class="main-header"><h1>⚙️ マスター設定</h1></div>', unsafe_allow_html=True)
    t1, t2, t3, t4, t5 = st.tabs(["🧴 原料", "🏭 メーカー", "👤 担当者", "⚠️ 発注点", "🧹 資材(備品)登録"])
    with t1:
        m1 = st.text_area("原料リスト (1行1件)", "\n".join(materials), height=200)
        if st.button("保存", key="b1"): save_materials([x.strip() for x in m1.splitlines() if x.strip()]); st.cache_data.clear(); st.rerun()
    with t2:
        m2 = st.text_area("メーカーリスト", "\n".join(makers), height=200)
        if st.button("保存", key="b2"): save_makers([x.strip() for x in m2.splitlines() if x.strip()]); st.cache_data.clear(); st.rerun()
    with t3:
        m3 = st.text_area("担当者リスト", "\n".join(inspectors), height=200)
        if st.button("保存", key="b3"): save_inspectors([x.strip() for x in m3.splitlines() if x.strip()]); st.cache_data.clear(); st.rerun()
    with t4:
        st.info("原料ごとの発注点（袋数）を設定")
        op_df = pd.DataFrame([{"原料名": m, "発注点(袋)": order_points.get(m, 0.0)} for m in materials])
        e_op = st.data_editor(op_df, use_container_width=True)
        if st.button("保存", key="b4"):
            save_order_points({r["原料名"]: r["発注点(袋)"] for _, r in e_op.iterrows() if float(r["発注点(袋)"]) > 0})
            st.cache_data.clear(); st.rerun()
    with t5:
        st.info("衛生備品や梱包資材などのマスター登録を行います（画像URLはネット上の画像リンクを貼ってください）")
        sup_df = pd.DataFrame(supplies) if supplies else pd.DataFrame(columns=SUPPLY_COLS)
        e_sup = st.data_editor(sup_df, num_rows="dynamic", use_container_width=True)
        if st.button("資材マスター保存", key="b5"):
            save_supplies(e_sup.to_dict("records"))
            st.cache_data.clear(); st.rerun()
# --- END OF FILE app.py ---
