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
    st.markdown('<div class="main-header"><h1>🧪 製造仕込み・配合計算</h1><p>配合比率に基づく投入量の自動算出と実績調整</p></div>', unsafe_allow_html=True)
    
    if "recipe_master" not in st.session_state:
        st.session_state.recipe_master = {
            "通常こんにゃく (国産原料)": {"こんにゃく精粉(kg)": 25.0, "海藻粉(kg)": 1.0, "デンプン(kg)": 5.0, "石灰(kg)": 2.0},
            "白こんにゃく (海藻不使用)": {"こんにゃく精粉(kg)": 24.0, "海藻粉(kg)": 0.0, "デンプン(kg)": 4.0, "石灰(kg)": 1.8},
            "手延べ風太麺": {"こんにゃく精粉(kg)": 30.0, "海藻粉(kg)": 1.5, "デンプン(kg)": 8.0, "石灰(kg)": 2.5}
        }

    tab_brw1, tab_brw2 = st.tabs(["🧪 配合計算・登録", "📋 仕込み履歴"])
    
    with tab_brw1:
        st.markdown('<div class="form-card"><div class="section-title">製品名と希望仕込み量の指定</div>', unsafe_allow_html=True)
        
        recipe_opts = list(st.session_state.recipe_master.keys()) + ["直接入力（マスタ外）"]
        selected_p = st.selectbox("製品名", recipe_opts)
        
        if selected_p == "直接入力（マスタ外）":
            p_name = st.text_input("品名を手動入力")
            standard_recipe = {"こんにゃく精粉(kg)": 25.0, "海藻粉(kg)": 1.0, "デンプン(kg)": 5.0, "石灰(kg)": 2.0}
        else:
            p_name = selected_p
            standard_recipe = st.session_state.recipe_master[selected_p]

        standard_sum = sum(standard_recipe.values())
        target_size = st.number_input("希望仕込製品量 (kg)", min_value=1.0, value=100.0, step=10.0)
        
        scale_ratio = target_size / 100.0 if selected_p != "直接入力（マスタ外）" else 1.0
        
        rec_k = standard_recipe.get("こんにゃく精粉(kg)", 0.0) * scale_ratio
        rec_s = standard_recipe.get("海藻粉(kg)", 0.0) * scale_ratio
        rec_st = standard_recipe.get("デンプン(kg)", 0.0) * scale_ratio
        rec_l = standard_recipe.get("石灰(kg)", 0.0) * scale_ratio

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="form-card"><div class="section-title">投入量実績値 (微調整可能)</div>', unsafe_allow_html=True)
        
        cx1, cx2 = st.columns(2)
        actual_k = cx1.number_input("こんにゃく精粉投入量 (kg)", min_value=0.0, value=rec_k, step=0.5)
        actual_s = cx2.number_input("海藻粉投入量 (kg)", min_value=0.0, value=rec_s, step=0.1)
        actual_st = cx1.number_input("加工デンプン投入量 (kg)", min_value=0.0, value=rec_st, step=0.5)
        actual_l = cx2.number_input("石灰投入量 (kg)", min_value=0.0, value=rec_l, step=0.1)

        st.markdown("<br><b>投入原料ロットの紐付け</b>", unsafe_allow_html=True)
        lots_list = ["─"] + sorted(list(set([str(a.get("ロットNo", "")).strip() for a in arrivals if a.get("ロットNo")])), reverse=True)
        
        col_lot1, col_lot2 = st.columns(2)
        lot_k_val = col_lot1.selectbox("主原料ロット", lots_list, key="b_lot_k")
        lot_s_val = col_lot2.selectbox("海藻粉ロット", lots_list, key="b_lot_s")
        lot_st_val = col_lot1.selectbox("加工デンプンロット", lots_list, key="b_lot_st")
        st.markdown('</div>', unsafe_allow_html=True)

        # 配合比の誤差チェック
        if selected_p != "直接入力（マスタ外）":
            actual_total = actual_k + actual_s + actual_st + actual_l
            if actual_total > 0:
                expected_pct = standard_recipe.get("こんにゃく精粉(kg)", 0.0) / standard_sum
                actual_pct = actual_k / actual_total
                
                if abs(actual_pct - expected_pct) > 0.05:
                    st.warning("⚠️ 警告: 標準マスタの配合比率から5%以上の乖離が発生しています。投入量を再確認してください。")

        if st.button("✅ この実績で仕込み記録を登録する", type="primary", use_container_width=True):
            if not p_name:
                st.error("品名が設定されていません。")
            else:
                sheets.append_brewing({
                    "仕込No": sheets.next_brewing_no(brewing), "仕込日": str(date.today()), "品名": p_name,
                    "メーカー": "自社", "主原料ロット": lot_k_val, "仕込量(kg)": target_size,
                    "こんにゃく精粉(kg)": actual_k, "海藻粉(kg)": actual_s, "海藻粉ロット": lot_s_val,
                    "デンプン(kg)": actual_st, "デンプンロット": lot_st_val, "デンプン種別": "-",
                    "石灰(kg)": actual_l, "石灰水(L)": 0, "その他添加物": "[]", "備考": "配合マスタ連動",
                    "登録日時": datetime.now().isoformat()
                })
                st.success("仕込み実績を記録しました。")
                refresh()

    with tab_brw2:
        if brewing:
            df_brw_all = pd.DataFrame(brewing)[["仕込No", "仕込日", "品名", "仕込量(kg)", "こんにゃく精粉(kg)", "主原料ロット", "海藻粉ロット"]]
            st.dataframe(df_brw_all[::-1], use_container_width=True, hide_index=True)
        else:
            st.info("過去の製造仕込み履歴はありません。")

# ═══════════════════════════════════════════════════════════════
#  4. 原料在庫・棚卸
# ═══════════════════════════════════════════════════════════════
elif page == "🏭 原料在庫・棚卸":
    st.markdown('<div class="main-header"><h1>🏭 原料在庫状況と調整</h1><p>現在庫のロット別自動算出と、実地棚卸ズレ修正</p></div>', unsafe_allow_html=True)
    
    tab_inv1, tab_inv2 = st.tabs(["📋 ロット別現在庫一覧", "⚖️ 棚卸し在庫調整"])
    
    with tab_inv1:
        st.markdown('<div class="section-title">ロットごとの詳細現在庫</div>', unsafe_allow_html=True)
        active_inv = [v for v in inventory_data.values() if abs(v["現在庫(袋)"]) > 0.001]
        if active_inv:
            df_curr_inv = pd.DataFrame(active_inv)[["入荷No", "原料種別", "ロットNo", "メーカー", "入荷袋数", "使用袋数", "調整袋数", "現在庫(袋)"]]
            st.dataframe(df_curr_inv, use_container_width=True, hide_index=True)
        else:
            st.info("現在庫のあるロットはありません。")

    with tab_inv2:
        st.markdown('<div class="form-card"><div class="section-title">棚卸による理論在庫ズレ調整</div>', unsafe_allow_html=True)
        if not inventory_data:
            st.warning("調整対象となる入荷情報が存在しません。")
        else:
            tgt_list = {f"{v['入荷No']} - {v['原料種別']} (ロット:{v['ロットNo']})": v["入荷No"] for v in inventory_data.values()}
            selected_tgt = st.selectbox("調整対象ロット", list(tgt_list.keys()))
            target_ano = tgt_list[selected_tgt]

            diff_bags = st.number_input("理論在庫との差分（袋数単位）", step=1.0, value=0.0)
            reason_txt = st.text_input("調整の理由", placeholder="例: 実地棚卸との差分修正")
            operator = st.selectbox("調整実施者", inspectors)

            if st.button("⚖️ 在庫データを上書き調整する", type="primary", use_container_width=True):
                sheets.append_adjustment({
                    "調整ID": f"ADJ-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "入荷No": target_ano,
                    "調整日": str(date.today()),
                    "調整袋数": diff_bags,
                    "理由": reason_txt,
                    "担当者": operator,
                    "登録日時": datetime.now().isoformat()
                })
                st.success("調整情報を書き込みました。在庫表を再構築します。")
                refresh()
        st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
#  5. 資材備品管理
# ═══════════════════════════════════════════════════════════════
elif page == "🧹 資材備品管理":
    st.markdown('<div class="main-header"><h1>🧹 資材・消耗品在庫管理</h1><p>資材の残量管理および入出庫の登録・削除</p></div>', unsafe_allow_html=True)
    
    tab_s1, tab_s2 = st.tabs(["📥 入出庫登録", "🕒 ログ管理と調整"])
    
    with tab_s1:
        if not supplies:
            st.warning("資材マスターが未登録です。マスタ設定よりご登録ください。")
        else:
            st.markdown('<div class="form-card"><div class="section-title">資材入出庫の記録</div>', unsafe_allow_html=True)
            col_sc1, col_sc2 = st.columns(2)
            sup_name = col_sc1.selectbox("資材名", [s.get("資材名") for s in supplies])
            action_type = col_sc2.selectbox("処理内容", ["➕ 補充する (入荷)", "➖ 使用する (出庫)"])
            
            qty_val = st.number_input("数量", min_value=1.0, value=1.0, step=1.0)
            operator_val = st.selectbox("作業担当者", inspectors, key="op_sup")
            notes_val = st.text_input("備考情報")
            
            if st.button("💾 資材変動を保存する", type="primary", use_container_width=True):
                target_sup = next(s for s in supplies if s.get("資材名") == sup_name)
                sheets.append_supply_log({
                    "ログID": f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                    "登録日": str(date.today()),
                    "資材ID": target_sup.get("資材ID"),
                    "処理": "入荷" if "補充" in action_type else "使用",
                    "数量": qty_val,
                    "作業者": operator_val,
                    "備考": notes_val,
                    "登録日時": datetime.now().isoformat()
                })
                st.success("資材情報を記録しました。")
                refresh()
            st.markdown('</div>', unsafe_allow_html=True)

    with tab_s2:
        st.markdown('<div class="section-title">入出庫ログ一覧（最新20件）</div>', unsafe_allow_html=True)
        if supply_logs:
            id_name_map = {s.get("資材ID"): s.get("資材名") for s in supplies}
            df_logs = pd.DataFrame(supply_logs).copy()
            df_logs["資材名"] = df_logs["資材ID"].map(id_name_map)
            
            st.dataframe(df_logs.tail(20)[::-1], use_container_width=True, hide_index=True)
            
            # 個別ログ削除
            st.markdown("---")
            st.markdown('<div class="section-title">🚨 特定ログの取り消し・削除</div>', unsafe_allow_html=True)
            log_id_to_del = st.text_input("削除するログIDを入力してください")
            if st.button("🗑️ このログIDを完全に削除する"):
                if log_id_to_del:
                    sheets.delete_supply_log(log_id_to_del)
                    st.success("ログを削除しました。")
                    refresh()
        else:
            st.info("資材入出庫履歴はありません。")

# ═══════════════════════════════════════════════════════════════
#  6. 双方向トレース
# ═══════════════════════════════════════════════════════════════
elif page == "🔍 双方向トレース":
    st.markdown('<div class="main-header"><h1>🔍 双方向原料トレース (HACCP対応)</h1><p>原料の入荷情報から製造製品、あるいは製品から使用した原料を特定します</p></div>', unsafe_allow_html=True)
    
    trace_dir = st.radio("トレース方向", ["➡️ 原料ロットから製品を追跡（フォワード）", "⬅️ 製品から原料を遡及（バックワード）"])
    
    if "フォワード" in trace_dir:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        lots_to_search = sorted(list(set([str(a.get("ロットNo", "")).strip() for a in arrivals if a.get("ロットNo")])), reverse=True)
        if not lots_to_search:
            st.info("利用可能なロット番号が見つかりません。")
        else:
            target_lot = st.selectbox("検索する原料ロット番号", lots_to_search)
            
            if st.button("➡️ 追跡を開始する", type="primary", use_container_width=True):
                # 入荷情報
                match_arr = [a for a in arrivals if str(a.get("ロットNo", "")).strip() == target_lot]
                if match_arr:
                    st.markdown("##### 📦 入荷・受け入れ情報")
                    st.dataframe(pd.DataFrame(match_arr)[["入荷No", "入荷日", "原料種別", "メーカー", "袋数", "外観", "担当者"]], use_container_width=True, hide_index=True)
                
                # 製造消費実績
                match_brw = []
                for b in brewing:
                    if (str(b.get("主原料ロット", "")).strip() == target_lot or 
                        str(b.get("海藻粉ロット", "")).strip() == target_lot or 
                        str(b.get("デンプンロット", "")).strip() == target_lot):
                        match_brw.append(b)
                        
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
                st.json({
                    "仕込No": selected_b.get("仕込No"),
                    "製造日": selected_b.get("仕込日"),
                    "品名": selected_b.get("品名"),
                    "製造量 (kg)": selected_b.get("仕込量(kg)")
                })
                
                used_lots = []
                for k, label in [("主原料ロット", "主原料"), ("海藻粉ロット", "海藻粉"), ("デンプンロット", "加工デンプン")]:
                    lot_num = str(selected_b.get(k, "")).strip()
                    if lot_num and lot_num != "─" and lot_num != "":
                        used_lots.append({"原料種別": label, "ロットNo": lot_num})
                
                if used_lots:
                    st.markdown("##### 📦 使用原料の入荷元情報")
                    details = []
                    for u in used_lots:
                        arr_match = next((a for a in arrivals if str(a.get("ロットNo", "")).strip() == u["ロットNo"]), None)
                        if arr_match:
                            details.append({
                                "原料種別": u["原料種別"],
                                "ロットNo": u["ロットNo"],
                                "入荷No": arr_match.get("入荷No"),
                                "入荷日": arr_match.get("入荷日"),
                                "メーカー": arr_match.get("メーカー"),
                                "外観検査": arr_match.get("外観")
                            })
                        else:
                            details.append({
                                "原料種別": u["原料種別"],
                                "ロットNo": u["ロットNo"],
                                "入荷No": "不明",
                                "入荷日": "不明",
                                "メーカー": "不明",
                                "外観検査": "不明"
                            })
                    st.dataframe(pd.DataFrame(details), use_container_width=True, hide_index=True)
                else:
                    st.warning("この製造ロットで使用された原料ロットの記録はありません。")
        st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
#  7. マスタ設定
# ═══════════════════════════════════════════════════════════════
elif page == "⚙️ マスタ設定":
    st.markdown('<div class="main-header"><h1>⚙️ マスターデータ設定</h1><p>原料マスタ、メーカー、担当者リスト、発注基準値、資材設定の登録・削除</p></div>', unsafe_allow_html=True)
    
    m_tab1, m_tab2, m_tab3, m_tab4 = st.tabs(["⚗️ 原料マスタ", "🏢 メーカー・担当者", "🚨 原料発注点", "📦 新規資材登録"])
    
    with m_tab1:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        st.write("プルダウン等の選択リストに並ぶ原料種別の名称リストです。")
        df_materials = pd.DataFrame({"原料名": materials})
        edited_materials = st.data_editor(df_materials, num_rows="dynamic", use_container_width=True, key="mat_ed_k")
        
        if st.button("💾 原料マスタを更新する", type="primary"):
            cleaned_list = [str(x).strip() for x in edited_materials["原料名"].tolist() if str(x).strip()]
            sheets.save_materials(cleaned_list)
            st.success("原料マスター情報を保存しました。")
            refresh()
        st.markdown('</div>', unsafe_allow_html=True)

    with m_tab2:
        col_sub1, col_sub2 = st.columns(2)
        with col_sub1:
            st.markdown('<div class="form-card"><div class="section-title">取引先メーカー</div>', unsafe_allow_html=True)
            df_makers = pd.DataFrame({"メーカー名": makers})
            edited_makers = st.data_editor(df_makers, num_rows="dynamic", use_container_width=True, key="maker_ed_k")
            if st.button("💾 メーカーリストを保存する"):
                cleaned_makers = [str(x).strip() for x in edited_makers["メーカー名"].tolist() if str(x).strip()]
                sheets.save_makers(cleaned_makers)
                st.success("メーカー情報を保存しました。")
                refresh()
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col_sub2:
            st.markdown('<div class="form-card"><div class="section-title">検査・調整担当者</div>', unsafe_allow_html=True)
            df_inspectors = pd.DataFrame({"担当者名": inspectors})
            edited_inspectors = st.data_editor(df_inspectors, num_rows="dynamic", use_container_width=True, key="inspector_ed_k")
            if st.button("💾 担当者リストを保存する"):
                cleaned_inspectors = [str(x).strip() for x in edited_inspectors["担当者名"].tolist() if str(x).strip()]
                sheets.save_inspectors(cleaned_inspectors)
                st.success("担当者情報を保存しました。")
                refresh()
            st.markdown('</div>', unsafe_allow_html=True)

    with m_tab3:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        st.write("原料ごとに、アラートを発生させる在庫の閾値（袋数単位）を定義します。")
        op_rows = [{"原料名": m, "発注点(袋)": float(order_points.get(m, 0.0))} for m in materials]
        df_op = pd.DataFrame(op_rows)
        edited_op = st.data_editor(df_op, use_container_width=True, key="op_ed_k")
        
        if st.button("💾 発注点設定を更新する", type="primary"):
            new_op_dict = {}
            for _, r in edited_op.iterrows():
                name_val = str(r["原料名"]).strip()
                val_float = float(r["発注点(袋)"] or 0.0)
                if name_val:
                    new_op_dict[name_val] = val_float
            sheets.save_order_points(new_op_dict)
            st.success("発注点設定を保存しました。")
            refresh()
        st.markdown('</div>', unsafe_allow_html=True)

    with m_tab4:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        st.write("消耗品、フィルム、外箱などの資材マスターを新しく追加します。")
        with st.form("new_sup_form"):
            c_s1, c_s2 = st.columns(2)
            new_s_name = c_s1.text_input("資材名称 ＊")
            new_s_cat = c_s2.text_input("カテゴリ (例: 包材, ダンボール)")
            
            c_s3, c_s4 = st.columns(2)
            new_s_stock = c_s3.number_input("初期在庫数量", min_value=0.0, value=0.0)
            new_s_point = c_s4.number_input("アラート発注点", min_value=0.0, value=10.0)
            
            if st.form_submit_button("➕ この資材をマスターに登録する"):
                if not new_s_name:
                    st.error("資材名称は必須入力項目です。")
                else:
                    current_supplies = supplies.copy()
                    current_supplies.append({
                        "資材ID": f"SUP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "資材名": new_s_name,
                        "カテゴリ": new_s_cat,
                        "画像URL": "",
                        "初期在庫": new_s_stock,
                        "発注点": new_s_point,
                        "登録日": str(date.today())
                    })
                    sheets.save_supplies(current_supplies)
                    st.success(f"資材: {new_s_name} の登録が完了しました。")
                    refresh()
        st.markdown('</div>', unsafe_allow_html=True)
