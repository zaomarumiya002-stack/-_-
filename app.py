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
.kpi-card { background:#fff; border-radius:12px; padding:16px 18px; box-shadow:0 1px 6px rgba(0,0,0,.07); border-top:3px solid #1565c0; text-align:center; }
.kpi-value { font-size:2rem; font-weight:700; color:#1a237e; line-height:1.15; }
.kpi-label { font-size:.8rem; color:#78909c; margin-top:4px; font-weight:500;}
.alert-ng { background:#fff3f3; border:1px solid #ffcdd2; border-left:4px solid #e53935; padding:10px 14px; border-radius:8px; color:#b71c1c; font-size:.88rem; font-weight:600; margin-bottom:8px; display:flex; align-items:center;}
.alert-warning { background:#fff8e1; border:1px solid #ffecb3; border-left:4px solid #ff9800; padding:10px 14px; border-radius:8px; color:#e65100; font-size:.88rem; font-weight:600; margin-bottom:8px; display:flex; align-items:center;}
.form-card { background:#ffffff; border:1px solid #cfd8dc; border-radius:12px; padding:20px; margin-bottom:20px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);}
.section-title { font-size:1.05rem; font-weight:700; color:#1565c0; border-bottom:2px solid #e3f2fd; padding-bottom:6px; margin-bottom:16px; }
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
    for sid, v in inv.items
