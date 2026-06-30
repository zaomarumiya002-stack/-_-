# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import json
from datetime import datetime, date, timedelta
import traceback

st.set_page_config(
    page_title="原料管理システム",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ════════════════════════════════════════════════════════════════
#  CSS スタイル定義（モバイル・タブレット最適化）
# ════════════════════════════════════════════════════════════════
st.markdown("""
<style>
:root {
    --c-bg: #f8fafc;
    --c-surface: #ffffff;
    --c-primary: #1e3a8a;
    --c-border: #cbd5e1;
}
.stApp { background: var(--c-bg); }

/* モバイルの入力欄を太く、指先で押しやすく調整 */
.stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea, .stDateInput input {
    background-color: var(--c-surface) !important;
    border: 2px solid var(--c-border) !important;
    border-radius: 8px !important;
    color: #0f172a !important;
    font-size: 1rem !important;
    padding: 10px !important;
    min-height: 46px;
}

label { 
    color: #334155 !important; 
    font-weight: 700 !important; 
    font-size: 0.85rem !important; 
    margin-bottom: 4px;
}

.main-header {
    background: linear-gradient(135deg, #1e3a8a, #2563eb);
    padding: 18px 24px;
    border-radius: 12px;
    margin-bottom: 20px;
    color: white;
}
.main-header h1 {
    font-size: 1.6rem !important;
    margin: 0 !important;
    font-weight: 800 !important;
}

.form-card {
    background: var(--c-surface);
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.02);
}

.section-title {
    font-size: 1rem;
    font-weight: 800;
    color: var(--c-primary);
    margin-bottom: 12px;
    border-left: 4px solid var(--c-primary);
    padding-left: 8px;
}

.alert-ng {
    background-color: #fee2e2;
    border-left: 5px solid #ef4444;
    color: #991b1b;
    padding: 12px;
    border-radius: 6px;
    margin-bottom: 10px;
    font-size: 0.85rem;
    font-weight: bold;
}
.alert-warning {
    background-color: #fef3c7;
    border-left: 5px solid #f59e0b;
    color: #92400e;
    padding: 12px;
    border-radius: 6px;
    margin-bottom: 10px;
    font-size: 0.85rem;
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
#  スプレッドシート連携モジュール接続の安全確認
# ════════════════════════════════════════════════════════════════
try:
    import sheets
    SHEETS_OK = True
except Exception as e:
    st.error("🚨 `sheets.py`（スプレッドシート連携モジュール）のインポート時にエラーが発生しました。")
    st.markdown("### エラーの推定原因:")
    st.info("1. Streamlit Secrets のサービスアカウントキー設定（`gcp_service_account` や `sheet_id`）に誤りがあるか設定されていません。\n"
            "2. 必要な外部ライブラリ（`gspread` 等）がインストールされていません。")
    st.write("詳細なエラーログ:")
    st.code(traceback.format_exc())
    st.stop()

def refresh():
    st.cache_data.clear()
    st.rerun()

# データの読込（例外発生時のトレースバックを詳細表示）
try:
    arrivals = sheets.load_arrivals()
    brewing = sheets.load_brewing()
    adjustments = sheets.load_adjustments()
    supplies = sheets.load_supplies()
    supply_logs = sheets.load_supply_logs()
    materials = sheets.load_materials()
    makers = sheets.load_makers()
    inspectors = sheets.load_inspectors()
    order_points = sheets.load_order_points()
except Exception as e:
    st.error("🚨 Google スプレッドシートからのデータ読み込みに失敗しました。認証情報またはスプレッドシートIDを再確認してください。")
    st.code(traceback.format_exc())
    st.stop()

# ════════════════════════════════════════════════════════════════
#  現在庫計算ロジック（スプレッドシートの日本語キー名に完全準拠）
# ════════════════════════════════════════════════════════════════
def get_inventory():
    inv = {}
    for a in arrivals:
        ano = str(a.get("入荷No", "")).strip()
        if not ano: continue
        inv[ano] = {
            "入荷No": ano, 
            "ロットNo": str(a.get("ロットNo", "")).strip(), 
            "メーカー": str(a.get("メーカー", "")).strip(),
            "原料種別": str(a.get("原料種別", "")).strip(), 
            "1袋重量": float(a.get("1袋重量(kg)") or 20.0),
            "入荷袋数": float(a.get("袋数") or 0.0), 
            "使用量(kg)": 0.0, 
            "調整袋数": 0.0
        }

    # 各仕込み消費量の集計
    for b in brewing:
        m_lot = str(b.get("主原料ロット", "")).strip()
        m_kg = float(b.get("こんにゃく精粉(kg)") or 0.0)
        
        s_lot = str(b.get("海藻粉ロット", "")).strip()
        s_kg = float(b.get("海藻粉(kg)") or 0.0)
        
        st_lot = str(b.get("デンプンロット", "")).strip()
        st_kg = float(b.get("デンプン(kg)") or 0.0)

        for v in inv.values():
            if m_lot and v["ロットNo"] == m_lot: v["使用量(kg)"] += m_kg
            if s_lot and v["ロットNo"] == s_lot: v["使用量(kg)"] += s_kg
            if st_lot and v["ロットNo"] == st_lot: v["使用量(kg)"] += st_kg

    for adj in adjustments:
        ano = str(adj.get("入荷No", "")).strip()
        if ano in inv:
            inv[ano]["調整袋数"] += float(adj.get("調整袋数") or 0.0)

    for v in inv.values():
        bpk = v["1袋重量"] if v["1袋重量"] > 0 else 20.0
        v["使用袋数"] = v["使用量(kg)"] / bpk
        v["現在庫(袋)"] = v["入荷袋数"] - v["使用袋数"] + v["調整袋数"]
        v["現在庫(kg)"] = v["現在庫(袋)"] * bpk
    return inv

inventory_data = get_inventory()

# 原料種別ごとの現在庫集計
type_totals = {}
for v in inventory_data.values():
    m_type = v["原料種別"]
    type_totals[m_type] = type_totals.get(m_type, 0.0) + v["現在庫(袋)"]

# ════════════════════════════════════════════════════════════════
#  サイドバー
# ════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🏭 製造管理 ERP")
    page = st.radio("機能メニュー", [
        "🏠 ダッシュボード", 
        "📦 原料入荷登録", 
        "🧪 仕込み・配合記録", 
        "🏭 原料在庫・棚卸", 
        "🧹 資材備品管理", 
        "🔍 双方向トレース", 
        "⚙️ マスタ設定"
    ])
    st.markdown("---")
    if st.button("🔄 データを手動更新", use_container_width=True):
        refresh()

# ════════════════════════════════════════════════════════════════
#  1. ダッシュボード
# ════════════════════════════════════════════════════════════════
if page == "🏠 ダッシュボード":
    st.markdown('<div class="main-header"><h1>📊 生産・在庫ダッシュボード</h1><p>工場の在庫状況およびアラート監視</p></div>', unsafe_allow_html=True)
    
    # 警告ロジック
    alerts = []
    for m in materials:
        current_bags = type_totals.get(m, 0.0)
        point = order_points.get(m, 0.0)
        if current_bags < point:
            alerts.append(f"🚨 【発注警告】{m} の在庫（{current_bags:.1f} 袋）が発注基準値（{point:.1f} 袋）を下回っています。")
            
    if alerts:
        for al in alerts:
            st.markdown(f'<div class="alert-ng">{al}</div>', unsafe_allow_html=True)
    else:
        st.success("🟢 すべての原料在庫は安全基準値を超えています。")

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown('<div class="section-title">⚖️ 原料・添加物 在庫状況</div>', unsafe_allow_html=True)
        for m in materials:
            current_val = type_totals.get(m, 0.0)
            threshold_val = order_points.get(m, 0.0)
            
            # 簡易表示（不具合の出ないマークアップ）
            st.metric(label=f"{m} (袋数)", value=f"{current_val:,.1f} 袋", delta=f"発注点: {threshold_val:,.1f} 袋", delta_color="inverse" if current_val < threshold_val else "normal")

    with col_g2:
        st.markdown('<div class="section-title">⏱️ 直近の製造仕込み（最新5件）</div>', unsafe_allow_html=True)
        if brewing:
            df_brw = pd.DataFrame(brewing)[["仕込No", "仕込日", "品名", "仕込量(kg)", "主原料ロット"]]
            st.dataframe(df_brw.tail(5)[::-1], use_container_width=True, hide_index=True)
        else:
            st.info("登録済みの製造履歴はありません。")

# ════════════════════════════════════════════════════════════════
#  2. 原料入荷登録
# ════════════════════════════════════════════════════════════════
elif page == "📦 原料入荷登録":
    st.markdown('<div class="main-header"><h1>📦 原料入荷品質記録</h1><p>入荷時の品質検査情報の登録と履歴一覧</p></div>', unsafe_allow_html=True)
    
    tab_a, tab_b = st.tabs(["➕ 新規入荷登録", "📋 入荷・品質検査履歴"])
    
    with tab_a:
        st.markdown('<div class="form-card"><div class="section-title">原料入荷情報</div>', unsafe_allow_html=True)
        new_no = next_arrival_no(arrivals)
        
        c1, c2 = st.columns(2)
        arr_no = c1.text_input("入荷No", value=new_no, disabled=True)
        arr_date = c2.date_input("入荷日", value=date.today())
        
        c3, c4 = st.columns(2)
        maker_sel = c3.selectbox("メーカー", makers + ["その他"])
        if maker_sel == "その他":
            maker_val = st.text_input("メーカー名を入力")
        else:
            maker_val = maker_sel
            
        lot_val = c4.text_input("ロットNo ＊")

        c5, c6 = st.columns(2)
        m_type = c5.selectbox("原料種別", materials)
        bags_qty = c6.number_input("入荷袋数", min_value=1, step=1, value=10)
        
        weight_per_bag = st.number_input("1袋重量 (kg)", min_value=1.0, value=20.0, step=0.5)
        st.info(f"💡 自動算出 合計重量: {bags_qty * weight_per_bag:,.1f} kg")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="form-card"><div class="section-title">🔍 受入検査</div>', unsafe_allow_html=True)
        cc1, cc2 = st.columns(2)
        chk_app = cc1.selectbox("① 外観", ["OK（正常）", "NG（異常あり）"])
        chk_spec = cc2.selectbox("② 品名・規格確認", ["OK（一致）", "NG（不一致）"])
        chk_exp = cc1.selectbox("③ 賞味期限", ["OK（期限内）", "NG（期限切れ）"])
        chk_dmg = cc2.selectbox("④ 異物・破損混入確認", ["OK（なし）", "NG（あり）"])
        
        abn_desc = ""
        if "NG" in [chk_app, chk_spec, chk_exp, chk_dmg]:
            abn_desc = st.text_input("⚠️ 異常内容の詳細", placeholder="異常詳細を入力")
            
        inspector_val = st.selectbox("受入検査担当者", inspectors)
        remarks_val = st.text_input("備考")
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("✅ 入荷記録を登録する", type="primary", use_container_width=True):
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
            df_arr = pd.DataFrame(arrivals)[["入荷No", "入荷日", "メーカー", "ロットNo", "原料種別", "袋数", "外観", "品名・規格確認", "賞味期限", "異物", "担当者"]]
            st.dataframe(df_arr[::-1], use_container_width=True, hide_index=True)
        else:
            st.info("過去の入荷記録はありません。")

# ═══════════════════════════════════════════════════════════════
#  3. 仕込み・配合記録（マスタ連動＆警告機能）
# ═══════════════════════════════════════════════════════════════
elif page == "🧪 仕込み・配合記録":
    st.markdown('<div class="main-header"><h1>🧪 製造仕込み・配合計算</h1><p>配合比率に基づく投入量の自動算出と実績調整</p></div>', unsafe_allow_html=Tr
