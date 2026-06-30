# app.py
import streamlit as st
import pandas as pd
import json
from datetime import datetime, date
import traceback

# 画像圧縮用のPillowインポート
try:
    from PIL import Image
    import base64
    from io import BytesIO
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

st.set_page_config(
    page_title="原料・資材管理システム",
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
#  データ接続
# ════════════════════════════════════════════════════════════════
try:
    import sheets
except Exception as e:
    st.error("🚨 `sheets.py` のインポート時にエラーが発生しました。")
    st.code(traceback.format_exc())
    st.stop()

def refresh():
    st.cache_data.clear()
    st.rerun()

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
    recipes_raw = sheets.load_recipes()  # 多成分レシピマスタをロード
except Exception as e:
    st.error("🚨 スプレッドシートからのロードに失敗しました。接続設定を確認してください。")
    st.code(traceback.format_exc())
    st.stop()

# ════════════════════════════════════════════════════════════════
#  現在庫算出ロジック
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

    for b in brewing:
        # 主原料、添加物ごとの消費量突合
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

        # その他添加物(JSON形式)の消費を突合
        oa = b.get("その他添加物", "")
        if oa:
            try:
                items = json.loads(oa)
                for item in items:
                    t_lot = str(item.get("lot", "")).strip()
                    t_kg = float(item.get("kg", 0.0))
                    for v in inv.values():
                        if t_lot and v["ロットNo"] == t_lot:
                            v["使用量(kg)"] += t_kg
            except:
                pass

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
# ═══════════════════════════════════════════════════════════════
elif page == "📦 原料入荷登録":
    st.markdown('<div class="main-header"><h1>📦 原料入荷品質記録</h1><p>入荷時の品質検査情報の登録と履歴一覧</p></div>', unsafe_allow_html=True)
    tab_a, tab_b = st.tabs(["➕ 新規入荷登録", "📋 入荷・品質検査履歴"])
    
    with tab_a:
        st.markdown('<div class="form-card"><div class="section-title">原料入荷情報</div>', unsafe_allow_html=True)
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
        st.info(f"💡 自動算出 合計重量: {bags_qty * weight_per_bag:,.1f} kg")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="form-card"><div class="section-title">🔍 受入検査</div>', unsafe_allow_html=True)
        cc1, cc2 = st.columns(2)
        chk_app = cc1.selectbox("① 外観", ["OK（正常）", "NG（異常あり）"])
        chk_spec = cc2.selectbox("② 品名・規格確認", ["OK（一致）", "NG（不一致）"])
        chk_exp = cc1.selectbox("③ 賞味期限", ["OK（期限内）", "NG（期限切れ）"])
        chk_dmg = cc2.selectbox("④ 異物・破損混入確認", ["OK（なし）", "NG（あり）"])
        
        abn_desc = st.text_input("⚠️ 異常内容の詳細", placeholder="異常詳細を入力") if "NG" in [chk_app, chk_spec, chk_exp, chk_dmg] else ""
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
#  3. 仕込み・配合記録（多成分動的フォーム：直近5ロット＋手入力）
# ═══════════════════════════════════════════════════════════════
elif page == "🧪 仕込み・配合記録":
    st.markdown('<div class="main-header"><h1>🧪 製造仕込み・配合計算</h1><p>最大10個の組み合わせ原料・添加物に対する動的仕込み登録フォーム</p></div>', unsafe_allow_html=True)
    
    tab_brw1, tab_brw2 = st.tabs(["🧪 配合計算・登録", "📋 仕込み履歴"])
    
    # 配合データのパース
    p_recipes = {}
    for r in recipes_raw:
        try:
            p_recipes[r["品名"]] = json.loads(r["配合JSON"])
        except:
            p_recipes[r["品名"]] = []

    with tab_brw1:
        st.markdown('<div class="form-card"><div class="section-title">製品名と希望仕込み量の指定</div>', unsafe_allow_html=True)
        recipe_opts = list(p_recipes.keys()) + ["直接入力（マスタ外）"]
        selected_p = st.selectbox("配合品名を選択", recipe_opts)
        
        target_size = st.number_input("希望仕込製品量 (kg)", min_value=1.0, value=100.0, step=10.0)
        st.markdown('</div>', unsafe_allow_html=True)

        if selected_p == "直接入力（マスタ外）":
            p_name = st.text_input("品名を手動入力")
            active_recipe = [{"原料名": "こんにゃく粉（国産）", "比率": 25.0}, {"原料名": "石灰", "比率": 2.0}]
        else:
            p_name = selected_p
            active_recipe = p_recipes[selected_p]

        # ーーー 直近入荷5件の重複なしロット抽出 ーーー
        recent_arrivals = sorted(arrivals, key=lambda x: x.get("入荷日", ""), reverse=True)
        recent_lots = []
        for a in recent_arrivals:
            l_no = str(a.get("ロットNo", "")).strip()
            if l_no and l_no not in recent_lots:
                recent_lots.append(l_no)
            if len(recent_lots) >= 5:
                break
        lots_choices = ["手入力する"] + recent_lots + ["─"]

        # 最大10個の配合原料動的インプット生成
        st.markdown('<div class="form-card"><div class="section-title">各構成原料・添加物の投入実績（最大10個まで対応）</div>', unsafe_allow_html=True)
        
        submitted_ingredients = []
        
        # 乖離警告フラグ
        any_mismatch = False

        # 品名が10個を超える場合の安全ガード
        for i, item in enumerate(active_recipe[:10]):
            r_name = item.get("原料名", "未定義原料")
            r_ratio = float(item.get("比率", 0.0))
            
            # 100kgあたりの標準比率から自動按分した推奨値
            rec_kg = r_ratio * (target_size / 100.0)
            
            st.write(f"🍏 **【原料 {i+1}】 {r_name}** （推奨: {rec_kg:.2f} kg）")
            col_kg, col_sel, col_txt = st.columns([1, 1, 1])
            
            act_kg = col_kg.number_input(f"投入重量 (kg)", min_value=0.0, value=rec_kg, step=0.1, key=f"act_kg_{i}")
            lot_sel = col_sel.selectbox("直近5件ロット", lots_choices, key=f"lot_sel_{i}")
            lot_txt = col_txt.text_input("ロットNo手入力", value="" if lot_sel == "手入力する" else lot_sel, disabled=(lot_sel != "手入力する"), key=f"lot_txt_{i}")
            
            final_lot = lot_txt if lot_sel == "手入力する" else lot_sel
            submitted_ingredients.append({
                "原料名": r_name,
                "kg": act_kg,
                "lot": final_lot
            })
            
            # 5%以上の配合乖離チェック
            if rec_kg > 0 and abs((act_kg - rec_kg) / rec_kg) > 0.05:
                any_mismatch = True

            st.markdown("---")

        if any_mismatch:
            st.markdown("""
            <div class="alert-warning">
                ⚠️ <b>配合比率警告:</b> 1つ以上の原料投入量が、推奨マスタ設定値から5%以上ズレています。投入値を確認してください。
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("✅ この配合実績で製造登録する", type="primary", use_container_width=True):
            if not p_name:
                st.error("品名が設定されていません。")
            else:
                # 従来の固定列（こんにゃく精粉(kg)など）への割り当てロジック（古いビューとの互換性のための処理）
                k_kg = 0.0
                k_lot = "─"
                s_kg = 0.0
                s_lot = "─"
                st_kg = 0.0
                st_lot = "─"
                lime_kg = 0.0
                
                for ing in submitted_ingredients:
                    n = ing["原料名"]
                    if "こんにゃく" in n:
                        k_kg = ing["kg"]
                        k_lot = ing["lot"]
                    elif "海藻" in n:
                        s_kg = ing["kg"]
                        s_lot = ing["lot"]
                    elif "デンプン" in n or "でんぷん" in n:
                        st_kg = ing["kg"]
                        st_lot = ing["lot"]
                    elif "石灰" in n:
                        lime_kg = ing["kg"]

                sheets.append_brewing({
                    "仕込No": sheets.next_brewing_no(brewing), "仕込日": str(date.today()), "品名": p_name,
                    "メーカー": "自社", "主原料ロット": k_lot, "仕込量(kg)": target_size,
                    "こんにゃく精粉(kg)": k_kg, "海藻粉(kg)": s_kg, "海藻粉ロット": s_lot,
                    "デンプン(kg)": st_kg, "デンプンロット": st_lot, "デンプン種別": "-",
                    "石灰(kg)": lime_kg, "石灰水(L)": 0, 
                    "その他添加物": json.dumps(submitted_ingredients, ensure_ascii=False), # すべての原料データを保存
                    "備考": "多成分動的登録",
                    "登録日時": datetime.now().isoformat()
                })
                st.success("仕込み・製造実績を登録しました。")
                refresh()

    with tab_brw2:
        if brewing:
            df_brw_all = pd.DataFrame(brewing)[["仕込No", "仕込日", "品名", "仕込量(kg)", "こんにゃく精粉(kg)", "主原料ロット", "海藻粉ロット"]]
            st.dataframe(df_brw_all[::-1], use_container_width=True, hide_index=True)
        else:
            st.info("過去の製造実績はありません。")

# ═══════════════════════════════════════════════════════════════
#  4. 原料在庫・棚卸
# ═══════════════════════════════════════════════════════════════
elif page == "🏭 原料在庫・棚卸":
    st.markdown('<div class="main-header"><h1>🏭 原料在庫状況と調整</h1><p>現在庫のロット別自動算出と、実地棚卸ズレ修正</p></div>', unsafe_allow_html=True)
    tab_inv1, tab_inv2 = st.tabs(["📋 ロット別現在庫一覧", "⚖️ 棚卸し在庫調整"])
    
    with tab_inv1:
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
                st.success("調整情報を書き込みました。")
                refresh()
        st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
#  5. 資材備品管理（画像アタッチメント機能復活）
# ═══════════════════════════════════════════════════════════════
elif page == "🧹 資材備品管理":
    st.markdown('<div class="main-header"><h1>🧹 資材・消耗品在庫管理</h1><p>資材の残量確認および登録履歴の削除</p></div>', unsafe_allow_html=True)
    tab_s1, tab_s2 = st.tabs(["📋 在庫一覧・入出庫", "🕒 ログ管理と調整"])
    
    with tab_s1:
        if supplies:
            st.markdown('<div class="section-title">🚦 資材発注点モニター</div>', unsafe_allow_html=True)
            # 画像付きでタイル型に並べる（モバイル・タブレットで見やすいUI）
            cols_grid = st.columns(max(2, min(4, len(supplies))))
            for idx, s in enumerate(supplies):
                with cols_grid[idx % len(cols_grid)]:
                    st.markdown(f"**{s.get('資材名')}** ({s.get('カテゴリ')})")
                    img_data = s.get("画像URL", "")
                    if img_data and img_data.startswith("data:image"):
                        st.image(img_data, width=100)
                    else:
                        st.caption("📷 画像なし")
                    st.write(f"初期: {s.get('初期在庫')} / 発注点: {s.get('発注点')}")
                    st.markdown("---")
            
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
    st.markdown('<div class="main-header"><h1>🔍 双方向原料トレース (HACCP対応)</h1><p>原料ロットと製品製造ロットの関連付け追跡</p></div>', unsafe_allow_html=True)
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
                
                # 通常消費に加えて、その他添加物JSON内のロット消費も含めて検索
                match_brw = []
                for b in brewing:
                    matched = False
                    if (str(b.get("主原料ロット", "")).strip() == target_lot or 
                        str(b.get("海藻粉ロット", "")).strip() == target_lot or 
                        str(b.get("デンプンロット", "")).strip() == target_lot):
                        matched = True
                    else:
                        # JSON内検索
                        try:
                            items = json.loads(b.get("その他添加物", "[]"))
                            if any(str(i.get("lot", "")).strip() == target_lot for i in items):
                                matched = True
                        except:
                            pass
                    if matched:
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
                st.json({"仕込No": selected_b.get("仕込No"), "製造日": selected_b.get("仕込日"), "品名": selected_b.get("品名"), "製造量 (kg)": selected_b.get("仕込量(kg)")})
                
                # すべての動的消費アイテムの抽出
                used_lots = []
                try:
                    items = json.loads(selected_b.get("その他添加物", "[]"))
                    for ing in items:
                        l_num = str(ing.get("lot", "")).strip()
                        if l_num and l_num != "─" and l_num != "":
                            used_lots.append({"原料種別": ing.get("原料名", "副資材"), "ロットNo": l_num})
                except:
                    # JSONデコード失敗時のフォールバック(主原料のみ)
                    m_l = str(selected_b.get("主原料ロット", "")).strip()
                    if m_l and m_l != "─":
                        used_lots.append({"原料種別": "主原料", "ロットNo": m_l})
                
                if used_lots:
                    st.markdown("##### 📦 使用原料の入荷元情報")
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
#  7. マスタ設定（多成分レシピエディタ＆画像リサイズ付き資材登録）
# ═══════════════════════════════════════════════════════════════
elif page == "⚙️ マスタ設定":
    st.markdown('<div class="main-header"><h1>⚙️ マスターデータ設定</h1><p>原料、メーカー、担当者、発注点、配合マスター設定、新規資材定義</p></div>', unsafe_allow_html=True)
    m_tab1, m_tab2, m_tab3, m_tab4, m_tab5 = st.tabs(["⚗️ 原料マスタ", "🏢 メーカー・担当者", "🚨 原料発注点", "🧪 配合レシピ設定", "📦 新規資材登録"])
    
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
            if st.button("💾 メーカーリストを保存する"):
                sheets.save_makers([str(x).strip() for x in edited_makers["メーカー名"].tolist() if str(x).strip()])
                st.success("メーカー情報を保存しました。")
                refresh()
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col_sub2:
            st.markdown('<div class="form-card"><div class="section-title">検査・調整担当者</div>', unsafe_allow_html=True)
            df_inspectors = pd.DataFrame({"担当者名": inspectors})
            edited_inspectors = st.data_editor(df_inspectors, num_rows="dynamic", use_container_width=True, key="inspector_ed_k")
            if st.button("💾 担当者リストを保存する"):
                sheets.save_inspectors([str(x).strip() for x in edited_inspectors["担当者名"].tolist() if str(x).strip()])
                st.success("担当者情報を保存しました。")
                refresh()
            st.markdown('</div>', unsafe_allow_html=True)

    with m_tab3:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        op_rows = [{"原料名": m, "発注点(袋)": float(order_points.get(m, 0.0))} for m in materials]
        df_op = pd.DataFrame(op_rows)
        edited_op = st.data_editor(df_op, use_container_width=True, key="op_ed_k")
        if st.button("💾 発注点設定を更新する", type="primary"):
            new_op_dict = {str(r["原料名"]).strip(): float(r["発注点(袋)"] or 0.0) for _, r in edited_op.iterrows() if str(r["原料名"]).strip()}
            sheets.save_order_points(new_op_dict)
            st.success("発注点設定を保存しました。")
            refresh()
        st.markdown('</div>', unsafe_allow_html=True)

    # ーーー 最大10種類の組み合わせレシピエディタ ーーー
    with m_tab4:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        st.write("製品の品名ごとに、最大10個までの配合原料と100kg製品に対する基準投入重量(kg)を決定します。")
        
        # 新しいレシピを組み立てるUI
        with st.form("new_recipe_builder"):
            new_p_name = st.text_input("製品の名称 (例: 極太糸こんにゃく)")
            
            st.write("🧪 **構成原料・比率の指定（最大10成分）**")
            cols_recipe_inputs = []
            for j in range(10):
                c_n, c_w = st.columns([2, 1])
                ing_mat = c_n.selectbox(f"原料 {j+1}", ["(未設定)"] + materials, key=f"rec_builder_mat_{j}")
                ing_ratio = c_w.number_input("100kgあたりの重量(kg)", min_value=0.0, step=0.1, key=f"rec_builder_ratio_{j}")
                cols_recipe_inputs.append({"name": ing_mat, "ratio": ing_ratio})
            
            if st.form_submit_button("➕ この配合比レシピを保存/追加する"):
                if not new_p_name:
                    st.error("製品の名称は必須です。")
                else:
                    # 有効なレシピ組み合わせを抽出
                    valid_items = []
                    for ing in cols_recipe_inputs:
                        if ing["name"] != "(未設定)" and ing["ratio"] > 0:
                            valid_items.append({"原料名": ing["name"], "比率": ing["ratio"]})
                    
                    if not valid_items:
                        st.error("有効な配合成分が1つも定義されていません。")
                    else:
                        # 既存リストに上書き・追加
                        new_recipe_entry = {
                            "品名": new_p_name,
                            "配合JSON": json.dumps(valid_items, ensure_ascii=False)
                        }
                        # 同名の古い定義を除去して新規追加
                        updated_recipes = [r for r in recipes_raw if r["品名"] != new_p_name]
                        updated_recipes.append(new_recipe_entry)
                        sheets.save_recipes(updated_recipes)
                        st.success(f"配合レシピ: {new_p_name} を保存しました。")
                        refresh()
        
        st.write("📋 **登録済みレシピ一覧**")
        for idx, rec in enumerate(recipes_raw):
            with st.expander(f"📦 {rec['品名']}"):
                try:
                    comp_list = json.loads(rec["配合JSON"])
                    df_comp = pd.DataFrame(comp_list)
                    st.dataframe(df_comp, use_container_width=True, hide_index=True)
                except:
                    st.write("配合データの読み出しに失敗しました。")
                
                if st.button("🗑️ この製品レシピを削除する", key=f"del_rec_btn_{idx}"):
                    updated_recipes = [r for r in recipes_raw if r["品名"] != rec["品名"]]
                    sheets.save_recipes(updated_recipes)
                    st.success("削除しました。")
                    refresh()
        st.markdown('</div>', unsafe_allow_html=True)

    # ーーー 新規資材登録（画像アップローダー＆Pillow軽量リサイズ・Base64化） ーーー
    with m_tab5:
        st.markdown('<div class="form-card"><div class="section-title">新規資材・衛生消耗品の登録</div>', unsafe_allow_html=True)
        st.write("衛生消耗品や梱包用の袋などの資材情報を追加します。スマートフォンなどのカメラ撮影写真、または画像ファイルをアップロードして添付保存が可能です。")
        
        with st.form("new_sup_form_rich"):
            c_s1, c_s2 = st.columns(2)
            new_s_name = c_s1.text_input("資材・備品名称 ＊")
            new_s_cat = c_s2.text_input("カテゴリ (例: 包材, 衛生消耗品)")
            
            c_s3, c_s4 = st.columns(2)
            new_s_stock = c_s3.number_input("現在の実地在庫数", min_value=0.0, value=0.0)
            new_s_point = c_s4.number_input("発注注意アラート点", min_value=0.0, value=10.0)
            
            # 軽量アタッチメント用アップローダー
            uploaded_file = st.file_uploader("📷 写真・画像をアップロード", type=["jpg", "png", "jpeg"])
            
            if st.form_submit_button("➕ 登録を完了する"):
                if not new_s_name:
                    st.error("資材名称は必須入力項目です。")
                else:
                    img_base64_str = ""
                    if uploaded_file and HAS_PIL:
                        try:
                            # Pillowで画像を読み込み、超軽量に縮小 (150x150)
                            img = Image.open(uploaded_file)
                            img.thumbnail((150, 150))
                            
                            # メモリバッファ上に圧縮保存
                            buffered = BytesIO()
                            img.save(buffered, format="PNG", optimize=True)
                            
                            # Base64データスキーム文字列を作成
                            img_base64_str = f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode('utf-8')}"
                        except Exception as e:
                            st.warning(f"画像の処理に失敗しました。画像なしで登録を続行します。: {e}")
                    
                    current_supplies = supplies.copy()
                    current_supplies.append({
                        "資材ID": f"SUP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        "資材名": new_s_name,
                        "カテゴリ": new_s_cat,
                        "画像URL": img_base64_str, # Base64文字列をそのままGoogleセルに保存
                        "初期在庫": new_s_stock,
                        "発注点": new_s_point,
                        "登録日": str(date.today())
                    })
                    sheets.save_supplies(current_supplies)
                    st.success(f"資材: {new_s_name} を登録しました！")
                    refresh()
        st.markdown('</div>', unsafe_allow_html=True)
