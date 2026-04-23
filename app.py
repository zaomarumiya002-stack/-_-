import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

st.set_page_config(
    page_title="原料使用記録 管理システム",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f1724 0%, #1a2744 100%);
}
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }

.main-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #0d47a1 100%);
    padding: 20px 28px; border-radius: 12px; margin-bottom: 24px;
    box-shadow: 0 4px 20px rgba(13,71,161,0.3);
}
.main-header h1 { color: #fff; font-size: 1.6rem; font-weight: 700; margin: 0; }
.main-header p  { color: #90caf9; font-size: 0.85rem; margin: 4px 0 0; }

.kpi-card {
    background: #fff; border-radius: 12px; padding: 18px 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07); border-left: 4px solid #1565c0;
    text-align: center;
}
.kpi-value { font-size: 2rem; font-weight: 700; color: #1a237e; }
.kpi-label { font-size: 0.8rem; color: #607d8b; margin-top: 4px; }

.form-card {
    background: #f8faff; border-radius: 12px; padding: 20px 24px;
    border: 1px solid #e3eaf5; margin-bottom: 16px;
}
.form-section-title {
    font-size: 0.9rem; font-weight: 700; color: #1565c0;
    border-bottom: 2px solid #e3eaf5; padding-bottom: 8px; margin-bottom: 16px;
}
.section-title {
    font-size: 1.1rem; font-weight: 700; color: #1a237e;
    margin: 20px 0 12px; padding-left: 10px;
    border-left: 4px solid #1565c0;
}
.alert-ng {
    background:#ffebee; border-left:4px solid #c62828;
    padding:10px 16px; border-radius:8px; color:#b71c1c; font-weight:600;
}
.stButton>button { border-radius: 8px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ─── Google Sheets 接続確認 ──────────────────────────────────────
try:
    from sheets import (
        load_arrivals, append_arrival,
        load_brewing, append_brewing,
        load_materials, save_materials,
        load_makers, save_makers,
        next_arrival_no, next_brewing_no
    )
    SHEETS_OK = True
except Exception as e:
    SHEETS_OK = False
    SHEETS_ERROR = str(e)

# ─── サイドバー ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🧪 原料管理システム")
    if SHEETS_OK:
        st.success("🟢 Google Sheets 接続中")
    else:
        st.error("🔴 接続エラー")
    st.markdown("---")
    page = st.radio(
        "メニュー",
        ["🏠 ダッシュボード", "📦 入荷記録", "🧪 仕込み記録",
         "🔍 原料トレース", "📊 月別集計", "⚙️ マスター設定"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.caption(f"更新: {datetime.now().strftime('%Y/%m/%d %H:%M')}")

# 接続エラー時の案内
if not SHEETS_OK:
    st.error(f"Google Sheets への接続に失敗しました。`.streamlit/secrets.toml` を確認してください。\n\n`{SHEETS_ERROR}`")
    st.info("📖 **セットアップ手順は README.md を参照してください**")
    st.stop()

# ─── データ読み込み（キャッシュ） ───────────────────────────────
@st.cache_data(ttl=30, show_spinner="📡 データを読み込み中...")
def cached_arrivals():  return load_arrivals()

@st.cache_data(ttl=30, show_spinner="📡 データを読み込み中...")
def cached_brewing():   return load_brewing()

@st.cache_data(ttl=60)
def cached_materials(): return load_materials()

@st.cache_data(ttl=60)
def cached_makers():    return load_makers()

def refresh():
    cached_arrivals.clear()
    cached_brewing.clear()
    st.rerun()

arrivals  = cached_arrivals()
brewing   = cached_brewing()
materials = cached_materials()
makers    = cached_makers()

# ════════════════════════════════════════════════════════════════
# ダッシュボード
# ════════════════════════════════════════════════════════════════
if page == "🏠 ダッシュボード":
    st.markdown("""
    <div class="main-header">
      <h1>🧪 原料使用記録 管理システム</h1>
      <p>Google Sheets 連携 ／ 入荷・仕込み・トレースを一元管理</p>
    </div>""", unsafe_allow_html=True)

    today = str(date.today())
    today_brew   = [b for b in brewing if b.get("brew_date") == today]
    recent7_brew = []
    for b in brewing:
        bd = b.get("brew_date","")
        if bd:
            try:
                if (date.today() - date.fromisoformat(bd)).days <= 7:
                    recent7_brew.append(b)
            except: pass

    c1,c2,c3,c4 = st.columns(4)
    for col, val, label in [
        (c1, len(arrivals),   "📦 総入荷件数"),
        (c2, len(brewing),    "🧪 総仕込み件数"),
        (c3, len(today_brew), "📅 本日の仕込み"),
        (c4, f"{sum(b.get('brew_amount',0) or 0 for b in recent7_brew):,.0f}", "⚖️ 直近7日 仕込量(kg)"),
    ]:
        col.markdown(f"""
        <div class="kpi-card">
          <div class="kpi-value">{val}</div>
          <div class="kpi-label">{label}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-title">📦 最近の入荷（10件）</div>', unsafe_allow_html=True)
        if arrivals:
            df = pd.DataFrame(arrivals[-10:][::-1])
            show = df.reindex(columns=["arrival_no","arrival_date","maker","lot_no","bags","total_kg","appearance","inspector"])
            show.columns = ["入荷No","入荷日","メーカー","ロットNo","袋数","総量(kg)","外観","担当者"]
            st.dataframe(show, use_container_width=True, hide_index=True, height=300)
        else:
            st.info("入荷記録がまだありません")

    with col2:
        st.markdown('<div class="section-title">🧪 最近の仕込み（10件）</div>', unsafe_allow_html=True)
        if brewing:
            df = pd.DataFrame(brewing[-10:][::-1])
            show = df.reindex(columns=["no","brew_date","product_name","maker","lot_no","brew_amount","material_kg"])
            show.columns = ["No","仕込日","品名","メーカー","ロットNo","仕込量(kg)","精粉(kg)"]
            st.dataframe(show, use_container_width=True, hide_index=True, height=300)
        else:
            st.info("仕込み記録がまだありません")

# ════════════════════════════════════════════════════════════════
# 入荷記録
# ════════════════════════════════════════════════════════════════
elif page == "📦 入荷記録":
    st.markdown("""
    <div class="main-header">
      <h1>📦 原料入荷記録</h1>
      <p>入荷時の外観検査・担当者記録を行います。記録は即座に Google Sheets へ保存されます。</p>
    </div>""", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["➕ 新規入荷登録", "📋 入荷一覧・帳票出力"])

    with tab1:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">📋 基本情報</div>', unsafe_allow_html=True)

        c1,c2,c3 = st.columns(3)
        with c1:
            new_no = next_arrival_no(arrivals)
            st.text_input("入荷No（自動採番）", value=new_no, disabled=True)
        with c2:
            arrival_date = st.date_input("入荷日", value=date.today())
        with c3:
            maker_opts = makers + ["その他"]
            maker = st.selectbox("メーカー", maker_opts)
            if maker == "その他":
                maker = st.text_input("メーカー名を直接入力")

        c4,c5,c6 = st.columns(3)
        with c4:
            lot_no = st.text_input("ロットNo ＊", placeholder="例: 1-101")
        with c5:
            material_type = st.selectbox("原料種別", materials)
        with c6:
            bags = st.number_input("袋数", min_value=0, step=1)

        bags_per = st.number_input("1袋あたり重量 (kg)", min_value=0.0, value=20.0, step=0.5)
        total_kg = bags * bags_per
        st.info(f"📦 自動計算 総量: **{total_kg:,.1f} kg**（{bags}袋 × {bags_per}kg）")

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">🔍 入荷時検査チェック</div>', unsafe_allow_html=True)

        c7,c8 = st.columns(2)
        CHECK_OK = ["OK（正常）", "NG（異常あり）", "要確認・未確認"]
        CHECK_TEMP = ["OK（基準内）", "NG（基準外）", "未確認"]
        CHECK_CONT = ["なし（正常）", "あり（要報告）", "未確認"]
        CHECK_BOOL = ["OK（良好）", "NG（異常あり）", "要確認"]

        with c7:
            transport_temp = st.selectbox("① 搬入温度",   CHECK_TEMP)
            appearance     = st.selectbox("② 外観",       CHECK_OK)
            odor           = st.selectbox("③ 臭い",       CHECK_OK)
            packaging      = st.selectbox("④ 包装状態",   CHECK_BOOL)
        with c8:
            color_check    = st.selectbox("⑤ 色調",       CHECK_OK)
            contamination  = st.selectbox("⑥ 異物混入",   CHECK_CONT)
            moisture       = st.selectbox("⑦ 水分状態",   CHECK_BOOL)
            expiry_check   = st.selectbox("⑧ 賞味期限確認", ["OK（期限内）","NG（期限切れ/不明）","未確認"])

        all_checks = [transport_temp, appearance, odor, packaging,
                      color_check, contamination, moisture, expiry_check]
        has_ng = any("NG" in c or "あり（要" in c for c in all_checks)

        abnormal_detail = ""
        if has_ng:
            st.markdown('<div class="alert-ng">⚠️ 異常が検出されました。詳細を記録し工場長に報告してください。</div>', unsafe_allow_html=True)
            abnormal_detail = st.text_area("異常内容・措置方法 ＊", placeholder="異常の詳細と対応措置を記入してください")

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">👤 担当者・備考</div>', unsafe_allow_html=True)

        c9,c10 = st.columns(2)
        with c9:
            inspector = st.text_input("担当者名 ＊", placeholder="例: 若槻")
        with c10:
            remarks = st.text_input("備考", placeholder="例: 製造年月日 R7/10/18")
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("✅ 入荷記録を Google Sheets へ保存", type="primary", use_container_width=True):
            if not lot_no:
                st.error("ロットNoを入力してください")
            elif not inspector:
                st.error("担当者名を入力してください")
            elif has_ng and not abnormal_detail:
                st.error("異常内容・措置方法を記入してください")
            else:
                with st.spinner("💾 Google Sheets へ保存中..."):
                    record = {
                        "arrival_no": new_no, "arrival_date": str(arrival_date),
                        "maker": maker, "lot_no": lot_no, "material_type": material_type,
                        "bags": bags, "bags_per_kg": bags_per, "total_kg": total_kg,
                        "transport_temp": transport_temp, "appearance": appearance,
                        "odor": odor, "packaging": packaging, "color_check": color_check,
                        "contamination": contamination, "moisture": moisture,
                        "expiry_check": expiry_check, "abnormal_detail": abnormal_detail,
                        "inspector": inspector, "remarks": remarks,
                        "registered_at": datetime.now().isoformat()
                    }
                    append_arrival(record)
                st.success(f"✅ **{new_no}** を Google Sheets へ保存しました！")
                refresh()

    with tab2:
        st.markdown('<div class="section-title">📋 入荷記録一覧</div>', unsafe_allow_html=True)

        fc1,fc2,fc3 = st.columns(3)
        with fc1: f_maker = st.selectbox("メーカー", ["全て"] + makers, key="af_maker")
        with fc2: f_lot   = st.text_input("ロットNo検索", key="af_lot")
        with fc3: f_app   = st.selectbox("外観", ["全て","OK（正常）","NG（異常あり）","要確認・未確認"], key="af_app")

        filtered = arrivals
        if f_maker != "全て": filtered = [a for a in filtered if a.get("maker") == f_maker]
        if f_lot:             filtered = [a for a in filtered if f_lot.lower() in str(a.get("lot_no","")).lower()]
        if f_app   != "全て": filtered = [a for a in filtered if a.get("appearance") == f_app]

        if filtered:
            df = pd.DataFrame(filtered)
            show_cols = {
                "arrival_no":"入荷No","arrival_date":"入荷日","maker":"メーカー",
                "lot_no":"ロットNo","material_type":"原料種別","bags":"袋数",
                "total_kg":"総量(kg)","appearance":"外観","transport_temp":"搬入温度",
                "inspector":"担当者","remarks":"備考"
            }
            df_show = df.reindex(columns=list(show_cols.keys()))
            df_show.columns = list(show_cols.values())
            st.dataframe(df_show[::-1].reset_index(drop=True),
                         use_container_width=True, hide_index=True, height=420)

            if st.button("📄 入荷記録帳票を出力（Excel）"):
                from report_generator import generate_arrival_report
                path = generate_arrival_report(filtered)
                with open(path,"rb") as f:
                    st.download_button("⬇️ Excelをダウンロード", f,
                        file_name=f"入荷記録_{date.today()}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("該当する入荷記録がありません")

# ════════════════════════════════════════════════════════════════
# 仕込み記録
# ════════════════════════════════════════════════════════════════
elif page == "🧪 仕込み記録":
    st.markdown("""
    <div class="main-header">
      <h1>🧪 仕込み記録</h1>
      <p>品目別の原料使用量・仕込み量を記録します</p>
    </div>""", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["➕ 新規仕込み登録", "📋 仕込み一覧・帳票出力"])

    with tab1:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">📋 基本情報</div>', unsafe_allow_html=True)

        c1,c2,c3 = st.columns(3)
        with c1: brew_date     = st.date_input("仕込日", value=date.today())
        with c2: product_name  = st.text_input("品名 ＊", placeholder="例: つきこん（黒）")
        with c3: brew_maker    = st.selectbox("メーカー", makers + ["その他"], key="bm")

        active_lots = sorted(set(a["lot_no"] for a in arrivals if a.get("lot_no")), reverse=True)
        c4,c5 = st.columns(2)
        with c4:
            lot_no_b = st.selectbox("ロットNo ＊（入荷記録から選択）",
                                    ["─ 選択してください ─"] + active_lots)
        with c5:
            brew_amount = st.number_input("仕込量 (kg)", min_value=0.0, step=50.0)

        # 選択ロットの入荷情報を表示
        if lot_no_b != "─ 選択してください ─":
            matched = next((a for a in arrivals if a.get("lot_no") == lot_no_b), None)
            if matched:
                st.info(f"📦 入荷No: **{matched['arrival_no']}** ／ メーカー: **{matched['maker']}** ／ 入荷日: **{matched['arrival_date']}** ／ 外観: **{matched['appearance']}**")

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        st.markdown('<div class="form-section-title">⚗️ 原料使用量入力</div>', unsafe_allow_html=True)

        c6,c7,c8 = st.columns(3)
        with c6:
            material_kg = st.number_input("こんにゃく精粉 (kg)", min_value=0.0, step=0.1, format="%.2f")
            seaweed_kg  = st.number_input("海藻粉 (kg)",         min_value=0.0, step=0.1, format="%.2f")
        with c7:
            starch_kg   = st.number_input("加工デンプン (kg)",   min_value=0.0, step=0.1, format="%.2f")
            starch_type = st.selectbox("デンプン種別", ["─","ゆり8","VA70","その他"])
        with c8:
            lime_kg      = st.number_input("石灰 (kg)",    min_value=0.0, step=0.1, format="%.2f")
            lime_water_l = st.number_input("石灰水 (ℓ)",  min_value=0.0, step=10.0, format="%.1f")

        notes_b = st.text_area("備考・メモ", placeholder="特記事項があれば入力")
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("✅ 仕込み記録を Google Sheets へ保存", type="primary", use_container_width=True):
            if not product_name:
                st.error("品名を入力してください")
            elif lot_no_b == "─ 選択してください ─":
                st.error("ロットNoを選択してください")
            else:
                with st.spinner("💾 Google Sheets へ保存中..."):
                    record = {
                        "no": next_brewing_no(brewing),
                        "brew_date": str(brew_date), "product_name": product_name,
                        "maker": brew_maker, "lot_no": lot_no_b,
                        "brew_amount": brew_amount, "material_kg": material_kg,
                        "seaweed_kg": seaweed_kg, "starch_kg": starch_kg,
                        "starch_type": starch_type if starch_type != "─" else "",
                        "lime_kg": lime_kg, "lime_water_l": lime_water_l,
                        "notes": notes_b, "registered_at": datetime.now().isoformat()
                    }
                    append_brewing(record)
                st.success(f"✅ 仕込み記録 **No.{record['no']}** を保存しました！")
                refresh()

    with tab2:
        st.markdown('<div class="section-title">📋 仕込み記録一覧</div>', unsafe_allow_html=True)

        fc1,fc2,fc3 = st.columns(3)
        with fc1: f_from = st.date_input("期間（開始）", value=None, key="bf_from")
        with fc2: f_to   = st.date_input("期間（終了）", value=None, key="bf_to")
        with fc3: f_lot_b = st.text_input("ロットNo検索", key="bf_lot")

        filtered_b = brewing
        if f_from:  filtered_b = [b for b in filtered_b if b.get("brew_date","") >= str(f_from)]
        if f_to:    filtered_b = [b for b in filtered_b if b.get("brew_date","") <= str(f_to)]
        if f_lot_b: filtered_b = [b for b in filtered_b if f_lot_b.lower() in str(b.get("lot_no","")).lower()]

        if filtered_b:
            df = pd.DataFrame(filtered_b)
            show_cols = {
                "no":"No","brew_date":"仕込日","product_name":"品名","maker":"メーカー",
                "lot_no":"ロットNo","brew_amount":"仕込量(kg)","material_kg":"精粉(kg)",
                "seaweed_kg":"海藻粉(kg)","starch_kg":"加工デンプン(kg)",
                "lime_kg":"石灰(kg)","lime_water_l":"石灰水(ℓ)"
            }
            df_show = df.reindex(columns=list(show_cols.keys()))
            df_show.columns = list(show_cols.values())
            st.dataframe(df_show[::-1].reset_index(drop=True),
                         use_container_width=True, hide_index=True, height=420)

            if st.button("📄 仕込み記録帳票を出力（Excel）"):
                from report_generator import generate_brewing_report
                path = generate_brewing_report(filtered_b)
                with open(path,"rb") as f:
                    st.download_button("⬇️ Excelをダウンロード", f,
                        file_name=f"仕込み記録_{date.today()}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("該当する仕込み記録がありません")

# ════════════════════════════════════════════════════════════════
# 原料トレース
# ════════════════════════════════════════════════════════════════
elif page == "🔍 原料トレース":
    st.markdown("""
    <div class="main-header">
      <h1>🔍 原料トレース</h1>
      <p>ロットNo・メーカー・入荷Noで入荷〜仕込みの全使用履歴を追跡します</p>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="form-card">', unsafe_allow_html=True)
    search_type = st.radio("検索種別", ["ロットNo","メーカー","入荷No","日付範囲"], horizontal=True)

    c1,c2 = st.columns(2)
    keyword = ""; date_from = date_to = None
    if search_type == "ロットNo":
        with c1: keyword = st.text_input("ロットNo", placeholder="例: 1-109")
    elif search_type == "メーカー":
        with c1: keyword = st.selectbox("メーカー", makers)
    elif search_type == "入荷No":
        with c1: keyword = st.text_input("入荷No", placeholder="例: A-0009")
    elif search_type == "日付範囲":
        with c1: date_from = st.date_input("開始日")
        with c2: date_to   = st.date_input("終了日")
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("🔍 トレース検索実行", type="primary"):
        results = []
        for b in brewing:
            lot = b.get("lot_no","")
            bd  = b.get("brew_date","")
            matched = False

            if search_type == "ロットNo" and keyword:
                matched = keyword.lower() in lot.lower()
            elif search_type == "メーカー" and keyword:
                maker_lots = {a["lot_no"] for a in arrivals if a.get("maker") == keyword}
                matched = lot in maker_lots
            elif search_type == "入荷No" and keyword:
                arr_lot = next((a["lot_no"] for a in arrivals if a.get("arrival_no") == keyword), None)
                matched = arr_lot == lot
            elif search_type == "日付範囲" and date_from and date_to:
                matched = str(date_from) <= bd <= str(date_to)

            if matched:
                arr = next((a for a in arrivals if a.get("lot_no") == lot), None)
                results.append({
                    "入荷No":      arr["arrival_no"] if arr else "-",
                    "メーカー":    arr["maker"] if arr else b.get("maker","-"),
                    "入荷日":      arr["arrival_date"] if arr else "-",
                    "ロットNo":    lot,
                    "袋数":        arr["bags"] if arr else "-",
                    "外観":        arr["appearance"] if arr else "-",
                    "使用日":      bd,
                    "品名":        b.get("product_name",""),
                    "精粉(kg)":   b.get("material_kg",0),
                    "仕込量(kg)": b.get("brew_amount",0),
                    "仕込みNo":    b.get("no",""),
                })

        if results:
            st.success(f"✅ **{len(results)}件** の使用履歴が見つかりました")
            df_t = pd.DataFrame(results)
            st.dataframe(df_t, use_container_width=True, hide_index=True)

            if st.button("📄 トレース帳票を出力（Excel）"):
                from report_generator import generate_trace_report
                kw = keyword or f"{date_from}〜{date_to}"
                path = generate_trace_report(results, search_type, kw)
                with open(path,"rb") as f:
                    st.download_button("⬇️ Excelをダウンロード", f,
                        file_name=f"原料トレース_{date.today()}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.warning("該当するトレース情報が見つかりませんでした")

# ════════════════════════════════════════════════════════════════
# 月別集計
# ════════════════════════════════════════════════════════════════
elif page == "📊 月別集計":
    st.markdown("""
    <div class="main-header">
      <h1>📊 月別集計・分析</h1>
      <p>原料使用量の月別トレンド</p>
    </div>""", unsafe_allow_html=True)

    if not brewing:
        st.info("仕込み記録がまだありません")
    else:
        df = pd.DataFrame(brewing)
        df["brew_date"] = pd.to_datetime(df["brew_date"], errors="coerce")
        df["year_month"] = df["brew_date"].dt.to_period("M").astype(str)

        for col in ["brew_amount","material_kg","seaweed_kg","lime_kg"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        monthly = df.groupby("year_month").agg(
            件数=("no","count"),
            仕込量=("brew_amount","sum"),
            精粉=("material_kg","sum"),
            海藻粉=("seaweed_kg","sum"),
            石灰=("lime_kg","sum"),
        ).reset_index()

        fig = go.Figure()
        fig.add_bar(x=monthly["year_month"], y=monthly["仕込量"], name="仕込量合計(kg)", marker_color="#1565c0")
        fig.add_bar(x=monthly["year_month"], y=monthly["精粉"],   name="精粉(kg)",      marker_color="#43a047")
        fig.add_bar(x=monthly["year_month"], y=monthly["海藻粉"], name="海藻粉(kg)",    marker_color="#e53935")
        fig.update_layout(
            barmode="group", height=380, plot_bgcolor="#f8faff", paper_bgcolor="#fff",
            font=dict(family="Noto Sans JP"), xaxis_title="年月", yaxis_title="量 (kg)",
            legend=dict(orientation="h", y=-0.2)
        )
        st.plotly_chart(fig, use_container_width=True)

        monthly_disp = monthly.copy()
        monthly_disp.columns = ["年月","件数","仕込量(kg)","精粉(kg)","海藻粉(kg)","石灰(kg)"]
        st.dataframe(monthly_disp, use_container_width=True, hide_index=True)

        if st.button("📄 月別集計帳票を出力（Excel）"):
            from report_generator import generate_monthly_report
            path = generate_monthly_report(monthly_disp.to_dict("records"), brewing)
            with open(path,"rb") as f:
                st.download_button("⬇️ Excelをダウンロード", f,
                    file_name=f"月別集計_{date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ════════════════════════════════════════════════════════════════
# マスター設定
# ════════════════════════════════════════════════════════════════
elif page == "⚙️ マスター設定":
    st.markdown("""
    <div class="main-header">
      <h1>⚙️ マスター設定</h1>
      <p>原料・メーカーのマスターデータを管理します（Google Sheetsへ保存）</p>
    </div>""", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🧴 原料マスター（最大20種）", "🏭 メーカーマスター"])

    with tab1:
        mat_text = st.text_area("原料リスト（1行1原料）", value="\n".join(materials), height=400)
        if st.button("💾 原料マスターを保存", type="primary"):
            new_mats = [m.strip() for m in mat_text.splitlines() if m.strip()]
            if len(new_mats) > 20:
                st.warning(f"原料は20種類まで登録可能です（現在{len(new_mats)}種）")
            else:
                with st.spinner("保存中..."):
                    save_materials(new_mats)
                    cached_materials.clear()
                st.success(f"✅ 原料マスター（{len(new_mats)}種）を保存しました")
                st.rerun()

    with tab2:
        maker_text = st.text_area("メーカーリスト（1行1メーカー）", value="\n".join(makers), height=200)
        if st.button("💾 メーカーマスターを保存", type="primary"):
            new_makers = [m.strip() for m in maker_text.splitlines() if m.strip()]
            with st.spinner("保存中..."):
                save_makers(new_makers)
                cached_makers.clear()
            st.success(f"✅ メーカーマスター（{len(new_makers)}件）を保存しました")
            st.rerun()
