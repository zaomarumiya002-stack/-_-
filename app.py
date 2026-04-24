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
.alert-ng { background:#ffebee; border-left:4px solid #c62828; padding:12px 16px; border-radius:8px; color:#b71c1c; font-weight:600; margin-bottom:10px; display:flex; align-items:center;}
</style>
""", unsafe_allow_html=True)

try:
    from sheets import (load_arrivals, append_arrival, load_brewing, append_brewing, load_adjustments, append_adjustment,
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
    page = st.radio("メニュー", ["🏠 ダッシュボード", "📦 入荷記録", "🧪 仕込み記録", "🏭 在庫管理", "🔍 原料トレース", "📊 集計・分析", "⚙️ マスター設定"], label_visibility="collapsed")
    if st.button("🔄 最新データに更新", use_container_width=True): st.cache_data.clear(); st.rerun()

if not SHEETS_OK: st.error(f"接続エラー: {SHEETS_ERROR}"); st.stop()

@st.cache_data(ttl=60)
def fetch_all(): return load_arrivals(), load_brewing(), load_adjustments(), load_materials(), load_makers(), load_inspectors(), load_order_points()
arrivals, brewing, adjustments, materials, makers, inspectors, order_points = fetch_all()

# --- 高速在庫計算（袋単位に変更） ---
@st.cache_data(ttl=60)
def calc_inventory(arrivals_list, brewing_list, adj_list):
    inv = {a["arrival_no"]: {
        "arrival_no": a["arrival_no"], "lot_no": a["lot_no"], "maker": a["maker"],
        "material_type": a["material_type"], 
        "bags_per_kg": float(a.get("bags_per_kg") or 20.0), # デフォルト20kg
        "total_in_bags": float(a.get("bags") or 0), 
        "total_out_kg": 0.0, "adj_bags": 0.0
    } for a in arrivals_list}
    
    for b in brewing_list:
        for lot_key, kg_key in [("lot_no","material_kg"), ("seaweed_lot","seaweed_kg"), ("starch_lot","starch_kg")]:
            lot_val = b.get(lot_key)
            if lot_val and lot_val != "─":
                m = [k for k, v in inv.items() if v["lot_no"] == lot_val]
                if m: inv[m[0]]["total_out_kg"] += float(b.get(kg_key) or 0)
        if b.get("other_additives"):
            try:
                for o in json.loads(b["other_additives"]):
                    if o.get("lot") and o["lot"] != "─":
                        m = [k for k, v in inv.items() if v["lot_no"] == o["lot"]]
                        if m: inv[m[0]]["total_out_kg"] += float(o.get("kg") or 0)
            except: pass
            
    # 在庫調整（袋単位）
    for adj in adj_list:
