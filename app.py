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

# ════════════════════════════════════════════════════════════════
#  デザイントークン & モバイル対応CSS
# ════════════════════════════════════════════════════════════════
WARN_BUFFER = 0.3

st.markdown("""
<style>
:root {
    --c-bg: #f8fafc;
    --c-surface: #ffffff;
    --c-primary: #1e3a8a;
    --c-border: #cbd5e1;
}
.stApp { background: var(--c-bg); }

/* モバイルフレンドリーなフォーム要素 */
.stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea, .stDateInput input {
    background-color: var(--c-surface) !important;
    border: 2px solid var(--c-border) !important;
    border-radius: 8px !important;
    color: #0f172a !important;
    font-size: 1rem !important;
    padding: 10px !important;
    min-height: 48px; /* 指で押しやすいサイズ */
}

/* ボタンの大型化 */
.stButton button {
    min-height: 48px;
    font-weight: 700 !important;
    border-radius: 8px !important;
    font-size: 1rem !important;
}

label { 
    color: #334155 !important; 
    font-weight: 700 !important; 
    font-size: 0.9rem !important; 
    margin-bottom: 4px;
}

.main-header {
    background: linear-gradient(135deg, #1e3a8a, #3b82f6);
    padding: 20px;
    border-radius: 12px;
    margin-bottom: 20px;
    color: white;
}
.main-header h1 {
    font-size: 1.8rem !important;
    margin: 0 0 5px 0 !important;
}

.form-card {
    background: var(--c-surface);
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 16px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}

.section-title {
    font-size: 1.05rem;
    font-weight: 800;
    color: var(--c-primary);
    margin-bottom: 12px;
    border-left: 4px solid var(--c-primary);
    padding-left: 8px;
}

/* アラート用スタイル */
.alert-ng {
    background-color: #fee2e2;
    border: 1px solid #fca5a5;
    color: #991b1b;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 10px;
    font-size: 0.9rem;
}
.alert-warning {
    background-color: #fef3c7;
    border: 1px solid #fcd34d;
    color: #92400e;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 10px;
    font-size: 0.9rem;
}

/* 在庫ゲージ用 */
.gauge-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 8px;
}
.gauge-head {
    display: flex;
    justify-content: space-between;
    margin-bottom: 6px;
    font-size: 0.85rem;
    font-weight: bold;
}
.gauge-track {
    background: #e2e8f0;
    height: 12px;
    border-radius: 6px;
    position: relative;
    overflow: hidden;
}
.gauge-fill {
    height: 100%;
    border-radius: 6px;
}
.gauge-fill.ok { background: #10b981; }
.gauge-fill.warn { background: #f59e0b; }
.gauge-fill.ng { background: #ef4444; }
.gauge-numbers {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: #64748b;
    margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
#  接続確認
# ════════════════════════════════════════════════════════════════
try:
    from sheets import (
        load_arrivals, append_arrival, update_arrival, load_brewing, append_brewing, update_brewing,
        load_adjustments, append_adjustment, load_supplies, save_supplies, load_supply_logs, append_supply_log,
        load_materials, save_materials, load_makers, save_makers, load_inspectors, save_inspectors,
        load_order_points, save_order_points, next_arrival_no, next_brewing_no, update_supply_log, delete_supply_log
    )
    SHEETS_OK = True
    HAS_LOG_EDIT = True
except Exception:
    st.error(f"🚨 システム接続エラー\n\n```\n{traceback.format_exc()}\n```")
    st.stop()

def refresh():
    st.cache_data.clear()
    st.rerun()

# ════════════════════════════════════════════════════════════════
#  共通データ処理
# ════════════════════════════════════════════════════════════════
STATUS_LABEL = {"ok": "正常", "warn": "注意", "ng": "要発注", "none": "未設定"}

def calc_status(current, threshold):
    if threshold is None or threshold <= 0: return "none"
    if current < threshold: return "ng"
    if current < threshold * (1 + WARN_BUFFER): return "warn"
    return "ok"

def gauge_html(label, current, threshold, unit="袋"):
    status = calc_status(current, threshold)
    scale_max = max(current * 1.15, threshold * 1.5, 1)
    fill_pct = max(min(current / scale_max * 100, 100), 0)
    
    status_class = "ok"
    if status == "ng": status_class = "ng"
    elif status == "warn": status_class = "warn"

    return f"""
    <div class="gauge-card">
        <div class="gauge-head">
            <span>{label}</span>
            <span class="gauge-fill {status_class}" style="padding: 2px 6px; border-radius: 4px; color: white; font-size: 0.75rem;">
                {STATUS_LABEL[status]}
            </span>
        </div>
        <div class="gauge-track">
            <div class="gauge-fill {status_class}" style="width: {fill_pct}%;"></div>
        </div>
        <div class="gauge-numbers">
            <span>現在: {current:,.1f} {unit}</span>
            <span>基準: {threshold:,.1f} {unit}</span>
        </div>
    </div>
    """

# データ一括取得
(arrivals, brewing, adjustments, supplies, supply_logs, materials, makers, inspectors, order_points) = (
    load_arrivals(), load_brewing(), load_adjustments(), load_supplies(), load_supply_logs(),
    load_materials(), load_makers(), load_inspectors(), load_order_points()
)

# ════════════════════════════════════════════════════════════════
#  現在庫（こんにゃく原料など）の算出
# ════════════════════════════════════════════════════════════════
def get_inventory():
    inv = {}
    for a in arrivals:
        ano = str(a.get("入荷No", ""))
        if not ano: continue
        inv[ano] = {
            "入荷No": ano, "ロットNo": str(a.get("ロットNo", "")), "メーカー": str(a.get("メーカー", "")),
            "原料種別": str(a.get("原料種別", "")), "1袋重量": float(a.get("1袋重量(kg)") or 20.0),
            "入荷袋数": float(a.get("袋数") or 0), "使用量(kg)": 0.0, "調整袋数": 0.0
        }

    for b in brewing:
        main_lot = str(b.get("主原料ロット", "")).strip()
        main_kg = float(b.get("こんにゃく精粉(kg)") or 0)
        for v in inv.values():
            if v["ロットNo"] == main_lot:
                v["使用量(kg)"] += main_kg

    for adj in adjustments:
        ano = str(adj.get("入荷No", ""))
        if ano in inv:
            inv[ano]["調整袋数"] += float(adj.get("調整袋数") or 0)

    for v in inv.values():
        bpk = v["1袋重量"] if v["1袋重量"] > 0 else 20.0
        v["使用袋数"] = v["使用量(kg)"] / bpk
        v["現在庫(袋)"] = v["入荷袋数"] - v["使用袋数"] + v["調整袋数"]
        v["現在庫(kg)"] = v["現在庫(袋)"] * bpk
    return inv

inventory_data = get_inventory()
type_totals = {}
for v in inventory_data.values():
    type_totals[v["原料種別"]] = type_totals.get(v["原料種別"], 0) + v["現在庫(袋)"]

raw_alerts = [f"⚠️ {m} の在庫（{c:,.1f}袋）が発注点（{order_points.get(m, 0):,.1f}袋）を下回っています。" for m, c in type_totals.items() if m in order_points and c < order_points[m]]

# ════════════════════════════════════════════════════════════════
#  サイドバーナビゲーション
# ════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🏭 原料管理 ERP")
    page = st.radio("メニュー", ["🏠 ダッシュボード", "📦 原料入荷記録", "🧪 仕込み・配合記録", "🏭 原料在庫一覧", "🧹 資材備品管理", "🔍 履歴トレース", "⚙️ マスタ設定"])
    st.markdown("---")
    if st.button("🔄 表示データを更新", use_container_width=True):
        refresh()

# ════════════════════════════════════════════════════════════════
#  1. ダッシュボード
# ════════════════════════════════════════════════════════════════
if page == "🏠 ダッシュボード":
    st.markdown('<div class="main-header"><h1>📊 工場稼働・在庫モニター</h1><p>現在の重要アラートおよび在庫状況</p></div>', unsafe_allow_html=True)
    
    if raw_alerts:
        for al in raw_alerts:
            st.markdown(f'<div class="alert-ng">{al}</div>', unsafe_allow_html=True)
    else:
        st.success("✅ すべての主原料在庫は基準値を満たしています。")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-title">⚗️ 原料在庫モニター</div>', unsafe_allow_html=True)
        for m, val in type_totals.items():
            st.markdown(gauge_html(m, val, order_points.get(m, 0)), unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="section-title">🧪 最新の仕込み状況 (直近5件)</div>', unsafe_allow_html=True)
        if brewing:
            df_b = pd.DataFrame(brewing)[["仕込日", "品名", "仕込量(kg)", "主原料ロット"]].tail(5)
            st.dataframe(df_b, use_container_width=True, hide_index=True)
        else:
            st.info("仕込み記録がまだありません。")

# ════════════════════════════════════════════════════════════════
#  2. 原料入荷記録
# ════════════════════════════════════════════════════════════════
elif page == "📦 原料入荷記録":
    st.markdown('<div class="main-header"><h1>📦 原料入荷記録</h1><p>入荷時の品質検査と保存</p></div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["➕ 新規入荷登録", "📋 入荷履歴一覧"])
    
    with tab1:
        st.markdown('<div class="form-card"><div class="section-title">基本情報</div>', unsafe_allow_html=True)
        new_no = next_arrival_no(arrivals)
        
        # モバイル環境（縦一列）になりがちな箇所は、小分けにして横並びに
        c1, c2 = st.columns(2)
        a_date = c1.date_input("入荷日", value=date.today())
        maker = c2.selectbox("メーカー", makers + ["その他"])
        if maker == "other":
            maker = st.text_input("メーカー名を入力")

        c3, c4 = st.columns(2)
        lot_no = c3.text_input("ロットNo ＊")
        m_type = c4.selectbox("原料種別", materials)

        c5, c6 = st.columns(2)
        bags = c5.number_input("袋数", min_value=1, step=1, value=10)
        b_per = c6.number_input("1袋の重量 (kg)", min_value=1.0, value=20.0, step=0.5)
        
        st.info(f"💡 合計重量: {(bags * b_per):,.1f} kg")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="form-card"><div class="section-title">品質検査</div>', unsafe_allow_html=True)
        ch1, ch2 = st.columns(2)
        v_app = ch1.selectbox("外観", ["OK（正常）", "NG（異常あり）"])
        v_name = ch2.selectbox("品名・規格確認", ["OK（一致）", "NG（不一致）"])
        v_exp = ch1.selectbox("賞味期限", ["OK（期限内）", "NG（期限外・不明）"])
        v_dmg = ch2.selectbox("異物確認", ["OK（なし）", "NG（あり）"])
        
        ins = st.selectbox("検査担当者", inspectors)
        rem = st.text_input("備考")
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("✅ 入荷記録を保存する", type="primary", use_container_width=True):
            if not lot_no:
                st.error("ロットNoを入力してください。")
            else:
                append_arrival({
                    "入荷No": new_no, "入荷日": str(a_date), "メーカー": maker, "ロットNo": lot_no,
                    "原料種別": m_type, "袋数": bags, "1袋重量(kg)": b_per, "総量(kg)": bags * b_per,
                    "外観": v_app, "品名・規格確認": v_name, "賞味期限": v_exp, "異物": v_dmg,
                    "搬入温度": "-", "臭い": "OK", "包装": "OK", "色調": "OK", "水分": "OK",
                    "異常内容": "", "担当者": ins, "備考": rem, "登録日時": datetime.now().isoformat()
                })
                st.success(f"入荷記録 {new_no} を保存しました。")
                refresh()

    with tab2:
        if arrivals:
            df_arr = pd.DataFrame(arrivals)[["入荷No", "入荷日", "メーカー", "ロットNo", "原料種別", "袋数", "外観", "担当者"]]
            st.dataframe(df_arr[::-1], use_container_width=True, hide_index=True)
        else:
            st.info("入荷データはありません。")

# ════════════════════════════════════════════════════════════════
#  3. 仕込み・配合記録（マスタ連動＆警告機能）
# ════════════════════════════════════════════════════════════════
elif page == "🧪 仕込み・配合記録":
    st.markdown('<div class="main-header"><h1>🧪 仕込み・配合計算</h1><p>マスタの配合比率に基づく自動計算と実績入力</p></div>', unsafe_allow_html=True)
    
    # 配合マスタの定義
    if "recipe_master" not in st.session_state:
        st.session_state.recipe_master = {
            "通常こんにゃく (国産)": {"こんにゃく精粉(kg)": 25.0, "海藻粉(kg)": 1.0, "デンプン(kg)": 5.0, "石灰(kg)": 2.0},
            "白こんにゃく": {"こんにゃく精粉(kg)": 24.0, "海藻粉(kg)": 0.0, "デンプン(kg)": 4.0, "石灰(kg)": 1.8},
            "特製手延べ": {"こんにゃく精粉(kg)": 30.0, "海藻粉(kg)": 2.0, "デンプン(kg)": 8.0, "石灰(kg)": 2.5}
        }

    tab_brew1, tab_brew2 = st.tabs(["🧪 配合計算・登録", "📋 仕込み履歴"])
    
    with tab_brew1:
        st.markdown('<div class="form-card"><div class="section-title">品名と仕込量指定</div>', unsafe_allow_html=True)
        
        # 品名選択（自由記述も可能）
        p_opt = list(st.session_state.recipe_master.keys()) + ["直接入力（マスタ外）"]
        p_select = st.selectbox("品名を選択", p_opt)
        
        if p_select == "直接入力（マスタ外）":
            p_name = st.text_input("品名を入力してください")
            # デフォルト値
            base_recipe = {"こんにゃく精粉(kg)": 25.0, "海藻粉(kg)": 1.0, "デンプン(kg)": 5.0, "石灰(kg)": 2.0}
        else:
            p_name = p_select
            base_recipe = st.session_state.recipe_master[p_select]

        # 基準（例: 製品合計仕込量 100kg あたりの配合）
        base_total = sum(base_recipe.values())
        
        target_kg = st.number_input("希望製品仕込み量 (kg)", min_value=1.0, value=100.0, step=10.0)
        
        # 比率に応じた推奨自動計算
        ratio = target_kg / 100.0 if p_select != "直接入力（マスタ外）" else 1.0
        
        rec_konjac = base_recipe.get("こんにゃく精粉(kg)", 0.0) * ratio
        rec_seaweed = base_recipe.get("海藻粉(kg)", 0.0) * ratio
        rec_starch = base_recipe.get("デンプン(kg)", 0.0) * ratio
        rec_lime = base_recipe.get("石灰(kg)", 0.0) * ratio

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="form-card"><div class="section-title">実際の配合量実績（手動調整可能）</div>', unsafe_allow_html=True)
        st.write("※ 計算された推奨値をベースに、実際の投入量を微調整できます。")
        
        col_m1, col_m2 = st.columns(2)
        act_konjac = col_m1.number_input("こんにゃく精粉投入量 (kg)", min_value=0.0, value=rec_konjac, step=0.5)
        act_seaweed = col_m2.number_input("海藻粉投入量 (kg)", min_value=0.0, value=rec_seaweed, step=0.1)
        act_starch = col_m1.number_input("加工デンプン投入量 (kg)", min_value=0.0, value=rec_starch, step=0.5)
        act_lime = col_m2.number_input("石灰投入量 (kg)", min_value=0.0, value=rec_lime, step=0.1)

        # ロット紐付け（入荷データから選択）
        st.markdown("<br><b>ロット選択</b>", unsafe_allow_html=True)
        lots_in_stock = ["─"] + list(set([str(a.get("ロットNo", "")) for a in arrivals if a.get("ロットNo")]))
        
        col_l1, col_l2 = st.columns(2)
        lot_konjac = col_l1.selectbox("主原料ロットNo", lots_in_stock)
        lot_seaweed = col_l2.selectbox("海藻粉ロットNo", lots_in_stock)
        lot_starch = col_l1.selectbox("デンプンロットNo", lots_in_stock)
        
        st.markdown('</div>', unsafe_allow_html=True)

        # ════ 配合比率のズレ警告 ════
        if p_select != "直接入力（マスタ外）":
            # 基準配合比に対する現在の入力比率のズレをチェック
            expected_total = act_konjac + act_seaweed + act_starch + act_lime
            if expected_total > 0:
                # 基準となる各項目の構成比率
                base_konjac_pct = (base_recipe.get("こんにゃく精粉(kg)", 0) / base_total)
                act_konjac_pct = (act_konjac / expected_total)
                
                # 乖離率（5% 以上のズレがあるか）
                if abs(act_konjac_pct - base_konjac_pct) > 0.05:
                    st.warning("⚠️ 警告: 基準の配合比率から5%以上の乖離が発生しています。投入量および希望仕込み量の設定に誤りがないか今一度ご確認ください。")

        if st.button("✅ この配合で仕込み記録を登録", type="primary", use_container_width=True):
            if not p_name:
                st.error("品名がありません。")
            else:
                append_brewing({
                    "仕込No": next_brewing_no(brewing),
                    "仕込日": str(date.today()),
                    "品名": p_name,
                    "メーカー": "自社製造",
                    "主原料ロット": lot_konjac,
                    "仕込量(kg)": target_kg,
                    "こんにゃく精粉(kg)": act_konjac,
                    "海藻粉(kg)": act_seaweed,
                    "海藻粉ロット": lot_seaweed,
                    "デンプン(kg)": act_starch,
                    "デンプンロット": lot_starch,
                    "デンプン種別": "-",
                    "石灰(kg)": act_lime,
                    "石灰水(L)": 0.0,
                    "その他添加物": "[]",
                    "備考": "配合自動計算登録",
                    "登録日時": datetime.now().isoformat()
                })
                st.success(f"仕込み記録: {p_name} ({target_kg}kg) の登録を完了しました。")
                refresh()

    with tab_brew2:
        if brewing:
            df_b_show = pd.DataFrame(brewing)[["仕込No", "仕込日", "品名", "仕込量(kg)", "こんにゃく精粉(kg)", "主原料ロット"]]
            st.dataframe(df_b_show[::-1], use_container_width=True, hide_index=True)
        else:
            st.info("仕込み履歴データはありません。")

# ════════════════════════════════════════════════════════════════
#  4. 原料在庫一覧
# ════════════════════════════════════════════════════════════════
elif page == "🏭 原料在庫一覧":
    st.markdown('<div class="main-header"><h1>🏭 原料在庫一覧</h1><p>入荷記録と仕込み消費に基づき自動算出</p></div>', unsafe_allow_html=True)
    
    col_t1, col_t2 = st.tabs(["📊 ロット別現在庫", "⚖️ 在庫調整（棚卸）"])
    
    with col_t1:
        inv_rows = []
        for k, v in inventory_data.items():
            if v["現在庫(袋)"] != 0:
                inv_rows.append(v)
        
        if inv_rows:
            df_inv = pd.DataFrame(inv_rows)[["入荷No", "原料種別", "ロットNo", "メーカー", "入荷袋数", "使用袋数", "調整袋数", "現在庫(袋)"]]
            st.dataframe(df_inv, use_container_width=True, hide_index=True)
        else:
            st.info("現在庫はありません。")

    with col_t2:
        st.markdown('<div class="form-card"><div class="section-title">在庫の微調整</div>', unsafe_allow_html=True)
        if not inventory_data:
            st.info("入荷データがないため調整できません。")
        else:
            target_opts = {f"{v['入荷No']} - {v['原料種別']} (ロット:{v['ロットNo']})": v["入荷No"] for v in inventory_data.values()}
            sel_label = st.selectbox("調整対象ロット", list(target_opts.keys()))
            sel_ano = target_opts[sel_label]
            
            diff_bags = st.number_input("調整する袋数 (+/-入力可能)", step=1.0, value=0.0)
            reason = st.text_input("調整の理由", placeholder="例: 棚卸誤差の修正")
            
            if st.button("⚖️ 在庫数を保存する", type="primary", use_container_width=True):
                append_adjustment({
                    "調整ID": f"ADJ-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "入荷No": sel_ano,
                    "調整日": str(date.today()),
                    "調整袋数": diff_bags,
                    "理由": reason,
                    "担当者": "管理者",
                    "登録日時": datetime.now().isoformat()
                })
                st.success("調整記録を書き込みました。")
                refresh()
        st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
#  5. 資材備品管理
# ════════════════════════════════════════════════════════════════
elif page == "🧹 資材備品管理":
    st.markdown('<div class="main-header"><h1>🧹 資材備品管理</h1><p>梱包・衛生などの備品管理</p></div>', unsafe_allow_html=True)
    
    # 簡易表示
    if supplies:
        df_sup = pd.DataFrame(supplies)[["資材ID", "資材名", "カテゴリ", "初期在庫", "発注点"]]
        st.dataframe(df_sup, use_container_width=True, hide_index=True)
    else:
        st.info("現在、資材マスターデータは設定されていません。")

# ════════════════════════════════════════════════════════════════
#  6. 履歴トレース
# ════════════════════════════════════════════════════════════════
elif page == "🔍 履歴トレース":
    st.markdown('<div class="main-header"><h1>🔍 双方向トレース</h1><p>主原料ロットに紐づく製品・入荷情報の追跡</p></div>', unsafe_allow_html=True)
    
    search_lot = st.text_input("検索するロットNoを入力してください（例: 1-109）")
    if search_lot:
        st.markdown(f"### ロット番号: **{search_lot}** の追跡結果")
        
        # 1. 入荷追跡
        match_arr = [a for a in arrivals if search_lot.lower() in str(a.get("ロットNo", "")).lower()]
        if match_arr:
            st.subheader("📦 該当原料の入荷記録")
            st.dataframe(pd.DataFrame(match_arr)[["入荷No", "入荷日", "原料種別", "ロットNo", "メーカー"]], use_container_width=True, hide_index=True)
        else:
            st.info("対応する原料入荷情報は見つかりませんでした。")
            
        # 2. 仕込み追跡
        match_brw = [b for b in brewing if search_lot.lower() in str(b.get("主原料ロット", "")).lower()]
        if match_brw:
            st.subheader("🧪 該当原料を使用した仕込み実績")
            st.dataframe(pd.DataFrame(match_brw)[["仕込No", "仕込日", "品名", "仕込量(kg)", "主原料ロット"]], use_container_width=True, hide_index=True)
        else:
            st.info("このロット原料を使用した仕込み実績はありません。")

# ════════════════════════════════════════════════════════════════
#  7. マスタ設定
# ════════════════════════════════════════════════════════════════
elif page == "⚙️ マスタ設定":
    st.markdown('<div class="main-header"><h1>⚙️ システムマスタ設定</h1><p>プルダウンメニューの選択肢および製品ごとの配合比基準</p></div>', unsafe_allow_html=True)
    
    m_tab1, m_tab2 = st.tabs(["⚗️ 原料マスタ", "🧪 配合比マスタ設定"])
    
    with m_tab1:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        st.write("プルダウンに表示される主原料名称の一覧です。")
        df_m = pd.DataFrame({"原料名": materials})
        edited_m = st.data_editor(df_m, num_rows="dynamic", use_container_width=True)
        if st.button("💾 原料マスタを保存", type="primary"):
            save_materials([str(x).strip() for x in edited_m["原料名"].tolist() if str(x).strip()])
            st.success("保存が完了しました。")
            refresh()
        st.markdown('</div>', unsafe_allow_html=True)

    with m_tab2:
        st.markdown('<div class="form-card"><div class="section-title">製品別 配合基準値</div>', unsafe_allow_html=True)
        st.write("各製品 100kg に対する標準配合量（kg）を設定します。")
        
        for p_key, recipe in list(st.session_state.recipe_master.items()):
            with st.expander(p_key):
                col_r1, col_r2 = st.columns(2)
                recipe["こんにゃく精粉(kg)"] = col_r1.number_number = col_r1.number_input(f"{p_key} - こんにゃく精粉 (kg)", min_value=0.0, value=recipe.get("こんにゃく精粉(kg)", 0.0), key=f"{p_key}_m1")
                recipe["海藻粉(kg)"] = col_r2.number_input(f"{p_key} - 海藻粉 (kg)", min_value=0.0, value=recipe.get("海藻粉(kg)", 0.0), key=f"{p_key}_m2")
                recipe["デンプン(kg)"] = col_r1.number_input(f"{p_key} - デンプン (kg)", min_value=0.0, value=recipe.get("デンプン(kg)", 0.0), key=f"{p_key}_m3")
                recipe["石灰(kg)"] = col_r2.number_input(f"{p_key} - 石灰 (kg)", min_value=0.0, value=recipe.get("石灰(kg)", 0.0), key=f"{p_key}_m4")
        
        if st.button("💾 配合比マスタ設定を確定", type="primary", use_container_width=True):
            st.success("設定をセッションに一時保存しました。")
        st.markdown('</div>', unsafe_allow_html=True)
