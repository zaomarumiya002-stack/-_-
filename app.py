# --- START OF FILE app.py ---
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import json
from datetime import datetime, date, timedelta
import traceback

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
.kpi-card { background:#fff; border-radius:12px; padding:16px 18px; box-shadow:0 1px 6px rgba(0,0,0,.07); border-top:3px solid #1565c0; text-align:center; height:100%;}
.kpi-value { font-size:2.2rem; font-weight:700; color:#1a237e; line-height:1.2; }
.kpi-label { font-size:.85rem; color:#78909c; margin-top:4px; font-weight:500;}
.alert-ng { background:#fff3f3; border:1px solid #ffcdd2; border-left:4px solid #e53935; padding:10px 14px; border-radius:8px; color:#b71c1c; font-size:.88rem; font-weight:600; margin-bottom:8px; display:flex; align-items:center;}
.alert-warning { background:#fff8e1; border:1px solid #ffecb3; border-left:4px solid #ff9800; padding:10px 14px; border-radius:8px; color:#e65100; font-size:.88rem; font-weight:600; margin-bottom:8px; display:flex; align-items:center;}
.form-card { background:#ffffff; border:1px solid #cfd8dc; border-radius:12px; padding:20px; margin-bottom:20px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);}
.section-title { font-size:1.05rem; font-weight:700; color:#1565c0; border-bottom:2px solid #e3f2fd; padding-bottom:6px; margin-bottom:16px; }
.kpi-sub { font-size:0.75rem; color:#90a4ae; margin-top:4px; display:block;}
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
    page = st.radio("", ["🏠 ダッシュボード", "📦 入荷記録", "🧪 仕込み記録", "🏭 原料在庫", "🧹 資材在庫", "🔍 双方向トレース", "📈 統計・比較分析", "⚙️ マスター設定"], label_visibility="collapsed")
    if st.button("🔄 データ手動更新", use_container_width=True): refresh()
    st.caption(f"最終読込: {datetime.now().strftime('%H:%M')}")

@st.cache_data(ttl=3600)
def fetch_all(): 
    return (load_arrivals(), load_brewing(), load_adjustments(), load_supplies(), load_supply_logs(), 
            load_materials(), load_makers(), load_inspectors(), load_order_points())

try:
    (arrivals, brewing, adjustments, supplies, supply_logs, materials, makers, inspectors, order_points) = fetch_all()
except Exception as e:
    st.error(f"🚨 データ取得エラー\n\n```\n{traceback.format_exc()}\n```")
    st.stop()

@st.cache_data(ttl=3600)
def get_inventory():
    if not arrivals: return {}
    inv = {str(a.get("入荷No")): {
        "入荷No": str(a.get("入荷No", "")), "ロットNo": str(a.get("ロットNo", "")), "メーカー": str(a.get("メーカー", "")),
        "原料種別": str(a.get("原料種別", "")), "1袋重量": float(a.get("1袋重量(kg)") or 20.0),
        "入荷袋数": float(a.get("袋数") or 0), "使用量(kg)": 0.0, "調整袋数": 0.0
    } for a in arrivals if a.get("入荷No")}
    
    lot_to_arr = {str(a.get("ロットNo", "")).strip(): str(a.get("入荷No", "")) for a in arrivals if str(a.get("ロットNo", "")).strip() and a.get("入荷No")}
    
    def _deduct(lot_str, kg):
        lot_str = str(lot_str).strip()
        if not lot_str or lot_str == "─": return
        if lot_str in inv: inv[lot_str]["使用量(kg)"] += float(kg or 0)
        elif lot_str in lot_to_arr: inv[lot_to_arr[lot_str]]["使用量(kg)"] += float(kg or 0)

    for b in brewing:
        _deduct(b.get("主原料ロット"), b.get("こんにゃく精粉(kg)"))
        _deduct(b.get("海藻粉ロット"), b.get("海藻粉(kg)"))
        _deduct(b.get("デンプンロット"), b.get("デンプン(kg)"))
        if b.get("その他添加物"):
            try:
                for o in json.loads(b["その他添加物"]): _deduct(o.get("lot"), o.get("kg"))
            except: pass

    for adj in adjustments:
        ano = str(adj.get("入荷No", ""))
        if ano in inv: inv[ano]["調整袋数"] += float(adj.get("調整袋数") or 0)
        
    for v in inv.values():
        bpk = v["1袋重量"] if v["1袋重量"] > 0 else 20.0
        v["使用袋数"] = v["使用量(kg)"] / bpk
        v["現在庫(袋)"] = v["入荷袋数"] - v["使用袋数"] + v["調整袋数"]
        v["現在庫(kg)"] = v["現在庫(袋)"] * bpk
    return inv

@st.cache_data(ttl=3600)
def get_supply_inv():
    if not supplies: return []
    inv = {str(s.get("資材ID")): {
        "資材ID": str(s.get("資材ID", "")), "資材名": str(s.get("資材名", "")), "カテゴリ": str(s.get("カテゴリ", "")),
        "画像URL": str(s.get("画像URL", "https://cdn-icons-png.flaticon.com/512/1243/1243324.png")),
        "initial": float(s.get("初期在庫") or 0), "発注点": float(s.get("発注点") or 0), "in_out": 0.0
    } for s in supplies if s.get("資材ID")}
    
    for lg in supply_logs:
        sid = str(lg.get("資材ID", ""))
        if sid in inv:
            amt = float(lg.get("数量") or 0)
            inv[sid]["in_out"] += amt if "入荷" in lg.get("処理", "") else -amt
            
    res = []
    for sid, v in inv.items():
        v["現在庫"] = v["initial"] + v["in_out"]
        res.append(v)
    return res

inventory_data = get_inventory()
supply_inventory = get_supply_inv()

type_totals = {}
for v in inventory_data.values(): type_totals[v["原料種別"]] = type_totals.get(v["原料種別"], 0) + v["現在庫(袋)"]
raw_alerts = [f"⚠️ 【原料アラート】 {m} の在庫（{c:,.1f}袋）が発注点（{order_points.get(m, 0):,.1f}袋）を下回っています！" for m, c in type_totals.items() if m in order_points and c < order_points[m]]
sup_alerts = [f"📦 【資材アラート】 {s['資材名']} の在庫（{s['現在庫']:.0f}個）が発注点（{s['発注点']:.0f}個）を下回っています！" for s in supply_inventory if s.get("発注点", 0) > 0 and s["現在庫"] < s["発注点"]]

def get_fancy_lots(mat_keywords, maker_filter="すべて", current_val=""):
    if isinstance(mat_keywords, str): mat_keywords = [mat_keywords]
    arrs = []
    for a in arrivals:
        m_type = str(a.get("原料種別", ""))
        lot = str(a.get("ロットNo", "")).strip()
        if lot and any(k in m_type for k in mat_keywords):
            if maker_filter == "すべて" or str(a.get("メーカー", "")) == maker_filter: arrs.append(a)
    opts = [f"{a['ロットNo']} | {a.get('メーカー','')} | 入荷:{str(a.get('入荷日',''))[-5:]}" for a in arrs]
    res = ["─"] + sorted(list(set(opts)), reverse=True)
    if current_val and current_val != "─" and not any(current_val == opt.split(" | ")[0].strip() for opt in res):
        res.insert(1, current_val)
    return res

def extract_lot(fancy_str):
    if not fancy_str or fancy_str == "─": return "─"
    return fancy_str.split(" | ")[0].strip()

# ════════════════════════════════════════════════════════════════
if page == "🏠 ダッシュボード":
    st.markdown('<div class="main-header"><div><h1>📊 ERP ダッシュボード</h1><p>工場の稼働状況・在庫・アラートをリアルタイムで把握します</p></div></div>', unsafe_allow_html=True)
    
    # --- アラート表示 ---
    if raw_alerts or sup_alerts:
        for al in raw_alerts: st.markdown(f'<div class="alert-ng">{al}</div>', unsafe_allow_html=True)
        for al in sup_alerts: st.markdown(f'<div class="alert-warning">{al}</div>', unsafe_allow_html=True)
    
    # --- データ整形（共通） ---
    df_b = pd.DataFrame(brewing)
    if not df_b.empty:
        df_b["仕込日"] = pd.to_datetime(df_b["仕込日"].astype(str).str.replace("/", "-").str.replace(".", "-"), errors="coerce")
        df_b["こんにゃく精粉(kg)"] = pd.to_numeric(df_b["こんにゃく精粉(kg)"], errors="coerce").fillna(0)
        df_b["こんにゃく粉(袋)"] = df_b["こんにゃく精粉(kg)"] / 20.0
        df_b["製品仕込量(kg)"] = pd.to_numeric(df_b["仕込量(kg)"], errors="coerce").fillna(0)
    
    # --- 1日・1ヶ月・1年の平均袋数計算 ---
    avg_day = avg_month = avg_year = 0.0
    if not df_b.empty:
        today = pd.to_datetime(date.today())
        
        df_day = df_b[df_b["仕込日"] >= today - timedelta(days=1)]
        if not df_day.empty and len(df_day) > 0: avg_day = df_day["こんにゃく粉(袋)"].sum() / len(df_day)
        
        df_month = df_b[df_b["仕込日"] >= today - timedelta(days=30)]
        if not df_month.empty and len(df_month) > 0: avg_month = df_month["こんにゃく粉(袋)"].sum() / len(df_month)
        
        df_year = df_b[df_b["仕込日"] >= today - timedelta(days=365)]
        if not df_year.empty and len(df_year) > 0: avg_year = df_year["こんにゃく粉(袋)"].sum() / len(df_year)

    # --- 上段 KPI（稼働サマリー） ---
    st.markdown('<div class="section-title">🏭 稼働・在庫サマリー</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    today_brews = len(df_b[df_b["仕込日"] == pd.to_datetime(date.today())]) if not df_b.empty else 0
    week_kg = df_b[df_b["仕込日"] >= pd.to_datetime(date.today() - timedelta(days=7))]["製品仕込量(kg)"].sum() if not df_b.empty else 0
    total_bags = sum(max(v["現在庫(袋)"], 0) for v in inventory_data.values())
    c1.markdown(f'<div class="kpi-card"><div class="kpi-value">{today_brews}</div><div class="kpi-label">本日の仕込み回数</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-card"><div class="kpi-value">{week_kg:,.0f}</div><div class="kpi-label">直近7日 製品仕込量(kg)</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-card"><div class="kpi-value">{total_bags:,.0f}</div><div class="kpi-label">全原料 総在庫(袋)</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi-card" style="border-top-color:#e53935;"><div class="kpi-value" style="color:#c62828;">{len(raw_alerts)+len(sup_alerts)}</div><div class="kpi-label">要発注アラート</div></div>', unsafe_allow_html=True)

    # --- 中段 KPI（粉の消費ペース） ---
    st.markdown('<div class="section-title">⚖️ 平均こんにゃく粉 消費ペース (1回あたり)</div>', unsafe_allow_html=True)
    c5, c6, c7 = st.columns(3)
    c5.markdown(f'<div class="kpi-card" style="border-top-color:#43a047;"><div class="kpi-value" style="color:#2e7d32;">{avg_day:,.1f} 袋</div><div class="kpi-label">直近 1日 平均</div></div>', unsafe_allow_html=True)
    c6.markdown(f'<div class="kpi-card" style="border-top-color:#43a047;"><div class="kpi-value" style="color:#2e7d32;">{avg_month:,.1f} 袋</div><div class="kpi-label">直近 1ヶ月 平均</div></div>', unsafe_allow_html=True)
    c7.markdown(f'<div class="kpi-card" style="border-top-color:#43a047;"><div class="kpi-value" style="color:#2e7d32;">{avg_year:,.1f} 袋</div><div class="kpi-label">直近 1年 平均</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- 下段 グラフ（昨対推移） ---
    col_left, col_right = st.columns([6, 4])
    
    with col_left:
        st.markdown('<div class="section-title">📈 昨対 生産トレンド (月別・袋数)</div>', unsafe_allow_html=True)
        if not df_b.empty:
            df_b["year"] = df_b["仕込日"].dt.year
            df_b["month"] = df_b["仕込日"].dt.month
            
            curr_year = date.today().year
            prev_year = curr_year - 1
            
            df_curr = df_b[df_b["year"] == curr_year].groupby("month")["こんにゃく粉(袋)"].sum().reset_index()
            df_prev = df_b[df_b["year"] == prev_year].groupby("month")["こんにゃく粉(袋)"].sum().reset_index()
            
            # 全月（1〜12月）の骨組みを作る
            months = pd.DataFrame({"month": range(1, 13)})
            df_curr = pd.merge(months, df_curr, on="month", how="left").fillna(0)
            df_prev = pd.merge(months, df_prev, on="month", how="left").fillna(0)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_curr["month"], y=df_curr["こんにゃく粉(袋)"], mode='lines+markers', name=f"今年 ({curr_year})", line=dict(color="#1565c0", width=4), marker=dict(size=8)))
            fig.add_trace(go.Scatter(x=df_prev["month"], y=df_prev["こんにゃく粉(袋)"], mode='lines+markers', name=f"昨年 ({prev_year})", line=dict(color="#b0bec5", width=3, dash='dash'), marker=dict(size=6)))
            
            fig.update_layout(
                height=350, margin=dict(l=20,r=20,t=20,b=20), plot_bgcolor="#f8faff", paper_bgcolor="#fff",
                xaxis=dict(title="月", tickmode='linear', tick0=1, dtick=1),
                yaxis=dict(title="こんにゃく粉 (袋)"),
                legend=dict(orientation="h", y=-0.15)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("データがありません")
            
    with col_right:
        st.markdown('<div class="section-title">⏱️ 最新アクティビティ</div>', unsafe_allow_html=True)
        tab_a, tab_b = st.tabs(["🧪 最新の仕込み", "📦 最新の入荷"])
        with tab_a:
            if brewing:
                df_sh = pd.DataFrame(brewing)[["仕込日", "品名", "主原料ロット", "仕込量(kg)"]][::-1].head(8)
                st.dataframe(df_sh, use_container_width=True, hide_index=True)
            else: st.write("データなし")
        with tab_b:
            if arrivals:
                df_ar = pd.DataFrame(arrivals)[["入荷日", "原料種別", "ロットNo", "袋数"]][::-1].head(8)
                st.dataframe(df_ar, use_container_width=True, hide_index=True)
            else: st.write("データなし")

# ════════════════════════════════════════════════════════════════
elif page == "📦 入荷記録":
    st.markdown('<div class="main-header"><div><h1>📦 原料入荷記録</h1><p>入荷時の品質検査と担当者記録</p></div></div>', unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["➕ 新規登録", "📋 履歴一覧", "✏️ 既存データ編集"])
    
    with t1:
        st.markdown('<div class="form-card"><div class="section-title">📦 基本情報</div>', unsafe_allow_html=True)
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
        st.info(f"💡 自動計算 総量: **{(bags or 0) * b_per:,.1f} kg**")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="form-card"><div class="section-title">🔍 品質検査</div>', unsafe_allow_html=True)
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
                    "入荷No": new_no, "入荷日": str(a_date), "メーカー": maker, "ロットNo": lot_no,
                    "原料種別": m_type, "袋数": bags or 0, "1袋重量(kg)": b_per, "総量(kg)": (bags or 0) * b_per,
                    "外観": app, "品名・規格確認": c_name, "賞味期限": c_exp, "異物": c_dmg,
                    "異常内容": abn, "担当者": ins, "備考": rem, "登録日時": datetime.now().isoformat()
                })
                st.success("保存しました！"); refresh()

    with t2:
        if arrivals: st.dataframe(pd.DataFrame(arrivals)[["入荷No", "入荷日", "メーカー", "ロットNo", "原料種別", "袋数", "外観", "担当者"]][::-1].reset_index(drop=True), use_container_width=True, height=500)

    with t3:
        if not arrivals: st.info("データなし")
        else:
            st.markdown('<div class="form-card">', unsafe_allow_html=True)
            edit_target = st.selectbox("編集する入荷Noを選択", [a.get("入荷No") for a in reversed(arrivals) if a.get("入荷No")], key="edit_arr_sel")
            if edit_target:
                td = next((a for a in arrivals if a.get("入荷No") == edit_target), None)
                e_date = st.text_input("入荷日", value=td.get("入荷日",""), key="ea_date")
                e_maker = st.text_input("メーカー", value=td.get("メーカー",""), key="ea_maker")
                e_lot = st.text_input("ロットNo", value=td.get("ロットNo",""), key="ea_lot")
                e_mat = st.selectbox("原料種別", materials, index=materials.index(td.get("原料種別")) if td.get("原料種別") in materials else 0, key="ea_mat")
                e_bags = st.number_input("袋数", value=int(td.get("袋数") or 0), key="ea_bags")
                if st.button("💾 変更を上書き保存", type="primary", key="ea_save"):
                    td.update({"入荷日": e_date, "メーカー": e_maker, "ロットNo": e_lot, "原料種別": e_mat, "袋数": e_bags})
                    update_arrival(td["入荷No"], td); st.success("更新しました！"); refresh()
            st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
elif page == "🧪 仕込み記録":
    st.markdown('<div class="main-header"><div><h1>🧪 仕込み記録</h1><p>品目別の原料使用量とロットの紐付け</p></div></div>', unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["➕ 新規登録", "📋 履歴一覧", "✏️ 既存データ編集"])
    
    with t1:
        st.markdown('<div class="form-card"><div class="section-title">📋 製品情報</div>', unsafe_allow_html=True)
        c1,c2,c3,c4 = st.columns(4)
        b_date = c1.date_input("仕込日", key="new_brw_date")
        p_name = c2.text_input("品名 ＊", key="new_brw_name")
        b_maker = c3.selectbox("得意先・メーカー", makers, key="new_brw_maker")
        b_amount = c4.number_input("製品仕込量(kg) ＊", min_value=0.0, value=None, step=10.0, key="new_brw_amt")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="form-card"><div class="section-title">⚗️ 主原料（こんにゃく粉）</div>', unsafe_allow_html=True)
        cm1, cm2, cm3 = st.columns(3)
        sf_makers = ["すべて"] + sorted(list(set(a.get("メーカー","") for a in arrivals if any(k in a.get("原料種別","") for k in ["こんにゃく粉", "精粉", "粉", "マンナン"]))))
        sel_sf_maker = cm1.selectbox("🔍 こんにゃく粉メーカーで絞り込み", sf_makers, key="filter_maker")
        
        lot_no_b_disp = cm2.selectbox("こんにゃく粉 ロットNo ＊", get_fancy_lots(["こんにゃく粉", "精粉", "粉", "マンナン"], maker_filter=sel_sf_maker), key="new_brw_lot")
        lot_no_b = extract_lot(lot_no_b_disp)
        mat_kg = cm3.number_input("こんにゃく粉 使用量(kg)", min_value=0.0, value=None, format="%.2f", key="new_brw_mkg")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="form-card"><div class="section-title">🌿 副原料（海藻・デンプン・石灰）</div>', unsafe_allow_html=True)
        r1, r2, r3 = st.columns(3)
        sea_lot_disp = r1.selectbox("海藻粉 ロット", get_fancy_lots(["海藻", "青海苔", "ひじき", "アラメ"]), key="new_brw_sl")
        sea_lot = extract_lot(sea_lot_disp)
        sea_type = r1.selectbox("海藻粉 種別", ["─", "青海苔", "ひじき", "アラメ", "その他"], key="new_brw_s_type")
        sea_kg = r1.number_input("海藻粉 使用量(kg)", min_value=0.0, value=None, format="%.2f", key="new_brw_skg")
        
        sta_lot_disp = r2.selectbox("加工デンプン ロット", get_fancy_lots(["デンプン", "でんぷん", "澱粉"]), key="new_brw_stl")
        sta_lot = extract_lot(sta_lot_disp)
        sta_type = r2.selectbox("デンプン 種別", ["─","ゆり8","VA70","その他"], key="new_brw_stt")
        sta_kg = r2.number_input("デンプン 使用量(kg)", min_value=0.0, value=None, format="%.2f", key="new_brw_stkg")
        
        r3.markdown("<br>", unsafe_allow_html=True)
        lime_kg = r3.number_input("石灰(kg)", min_value=0.0, value=None, format="%.2f", key="new_brw_lkg")
        lime_w = r3.number_input("石灰水(L)", min_value=0.0, value=None, format="%.1f", key="new_brw_lw")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="form-card"><div class="section-title">🧂 その他添加物</div>', unsafe_allow_html=True)
        st.caption("原料を選ぶと、その原料の入荷ロット（メーカー・日付付き）が自動でドロップダウンに表示されます。")
        
        if "other_rows" not in st.session_state: st.session_state.other_rows = []
        for i, row in enumerate(st.session_state.other_rows):
            oc1, oc2, oc3, oc4 = st.columns([3,4,2,1])
            sel_mat = oc1.selectbox("原料名", materials, key=f"mat_{i}", index=materials.index(row["name"]) if row["name"] in materials else 0)
            
            sel_lot_disp = oc2.selectbox("ロットNo", get_fancy_lots([sel_mat], current_val=row.get("lot")), key=f"lot_{i}")
            sel_lot = extract_lot(sel_lot_disp)
            
            sel_kg = oc3.number_input("使用量(kg)", min_value=0.0, format="%.2f", key=f"kg_{i}", value=float(row["kg"]) if row["kg"] else None)
            if oc4.button("❌", key=f"del_{i}"): st.session_state.other_rows.pop(i); st.rerun()
            st.session_state.other_rows[i] = {"name": sel_mat, "lot": sel_lot, "kg": sel_kg or 0.0}
            
        if st.button("➕ 添加物を追加", key="add_oth"): st.session_state.other_rows.append({"name": materials[0], "lot": "─", "kg": 0.0}); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("✅ 仕込み記録を保存", type="primary", use_container_width=True, key="save_brw_btn"):
            if not p_name or lot_no_b == "─" or not b_amount: st.error("品名、主原料ロット、仕込量は必須です")
            else:
                others_json = json.dumps([r for r in st.session_state.other_rows if r["kg"] > 0], ensure_ascii=False)
                append_brewing({
                    "仕込No": next_brewing_no(brewing), "仕込日": str(b_date), "品名": p_name, "メーカー": b_maker, 
                    "主原料ロット": lot_no_b, "仕込量(kg)": b_amount or 0.0, "こんにゃく精粉(kg)": mat_kg or 0.0, 
                    "海藻粉(kg)": sea_kg or 0.0, "海藻粉ロット": sea_lot, "海藻粉種別": sea_type,
                    "デンプン(kg)": sta_kg or 0.0, "デンプンロット": sta_lot, "デンプン種別": sta_type, 
                    "石灰(kg)": lime_kg or 0.0, "石灰水(L)": lime_w or 0.0, "その他添加物": others_json, 
                    "登録日時": datetime.now().isoformat()
                })
                st.session_state.other_rows = []
                st.success("保存しました！"); refresh()

    with t2:
        if brewing: st.dataframe(pd.DataFrame(brewing)[["仕込No","仕込日","品名","主原料ロット","海藻粉ロット","デンプンロット","仕込量(kg)"]][::-1].reset_index(drop=True), use_container_width=True, height=500)

    with t3:
        if not brewing: st.info("データなし")
        else:
            st.markdown('<div class="form-card">', unsafe_allow_html=True)
            edit_target_b = st.selectbox("編集する仕込Noを選択", [f"{b.get('仕込No')} - {b.get('品名')}" for b in reversed(brewing) if b.get("仕込No")], key="edit_brw_sel")
            if edit_target_b:
                t_no = edit_target_b.split(" - ")[0]
                td = next((b for b in brewing if str(b.get("仕込No")) == str(t_no)), None)
                
                eb_name = st.text_input("品名", value=td.get("品名",""), key="eb_name")
                
                eb_lot_disp = st.selectbox("こんにゃく粉ロットNo", get_fancy_lots(["こんにゃく粉","精粉","粉","マンナン"], current_val=td.get("主原料ロット","")), key="eb_lot")
                eb_sl_disp = st.selectbox("海藻粉ロットNo", get_fancy_lots(["海藻"], current_val=td.get("海藻粉ロット","")), key="eb_slot")
                eb_stl_disp = st.selectbox("デンプンロットNo", get_fancy_lots(["デンプン"], current_val=td.get("デンプンロット","")), key="eb_stlot")
                
                eb_amt = st.number_input("仕込量(kg)", value=float(td.get("仕込量(kg)") or 0), key="eb_amt")
                eb_mat = st.number_input("こんにゃく粉(kg)", value=float(td.get("こんにゃく精粉(kg)") or 0), key="eb_mat")
                
                if st.button("💾 変更を上書き保存", type="primary", key="eb_save"):
                    td.update({
                        "品名": eb_name, 
                        "主原料ロット": extract_lot(eb_lot_disp), 
                        "海藻粉ロット": extract_lot(eb_sl_disp), 
                        "デンプンロット": extract_lot(eb_stl_disp), 
                        "仕込量(kg)": eb_amt, "こんにゃく精粉(kg)": eb_mat
                    })
                    update_brewing(td["仕込No"], td); st.success("更新しました！"); refresh()
            st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
elif page == "🏭 原料在庫":
    st.markdown('<div class="main-header"><div><h1>🏭 原料在庫管理</h1><p>自動計算された現在庫（袋単位）と棚卸し調整</p></div></div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["📋 現在庫一覧", "⚖️ 在庫ズレ調整"])
    with t1:
        if not inventory_data: st.info("データなし")
        else:
            inv_df = pd.DataFrame(list(inventory_data.values()))[["入荷No", "原料種別", "ロットNo", "入荷袋数", "使用袋数", "調整袋数", "現在庫(袋)"]]
            inv_df.columns = ["入荷No", "原料種別", "ロットNo", "入荷(袋)", "使用(袋)", "調整(袋)", "現在庫(袋)"]
            st.dataframe(inv_df, column_config={"入荷(袋)": st.column_config.NumberColumn(format="%.1f"), "使用(袋)": st.column_config.NumberColumn(format="%.1f"), "調整(袋)": st.column_config.NumberColumn(format="%.1f"), "現在庫(袋)": st.column_config.NumberColumn(format="%.1f")}, use_container_width=True, height=400)
    with t2:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        if inventory_data:
            target_arr = st.selectbox("対象ロット", [f"{v['入荷No']} ({v['原料種別']} / ロット:{v['ロットNo']} / 現在庫:{v['現在庫(袋)']:.1f}袋)" for v in inventory_data.values()], key="adj_sel")
            if target_arr:
                arr_id = target_arr.split(" ")[0]
                real_val = st.number_input("実在庫 (袋)", value=float(inventory_data[arr_id]["現在庫(袋)"]), step=1.0, key="adj_val")
                diff = real_val - inventory_data[arr_id]["現在庫(袋)"]
                st.write(f"👉 調整量: **{diff:+.1f} 袋**")
                reason = st.text_input("調整理由", key="adj_rsn")
                if st.button("⚖️ 在庫を調整する", type="primary", key="adj_btn"):
                    append_adjustment({"調整日": str(date.today()), "入荷No": arr_id, "調整袋数": diff, "理由": reason, "登録日時": datetime.now().isoformat()})
                    st.success("記録しました！"); refresh()
        st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
elif page == "🧹 資材在庫":
    st.markdown('<div class="main-header"><div><h1>🧹 資材・衛生備品 管理</h1><p>スマホ対応：写真を見ながら簡単に入出庫記録ができます</p></div></div>', unsafe_allow_html=True)
    
    if sup_alerts:
        for al in sup_alerts: st.markdown(f'<div class="alert-warning">{al}</div>', unsafe_allow_html=True)
        
    st.markdown('<div class="form-card" style="border-left: 5px solid #ff9800;">', unsafe_allow_html=True)
    if not supplies: st.warning("資材マスターが未登録です")
    else:
        sc1, sc2 = st.columns([2, 1])
        sup_sel = sc1.selectbox("資材を選択", [s.get("資材名","") for s in supplies if s.get("資材名")], key="sup_sel")
        act_sel = sc2.selectbox("処理", ["➖ 使用する (出庫)", "➕ 補充する (入荷)"], key="sup_act")
        sc3, sc4 = st.columns([2, 1])
        amt_val = sc3.number_input("数量（個/セット）", min_value=1, step=1, key="sup_amt")
        ins_sel = sc4.selectbox("作業者", inspectors, key="sup_ins")
        if st.button("✅ 記録を保存", type="primary", use_container_width=True, key="sup_btn"):
            target_id = next((s["資材ID"] for s in supplies if s.get("資材名") == sup_sel), None)
            append_supply_log({"登録日": str(date.today()), "資材ID": target_id, "処理": "入荷" if "➕" in act_sel else "使用", "数量": amt_val, "作業者": ins_sel, "登録日時": datetime.now().isoformat()})
            st.success("記録しました！"); refresh()
    st.markdown('</div>', unsafe_allow_html=True)
    
    if supply_inventory:
        df_sup = pd.DataFrame(supply_inventory)[["画像URL", "資材名", "カテゴリ", "現在庫", "発注点"]]
        df_sup["状態"] = df_sup.apply(lambda r: "🔴発注" if r["発注点"] > 0 and r["現在庫"] < r["発注点"] else "✅正常", axis=1)
        st.dataframe(df_sup, column_config={
            "画像URL": st.column_config.ImageColumn("画像"), 
            "現在庫": st.column_config.NumberColumn("現在庫", format="%d"),
            "発注点": st.column_config.NumberColumn("発注点", format="%d")
        }, use_container_width=True, hide_index=True, height=500)

# ════════════════════════════════════════════════════════════════
elif page == "🔍 双方向トレース":
    st.markdown('<div class="main-header"><div><h1>🔍 双方向原料トレース (HACCP対応)</h1><p>原料の行方と製品の構成を追跡</p></div></div>', unsafe_allow_html=True)
    tab_fwd, tab_bwd = st.tabs(["➡️ 原料から製品を追跡", "⬅️ 製品から原料を遡る"])

    with tab_fwd:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        search_type = st.radio("検索方法", ["ロットNoで検索", "メーカー名で検索"], horizontal=True)
        if search_type == "ロットNoで検索":
            kw_fwd = st.text_input("ロットNoを入力", placeholder="例: 1-109", key="kw_fwd")
            maker_fwd = ""
        else:
            kw_fwd = ""
            maker_fwd = st.selectbox("登録メーカーから選択", makers, key="maker_fwd")
            
        if st.button("➡️ 追跡実行", type="primary", key="btn_fwd"):
            if kw_fwd:
                arr_info = [a for a in arrivals if kw_fwd.lower() in str(a.get("ロットNo","")).lower()]
            else:
                arr_info = [a for a in arrivals if maker_fwd == a.get("メーカー","")]
                
            if arr_info:
                st.markdown("#### 📦 対象の原料入荷記録")
                st.dataframe(pd.DataFrame(arr_info)[["入荷No","入荷日","メーカー","原料種別","ロットNo","袋数"]], use_container_width=True, hide_index=True)
            
            res_fwd = []
            for b in brewing:
                is_match = False
                for l_key in ["主原料ロット", "海藻粉ロット", "デンプンロット"]:
                    if kw_fwd and kw_fwd.lower() in str(b.get(l_key,"")).lower(): is_match = True
                if maker_fwd and b.get("メーカー") == maker_fwd: is_match = True
                
                if b.get("その他添加物") and kw_fwd:
                    try:
                        for o in json.loads(b.get("その他添加物")):
                            if kw_fwd.lower() in str(o.get("lot","")).lower(): is_match = True
                    except: pass
                    
                if is_match:
                    res_fwd.append({"仕込No": b.get("仕込No",""), "仕込日": b.get("仕込日",""), "品名": b.get("品名",""), "メーカー": b.get("メーカー",""), "主原料ロット": b.get("主原料ロット",""), "海藻粉ロット": b.get("海藻粉ロット",""), "デンプンロット": b.get("デンプンロット","")})
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
            if kw_date: target_brews = [b for b in target_brews if b.get("仕込日") == str(kw_date).replace("-","/")]
            if kw_prod: target_brews = [b for b in target_brews if kw_prod.lower() in str(b.get("品名","")).lower()]

            if not target_brews: st.warning("該当する仕込み記録が見つかりません。")
            else:
                for tb in target_brews:
                    st.markdown(f"### 🧪 仕込No: {tb.get('仕込No')} - {tb.get('仕込日')} 【{tb.get('品名')}】")
                    used_lots = []
                    for k, n in [("主原料ロット","こんにゃく粉"), ("海藻粉ロット","海藻粉"), ("デンプンロット","加工デンプン")]:
                        if tb.get(k) and tb.get(k) != "─": used_lots.append({"役割": n, "ロットNo": tb.get(k)})
                    if tb.get("その他添加物"):
                        try:
                            for o in json.loads(tb.get("その他添加物")):
                                if o.get("lot") and o.get("lot") != "─": used_lots.append({"役割": o.get("name","添加物"), "ロットNo": o.get("lot")})
                        except: pass
                    st.dataframe(pd.DataFrame(used_lots), use_container_width=True, hide_index=True)
                    st.markdown("---")
        st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
elif page == "📈 統計・比較分析":
    st.markdown('<div class="main-header"><div><h1>📈 統計・比較分析</h1><p>こんにゃく粉(袋換算)と添加物の使用量推移と前期間比較</p></div></div>', unsafe_allow_html=True)
    if not brewing: st.info("データがありません"); st.stop()
    
    df = pd.DataFrame(brewing)
    df["仕込日"] = df["仕込日"].astype(str).str.replace("/", "-").str.replace(".", "-")
    df["仕込日"] = pd.to_datetime(df["仕込日"], errors="coerce")
    df = df.dropna(subset=["仕込日"])
    
    for c in ["仕込量(kg)", "こんにゃく精粉(kg)", "海藻粉(kg)", "デンプン(kg)", "石灰(kg)"]: 
        df[c] = df[c].astype(str).str.replace(",", "").str.replace(" ", "")
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        
    df["こんにゃく粉(袋)"] = (df["こんにゃく精粉(kg)"] / 20.0).round(1)
    df.rename(columns={"こんにゃく精粉(kg)": "こんにゃく粉(kg)"}, inplace=True)
    
    pt = st.radio("集計単位を選択", ["日別", "月別", "年別"], horizontal=True, key="pt_sel")
    if pt == "日別": df["period"] = df["仕込日"].dt.date.astype(str)
    elif pt == "月別": df["period"] = df["仕込日"].dt.to_period("M").astype(str)
    else: df["period"] = df["仕込日"].dt.to_period("Y").astype(str)
    
    grp = df.groupby("period").agg(
        仕込回数=("仕込No", "count"), 
        製品仕込量=("仕込量(kg)", "sum"), 
        こんにゃく粉_袋=("こんにゃく粉(袋)", "sum"),
        こんにゃく粉_kg=("こんにゃく粉(kg)", "sum"),
        海藻粉=("海藻粉(kg)", "sum"),
        加工デンプン=("デンプン(kg)", "sum"),
        石灰=("石灰(kg)", "sum")
    ).reset_index().sort_values("period")
    
    other_data = []
    for _, r in df.iterrows():
        period = r["period"]
        if r.get("その他添加物"):
            try:
                for o in json.loads(r["その他添加物"]):
                    name = o.get("name")
                    kg = float(str(o.get("kg") or 0).replace(",",""))
                    if name and kg > 0:
                        other_data.append({"period": period, "name": name, "kg": kg})
            except: pass
            
    if other_data:
        df_others = pd.DataFrame(other_data)
        others_pivot = df_others.groupby(["period", "name"])["kg"].sum().unstack(fill_value=0).reset_index()
        grp = pd.merge(grp, others_pivot, on="period", how="left").fillna(0)
        
    grp["歩留まり(倍)"] = (grp["製品仕込量"] / grp["こんにゃく粉_kg"].replace(0, float("nan"))).round(2)
    
    st.markdown('<div class="section-title">📊 直近実績 と 前期間比較</div>', unsafe_allow_html=True)
    if len(grp) >= 2:
        curr = grp.iloc[-1]
        prev = grp.iloc[-2]
        
        m1, m2, m3, m4 = st.columns(4)
        def _delta(c, p): return f"{(c - p) / p * 100:+.1f}%" if p else "N/A"
        
        m1.metric(f"最新仕込回数 ({curr['period']})", f"{curr['仕込回数']:.0f}回", _delta(curr['仕込回数'], prev['仕込回数']))
        m2.metric("製品仕込量", f"{curr['製品仕込量']:,.0f} kg", _delta(curr['製品仕込量'], prev['製品仕込量']))
        m3.metric("こんにゃく粉(袋)", f"{curr['こんにゃく粉_袋']:,.1f} 袋", _delta(curr['こんにゃく粉_袋'], prev['こんにゃく粉_袋']))
        m4.metric("歩留まり", f"{curr['歩留まり(倍)']:.2f} 倍", f"{curr['歩留まり(倍)'] - prev['歩留まり(倍)']:+.2f}")
    else:
        st.info("比較するための過去データが不足しています。")
    
    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["📈 こんにゃく粉 と 生産量トレンド", "📊 全添加物の使用内訳", "📋 使用比率データ表"])
    
    with tab1:
        fig1 = go.Figure()
        fig1.add_trace(go.Bar(x=grp["period"], y=grp["こんにゃく粉_袋"], name="こんにゃく粉(袋)", marker_color="#43a047"))
        fig1.add_trace(go.Bar(x=grp["period"], y=grp["製品仕込量"], name="製品仕込量(kg)", marker_color="#1565c0", yaxis="y2"))
        fig1.add_trace(go.Scatter(x=grp["period"], y=grp["歩留まり(倍)"], name="歩留まり(倍)", yaxis="y3", mode="lines+markers", line=dict(color="#f57f17", width=3)))
        fig1.update_layout(
            barmode="group", height=450, plot_bgcolor="#f8faff",
            yaxis=dict(title="こんにゃく粉 (袋)"),
            yaxis2=dict(title="製品仕込量 (kg)", overlaying="y", side="right", showgrid=False),
            yaxis3=dict(title="歩留まり(倍)", overlaying="y", side="right", position=0.95, showgrid=False),
            legend=dict(orientation="h", y=-0.15)
        )
        st.plotly_chart(fig1, use_container_width=True)
        
    with tab2:
        base_additives = ["海藻粉", "加工デンプン", "石灰"]
        other_additives = [c for c in grp.columns if c not in ["period", "仕込回数", "製品仕込量", "歩留まり(倍)", "こんにゃく粉_袋", "こんにゃく粉_kg"] + base_additives]
        col_g1, col_g2 = st.columns([7, 3])
        with col_g1:
            fig2 = go.Figure()
            colors = ["#e53935", "#fb8c00", "#8e24aa", "#3949ab", "#1e88e5", "#039be5", "#00acc1", "#00897b", "#00838f"]
            for i, mat in enumerate(base_additives + other_additives):
                if mat in grp.columns:
                    fig2.add_trace(go.Bar(x=grp["period"], y=grp[mat], name=mat, marker_color=colors[i % len(colors)]))
            fig2.update_layout(barmode="stack", height=400, plot_bgcolor="#f8faff", yaxis=dict(title="使用量 (kg)"), legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig2, use_container_width=True)
            
        with col_g2:
            if len(grp) > 0:
                latest = grp.iloc[-1]
                pie_data = {mat: latest[mat] for mat in base_additives + other_additives if mat in latest and latest[mat] > 0}
                if pie_data:
                    fig_pie = px.pie(names=list(pie_data.keys()), values=list(pie_data.values()), title=f"添加物割合 ({latest['period']})", hole=0.4)
                    fig_pie.update_layout(height=400, showlegend=False)
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_pie, use_container_width=True)
        
    with tab3:
        st.info("※ こんにゃく粉の重量(kg)を100%とした場合の、各添加物の使用比率です。毎日のレシピのブレを確認できます。")
        ratio_df = grp[["period", "仕込回数", "製品仕込量", "こんにゃく粉_袋", "歩留まり(倍)"]].copy()
        for mat in base_additives + other_additives:
            if mat in grp.columns:
                ratio_df[f"{mat} 比率(%)"] = (grp[mat] / grp["こんにゃく粉_kg"].replace(0, float("nan")) * 100).round(2)
        st.dataframe(ratio_df.sort_values("period", ascending=False), use_container_width=True)

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
        st.info("衛生備品や梱包資材の登録を行います。PCやスマホから直接画像をアップロード可能です。")
        with st.form("new_supply_form"):
            sc1, sc2, sc3, sc_op = st.columns(4)
            n_name  = sc1.text_input("資材名 ＊")
            n_cat   = sc2.text_input("カテゴリ (例: 衛生, 梱包)")
            n_stock = sc3.number_input("初期在庫", min_value=0, step=1)
            n_order = sc_op.number_input("発注点(警告)", min_value=0, step=1)
            
            sc4, sc5 = st.columns(2)
            n_file = sc4.file_uploader("📷 写真・画像をアップロード", type=["png","jpg","jpeg"])
            n_url  = sc5.text_input("🌐 または画像のURLを指定")
            
            if st.form_submit_button("➕ 新規資材を登録"):
                if not n_name:
                    st.error("資材名を入力してください")
                else:
                    img_val = "https://cdn-icons-png.flaticon.com/512/1243/1243324.png"
                    if n_file and HAS_PIL:
                        img = Image.open(n_file)
                        img.thumbnail((200, 200))
                        buf = BytesIO()
                        img.save(buf, format="PNG")
                        img_val = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
                    elif n_url:
                        img_val = n_url
                        
                    current_supplies = supplies.copy()
                    current_supplies.append({
                        "資材ID": f"SUP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "資材名": n_name, "カテゴリ": n_cat, "画像URL": img_val, 
                        "初期在庫": n_stock, "発注点": n_order
                    })
                    save_supplies(current_supplies)
                    st.success(f"{n_name} を登録しました！")
                    refresh()

        st.markdown("#### 登録済み資材の一覧・削除")
        if supplies:
            del_sup = st.selectbox("削除する資材を選択", ["─"] + [s.get("資材名","") for s in supplies])
            if st.button("🗑 選択した資材を削除"):
                if del_sup != "─":
                    save_supplies([s for s in supplies if s.get("資材名") != del_sup])
                    st.success("削除しました")
                    refresh()
                    
            df_s = pd.DataFrame(supplies)[["画像URL", "資材名", "カテゴリ", "初期在庫", "発注点"]]
            st.dataframe(
                df_s,
                column_config={"画像URL": st.column_config.ImageColumn("画像")},
                use_container_width=True, hide_index=True
            )
# --- END OF FILE app.py ---
