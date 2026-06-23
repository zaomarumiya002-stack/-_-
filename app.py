import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import json
from datetime import datetime, date, timedelta
from collections import Counter
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
#  デザイントークン & グローバルCSS
# ════════════════════════════════════════════════════════════════
WARN_BUFFER = 0.3  # 発注点の何%上まで「注意」ゾーンにするか（0.3=30%）

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=JetBrains+Mono:wght@500;700&display=swap');

:root{
  --c-bg:#f1f5f9; --c-surface:#ffffff; --c-primary:#163b66; 
  --c-primary-light:#2f6fb0; --c-border:#94a3b8;
}
*, html, body { font-family:'Noto Sans JP', sans-serif; }
.stApp { background: var(--c-bg); }

/* Improved Input Field Visibility */
.stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"], 
.stTextArea textarea, .stDateInput input {
    background-color: #ffffff !important;
    border: 2px solid var(--c-border) !important;
    border-radius: 8px !important;
    color: #0f172a !important;
    font-size: 1rem !important;
    font-weight: 500 !important;
    padding: 12px !important;
}

/* Enhanced Focus Effect */
.stTextInput input:focus, .stNumberInput input:focus, 
.stSelectbox div[data-baseweb="select"]:focus-within {
    border-color: var(--c-primary) !important;
    box-shadow: 0 0 0 4px rgba(22, 59, 102, 0.1) !important;
}

/* Label Styling */
label { 
    color: #1e293b !important; 
    font-weight: 700 !important; 
    margin-bottom: 5px !important; 
    font-size: 0.95rem !important;
}

/* Card Styling */
.form-card { 
    background: var(--c-surface); 
    border: 1px solid #cbd5e1; 
    border-radius: 12px; 
    padding: 24px; 
    margin-bottom: 20px; 
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); 
}

/* Header Styling */
.main-header{ 
    background:linear-gradient(120deg, #163b66, #2f6fb0); 
    padding:24px; border-radius:12px; margin-bottom:24px; color:white;
    box-shadow: 0 4px 12px rgba(22,59,102,0.3);
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
#  sheets.py 接続（必須関数 / 追加機能用の任意関数）
# ════════════════════════════════════════════════════════════════
try:
    from sheets import (
        load_arrivals, append_arrival, update_arrival, load_brewing, append_brewing, update_brewing,
        load_adjustments, append_adjustment, load_supplies, save_supplies, load_supply_logs, append_supply_log,
        load_materials, save_materials, load_makers, save_makers, load_inspectors, save_inspectors,
        load_order_points, save_order_points, next_arrival_no, next_brewing_no
    )
    SHEETS_OK = True
except Exception:
    st.error(f"🚨 システム起動エラー\n\n```\n{traceback.format_exc()}\n```")
    st.stop()

# 任意機能：資材の入出庫ログを個別に編集・削除する関数。
# sheets.py に未実装の場合でもアプリ全体は問題なく動作し、該当UIのみ案内表示に切り替わる。
try:
    from sheets import update_supply_log, delete_supply_log
    HAS_LOG_EDIT = True
except Exception:
    HAS_LOG_EDIT = False
    def update_supply_log(*a, **kw): pass
    def delete_supply_log(*a, **kw): pass

def refresh():
    st.cache_data.clear()
    st.rerun()

# ════════════════════════════════════════════════════════════════
#  共通ヘルパー
# ════════════════════════════════════════════════════════════════
STATUS_LABEL = {"ok": "正常", "warn": "注意", "ng": "発注", "none": "未設定"}

def calc_status(current, threshold):
    if threshold is None or threshold <= 0: return "none"
    if current < threshold: return "ng"
    if current < threshold * (1 + WARN_BUFFER): return "warn"
    return "ok"

def gauge_html(label, current, threshold, unit="袋", caption=""):
    status = calc_status(current, threshold)
    if threshold and threshold > 0:
        scale_max = max(current * 1.15, threshold * 1.5, 1)
        fill_pct = max(min(current / scale_max * 100, 100), 0)
        thresh_pct = max(min(threshold / scale_max * 100, 100), 0)
        marker = f'<div class="gauge-threshold-marker" style="left:{thresh_pct:.1f}%;"></div>'
        nums = f'<span class="gauge-current">{current:,.1f} {unit}</span><span class="gauge-sep">発注点 {threshold:,.1f} {unit}</span>'
    else:
        scale_max = max(current * 1.2, 1)
        fill_pct = max(min(current / scale_max * 100, 100), 0)
        marker = ""
        nums = f'<span class="gauge-current">{current:,.1f} {unit}</span><span class="gauge-sep">発注点未設定</span>'
    cap = f'<div class="gauge-caption">{caption}</div>' if caption else ""
    return (f'<div class="gauge-card"><div class="gauge-head"><span class="gauge-label">{label}</span>'
            f'<span class="gauge-badge {status}">{STATUS_LABEL[status]}</span></div>'
            f'<div class="gauge-track"><div class="gauge-fill {status}" style="width:{fill_pct:.1f}%;"></div>{marker}</div>'
            f'<div class="gauge-numbers">{nums}</div>{cap}</div>')

def status_chip(current, threshold):
    status = calc_status(current, threshold)
    icon = {"ok": "🟢", "warn": "🟡", "ng": "🔴", "none": "⚪"}[status]
    return f'<span class="status-chip {status}">{icon} {STATUS_LABEL[status]}</span>'

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

def safe_index(lst, val, default=0):
    try: return lst.index(val)
    except ValueError: return default

# ════════════════════════════════════════════════════════════════
#  サイドバー
# ════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🏭 原料管理 ERP")
    st.markdown('<span style="color:#4caf50;font-size:.8rem">● データベース接続中</span>', unsafe_allow_html=True)
    st.markdown("---")
    page = st.radio("", ["🏠 ダッシュボード", "📦 入荷記録", "🧪 仕込み記録", "🏭 原料在庫", "🧹 資材在庫", "🔍 双方向トレース", "📈 統計・比較分析", "⚙️ マスター設定"], label_visibility="collapsed")
    if st.button("🔄 データ手動更新", use_container_width=True): refresh()
    st.caption(f"最終読込: {datetime.now().strftime('%H:%M')}")

# ════════════════════════════════════════════════════════════════
#  データ取得
# ════════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def fetch_all():
    return (load_arrivals(), load_brewing(), load_adjustments(), load_supplies(), load_supply_logs(),
            load_materials(), load_makers(), load_inspectors(), load_order_points())

try:
    (arrivals, brewing, adjustments, supplies, supply_logs, materials, makers, inspectors, order_points) = fetch_all()
except Exception:
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
            except Exception: pass

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
        "initial": float(s.get("初期在庫") or 0), "発注点": float(s.get("発注点") or 0), "in_out": 0.0,
        "登録日": str(s.get("登録日", ""))
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

def build_supply_timeline(supply_id, initial):
    """指定した資材IDの在庫推移（時系列の累積在庫）を構築する"""
    logs = [lg for lg in supply_logs if str(lg.get("資材ID", "")) == str(supply_id)]
    def _parse_date(s):
        s = str(s).replace("/", "-").replace(".", "-")
        try: return pd.to_datetime(s)
        except Exception: return pd.NaT
    rows = []
    for lg in logs:
        d = _parse_date(lg.get("登録日"))
        amt = float(lg.get("数量") or 0)
        delta = amt if "入荷" in str(lg.get("処理", "")) else -amt
        rows.append({"date": d, "delta": delta, "処理": lg.get("処理", ""), "数量": amt, "作業者": lg.get("作業者", ""), "ログID": lg.get("ログID", "")})
    df = pd.DataFrame(rows).dropna(subset=["date"]).sort_values("date")
    if df.empty:
        return pd.DataFrame({"date": [pd.to_datetime(date.today())], "在庫": [initial]}), df
    start_date = df["date"].min() - timedelta(days=1)
    timeline = [{"date": start_date, "在庫": initial}]
    running = initial
    for _, r in df.iterrows():
        running += r["delta"]
        timeline.append({"date": r["date"], "在庫": running})
    return pd.DataFrame(timeline), df

inventory_data = get_inventory()
supply_inventory = get_supply_inv()

type_totals = {}
for v in inventory_data.values(): type_totals[v["原料種別"]] = type_totals.get(v["原料種別"], 0) + v["現在庫(袋)"]

raw_alerts = [f"⚠️ 【原料アラート】 {m} の在庫（{c:,.1f}袋）が発注点（{order_points.get(m, 0):,.1f}袋）を下回っています！" for m, c in type_totals.items() if m in order_points and c < order_points[m]]
sup_alerts = [f"📦 【資材アラート】 {s['資材名']} の在庫（{s['現在庫']:.0f}個）が発注点（{s['発注点']:.0f}個）を下回っています！" for s in supply_inventory if s.get("発注点", 0) > 0 and s["現在庫"] < s["発注点"]]

_STATUS_ORDER = {"ng": 0, "warn": 1, "ok": 2, "none": 3}

if page == "🏠 ダッシュボード":
    st.markdown(f'<div class="main-header"><div><h1>📊 ERP ダッシュボード</h1>'
                f'<p>工場の稼働状況・在庫・アラートをリアルタイムで把握します</p></div>'
                f'<div class="hdr-right">最終更新<br>{datetime.now().strftime("%Y/%m/%d %H:%M")}</div></div>', unsafe_allow_html=True)

    if raw_alerts or sup_alerts:
        for al in raw_alerts: st.markdown(f'<div class="alert-ng">{al}</div>', unsafe_allow_html=True)
        for al in sup_alerts: st.markdown(f'<div class="alert-warning">{al}</div>', unsafe_allow_html=True)

    df_b = pd.DataFrame(brewing)
    if not df_b.empty:
        df_b["仕込日"] = pd.to_datetime(df_b["仕込日"].astype(str).str.replace("/", "-").str.replace(".", "-"), errors="coerce")
        df_b["こんにゃく精粉(kg)"] = pd.to_numeric(df_b["こんにゃく精粉(kg)"], errors="coerce").fillna(0)
        df_b["こんにゃく粉(袋)"] = df_b["こんにゃく精粉(kg)"] / 20.0
        df_b["製品仕込量(kg)"] = pd.to_numeric(df_b["仕込量(kg)"], errors="coerce").fillna(0)

    avg_day = avg_month = avg_year = 0.0
    if not df_b.empty:
        today = pd.to_datetime(date.today())
        df_day = df_b[df_b["仕込日"] >= today - timedelta(days=1)]
        if not df_day.empty and len(df_day) > 0: avg_day = df_day["こんにゃく粉(袋)"].sum() / len(df_day)
        df_month = df_b[df_b["仕込日"] >= today - timedelta(days=30)]
        if not df_month.empty and len(df_month) > 0: avg_month = df_month["こんにゃく粉(袋)"].sum() / len(df_month)
        df_year = df_b[df_b["仕込日"] >= today - timedelta(days=365)]
        if not df_year.empty and len(df_year) > 0: avg_year = df_year["こんにゃく粉(袋)"].sum() / len(df_year)

    st.markdown('<div class="section-title">🏭 稼働・在庫サマリー</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    today_brews = len(df_b[df_b["仕込日"] == pd.to_datetime(date.today())]) if not df_b.empty else 0
    week_kg = df_b[df_b["仕込日"] >= pd.to_datetime(date.today() - timedelta(days=7))]["製品仕込量(kg)"].sum() if not df_b.empty else 0
    total_bags = sum(max(v["現在庫(袋)"], 0) for v in inventory_data.values())
    c1.markdown(f'<div class="kpi-card"><div class="kpi-value">{today_brews}</div><div class="kpi-label">本日の仕込み回数</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-card"><div class="kpi-value">{week_kg:,.0f}</div><div class="kpi-label">直近7日 製品仕込量(kg)</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-card"><div class="kpi-value">{total_bags:,.0f}</div><div class="kpi-label">全原料 総在庫(袋)</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi-card" style="border-top-color:#dc2626;"><div class="kpi-value" style="color:#c62828;">{len(raw_alerts)+len(sup_alerts)}</div><div class="kpi-label">要発注アラート</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">⚖️ 平均こんにゃく粉 消費ペース (1回あたり)</div>', unsafe_allow_html=True)
    c5, c6, c7 = st.columns(3)
    c5.markdown(f'<div class="kpi-card" style="border-top-color:#16a34a;"><div class="kpi-value" style="color:#15803d;">{avg_day:,.1f} 袋</div><div class="kpi-label">直近 1日 平均</div></div>', unsafe_allow_html=True)
    c6.markdown(f'<div class="kpi-card" style="border-top-color:#16a34a;"><div class="kpi-value" style="color:#15803d;">{avg_month:,.1f} 袋</div><div class="kpi-label">直近 1ヶ月 平均</div></div>', unsafe_allow_html=True)
    c7.markdown(f'<div class="kpi-card" style="border-top-color:#16a34a;"><div class="kpi-value" style="color:#15803d;">{avg_year:,.1f} 袋</div><div class="kpi-label">直近 1年 平均</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">🚦 発注点モニター（原料・添加物 / 資材）</div>', unsafe_allow_html=True)
    st.markdown('<p class="subtle-note">バーが赤に近いほど発注が必要です。縦線は発注点の位置を示します。発注点は「⚙️ マスター設定」でいつでも変更できます。</p>', unsafe_allow_html=True)
    gcol1, gcol2 = st.columns(2)
    with gcol1:
        st.markdown("##### ⚗️ 原料・添加物（種別ごとの合計在庫）")
        mats_sorted = sorted(type_totals.items(), key=lambda kv: _STATUS_ORDER[calc_status(kv[1], order_points.get(kv[0]))])
        if mats_sorted:
            for m, c in mats_sorted:
                st.markdown(gauge_html(m, c, order_points.get(m, 0)), unsafe_allow_html=True)
        else:
            st.info("原料データがありません")
    with gcol2:
        st.markdown("##### 🧹 資材・衛生備品")
        sups_sorted = sorted(supply_inventory, key=lambda s: _STATUS_ORDER[calc_status(s["現在庫"], s.get("発注点", 0))])
        if sups_sorted:
            for s in sups_sorted[:8]:
                st.markdown(gauge_html(s["資材名"], s["現在庫"], s.get("発注点", 0), unit="個"), unsafe_allow_html=True)
            if len(sups_sorted) > 8:
                with st.expander(f"他 {len(sups_sorted) - 8} 件を表示"):
                    for s in sups_sorted[8:]:
                        st.markdown(gauge_html(s["資材名"], s["現在庫"], s.get("発注点", 0), unit="個"), unsafe_allow_html=True)
        else:
            st.info("資材データがありません")

    st.markdown("<br>", unsafe_allow_html=True)
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
            months = pd.DataFrame({"month": range(1, 13)})
            df_curr = pd.merge(months, df_curr, on="month", how="left").fillna(0)
            df_prev = pd.merge(months, df_prev, on="month", how="left").fillna(0)

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_curr["month"], y=df_curr["こんにゃく粉(袋)"], mode='lines+markers', name=f"今年 ({curr_year})", line=dict(color="#163b66", width=4), marker=dict(size=8)))
            fig.add_trace(go.Scatter(x=df_prev["month"], y=df_prev["こんにゃく粉(袋)"], mode='lines+markers', name=f"昨年 ({prev_year})", line=dict(color="#b0bec5", width=3, dash='dash'), marker=dict(size=6)))
            fig.update_layout(height=350, margin=dict(l=20, r=20, t=20, b=20), plot_bgcolor="#f8faff", paper_bgcolor="#fff", xaxis=dict(title="月", tickmode='linear', tick0=1, dtick=1), yaxis=dict(title="こんにゃく粉 (袋)"), legend=dict(orientation="h", y=-0.15))
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("データがありません")

    with col_right:
        st.markdown('<div class="section-title">⏱️ 最新アクティビティ</div>', unsafe_allow_html=True)
        tab_a, tab_b = st.tabs(["🧪 最新の仕込み", "📦 最新の入荷"])
        with tab_a:
            if brewing: st.dataframe(pd.DataFrame(brewing)[["仕込日", "品名", "主原料ロット", "仕込量(kg)"]][::-1].head(8), use_container_width=True, hide_index=True)
            else: st.write("データなし")
        with tab_b:
            if arrivals: st.dataframe(pd.DataFrame(arrivals)[["入荷日", "原料種別", "ロットNo", "袋数"]][::-1].head(8), use_container_width=True, hide_index=True)
            else: st.write("データなし")

elif page == "📦 入荷記録":
    st.markdown('<div class="main-header"><div><h1>📦 原料入荷記録</h1><p>入荷時の品質検査と担当者記録</p></div></div>', unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["➕ 新規登録", "📋 履歴一覧", "✏️ 既存データ編集"])

    with t1:
        st.markdown('<div class="form-card"><div class="section-title">📦 基本情報</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        new_no = next_arrival_no(arrivals)
        c1.text_input("入荷No", value=new_no, disabled=True, key="new_arr_no")
        a_date = c2.date_input("入荷日", key="new_arr_date")
        maker = c3.selectbox("メーカー", makers + ["その他"], key="new_arr_maker")
        if maker == "その他": maker = st.text_input("メーカー直接入力", key="new_arr_maker_free")

        c4, c5, c6 = st.columns(3)
        lot_no = c4.text_input("ロットNo ＊", key="new_arr_lot")
        m_type = c5.selectbox("原料種別", materials, key="new_arr_mat")
        bags = c6.number_input("袋数", min_value=0, step=1, value=None, key="new_arr_bags")
        b_per = st.number_input("1袋重量(kg)", value=20.0, step=0.5, key="new_arr_bper")
        st.info(f"💡 自動計算 総量: **{(bags or 0) * b_per:,.1f} kg**")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="form-card"><div class="section-title">🔍 品質検査</div>', unsafe_allow_html=True)
        ck1, ck2 = st.columns(2)
        app = ck1.selectbox("① 外観検査", ["OK（正常）", "NG（異常あり）", "要確認"], key="new_arr_app")
        c_name = ck1.selectbox("② 品名・規格確認", ["OK（一致）", "NG（不一致）"], key="new_arr_name")
        c_exp = ck2.selectbox("③ 賞味・消費期限", ["OK（期限内）", "NG（期限外・不明）"], key="new_arr_exp")
        c_dmg = ck2.selectbox("④ 異物・破損確認", ["OK（なし）", "NG（あり）"], key="new_arr_dmg")

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
        if not arrivals:
            st.info("データがありません")
        else:
            st.markdown('<div class="section-title">📋 入荷履歴・品質検査結果一覧</div>', unsafe_allow_html=True)
            df_arr = pd.DataFrame(arrivals)[["入荷No", "入荷日", "メーカー", "ロットNo", "原料種別", "袋数", "外観", "品名・規格確認", "賞味期限", "異物", "異常内容", "担当者"]]

            def highlight_ng(s):
                return ['background-color: #fdeaea; color: #c62828; font-weight: bold' if 'NG' in str(v) else '' for v in s]

            st.dataframe(
                df_arr[::-1].reset_index(drop=True).style.apply(highlight_ng, subset=["外観", "品名・規格確認", "賞味期限", "異物"]),
                use_container_width=True, height=600
            )

    with t3:
        if not arrivals: st.info("データなし")
        else:
            st.markdown('<div class="form-card">', unsafe_allow_html=True)
            edit_target = st.selectbox("編集する入荷Noを選択", [a.get("入荷No") for a in reversed(arrivals) if a.get("入荷No")], key="edit_arr_sel")
            if edit_target:
                td = next((a for a in arrivals if a.get("入荷No") == edit_target), None)

                c_e1, c_e2, c_e3 = st.columns(3)
                e_date = c_e1.text_input("入荷日", value=td.get("入荷日", ""), key="ea_date")
                e_maker = c_e2.selectbox("メーカー", makers + ["その他"], index=safe_index(makers, td.get("メーカー"), len(makers)), key="ea_maker")
                if e_maker == "その他": e_maker = st.text_input("メーカー直接入力", value=td.get("メーカー", ""), key="ea_maker_free")
                e_lot = c_e3.text_input("ロットNo", value=td.get("ロットNo", ""), key="ea_lot")

                c_e4, c_e5 = st.columns(2)
                e_mat = c_e4.selectbox("原料種別", materials, index=safe_index(materials, td.get("原料種別"), 0), key="ea_mat")
                e_bags = c_e5.number_input("袋数", value=int(td.get("袋数") or 0), key="ea_bags")

                st.markdown('<div class="section-title" style="margin-top:10px;">🔍 品質検査の修正</div>', unsafe_allow_html=True)
                ck_e1, ck_e2 = st.columns(2)

                opts_app = ["OK（正常）", "NG（異常あり）", "要確認"]
                e_app = ck_e1.selectbox("外観検査", opts_app, index=safe_index(opts_app, td.get("外観", "OK（正常）")), key="ea_app")

                opts_name = ["OK（一致）", "NG（不一致）"]
                e_name = ck_e1.selectbox("品名・規格確認", opts_name, index=safe_index(opts_name, td.get("品名・規格確認", "OK（一致）")), key="ea_name")

                opts_exp = ["OK（期限内）", "NG（期限外・不明）"]
                e_exp = ck_e2.selectbox("賞味・消費期限", opts_exp, index=safe_index(opts_exp, td.get("賞味期限", "OK（期限内）")), key="ea_exp")

                opts_dmg = ["OK（なし）", "NG（あり）"]
                e_dmg = ck_e2.selectbox("異物・破損確認", opts_dmg, index=safe_index(opts_dmg, td.get("異物", "OK（なし）")), key="ea_dmg")

                e_abn = st.text_input("異常内容（NG時）", value=td.get("異常内容", ""), key="ea_abn")

                if st.button("💾 変更を上書き保存", type="primary", key="ea_save"):
                    td.update({
                        "入荷日": e_date, "メーカー": e_maker, "ロットNo": e_lot, "原料種別": e_mat, "袋数": e_bags,
                        "外観": e_app, "品名・規格確認": e_name, "賞味期限": e_exp, "異物": e_dmg, "異常内容": e_abn
                    })
                    update_arrival(td["入荷No"], td); st.success("更新しました！"); refresh()
            st.markdown('</div>', unsafe_allow_html=True)

elif page == "🧪 仕込み記録":
    st.markdown('<div class="main-header"><div><h1>🧪 仕込み記録</h1><p>品目別の原料使用量とロットの紐付け</p></div></div>', unsafe_allow_html=True)

    mode = st.radio("入力モード", ["🖥️ オフィスモード（PC・詳細入力）", "📱 現場タブレットモード（大きいボタン・ステップ入力）"], horizontal=True, key="brw_mode")
    is_tablet = mode.startswith("📱")

    tab_new, tab_hist, tab_edit = st.tabs(["➕ 新規登録", "📋 履歴一覧", "✏️ 既存データ編集"])

    with tab_new:
        if not is_tablet:
            st.markdown('<div class="form-card"><div class="section-title">📋 製品情報</div>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            b_date = c1.date_input("仕込日", key="new_brw_date")
            p_name = c2.text_input("品名 ＊", key="new_brw_name")
            b_amount = c3.number_input("製品仕込量(kg) ＊", min_value=0.0, value=None, step=10.0, key="new_brw_amt")
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="form-card"><div class="section-title">⚗️ 主原料（こんにゃく粉）</div>', unsafe_allow_html=True)
            cm1, cm2, cm3 = st.columns(3)
            sf_makers = ["すべて"] + sorted(list(set(a.get("メーカー", "") for a in arrivals if any(k in a.get("原料種別", "") for k in ["こんにゃく粉", "精粉", "粉", "マンナン"]))))
            sel_sf_maker = cm1.selectbox("🔍 こんにゃく粉メーカーで絞り込み", sf_makers, key="filter_maker")
            lot_no_b_disp = cm2.selectbox("こんにゃく粉 ロットNo ＊", get_fancy_lots(["こんにゃく粉", "精粉", "粉", "マンナン"], maker_filter=sel_sf_maker), key="new_brw_lot")
            lot_no_b = extract_lot(lot_no_b_disp)
            mat_kg = cm3.number_input("こんにゃく粉 使用量(kg)", min_value=0.0, value=None, format="%.2f", key="new_brw_mkg")
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="form-card"><div class="section-title">🌿 副原料（海藻・デンプン・石灰）</div>', unsafe_allow_html=True)
            r1, r2, r3 = st.columns(3)
            sea_lot_disp = r1.selectbox("海藻粉 ロット", get_fancy_lots(["海藻", "青海苔", "ひじき", "アラメ"]), key="new_brw_sl")
            sea_lot = extract_lot(sea_lot_disp)
            sea_kg = r1.number_input("海藻粉 使用量(kg)", min_value=0.0, value=None, format="%.2f", key="new_brw_skg")

            sta_lot_disp = r2.selectbox("加工デンプン ロット", get_fancy_lots(["デンプン", "でんぷん", "澱粉"]), key="new_brw_stl")
            sta_lot = extract_lot(sta_lot_disp)
            sta_kg = r2.number_input("デンプン 使用量(kg)", min_value=0.0, value=None, format="%.2f", key="new_brw_stkg")
            sta_type = r2.selectbox("デンプン種別", ["─", "ゆり8", "VA70", "その他"], key="new_brw_stt")

            lime_lot_disp = r3.selectbox("石灰 ロット", get_fancy_lots(["石灰"]), key="new_brw_ll")
            lime_lot = extract_lot(lime_lot_disp)
            lime_kg = r3.number_input("石灰(kg)", min_value=0.0, value=None, format="%.2f", key="new_brw_lkg")
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="form-card"><div class="section-title">🧂 その他添加物</div>', unsafe_allow_html=True)
            if "other_rows" not in st.session_state: st.session_state.other_rows = []
            for i, row in enumerate(st.session_state.other_rows):
                oc1, oc2, oc3, oc4 = st.columns([3, 4, 2, 1])
                sel_mat = oc1.selectbox("原料名", materials, key=f"mat_{i}", index=safe_index(materials, row["name"], 0))
                sel_lot_disp = oc2.selectbox("ロットNo", get_fancy_lots([sel_mat], current_val=row.get("lot")), key=f"lot_{i}")
                sel_lot = extract_lot(sel_lot_disp)
                sel_kg = oc3.number_input("使用量(kg)", min_value=0.0, format="%.2f", key=f"kg_{i}", value=float(row["kg"]) if row["kg"] else None)
                if oc4.button("❌", key=f"del_{i}"): st.session_state.other_rows.pop(i); st.rerun()
                st.session_state.other_rows[i] = {"name": sel_mat, "lot": sel_lot, "kg": sel_kg or 0.0}

            if st.button("➕ 添加物を追加", key="add_oth"): st.session_state.other_rows.append({"name": materials[0], "lot": "─", "kg": 0.0}); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

            if st.button("✅ 仕込み記録を保存", type="primary", use_container_width=True, key="save_brw_btn"):
                if not p_name or lot_no_b == "─" or not b_amount:
                    st.error("品名、主原料ロット、仕込量は必須です")
                else:
                    others_json = json.dumps([r for r in st.session_state.other_rows if r["kg"] > 0], ensure_ascii=False)
                    append_brewing({
                        "仕込No": next_brewing_no(brewing), "仕込日": str(b_date), "品名": p_name,
                        "主原料ロット": lot_no_b, "仕込量(kg)": b_amount or 0.0, "こんにゃく精粉(kg)": mat_kg or 0.0,
                        "海藻粉(kg)": sea_kg or 0.0, "海藻粉ロット": sea_lot,
                        "デンプン(kg)": sta_kg or 0.0, "デンプンロット": sta_lot, "デンプン種別": sta_type,
                        "石灰(kg)": lime_kg or 0.0, "石灰ロット": lime_lot,
                        "その他添加物": others_json, "登録日時": datetime.now().isoformat()
                    })
                    st.session_state.other_rows = []
                    st.success("保存しました！"); refresh()

        else:
            if "tablet_step" not in st.session_state: st.session_state.tablet_step = 1
            if "tablet_other_rows" not in st.session_state: st.session_state.tablet_other_rows = []
            if "tablet_data" not in st.session_state: st.session_state.tablet_data = {}
            TD = st.session_state.tablet_data

            def _lot_idx(opts, raw):
                if not raw: return 0
                for i, o in enumerate(opts):
                    if extract_lot(o) == raw: return i
                return 0

            with st.container(key="tablet_wizard"):
                step_labels = ["基本情報", "主原料", "副原料・添加物", "確認・保存"]
                step = st.session_state.tablet_step
                badges = "".join(
                    f'<span class="tablet-step-badge" style="opacity:{1 if i + 1 == step else .4};">{i + 1}. {lbl}</span>　'
                    for i, lbl in enumerate(step_labels)
                )
                st.markdown(badges, unsafe_allow_html=True)
                st.progress(step / 4)

                if step == 1:
                    st.markdown('<div class="form-card"><div class="section-title">① 基本情報</div>', unsafe_allow_html=True)
                    freq_names = [n for n, _ in Counter([b.get("品名") for b in brewing if b.get("品名")]).most_common(6)]
                    if freq_names:
                        st.caption("👉 よく使う品名をタップ:")
                        qcols = st.columns(min(len(freq_names), 6))
                        for i, n in enumerate(freq_names):
                            if qcols[i % len(qcols)].button(n, key=f"tb_qn_{i}", use_container_width=True):
                                st.session_state["tb_name"] = n; st.rerun()
                    b_date = st.date_input("仕込日", value=TD.get("date", date.today()), key="tb_date")
                    p_name = st.text_input("品名 ＊", value=TD.get("name", ""), key="tb_name")
                    b_amount = st.number_input("製品仕込量(kg) ＊", min_value=0.0, value=TD.get("amount"), step=10.0, key="tb_amount")
                    st.markdown('</div>', unsafe_allow_html=True)
                    if st.button("次へ →", type="primary", use_container_width=True, key="tb_next1"):
                        TD["date"], TD["name"], TD["amount"] = b_date, p_name, b_amount
                        if not p_name or not b_amount:
                            st.error("品名と製品仕込量は必須です")
                        else:
                            st.session_state.tablet_step = 2; st.rerun()

                elif step == 2:
                    st.markdown('<div class="form-card"><div class="section-title">② 主原料（こんにゃく粉）</div>', unsafe_allow_html=True)
                    main_opts = get_fancy_lots(["こんにゃく粉", "精粉", "粉", "マンナン"])
                    lot_map = {extract_lot(o): o for o in main_opts}
                    recent_lots = []
                    for b in reversed(brewing):
                        lot = b.get("主原料ロット")
                        if lot and lot != "─" and lot in lot_map and lot not in recent_lots:
                            recent_lots.append(lot)
                        if len(recent_lots) >= 4: break
                    if recent_lots:
                        st.caption("👉 最近使用したロットをタップ:")
                        rcols = st.columns(len(recent_lots))
                        for i, lot in enumerate(recent_lots):
                            if rcols[i].button(lot, key=f"tb_ql_{i}", use_container_width=True):
                                st.session_state["tb_main_lot"] = lot_map[lot]; st.rerun()
                    main_disp = st.selectbox("こんにゃく粉 ロットNo ＊", main_opts, index=_lot_idx(main_opts, TD.get("main_lot_raw", "")), key="tb_main_lot")
                    main_kg = st.number_input("こんにゃく粉 使用量(kg) ＊", min_value=0.0, value=TD.get("main_kg"), format="%.2f", key="tb_main_kg")
                    st.markdown('</div>', unsafe_allow_html=True)
                    nb1, nb2 = st.columns(2)
                    if nb1.button("← 戻る", use_container_width=True, key="tb_back2"):
                        TD["main_lot_raw"], TD["main_kg"] = extract_lot(main_disp), main_kg
                        st.session_state.tablet_step = 1; st.rerun()
                    if nb2.button("次へ →", type="primary", use_container_width=True, key="tb_next2"):
                        TD["main_lot_raw"], TD["main_kg"] = extract_lot(main_disp), main_kg
                        if TD["main_lot_raw"] == "─" or not main_kg:
                            st.error("主原料ロットと使用量は必須です")
                        else:
                            st.session_state.tablet_step = 3; st.rerun()

                elif step == 3:
                    st.markdown('<div class="form-card"><div class="section-title">③ 副原料（海藻・デンプン・石灰）</div>', unsafe_allow_html=True)
                    sea_opts = get_fancy_lots(["海藻", "青海苔", "ひじき", "アラメ"])
                    sea_disp = st.selectbox("海藻粉 ロット", sea_opts, index=_lot_idx(sea_opts, TD.get("sea_lot_raw", "")), key="tb_sea_lot")
                    sea_kg = st.number_input("海藻粉 使用量(kg)", min_value=0.0, value=TD.get("sea_kg"), format="%.2f", key="tb_sea_kg")
                    st.markdown("---")
                    starch_opts = get_fancy_lots(["デンプン", "でんぷん", "澱粉"])
                    starch_disp = st.selectbox("加工デンプン ロット", starch_opts, index=_lot_idx(starch_opts, TD.get("starch_lot_raw", "")), key="tb_starch_lot")
                    starch_kg = st.number_input("デンプン 使用量(kg)", min_value=0.0, value=TD.get("starch_kg"), format="%.2f", key="tb_starch_kg")
                    starch_types = ["─", "ゆり8", "VA70", "その他"]
                    starch_type = st.selectbox("デンプン種別", starch_types, index=safe_index(starch_types, TD.get("starch_type"), 0), key="tb_starch_type")
                    st.markdown("---")
                    lime_opts = get_fancy_lots(["石灰"])
                    lime_disp = st.selectbox("石灰 ロット", lime_opts, index=_lot_idx(lime_opts, TD.get("lime_lot_raw", "")), key="tb_lime_lot")
                    lime_kg = st.number_input("石灰 使用量(kg)", min_value=0.0, value=TD.get("lime_kg"), format="%.2f", key="tb_lime_kg")
                    st.markdown('</div>', unsafe_allow_html=True)

                    st.markdown('<div class="form-card"><div class="section-title">🧂 その他添加物（任意）</div>', unsafe_allow_html=True)
                    for i, row in enumerate(st.session_state.tablet_other_rows):
                        oc1, oc2, oc3, oc4 = st.columns([3, 4, 2, 1])
                        sel_mat = oc1.selectbox("原料名", materials, key=f"tb_mat_{i}", index=safe_index(materials, row["name"], 0))
                        sel_lot_disp = oc2.selectbox("ロットNo", get_fancy_lots([sel_mat], current_val=row.get("lot")), key=f"tb_lot_{i}")
                        sel_kg = oc3.number_input("使用量(kg)", min_value=0.0, format="%.2f", key=f"tb_kg_{i}", value=float(row["kg"]) if row["kg"] else None)
                        if oc4.button("❌", key=f"tb_del_{i}"): st.session_state.tablet_other_rows.pop(i); st.rerun()
                        st.session_state.tablet_other_rows[i] = {"name": sel_mat, "lot": extract_lot(sel_lot_disp), "kg": sel_kg or 0.0}
                    if st.button("➕ 添加物を追加", key="tb_add_oth", use_container_width=True):
                        st.session_state.tablet_other_rows.append({"name": materials[0], "lot": "─", "kg": 0.0}); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                    def _snap3():
                        TD["sea_lot_raw"], TD["sea_kg"] = extract_lot(sea_disp), sea_kg
                        TD["starch_lot_raw"], TD["starch_kg"], TD["starch_type"] = extract_lot(starch_disp), starch_kg, starch_type
                        TD["lime_lot_raw"], TD["lime_kg"] = extract_lot(lime_disp), lime_kg

                    nb1, nb2 = st.columns(2)
                    if nb1.button("← 戻る", use_container_width=True, key="tb_back3"):
                        _snap3(); st.session_state.tablet_step = 2; st.rerun()
                    if nb2.button("確認画面へ →", type="primary", use_container_width=True, key="tb_next3"):
                        _snap3(); st.session_state.tablet_step = 4; st.rerun()

                elif step == 4:
                    main_lot_f = TD.get("main_lot_raw") or "─"
                    sea_lot_f = TD.get("sea_lot_raw") or "─"
                    starch_lot_f = TD.get("starch_lot_raw") or "─"
                    lime_lot_f = TD.get("lime_lot_raw") or "─"
                    st.markdown('<div class="form-card"><div class="section-title">④ 入力内容の確認</div>', unsafe_allow_html=True)
                    rows = [
                        ("仕込日", str(TD.get("date", ""))), ("品名", TD.get("name", "")),
                        ("製品仕込量", f"{TD.get('amount') or 0:,.1f} kg"),
                        ("主原料ロット", main_lot_f), ("こんにゃく粉 使用量", f"{TD.get('main_kg') or 0:,.2f} kg"),
                    ]
                    if sea_lot_f != "─": rows.append(("海藻粉", f"ロット {sea_lot_f} ／ {TD.get('sea_kg') or 0:,.2f} kg"))
                    if starch_lot_f != "─": rows.append(("デンプン", f"ロット {starch_lot_f} ／ {TD.get('starch_kg') or 0:,.2f} kg ／ {TD.get('starch_type', '─')}"))
                    if lime_lot_f != "─": rows.append(("石灰", f"ロット {lime_lot_f} ／ {TD.get('lime_kg') or 0:,.2f} kg"))
                    for r in st.session_state.tablet_other_rows:
                        if r["kg"] > 0: rows.append((r["name"], f"ロット {r['lot']} ／ {r['kg']:,.2f} kg"))
                    st.markdown("".join(f'<div class="tablet-review-row"><span>{k}</span><b>{v}</b></div>' for k, v in rows), unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                    nb1, nb2 = st.columns(2)
                    if nb1.button("← 内容を修正", use_container_width=True, key="tb_back4"):
                        st.session_state.tablet_step = 3; st.rerun()
                    if nb2.button("✅ この内容で保存する", type="primary", use_container_width=True, key="tb_save"):
                        others_json = json.dumps([r for r in st.session_state.tablet_other_rows if r["kg"] > 0], ensure_ascii=False)
                        append_brewing({
                            "仕込No": next_brewing_no(brewing), "仕込日": str(TD.get("date", "")), "品名": TD.get("name", ""),
                            "主原料ロット": main_lot_f, "仕込量(kg)": TD.get("amount") or 0.0, "こんにゃく精粉(kg)": TD.get("main_kg") or 0.0,
                            "海藻粉(kg)": TD.get("sea_kg") or 0.0, "海藻粉ロット": sea_lot_f,
                            "デンプン(kg)": TD.get("starch_kg") or 0.0, "デンプンロット": starch_lot_f, "デンプン種別": TD.get("starch_type", "─"),
                            "石灰(kg)": TD.get("lime_kg") or 0.0, "石灰ロット": lime_lot_f,
                            "その他添加物": others_json, "登録日時": datetime.now().isoformat()
                        })
                        st.session_state.tablet_data = {}
                        st.session_state.tablet_other_rows = []
                        st.session_state.tablet_step = 1
                        st.success("保存しました！"); refresh()

    with tab_hist:
        if brewing:
            st.markdown('<div class="section-title">📋 仕込み履歴一覧</div>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(brewing)[["仕込No", "仕込日", "品名", "主原料ロット", "海藻粉ロット", "デンプンロット", "仕込量(kg)"]][::-1].reset_index(drop=True), use_container_width=True, height=500)
        else:
            st.info("データがありません")

    with tab_edit:
        if not brewing:
            st.info("データなし")
        else:
            st.markdown('<div class="form-card">', unsafe_allow_html=True)
            edit_target_b = st.selectbox("編集する仕込Noを選択", [f"{b.get('仕込No')} - {b.get('品名')}" for b in reversed(brewing) if b.get("仕込No")], key="edit_brw_sel")
            if edit_target_b:
                t_no = edit_target_b.split(" - ")[0]
                td = next((b for b in brewing if str(b.get("仕込No")) == str(t_no)), None)

                eb_name = st.text_input("品名", value=td.get("品名", ""), key="eb_name")
                eb_lot_disp = st.selectbox("こんにゃく粉ロットNo", get_fancy_lots(["こんにゃく粉", "精粉", "粉", "マンナン"], current_val=td.get("主原料ロット", "")), key="eb_lot")
                eb_sl_disp = st.selectbox("海藻粉ロットNo", get_fancy_lots(["海藻"], current_val=td.get("海藻粉ロット", "")), key="eb_slot")
                eb_stl_disp = st.selectbox("デンプンロットNo", get_fancy_lots(["デンプン"], current_val=td.get("デンプンロット", "")), key="eb_stlot")
                eb_amt = st.number_input("仕込量(kg)", value=float(td.get("仕込量(kg)") or 0), key="eb_amt")
                eb_mat = st.number_input("こんにゃく粉(kg)", value=float(td.get("こんにゃく精粉(kg)") or 0), key="eb_mat")
                if st.button("💾 変更を上書き保存", type="primary", key="eb_save"):
                    td.update({"品名": eb_name, "主原料ロット": extract_lot(eb_lot_disp), "海藻粉ロット": extract_lot(eb_sl_disp), "デンプンロット": extract_lot(eb_stl_disp), "仕込量(kg)": eb_amt, "こんにゃく精粉(kg)": eb_mat})
                    update_brewing(td["仕込No"], td); st.success("更新しました！"); refresh()
            st.markdown('</div>', unsafe_allow_html=True)

elif page == "🏭 原料在庫":
    st.markdown('<div class="main-header"><div><h1>🏭 原料在庫管理</h1><p>自動計算された現在庫（袋単位）と発注点モニター、棚卸し調整</p></div></div>', unsafe_allow_html=True)
    rt1, rt2, rt3 = st.tabs(["📊 発注点モニター", "📋 現在庫一覧（ロット別）", "⚖️ 在庫ズレ調整"])

    with rt1:
        st.markdown('<p class="subtle-note">原料種別ごとの合計在庫と発注点の状況です。発注点は「⚙️ マスター設定」の「発注点」タブで変更できます。</p>', unsafe_allow_html=True)
        if not type_totals:
            st.info("原料データがありません")
        else:
            mats_sorted = sorted(type_totals.items(), key=lambda kv: _STATUS_ORDER[calc_status(kv[1], order_points.get(kv[0]))])
            gc1, gc2 = st.columns(2)
            for i, (m, c) in enumerate(mats_sorted):
                (gc1 if i % 2 == 0 else gc2).markdown(gauge_html(m, c, order_points.get(m, 0)), unsafe_allow_html=True)

    with rt2:
        if not inventory_data:
            st.info("データなし")
        else:
            st.markdown('<div class="section-title">📋 ロット別 現在庫一覧</div>', unsafe_allow_html=True)
            inv_df = pd.DataFrame(list(inventory_data.values()))[["入荷No", "原料種別", "ロットNo", "入荷袋数", "使用袋数", "調整袋数", "現在庫(袋)"]]
            inv_df.columns = ["入荷No", "原料種別", "ロットNo", "入荷(袋)", "使用(袋)", "調整(袋)", "現在庫(袋)"]
            st.dataframe(inv_df, column_config={
                "入荷(袋)": st.column_config.NumberColumn(format="%.1f"), "使用(袋)": st.column_config.NumberColumn(format="%.1f"),
                "調整(袋)": st.column_config.NumberColumn(format="%.1f"), "現在庫(袋)": st.column_config.NumberColumn(format="%.1f")
            }, use_container_width=True, height=450)

    with rt3:
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        if not inventory_data:
            st.info("データなし")
        else:
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

elif page == "🧹 資材在庫":
    st.markdown('<div class="main-header"><div><h1>🧹 資材・衛生備品 管理</h1><p>一覧・入出庫記録、在庫推移の確認、編集・削除がこの1ページで行えます</p></div></div>', unsafe_allow_html=True)
    s_t1, s_t2, s_t3 = st.tabs(["📋 一覧・入出庫記録", "📈 推移グラフ", "✏️ 編集・削除"])

    with s_t1:
        if sup_alerts:
            for al in sup_alerts: st.markdown(f'<div class="alert-warning">{al}</div>', unsafe_allow_html=True)

        st.markdown('<div class="form-card" style="border-left:5px solid #d97706;"><div class="section-title">📥 入出庫を記録</div>', unsafe_allow_html=True)
        if not supplies:
            st.warning("資材マスターが未登録です。「⚙️ マスター設定」の「資材(備品)登録」タブから登録してください。")
        else:
            sc1, sc2 = st.columns([2, 1])
            sup_sel = sc1.selectbox("資材を選択", [s.get("資材名", "") for s in supplies if s.get("資材名")], key="sup_sel")
            act_sel = sc2.selectbox("処理", ["➖ 使用する (出庫)", "➕ 補充する (入荷)"], key="sup_act")
            sc3, sc4 = st.columns([2, 1])
            amt_val = sc3.number_input("数量（個/セット）", min_value=1, step=1, key="sup_amt")
            ins_sel = sc4.selectbox("作業者", inspectors, key="sup_ins")
            if st.button("✅ 記録を保存", type="primary", use_container_width=True, key="sup_btn"):
                target_id = next((s["資材ID"] for s in supplies if s.get("資材名") == sup_sel), None)
                append_supply_log({
                    "ログID": f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                    "登録日": str(date.today()), "資材ID": target_id, "処理": "入荷" if "➕" in act_sel else "使用",
                    "数量": amt_val, "作業者": ins_sel, "登録日時": datetime.now().isoformat()
                })
                st.success("記録しました！"); refresh()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-title">🚦 資材 発注点モニター</div>', unsafe_allow_html=True)
        if supply_inventory:
            sups_sorted = sorted(supply_inventory, key=lambda s: _STATUS_ORDER[calc_status(s["現在庫"], s.get("発注点", 0))])
            gcA, gcB = st.columns(2)
            for i, sv in enumerate(sups_sorted):
                (gcA if i % 2 == 0 else gcB).markdown(gauge_html(sv["資材名"], sv["現在庫"], sv.get("発注点", 0), unit="個", caption=sv.get("カテゴリ", "")), unsafe_allow_html=True)
        else:
            st.info("資材データがありません")

        if supply_logs:
            st.markdown('<div class="section-title">🕒 最近の入出庫履歴</div>', unsafe_allow_html=True)
            id_to_name = {str(s.get("資材ID")): s.get("資材名", "") for s in supplies}
            df_logs = pd.DataFrame(supply_logs).copy()
            df_logs["資材名"] = df_logs["資材ID"].astype(str).map(id_to_name).fillna(df_logs.get("資材ID"))
            cols_show = [c for c in ["登録日", "資材名", "処理", "数量", "作業者"] if c in df_logs.columns]
            st.dataframe(df_logs[cols_show][::-1].head(15).reset_index(drop=True), use_container_width=True, hide_index=True)

    with s_t2:
        if not supplies:
            st.info("資材マスターが未登録です")
        else:
            sel_name = st.selectbox("資材を選択", [s.get("資材名", "") for s in supplies if s.get("資材名")], key="trend_sup_sel")
            sel_sup = next((s for s in supplies if s.get("資材名") == sel_name), None)
            if sel_sup:
                sid = sel_sup.get("資材ID")
                initial = float(sel_sup.get("初期在庫") or 0)
                threshold = float(sel_sup.get("発注点") or 0)
                df_timeline, df_raw = build_supply_timeline(sid, initial)
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_timeline["date"], y=df_timeline["在庫"], mode="lines+markers", name="在庫数", line=dict(color="#0d9aa6", width=3, shape="hv"), marker=dict(size=7)))
                if threshold > 0:
                    fig.add_hline(y=threshold, line_dash="dash", line_color="#dc2626", annotation_text=f"発注点 {threshold:.0f}", annotation_position="top left")
                fig.update_layout(height=380, margin=dict(l=20, r=20, t=30, b=20), plot_bgcolor="#f8faff", paper_bgcolor="#fff", yaxis=dict(title="在庫数"), xaxis=dict(title="日付"))
                st.plotly_chart(fig, use_container_width=True)
                if not df_raw.empty:
                    st.markdown('<div class="section-title">📋 入出庫履歴データ</div>', unsafe_allow_html=True)
                    st.dataframe(df_raw[["date", "処理", "数量", "作業者"]].sort_values("date", ascending=False).reset_index(drop=True), use_container_width=True, hide_index=True)
                else:
                    st.info("この資材の入出庫履歴はまだありません（初期在庫のみ表示）")

    with s_t3:
        st.markdown('<div class="section-title">🧰 資材マスター 編集・削除</div>', unsafe_allow_html=True)
        st.markdown('<p class="subtle-note">表を直接編集、または行を選んで🗑（行削除）ができます。画像・登録日はこの一覧には表示されませんが、保存時にそのまま保持されます。</p>', unsafe_allow_html=True)
        if not supplies:
            st.info("資材マスターが未登録です")
        else:
            base_df = pd.DataFrame([{
                "資材ID": s.get("資材ID", ""), "資材名": s.get("資材名", ""), "カテゴリ": s.get("カテゴリ", ""),
                "初期在庫": float(s.get("初期在庫") or 0), "発注点": float(s.get("発注点") or 0)
            } for s in supplies])
            edited = st.data_editor(base_df, num_rows="dynamic", use_container_width=True, key="sup_master_editor",
                                     column_config={"資材ID": st.column_config.TextColumn(disabled=True)})
            if st.button("💾 変更を保存", type="primary", key="sup_master_save"):
                orig_by_id = {str(s.get("資材ID")): s for s in supplies}
                new_list = []
                for _, r in edited.iterrows():
                    rid = str(r["資材ID"]).strip()
                    if rid and rid in orig_by_id:
                        rec = dict(orig_by_id[rid])
                        rec.update({"資材名": r["資材名"], "カテゴリ": r["カテゴリ"], "初期在庫": r["初期在庫"], "発注点": r["発注点"]})
                    else:
                        rec = {
                            "資材ID": f"SUP-{datetime.now().strftime('%Y%m%d%H%M%S%f')}", "資材名": r["資材名"], "カテゴリ": r["カテゴリ"],
                            "画像URL": "https://cdn-icons-png.flaticon.com/512/1243/1243324.png", "初期在庫": r["初期在庫"], "発注点": r["発注点"],
                            "登録日": str(date.today())
                        }
                    if rec.get("資材名"): new_list.append(rec)
                save_supplies(new_list)
                st.success("保存しました！"); refresh()

        st.markdown("---")
        st.markdown('<div class="section-title">🗒️ 入出庫ログの個別編集・削除</div>', unsafe_allow_html=True)
        if not HAS_LOG_EDIT:
            st.info("💡 入出庫ログを個別に編集・削除するには、sheets.py に `update_supply_log(log_id, data)` と `delete_supply_log(log_id)` を追加してください（仕様は既存の update_arrival / update_brewing と同様です）。追加されるまでは、このセクションは利用できません。資材マスター自体の編集・削除は上記で問題なく利用できます。")
        else:
            editable_logs = [lg for lg in supply_logs if lg.get("ログID")]
            if not editable_logs:
                st.info("編集可能なログがありません。ログIDが付与されるのは、今回のアップデート以降に新しく記録した入出庫からです。")
            else:
                id_to_name = {str(s.get("資材ID")): s.get("資材名", "") for s in supplies}
                log_opts = {f"{lg.get('登録日','')} | {id_to_name.get(str(lg.get('資材ID')), lg.get('資材ID'))} | {lg.get('処理','')} {lg.get('数量','')}": lg for lg in reversed(editable_logs)}
                sel_log_label = st.selectbox("編集するログを選択", list(log_opts.keys()), key="log_edit_sel")
                if sel_log_label:
                    target_log = log_opts[sel_log_label]
                    lc1, lc2, lc3 = st.columns(3)
                    e_date = lc1.text_input("登録日", value=str(target_log.get("登録日", "")), key="log_e_date")
                    e_proc = lc2.selectbox("処理", ["入荷", "使用"], index=0 if "入荷" in str(target_log.get("処理", "")) else 1, key="log_e_proc")
                    e_amt = lc3.number_input("数量", value=float(target_log.get("数量") or 0), key="log_e_amt")
                    e_ins = st.selectbox("作業者", inspectors, index=safe_index(inspectors, target_log.get("作業者"), 0), key="log_e_ins")
                    bcol1, bcol2 = st.columns(2)
                    if bcol1.button("💾 この内容で更新", type="primary", key="log_e_save"):
                        update_supply_log(target_log["ログID"], {"登録日": e_date, "処理": e_proc, "数量": e_amt, "作業者": e_ins})
                        st.success("更新しました！"); refresh()
                    if bcol2.button("🗑 このログを削除", key="log_e_del"):
                        delete_supply_log(target_log["ログID"])
                        st.success("削除しました！"); refresh()

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
            arr_info = [a for a in arrivals if kw_fwd.lower() in str(a.get("ロットNo", "")).lower()] if kw_fwd else [a for a in arrivals if maker_fwd == a.get("メーカー", "")]
            if arr_info:
                st.markdown("#### 📦 対象の原料入荷記録")
                st.dataframe(pd.DataFrame(arr_info)[["入荷No", "入荷日", "メーカー", "原料種別", "ロットNo", "袋数"]], use_container_width=True, hide_index=True)

            res_fwd = []
            for b in brewing:
                is_match = False
                for l_key in ["主原料ロット", "海藻粉ロット", "デンプンロット"]:
                    if kw_fwd and kw_fwd.lower() in str(b.get(l_key, "")).lower(): is_match = True
                if b.get("その他添加物") and kw_fwd:
                    try:
                        for o in json.loads(b.get("その他添加物")):
                            if kw_fwd.lower() in str(o.get("lot", "")).lower(): is_match = True
                    except Exception: pass

                if is_match:
                    res_fwd.append({"仕込No": b.get("仕込No", ""), "仕込日": b.get("仕込日", ""), "品名": b.get("品名", ""), "メーカー": b.get("メーカー", ""), "主原料ロット": b.get("主原料ロット", ""), "海藻粉ロット": b.get("海藻粉ロット", ""), "デンプンロット": b.get("デンプンロット", "")})
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
            if kw_date: target_brews = [b for b in target_brews if b.get("仕込日") == str(kw_date).replace("-", "/")]
            if kw_prod: target_brews = [b for b in target_brews if kw_prod.lower() in str(b.get("品名", "")).lower()]

            if not target_brews: st.warning("該当する仕込み記録が見つかりません。")
            else:
                for tb in target_brews:
                    st.markdown(f"### 🧪 仕込No: {tb.get('仕込No')} - {tb.get('仕込日')} 【{tb.get('品名')}】")
                    used_lots = []
                    for k, n in [("主原料ロット", "こんにゃく粉"), ("海藻粉ロット", "海藻粉"), ("デンプンロット", "加工デンプン")]:
                        if tb.get(k) and tb.get(k) != "─": used_lots.append({"役割": n, "ロットNo": tb.get(k)})
                    if tb.get("その他添加物"):
                        try:
                            for o in json.loads(tb.get("その他添加物")):
                                if o.get("lot") and o.get("lot") != "─": used_lots.append({"役割": o.get("name", "添加物"), "ロットNo": o.get("lot")})
                        except Exception: pass
                    st.dataframe(pd.DataFrame(used_lots), use_container_width=True, hide_index=True)
                    st.markdown("---")
        st.markdown('</div>', unsafe_allow_html=True)

elif page == "📈 統計・比較分析":
    st.markdown('<div class="main-header"><div><h1>📈 統計・比較分析</h1><p>こんにゃく粉(袋換算)と添加物の使用量推移と前期間比較</p></div></div>', unsafe_allow_html=True)
    if not brewing:
        st.info("データがありません")
    else:
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
                    for o in json.loads(r.get("その他添加物")):
                        name = o.get("name")
                        kg = float(str(o.get("kg") or 0).replace(",", ""))
                        if name and kg > 0:
                            other_data.append({"period": period, "name": name, "kg": kg})
                except Exception: pass

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
            fig1.add_trace(go.Bar(x=grp["period"], y=grp["こんにゃく粉_袋"], name="こんにゃく粉(袋)", marker_color="#16a34a"))
            fig1.add_trace(go.Bar(x=grp["period"], y=grp["製品仕込量"], name="製品仕込量(kg)", marker_color="#163b66", yaxis="y2"))
            fig1.add_trace(go.Scatter(x=grp["period"], y=grp["歩留まり(倍)"], name="歩留まり(倍)", yaxis="y3", mode="lines+markers", line=dict(color="#d97706", width=3)))
            fig1.update_layout(barmode="group", height=450, plot_bgcolor="#f8faff", paper_bgcolor="#fff", yaxis=dict(title="こんにゃく粉 (袋)"), yaxis2=dict(title="製品仕込量 (kg)", overlaying="y", side="right", showgrid=False), yaxis3=dict(title="歩留まり(倍)", overlaying="y", side="right", position=0.95, showgrid=False), legend=dict(orientation="h", y=-0.15))
            st.plotly_chart(fig1, use_container_width=True)

        with tab2:
            base_additives = ["海藻粉", "加工デンプン", "石灰"]
            other_additives = [c for c in grp.columns if c not in ["period", "仕込回数", "製品仕込量", "歩留まり(倍)", "こんにゃく粉_袋", "こんにゃく粉_kg"] + base_additives]
            col_g1, col_g2 = st.columns([7, 3])
            with col_g1:
                fig2 = go.Figure()
                colors = ["#dc2626", "#d97706", "#8e24aa", "#163b66", "#2f6fb0", "#0d9aa6", "#16a34a", "#0891b2", "#7c3aed"]
                for i, mat in enumerate(base_additives + other_additives):
                    if mat in grp.columns:
                        fig2.add_trace(go.Bar(x=grp["period"], y=grp[mat], name=mat, marker_color=colors[i % len(colors)]))
                fig2.update_layout(barmode="stack", height=400, plot_bgcolor="#f8faff", paper_bgcolor="#fff", yaxis=dict(title="使用量 (kg)"), legend=dict(orientation="h", y=-0.2))
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

elif page == "⚙️ マスター設定":
    st.markdown('<div class="main-header"><div><h1>⚙️ マスター設定</h1><p>原料・メーカー・担当者・発注点・資材登録をここで管理します</p></div></div>', unsafe_allow_html=True)
    t1, t2, t3, t4, t5 = st.tabs(["🧴 原料", "🏭 メーカー", "👤 担当者", "⚠️ 発注点", "🧹 資材(備品)登録"])

    with t1:
        st.markdown('<p class="subtle-note">表を直接編集できます。空の行に入力して追加、行を選んで🗑で削除してください。</p>', unsafe_allow_html=True)
        df_mat = pd.DataFrame({"原料名": materials})
        edited_mat = st.data_editor(df_mat, num_rows="dynamic", use_container_width=True, key="mst_mat_editor")
        if st.button("💾 保存", type="primary", key="b1"):
            save_materials([str(x).strip() for x in edited_mat["原料名"].tolist() if str(x).strip()]); refresh()

    with t2:
        st.markdown('<p class="subtle-note">表を直接編集できます。空の行に入力して追加、行を選んで🗑で削除してください。</p>', unsafe_allow_html=True)
        df_mak = pd.DataFrame({"メーカー名": makers})
        edited_mak = st.data_editor(df_mak, num_rows="dynamic", use_container_width=True, key="mst_mak_editor")
        if st.button("💾 保存", type="primary", key="b2"):
            save_makers([str(x).strip() for x in edited_mak["メーカー名"].tolist() if str(x).strip()]); refresh()

    with t3:
        st.markdown('<p class="subtle-note">表を直接編集できます。空の行に入力して追加、行を選んで🗑で削除してください。</p>', unsafe_allow_html=True)
        df_ins = pd.DataFrame({"担当者名": inspectors})
        edited_ins = st.data_editor(df_ins, num_rows="dynamic", use_container_width=True, key="mst_ins_editor")
        if st.button("💾 保存", type="primary", key="b3"):
            save_inspectors([str(x).strip() for x in edited_ins["担当者名"].tolist() if str(x).strip()]); refresh()

    with t4:
        st.info("原料ごとの発注点（袋数）を設定します。現在庫を見ながら、無理のない値に調整してください。")
        op_df = pd.DataFrame([{"原料名": m, "現在庫(袋)": round(type_totals.get(m, 0.0), 1), "発注点(袋)": order_points.get(m, 0.0)} for m in materials])
        e_op = st.data_editor(op_df, use_container_width=True, key="mst_op", column_config={
            "現在庫(袋)": st.column_config.NumberColumn(disabled=True, format="%.1f", help="現在の合計在庫（参考表示・編集不可）"),
            "発注点(袋)": st.column_config.NumberColumn(format="%.1f")
        })
        if st.button("💾 保存", type="primary", key="b4"):
            save_order_points({r["原料名"]: r["発注点(袋)"] for _, r in e_op.iterrows() if float(r["発注点(袋)"]) > 0})
            refresh()

    with t5:
        st.info("衛生備品や梱包資材の新規登録を行います。PCやスマホから直接画像をアップロード可能です。")
        with st.form("new_supply_form"):
            sc1, sc2, sc3, sc_op = st.columns(4)
            n_name = sc1.text_input("資材名 ＊")
            n_cat = sc2.text_input("カテゴリ (例: 衛生, 梱包)")
            n_stock = sc3.number_input("初期在庫", min_value=0, step=1)
            n_order = sc_op.number_input("発注点(警告)", min_value=0, step=1)

            sc4, sc5 = st.columns(2)
            n_file = sc4.file_uploader("📷 写真・画像をアップロード", type=["png", "jpg", "jpeg"])
            n_url = sc5.text_input("🌐 または画像のURLを指定")

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
                        "初期在庫": n_stock, "発注点": n_order, "登録日": str(date.today())
                    })
                    save_supplies(current_supplies)
                    st.success(f"{n_name} を登録しました！")
                    refresh()

        st.markdown('<p class="subtle-note">💡 登録済み資材の編集・削除、入出庫履歴の確認は「🧹 資材在庫」ページの「✏️ 編集・削除」タブから行えます。</p>', unsafe_allow_html=True)
