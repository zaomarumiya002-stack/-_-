# --- START OF FILE app.py ---
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
from datetime import datetime, date, timedelta
import traceback

# 画像処理用ライブラリ
try:
    from PIL import Image
    import base64
    from io import BytesIO
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

st.set_page_config(page_title="原料管理ERP", page_icon="🏭", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');
*, html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }
section[data-testid="stSidebar"] { background: #0f172a !important; border-right: 1px solid #1e293b; }
section[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
.main-header { display:flex; align-items:center; gap:14px; background: linear-gradient(135deg,#1e3a5f,#1565c0); padding:18px 24px; border-radius:14px; margin-bottom:22px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);}
.main-header h1 { color:#fff; font-size:1.6rem; font-weight:700; margin:0; }
.main-header p  { color:#90caf9; font-size:0.85rem; margin:3px 0 0; }
.kpi-card { background:#fff; border-radius:12px; padding:16px 18px; box-shadow:0 1px 6px rgba(0,0,0,.07); border-top:3px solid #1565c0; text-align:center; }
.kpi-value { font-size:2rem; font-weight:700; color:#1a237e; line-height:1.15; }
.kpi-label { font-size:.8rem; color:#78909c; margin-top:4px; font-weight:500;}
.alert-ng { background:#fff3f3; border:1px solid #ffcdd2; border-left:4px solid #e53935; padding:10px 14px; border-radius:8px; color:#b71c1c; font-size:.88rem; font-weight:600; margin-bottom:8px; }
.form-card { background:#f8faff; border:1px solid #dde6f5; border-radius:12px; padding:18px 20px; margin-bottom:14px; }
.section-title { font-size:1rem; font-weight:700; color:#1a237e; border-left:4px solid #1565c0; padding-left:10px; margin:18px 0 10px; }
</style>
""", unsafe_allow_html=True)

try:
    from sheets import (
        load_arrivals, append_arrival, update_arrival, load_brewing, append_brewing, update_brewing,
        load_adjustments, append_adjustment, load_supplies, save_supplies, load_supply_logs, append_supply_log,
        load_materials, save_materials, load_makers, save_makers, load_inspectors, save_inspectors,
        load_order_points, save_order_points, next_arrival_no, next_brewing_no
    )
    SHEETS_OK = True
except Exception as e:
    st.error(f"🚨 システム起動エラー\n\n```\n{traceback.format_exc()}\n```")
    st.stop()

def refresh():
    st.cache_data.clear()
    st.rerun()

with st.sidebar:
    st.markdown("### 🏭 原料管理 ERP")
    st.markdown('<span style="color:#4caf50;font-size:.8rem">● データベース接続中</span>', unsafe_allow_html=True)
    st.markdown("---")
    page = st.radio("", ["🏠 ダッシュボード", "📦 入荷記録", "🧪 仕込み記録", "🏭 原料在庫", "🧹 資材在庫", "🔍 双方向トレース", "📊 生産分析", "⚙️ マスター設定"], label_visibility="collapsed")
    if st.button("🔄 データ手動更新", use_container_width=True): refresh()
    st.caption(f"最終読込: {datetime.now().strftime('%H:%M')}")

# ── データのキャッシュ（反映速度向上のため60秒に変更） ──
@st.cache_data(ttl=60)
def fetch_all(): 
    return (load_arrivals(), load_brewing(), load_adjustments(), load_supplies(), load_supply_logs(), 
            load_materials(), load_makers(), load_inspectors(), load_order_points())

try:
    (arrivals, brewing, adjustments, supplies, supply_logs, materials, makers, inspectors, order_points) = fetch_all()
except Exception as e:
    st.error(f"🚨 データ取得エラー\n\n```\n{traceback.format_exc()}\n```")
    st.stop()

@st.cache_data(ttl=60)
def calc_inventory(arr_t, brew_t, adj_t):
    if not arr_t: return {}
    inv = {a["arrival_no"]: {
        "arrival_no": a["arrival_no"], "lot_no": a["lot_no"], "maker": a["maker"],
        "material_type": a["material_type"], "bags_per_kg": float(a.get("bags_per_kg") or 20.0),
        "total_in_bags": float(a.get("bags") or 0), "total_out_kg": 0.0, "adj_bags": 0.0
    } for a in arr_t}
    
    lot_to_arr = {str(a.get("lot_no", "")).strip(): a["arrival_no"] for a in arr_t if str(a.get("lot_no", "")).strip()}
    def _deduct(lot_str, kg):
        lot_str = str(lot_str).strip()
        if not lot_str or lot_str == "─": return
        if lot_str in inv: inv[lot_str]["total_out_kg"] += float(kg or 0)
        elif lot_str in lot_to_arr: inv[lot_to_arr[lot_str]]["total_out_kg"] += float(kg or 0)

    for b in brew_t:
        _deduct(b.get("lot_no"), b.get("material_kg"))
        _deduct(b.get("seaweed_lot"), b.get("seaweed_kg"))
        _deduct(b.get("starch_lot"), b.get("starch_kg"))
        if b.get("other_additives"):
            try:
                for o in json.loads(b["other_additives"]): _deduct(o.get("lot"), o.get("kg"))
            except: pass

    for adj in adj_t:
        ano = adj.get("arrival_no")
        if ano in inv: inv[ano]["adj_bags"] += float(adj.get("diff_bags") or 0)
        
    for v in inv.values():
        bpk = v["bags_per_kg"] if v["bags_per_kg"] > 0 else 20.0
        v["total_out_bags"] = v["total_out_kg"] / bpk
        v["current_bags"] = v["total_in_bags"] - v["total_out_bags"] + v["adj_bags"]
        v["current_kg"] = v["current_bags"] * bpk
    return inv

@st.cache_data(ttl=60)
def calc_supply_inv(sup_t, log_t):
    if not sup_t: return []
    inv = {s["supply_id"]: {**s, "initial": float(s.get("initial_stock") or 0), "in_out": 0.0} for s in sup_t if s.get("supply_id")}
    for lg in log_t:
        sid = lg.get("supply_id")
        if sid in inv:
            amt = float(lg.get("amount") or 0)
            inv[sid]["in_out"] += amt if "入荷" in lg.get("action_type", "") else -amt
    res = []
    for sid, v in inv.items():
        v["current_stock"] = v["initial"] + v["in_out"]
        res.append(v)
    return res

inventory_data = calc_inventory(arrivals, brewing, adjustments)
supply_inventory = calc_supply_inv(supplies, supply_logs)

type_totals = {}
for v in inventory_data.values(): type_totals[v["material_type"]] = type_totals.get(v["material_type"], 0) + v["current_bags"]
alerts = [f"⚠️ {m}：在庫 {c:,.1f}袋 ＜ 発注点 {order_points[m]:,.1f}袋" for m, c in type_totals.items() if m in order_points and c < order_points[m]]

# ════════════════════════════════════════════════════════════════
if page == "🏠 ダッシュボード":
    st.markdown('<div class="main-header"><div><h1>📊 ERP ダッシュボード</h1><p>工場の稼働状況・在庫・アラートをリアルタイムで把握します</p></div></div>', unsafe_allow_html=True)
    if alerts:
        for al in alerts: st.markdown(f'<div class="alert-ng">{al}</div>', unsafe_allow_html=True)
    
    c1,c2,c3,c4 = st.columns(4)
    week_brew = [b for b in brewing if str(b.get("brew_date", "")) >= str(date.today() - timedelta(days=7))]
    c1.markdown(f'<div class="kpi-card"><div class="kpi-value">{len([b for b in brewing if str(b.get("brew_date"))==str(date.today())])}</div><div class="kpi-label">本日の仕込み回数</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-card"><div class="kpi-value">{sum(float(b.get("brew_amount") or 0) for b in week_brew):,.0f}</div><div class="kpi-label">直近7日 仕込量(kg)</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-card"><div class="kpi-value">{sum(max(v["current_bags"],0) for v in inventory_data.values()):,.0f}</div><div class="kpi-label">全原料 総在庫(袋)</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi-card" style="border-top-color:#e53935;"><div class="kpi-value" style="color:#c62828;">{len(alerts)}</div><div class="kpi-label">要発注アラート</div></div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
elif page == "📦 入荷記録":
    st.markdown('<div class="main-header"><div><h1>📦 原料入荷記録</h1><p>入荷時の品質検査と担当者記録</p></div></div>', unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["➕ 新規登録", "📋 履歴一覧", "✏️ 既存データ編集"])
    
    with t1:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        c1,c2,c3 = st.columns(3)
        new_no = next_arrival_no(arrivals)
        c1.text_input("入荷No", value=new_no, disabled=True, key="new_arr_no")
        a_date = c2.date_input("入荷日", key="new_arr_date")
        maker = c3.selectbox("メーカー", makers + ["その他"], key="new_arr_maker")
        if maker == "その他": maker = st.text_input("メーカー直接入力", key="new_arr_maker_free")
        
        c4,c5,c6 = st.columns(3)
        lot_no = c4.text_input("ロットNo ＊", key="new_arr_lot")
        m_type = c5.selectbox("原料種別", materials, key="new_arr_mat")
        bags = c6.number_input("袋数", min_value=0, step=1, value=None, key="new_arr_bags")
        b_per = st.number_input("1袋重量(kg)", value=20.0, step=0.5, key="new_arr_bper")
        st.markdown('</div><div class="form-card"><div class="section-title">🔍 品質検査</div>', unsafe_allow_html=True)
        
        ck1, ck2 = st.columns(2)
        app    = ck1.selectbox("① 外観検査", ["OK（正常）", "NG（異常あり）", "要確認"], key="new_arr_app")
        c_name = ck1.selectbox("② 品名・規格確認", ["OK（一致）", "NG（不一致）"], key="new_arr_name")
        c_exp  = ck2.selectbox("③ 賞味・消費期限", ["OK（期限内）", "NG（期限外・不明）"], key="new_arr_exp")
        c_dmg  = ck2.selectbox("④ 異物・破損確認", ["OK（なし）", "NG（あり）"], key="new_arr_dmg")
        
        abn = st.text_input("⚠️ 異常内容（NG時）", placeholder="詳細を記入", key="new_arr_abn") if any("NG" in x for x in [app, c_name, c_exp, c_dmg]) else ""
        ins = st.selectbox("担当者 ＊", inspectors, key="new_arr_ins")
        rem = st.text_input("備考", key="new_arr_rem")
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("✅ 入荷記録を保存", type="primary", use_container_width=True, key="save_arr_btn"):
            if not lot_no: st.error("ロットNoは必須です")
            else:
                append_arrival({
                    "arrival_no": new_no, "arrival_date": str(a_date), "maker": maker, "lot_no": lot_no,
                    "material_type": m_type, "bags": bags or 0, "bags_per_kg": b_per, "total_kg": (bags or 0) * b_per,
                    "appearance": app, "check_name_std": c_name, "expiry_check": c_exp, "contamination": c_dmg,
                    "abnormal_detail": abn, "inspector": ins, "remarks": rem, "registered_at": datetime.now().isoformat()
                })
                st.success("保存しました！"); refresh()

    with t2:
        if arrivals: st.dataframe(pd.DataFrame(arrivals)[["arrival_no", "arrival_date", "maker", "lot_no", "material_type", "bags", "appearance", "inspector"]][::-1].reset_index(drop=True), use_container_width=True, height=500)

    with t3:
        if not arrivals: st.info("データなし")
        else:
            st.markdown('<div class="form-card">', unsafe_allow_html=True)
            edit_target = st.selectbox("編集する入荷Noを選択", [a["arrival_no"] for a in reversed(arrivals)], key="edit_arr_sel")
            if edit_target:
                td = next((a for a in arrivals if a["arrival_no"] == edit_target), None)
                e_date = st.text_input("入荷日", value=td.get("arrival_date",""), key="ea_date")
                e_maker = st.text_input("メーカー", value=td.get("maker",""), key="ea_maker")
                e_lot = st.text_input("ロットNo", value=td.get("lot_no",""), key="ea_lot")
                e_mat = st.selectbox("原料種別", materials, index=materials.index(td["material_type"]) if td.get("material_type") in materials else 0, key="ea_mat")
                e_bags = st.number_input("袋数", value=int(td.get("bags") or 0), key="ea_bags")
                if st.button("💾 変更を上書き保存", type="primary", key="ea_save"):
                    td.update({"arrival_date": e_date, "maker": e_maker, "lot_no": e_lot, "material_type": e_mat, "bags": e_bags})
                    update_arrival(td["arrival_no"], td); st.success("更新しました！"); refresh()
            st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
elif page == "🧪 仕込み記録":
    st.markdown('<div class="main-header"><div><h1>🧪 仕込み記録</h1><p>品目別の原料使用量と仕込み量</p></div></div>', unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["➕ 新規登録", "📋 履歴一覧", "✏️ 既存データ編集"])
    
    def get_lots_by_type(mat_type):
        lts = [a["lot_no"] for a in arrivals if mat_type in a.get("material_type","") and str(a.get("lot_no")).strip()]
        return ["─"] + sorted(list(set(lts)), reverse=True)
    
    with t1:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        c1,c2,c3 = st.columns(3)
        b_date = c1.date_input("仕込日", key="new_brw_date")
        p_name = c2.text_input("品名 ＊", key="new_brw_name")
        b_maker = c3.selectbox("メーカー", makers, key="new_brw_maker")
        c4, c5 = st.columns(2)
        lot_no_b = c4.selectbox("主原料（精粉）ロットNo ＊", get_lots_by_type("精粉"), key="new_brw_lot")
        b_amount = c5.number_input("仕込量(kg) ＊", min_value=0.0, value=None, step=10.0, key="new_brw_amt")
        st.markdown('</div><div class="form-card"><div class="section-title">⚗️ 基本原料</div>', unsafe_allow_html=True)
        
        c6,c7,c8 = st.columns(3)
        mat_kg = c6.number_input("精粉 使用量(kg)", min_value=0.0, value=None, format="%.2f", key="new_brw_mkg")
        sea_lot = c6.selectbox("海藻粉 ロット", get_lots_by_type("海藻"), key="new_brw_sl")
        sea_kg = c6.number_input("海藻粉 使用量(kg)", min_value=0.0, value=None, format="%.2f", key="new_brw_skg")
        
        sta_lot = c7.selectbox("加工デンプン ロット", get_lots_by_type("デンプン"), key="new_brw_stl")
        sta_kg = c7.number_input("デンプン 使用量(kg)", min_value=0.0, value=None, format="%.2f", key="new_brw_stkg")
        sta_type = c7.selectbox("デンプン種別", ["─","ゆり8","VA70","その他"], key="new_brw_stt")
        
        lime_kg = c8.number_input("石灰(kg)", min_value=0.0, value=None, format="%.2f", key="new_brw_lkg")
        lime_w = c8.number_input("石灰水(ℓ)", min_value=0.0, value=None, format="%.1f", key="new_brw_lw")
        st.markdown('</div><div class="form-card"><div class="section-title">🧂 その他添加物</div>', unsafe_allow_html=True)
        
        if "other_rows" not in st.session_state: st.session_state.other_rows = []
        for i, row in enumerate(st.session_state.other_rows):
            oc1, oc2, oc3, oc4 = st.columns([3,3,2,1])
            sel_mat = oc1.selectbox("原料名", materials, key=f"mat_{i}", index=materials.index(row["name"]) if row["name"] in materials else 0)
            avail_lots = ["─"] + sorted(list(set([a["lot_no"] for a in arrivals if a.get("material_type") == sel_mat and str(a.get("lot_no")).strip()])), reverse=True)
            sel_lot = oc2.selectbox("ロットNo", avail_lots, key=f"lot_{i}")
            sel_kg = oc3.number_input("使用量(kg)", min_value=0.0, format="%.2f", key=f"kg_{i}", value=float(row["kg"]) if row["kg"] else None)
            
            if oc4.button("❌", key=f"del_{i}"): 
                st.session_state.other_rows.pop(i); st.rerun()
            st.session_state.other_rows[i] = {"name": sel_mat, "lot": sel_lot, "kg": sel_kg or 0.0}
            
        if st.button("➕ 添加物を追加", key="add_oth"): 
            st.session_state.other_rows.append({"name": materials[0], "lot": "─", "kg": 0.0}); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("✅ 仕込み記録を保存", type="primary", use_container_width=True, key="save_brw_btn"):
            if not p_name or lot_no_b == "─" or not b_amount: 
                st.error("品名、主ロット、仕込量は必須です")
            else:
                others_json = json.dumps([r for r in st.session_state.other_rows if r["kg"] > 0], ensure_ascii=False)
                append_brewing({
                    "no": next_brewing_no(brewing), "brew_date": str(b_date), "product_name": p_name, "maker": b_maker, 
                    "lot_no": lot_no_b, "seaweed_lot": sea_lot, "starch_lot": sta_lot, 
                    "brew_amount": b_amount or 0.0, "material_kg": mat_kg or 0.0, "seaweed_kg": sea_kg or 0.0, 
                    "starch_kg": sta_kg or 0.0, "starch_type": sta_type, "lime_kg": lime_kg or 0.0, "lime_water_l": lime_w or 0.0, 
                    "other_additives": others_json, "registered_at": datetime.now().isoformat()
                })
                st.session_state.other_rows = []
                st.success("保存しました！"); refresh()

    with t2:
        if brewing: st.dataframe(pd.DataFrame(brewing)[["no","brew_date","product_name","lot_no","seaweed_lot","starch_lot","brew_amount"]][::-1].reset_index(drop=True), use_container_width=True, height=500)

    with t3:
        if not brewing: st.info("データなし")
        else:
            st.markdown('<div class="form-card">', unsafe_allow_html=True)
            edit_target_b = st.selectbox("編集する仕込Noを選択", [f"{b['no']} - {b['product_name']}" for b in reversed(brewing)], key="edit_brw_sel")
            if edit_target_b:
                t_no = edit_target_b.split(" - ")[0]
                td = next((b for b in brewing if str(b["no"]) == str(t_no)), None)
                eb_name = st.text_input("品名", value=td.get("product_name",""), key="eb_name")
                eb_lot = st.text_input("主原料ロットNo", value=td.get("lot_no",""), key="eb_lot")
                eb_amt = st.number_input("仕込量(kg)", value=float(td.get("brew_amount") or 0), key="eb_amt")
                eb_mat = st.number_input("精粉(kg)", value=float(td.get("material_kg") or 0), key="eb_mat")
                if st.button("💾 変更を上書き保存", type="primary", key="eb_save"):
                    td.update({"product_name": eb_name, "lot_no": eb_lot, "brew_amount": eb_amt, "material_kg": eb_mat})
                    update_brewing(td["no"], td); st.success("更新しました！"); refresh()
            st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
elif page == "🏭 原料在庫":
    st.markdown('<div class="main-header"><div><h1>🏭 原料在庫管理</h1><p>自動計算された現在庫（袋単位）と棚卸し調整</p></div></div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["📋 現在庫一覧", "⚖️ 在庫ズレ調整"])
    with t1:
        if not inventory_data: st.info("データなし")
        else:
            inv_df = pd.DataFrame(list(inventory_data.values()))[["arrival_no", "material_type", "lot_no", "total_in_bags", "total_out_bags", "adj_bags", "current_bags"]]
            inv_df.columns = ["入荷No", "原料種別", "ロットNo", "入荷(袋)", "使用(袋)", "調整(袋)", "現在庫(袋)"]
            st.dataframe(inv_df, column_config={"入荷(袋)": st.column_config.NumberColumn(format="%.1f"), "使用(袋)": st.column_config.NumberColumn(format="%.1f"), "調整(袋)": st.column_config.NumberColumn(format="%.1f"), "現在庫(袋)": st.column_config.NumberColumn(format="%.1f")}, use_container_width=True, height=400)
    with t2:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        if inventory_data:
            target_arr = st.selectbox("対象ロット", [f"{v['arrival_no']} ({v['material_type']} / ロット:{v['lot_no']} / 現在庫:{v['current_bags']:.1f}袋)" for v in inventory_data.values()], key="adj_sel")
            if target_arr:
                arr_id = target_arr.split(" ")[0]
                real_val = st.number_input("実在庫 (袋)", value=float(inventory_data[arr_id]["current_bags"]), step=1.0, key="adj_val")
                diff = real_val - inventory_data[arr_id]["current_bags"]
                st.write(f"👉 調整量: **{diff:+.1f} 袋**")
                reason = st.text_input("調整理由", key="adj_rsn")
                if st.button("⚖️ 在庫を調整する", type="primary", key="adj_btn"):
                    append_adjustment({"adj_date": str(date.today()), "arrival_no": arr_id, "lot_no": inventory_data[arr_id]["lot_no"], "material_type": inventory_data[arr_id]["material_type"], "diff_bags": diff, "reason": reason, "registered_at": datetime.now().isoformat()})
                    st.success("記録しました！"); refresh()
        st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
elif page == "🧹 資材在庫":
    st.markdown('<div class="main-header"><div><h1>🧹 資材・衛生備品 管理</h1><p>スマホ対応：写真を見ながら簡単に入出庫記録ができます</p></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="form-card" style="border-left: 5px solid #ff9800;">', unsafe_allow_html=True)
    if not supplies: st.warning("資材マスターが未登録です")
    else:
        sc1, sc2 = st.columns([2, 1])
        sup_sel = sc1.selectbox("資材を選択", [s["name"] for s in supplies], key="sup_sel")
        act_sel = sc2.selectbox("処理", ["➖ 使用する (出庫)", "➕ 補充する (入荷)"], key="sup_act")
        sc3, sc4 = st.columns([2, 1])
        amt_val = sc3.number_input("数量（個/セット）", min_value=1, step=1, key="sup_amt")
        ins_sel = sc4.selectbox("作業者", inspectors, key="sup_ins")
        if st.button("✅ 記録を保存", type="primary", use_container_width=True, key="sup_btn"):
            target_id = next(s["supply_id"] for s in supplies if s["name"] == sup_sel)
            append_supply_log({"date": str(date.today()), "supply_id": target_id, "action_type": "入荷" if "➕" in act_sel else "使用", "amount": amt_val, "inspector": ins_sel, "note": "", "registered_at": datetime.now().isoformat()})
            st.success("記録しました！"); refresh()
    st.markdown('</div>', unsafe_allow_html=True)
    if supply_inventory:
        df_sup = pd.DataFrame(supply_inventory)[["image_url", "name", "category", "current_stock"]]
        st.dataframe(df_sup, column_config={"image_url": st.column_config.ImageColumn("画像"), "name": "資材名", "category": "カテゴリ", "current_stock": st.column_config.NumberColumn("現在庫", format="%d")}, use_container_width=True, hide_index=True, height=500)

# ════════════════════════════════════════════════════════════════
elif page == "🔍 双方向トレース":
    st.markdown('<div class="main-header"><div><h1>🔍 双方向原料トレース (HACCP対応)</h1><p>原料の行方と製品の構成を追跡</p></div></div>', unsafe_allow_html=True)
    tab_fwd, tab_bwd = st.tabs(["➡️ 原料から製品を追跡", "⬅️ 製品から原料を遡る"])

    with tab_fwd:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        kw_fwd = st.text_input("検索する原料の「ロットNo」または「メーカー名」", placeholder="例: 1-109 または オリヒロ", key="kw_fwd")
        if kw_fwd and st.button("➡️ 追跡実行", type="primary", key="btn_fwd"):
            kw_l = kw_fwd.strip().lower()
            arr_info = [a for a in arrivals if kw_l in str(a.get("lot_no","")).lower() or kw_l in str(a.get("maker","")).lower()]
            if arr_info:
                st.markdown("#### 📦 対象の原料入荷記録")
                st.dataframe(pd.DataFrame(arr_info)[["arrival_no","arrival_date","maker","material_type","lot_no","bags"]], use_container_width=True, hide_index=True)
            
            res_fwd = []
            for b in brewing:
                is_match = False
                for l_key in ["lot_no", "seaweed_lot", "starch_lot"]:
                    if kw_l in str(b.get(l_key,"")).lower(): is_match = True
                if b.get("other_additives"):
                    try:
                        for o in json.loads(b["other_additives"]):
                            if kw_l in str(o.get("lot","")).lower(): is_match = True
                    except: pass
                if is_match:
                    res_fwd.append({"仕込No": b.get("no",""), "仕込日": b.get("brew_date",""), "品名": b.get("product_name",""), "主ロット": b.get("lot_no",""), "海藻ロット": b.get("seaweed_lot",""), "デンプンロット": b.get("starch_lot","")})
            if res_fwd: st.dataframe(pd.DataFrame(res_fwd), use_container_width=True, hide_index=True)
            else: st.warning("まだ製品に使用されていません。")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab_bwd:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        bc1, bc2 = st.columns(2)
        kw_date = bc1.date_input("対象の仕込日", value=None, key="kw_date")
        kw_prod = bc2.text_input("品名（一部でも可）", placeholder="例: つきこん", key="kw_prod")
        if st.button("⬅️ 遡及実行", type="primary", key="btn_bwd"):
            target_brews = brewing
            if kw_date: target_brews = [b for b in target_brews if b.get("brew_date") == str(kw_date)]
            if kw_prod: target_brews = [b for b in target_brews if kw_prod.lower() in str(b.get("product_name","")).lower()]

            if not target_brews: st.warning("該当する仕込み記録が見つかりません。")
            else:
                for tb in target_brews:
                    st.markdown(f"### 🧪 仕込No: {tb.get('no')} - {tb.get('brew_date')} 【{tb.get('product_name')}】")
                    used_lots = []
                    for k, n in [("lot_no","主原料"), ("seaweed_lot","海藻粉"), ("starch_lot","加工デンプン")]:
                        if tb.get(k) and tb.get(k) != "─": used_lots.append({"役割": n, "ロットNo": tb.get(k)})
                    if tb.get("other_additives"):
                        try:
                            for o in json.loads(tb["other_additives"]):
                                if o.get("lot") and o.get("lot") != "─": used_lots.append({"役割": o.get("name","添加物"), "ロットNo": o.get("lot")})
                        except: pass
                    st.dataframe(pd.DataFrame(used_lots), use_container_width=True, hide_index=True)
                    st.markdown("---")
        st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
elif page == "📊 生産分析":
    st.markdown('<div class="main-header"><div><h1>📊 生産分析・歩留</h1><p>精粉使用量・添加物の比較と歩留まりの客観的評価</p></div></div>', unsafe_allow_html=True)
    if not brewing: 
        st.info("データがありません")
        st.stop()
    
    df = pd.DataFrame(brewing)
    
    # 🌟 日付の強力パース（スプレッドシートの直接編集対応）
    df["brew_date"] = df["brew_date"].astype(str).str.replace("/", "-").str.replace(".", "-")
    df["brew_date"] = pd.to_datetime(df["brew_date"], errors="coerce")
    df = df.dropna(subset=["brew_date"])
    
    # 🌟 数値の強力パース（カンマ除去）
    for c in ["brew_amount", "material_kg", "seaweed_kg", "starch_kg", "lime_kg"]: 
        df[c] = df[c].astype(str).str.replace(",", "").str.replace(" ", "")
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    
    pt = st.radio("集計単位", ["日別", "月別", "年間"], horizontal=True, key="pt_sel")
    if pt == "日別": df["period"] = df["brew_date"].dt.date.astype(str)
    elif pt == "月別": df["period"] = df["brew_date"].dt.to_period("M").astype(str)
    else: df["period"] = df["brew_date"].dt.to_period("Y").astype(str)
    
    grp = df.groupby("period").agg(
        仕込回数=("no", "count"), 
        製品仕込量=("brew_amount", "sum"), 
        精粉=("material_kg", "sum"),
        海藻粉=("seaweed_kg", "sum"),
        加工デンプン=("starch_kg", "sum"),
        石灰=("lime_kg", "sum")
    ).reset_index()
    
    other_data = []
    for _, r in df.iterrows():
        period = r["period"]
        if r.get("other_additives"):
            try:
                for o in json.loads(r["other_additives"]):
                    name = o.get("name")
                    kg = float(str(o.get("kg") or 0).replace(",",""))
                    if name and kg > 0:
                        other_data.append({"period": period, "name": name, "kg": kg})
            except: pass
            
    if other_data:
        df_others = pd.DataFrame(other_data)
        others_pivot = df_others.groupby(["period", "name"])["kg"].sum().unstack(fill_value=0).reset_index()
        grp = pd.merge(grp, others_pivot, on="period", how="left").fillna(0)
        
    grp["歩留まり(倍)"] = (grp["製品仕込量"] / grp["精粉"].replace(0, float("nan"))).round(2)
    
    tab1, tab2, tab3 = st.tabs(["📈 生産量・歩留まり推移", "📊 原料・添加物 内訳比較", "📋 データ詳細・比率検証"])
    
    with tab1:
        st.markdown('<div class="section-title">製品仕込量・精粉使用量・歩留まり(倍)</div>', unsafe_allow_html=True)
        fig1 = go.Figure()
        fig1.add_trace(go.Bar(x=grp["period"], y=grp["製品仕込量"], name="製品仕込量(kg)", marker_color="#1565c0"))
        fig1.add_trace(go.Bar(x=grp["period"], y=grp["精粉"], name="精粉(kg)", marker_color="#43a047"))
        fig1.add_trace(go.Scatter(x=grp["period"], y=grp["歩留まり(倍)"], name="歩留まり(倍)", yaxis="y2", mode="lines+markers", line=dict(color="#f57f17", width=3)))
        fig1.update_layout(barmode="group", height=450, plot_bgcolor="#f8faff", yaxis=dict(title="重量 (kg)"), yaxis2=dict(title="歩留まり(倍)", overlaying="y", side="right", showgrid=False), legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig1, use_container_width=True)
        
    with tab2:
        st.markdown('<div class="section-title">原料・添加物 使用量内訳 (kg)</div>', unsafe_allow_html=True)
        base_materials = ["精粉", "海藻粉", "加工デンプン", "石灰"]
        other_additives = [c for c in grp.columns if c not in ["period", "仕込回数", "製品仕込量", "歩留まり(倍)"] + base_materials]
        
        fig2 = go.Figure()
        colors = ["#43a047", "#e53935", "#fb8c00", "#8e24aa", "#3949ab", "#1e88e5", "#039be5", "#00acc1", "#00897b", "#00838f"]
        for i, mat in enumerate(base_materials + other_additives):
            if mat in grp.columns:
                fig2.add_trace(go.Bar(x=grp["period"], y=grp[mat], name=mat, marker_color=colors[i % len(colors)]))
                
        fig2.update_layout(barmode="stack", height=450, plot_bgcolor="#f8faff", yaxis=dict(title="使用量 (kg)"), legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig2, use_container_width=True)
        
    with tab3:
        st.markdown('<div class="section-title">データ詳細・精粉に対する添加物比率(%)</div>', unsafe_allow_html=True)
        st.info("※ 精粉を100%とした場合の、各添加物の使用比率を検証できます（レシピのブレや過剰添加の確認用）。")
        ratio_df = grp[["period", "仕込回数", "製品仕込量", "精粉", "歩留まり(倍)"]].copy()
        for mat in base_materials[1:] + other_additives:
            if mat in grp.columns:
                ratio_df[f"{mat} 比率(%)"] = (grp[mat] / grp["精粉"].replace(0, float("nan")) * 100).round(2)
        st.dataframe(ratio_df, use_container_width=True)
        st.markdown("##### 実数データ")
        format_dict = {c: "{:.1f}" for c in grp.columns if c not in ["period", "仕込回数"]}
        st.dataframe(grp.style.format(format_dict), use_container_width=True)

# ════════════════════════════════════════════════════════════════
elif page == "⚙️ マスター設定":
    st.markdown('<div class="main-header"><div><h1>⚙️ マスター設定</h1></div></div>', unsafe_allow_html=True)
    t1, t2, t3, t4, t5 = st.tabs(["🧴 原料", "🏭 メーカー", "👤 担当者", "⚠️ 発注点", "🧹 資材(備品)登録"])
    
    with t1:
        m1 = st.text_area("原料リスト (1行1件)", "\n".join(materials), height=200, key="mst_mat")
        if st.button("保存", key="b1"): save_materials([x.strip() for x in m1.splitlines() if x.strip()]); refresh()
    with t2:
        m2 = st.text_area("メーカーリスト", "\n".join(makers), height=200, key="mst_mak")
        if st.button("保存", key="b2"): save_makers([x.strip() for x in m2.splitlines() if x.strip()]); refresh()
    with t3:
        m3 = st.text_area("担当者リスト", "\n".join(inspectors), height=200, key="mst_ins")
        if st.button("保存", key="b3"): save_inspectors([x.strip() for x in m3.splitlines() if x.strip()]); refresh()
    with t4:
        st.info("原料ごとの発注点（袋数）を設定")
        op_df = pd.DataFrame([{"原料名": m, "発注点(袋)": order_points.get(m, 0.0)} for m in materials])
        e_op = st.data_editor(op_df, use_container_width=True, key="mst_op")
        if st.button("保存", key="b4"):
            save_order_points({r["原料名"]: r["発注点(袋)"] for _, r in e_op.iterrows() if float(r["発注点(袋)"]) > 0})
            refresh()
            
    with t5:
        st.info("衛生備品や梱包資材の登録を行います。画像はPC/スマホからアップロードするか、URLを指定してください。")
        
        # 🌟 PC・スマホからの画像アップロード対応 フォーム
        with st.form("new_supply_form"):
            sc1, sc2, sc3 = st.columns(3)
            n_name  = sc1.text_input("資材名 ＊")
            n_cat   = sc2.text_input("カテゴリ (例: 衛生, 梱包)")
            n_stock = sc3.number_input("初期在庫", min_value=0, step=1)
            
            sc4, sc5 = st.columns(2)
            n_file = sc4.file_uploader("📷 画像をアップロード", type=["png","jpg","jpeg"])
            n_url  = sc5.text_input("🌐 または画像のURLを指定")
            
            if st.form_submit_button("➕ 新規資材を登録"):
                if not n_name:
                    st.error("資材名を入力してください")
                else:
                    img_val = "https://cdn-icons-png.flaticon.com/512/1243/1243324.png"
                    if n_file and HAS_PIL:
                        # 画像を圧縮してBase64に変換し、直接スプレッドシートに保存
                        img = Image.open(n_file)
                        img.thumbnail((150, 150))
                        buf = BytesIO()
                        img.save(buf, format="PNG")
                        img_val = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
                    elif n_url:
                        img_val = n_url
                        
                    current_supplies = supplies.copy()
                    current_supplies.append({
                        "supply_id": f"SUP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "name": n_name, "category": n_cat, "image_url": img_val, "initial_stock": n_stock
                    })
                    save_supplies(current_supplies)
                    st.success(f"{n_name} を登録しました！")
                    refresh()

        st.markdown("#### 登録済み資材の一覧・削除")
        if supplies:
            del_sup = st.selectbox("削除する資材を選択", ["─"] + [s["name"] for s in supplies])
            if st.button("🗑 選択した資材を削除"):
                if del_sup != "─":
                    save_supplies([s for s in supplies if s["name"] != del_sup])
                    st.success("削除しました")
                    refresh()
                    
            df_s = pd.DataFrame(supplies)[["image_url", "name", "category", "initial_stock"]]
            st.dataframe(
                df_s,
                column_config={"image_url": st.column_config.ImageColumn("画像")},
                use_container_width=True, hide_index=True
            )
# --- END OF FILE app.py ---
