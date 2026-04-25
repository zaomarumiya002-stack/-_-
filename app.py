"""
app.py  ─  食品工場 原料管理ERP（完全版）
Google Sheets バックエンド | 双方向トレース対応 | HACCP準拠
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import json
from datetime import datetime, date, timedelta

st.set_page_config(
    page_title="原料管理ERP", page_icon="🏭",
    layout="wide", initial_sidebar_state="expanded"
)

# ─── CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');
*, html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }

/* サイドバー */
section[data-testid="stSidebar"] {
    background: #0f172a !important;
    border-right: 1px solid #1e293b;
}
section[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
section[data-testid="stSidebar"] .stRadio label {
    padding: 6px 10px; border-radius: 8px; transition: background .15s;
    display: block; font-size: 0.9rem;
}
section[data-testid="stSidebar"] .stRadio label:hover { background: #1e293b; }

/* ページヘッダー */
.ph {
    display:flex; align-items:center; gap:14px;
    background: linear-gradient(135deg,#1e3a5f,#1565c0);
    padding:18px 24px; border-radius:14px; margin-bottom:22px;
}
.ph-icon { font-size:2rem; line-height:1; }
.ph h1 { color:#fff; font-size:1.5rem; font-weight:700; margin:0; }
.ph p  { color:#90caf9; font-size:0.82rem; margin:3px 0 0; }

/* KPI カード */
.kpi { background:#fff; border-radius:12px; padding:16px 18px;
    box-shadow:0 1px 6px rgba(0,0,0,.07); border-top:3px solid #1565c0;
    text-align:center; }
.kpi-v { font-size:2rem; font-weight:700; color:#1a237e; line-height:1.15; }
.kpi-l { font-size:.78rem; color:#78909c; margin-top:4px; }
.kpi.red   { border-top-color:#e53935; }
.kpi.green { border-top-color:#43a047; }
.kpi.amber { border-top-color:#fb8c00; }
.kpi.red .kpi-v   { color:#c62828; }
.kpi.green .kpi-v { color:#2e7d32; }
.kpi.amber .kpi-v { color:#e65100; }

/* フォームカード */
.fc { background:#f8faff; border:1px solid #dde6f5; border-radius:12px;
      padding:18px 20px; margin-bottom:14px; }
.fc-title { font-size:.85rem; font-weight:700; color:#1565c0;
    border-bottom:1.5px solid #dde6f5; padding-bottom:7px; margin-bottom:14px; }

/* セクションタイトル */
.st2 { font-size:1rem; font-weight:700; color:#1a237e;
    border-left:4px solid #1565c0; padding-left:10px; margin:18px 0 10px; }

/* アラートバー */
.alng { background:#fff3f3; border:1px solid #ffcdd2; border-left:4px solid #e53935;
    padding:10px 14px; border-radius:8px; color:#b71c1c;
    font-size:.88rem; font-weight:600; margin-bottom:8px; }

/* トレース結果カード */
.tc { background:#fff; border:1px solid #e3eaf5; border-radius:10px;
    padding:14px 18px; margin-bottom:12px; }
.tc-head { font-size:.95rem; font-weight:700; color:#1565c0; margin-bottom:8px; }

/* バッジ */
.badge { display:inline-block; padding:2px 9px; border-radius:12px;
    font-size:.75rem; font-weight:600; }
.ok   { background:#e8f5e9; color:#2e7d32; }
.ng   { background:#ffebee; color:#c62828; }
.warn { background:#fff8e1; color:#f57f17; }

/* テーブル上部の検索バー */
.search-row { display:flex; gap:10px; align-items:center; margin-bottom:10px; }
</style>
""", unsafe_allow_html=True)


# ─── sheets.py インポート ────────────────────────────────────────
try:
    from sheets import (
        load_arrivals, append_arrival, update_arrival,
        load_brewing, append_brewing, update_brewing,
        load_adjustments, append_adjustment,
        load_supplies, save_supplies,
        load_supply_logs, append_supply_log,
        load_materials, save_materials,
        load_makers, save_makers,
        load_inspectors, save_inspectors,
        load_order_points, save_order_points,
        next_arrival_no, next_brewing_no,
    )
    SHEETS_OK = True
except Exception as e:
    SHEETS_OK, SHEETS_ERROR = False, str(e)

# ─── サイドバー ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏭 原料管理 ERP")
    if SHEETS_OK:
        st.markdown('<span style="color:#4caf50;font-size:.8rem">● Google Sheets 接続中</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span style="color:#ef5350;font-size:.8rem">● 接続エラー</span>', unsafe_allow_html=True)
    st.markdown("---")
    page = st.radio("", [
        "🏠 ダッシュボード",
        "📦 入荷記録",
        "🧪 仕込み記録",
        "🏭 原料在庫",
        "🧹 資材在庫",
        "🔍 双方向トレース",
        "📊 生産分析",
        "⚙️ マスター設定",
    ], label_visibility="collapsed")
    st.markdown("---")
    if st.button("🔄 データ更新", use_container_width=True):
        st.cache_data.clear(); st.rerun()
    st.caption(f"更新: {datetime.now().strftime('%H:%M')}")

if not SHEETS_OK:
    st.error(f"Google Sheets 接続エラー: {SHEETS_ERROR}")
    st.info("`.streamlit/secrets.toml` の設定を確認してください。")
    st.stop()


# ─── データ取得（キャッシュ） ────────────────────────────────────
@st.cache_data(ttl=60, show_spinner="📡 データを読み込み中...")
def fetch_all():
    return (
        load_arrivals(), load_brewing(), load_adjustments(),
        load_supplies(), load_supply_logs(),
        load_materials(), load_makers(), load_inspectors(), load_order_points()
    )

(arrivals, brewing, adjustments, supplies, supply_logs,
 materials, makers, inspectors, order_points) = fetch_all()


# ─── 在庫計算（キャッシュ） ─────────────────────────────────────
@st.cache_data(ttl=60)
def calc_inventory(arr_t, brew_t, adj_t):
    """
    入荷レコードごとに在庫を計算。
    - トレースはロットNoだけでなく入荷No（arrival_no）でも紐づけ可能
    - ロットNoが空の場合でも入荷No をキーに動作する
    """
    if not arr_t:
        return {}

    # arrival_no をキーにした辞書（ロットNoは補助インデックスとして別途作成）
    inv = {}
    lot_to_arrival = {}   # lot_no → arrival_no (高速参照用)

    for a in arr_t:
        ano = a["arrival_no"]
        inv[ano] = {
            "arrival_no":    ano,
            "lot_no":        a.get("lot_no", ""),
            "maker":         a.get("maker", ""),
            "material_type": a.get("material_type", ""),
            "bags_per_kg":   float(a.get("bags_per_kg") or 20.0),
            "total_in_bags": float(a.get("bags") or 0),
            "total_out_kg":  0.0,
            "adj_bags":      0.0,
        }
        lot = str(a.get("lot_no", "")).strip()
        if lot:
            lot_to_arrival[lot] = ano

    def _deduct(lot_or_no: str, kg: float):
        """ロットNoまたは入荷Noで在庫を引く"""
        lot_or_no = str(lot_or_no).strip()
        if not lot_or_no or lot_or_no in ("─", ""):
            return
        # まず入荷No で検索
        if lot_or_no in inv:
            inv[lot_or_no]["total_out_kg"] += kg
        # 次にロットNo で検索
        elif lot_or_no in lot_to_arrival:
            inv[lot_to_arrival[lot_or_no]]["total_out_kg"] += kg

    for b in brew_t:
        _deduct(b.get("lot_no", ""),        float(b.get("material_kg", 0) or 0))
        _deduct(b.get("seaweed_lot", ""),   float(b.get("seaweed_kg", 0) or 0))
        _deduct(b.get("starch_lot", ""),    float(b.get("starch_kg", 0) or 0))
        oa = b.get("other_additives", "")
        if oa:
            try:
                for o in json.loads(oa):
                    _deduct(o.get("lot", ""), float(o.get("kg", 0) or 0))
            except Exception:
                pass

    for adj in adj_t:
        ano = adj.get("arrival_no", "")
        if ano in inv:
            inv[ano]["adj_bags"] += float(adj.get("diff_bags") or 0)

    for v in inv.values():
        bpk = v["bags_per_kg"] if v["bags_per_kg"] > 0 else 20.0
        v["total_out_bags"] = v["total_out_kg"] / bpk
        v["current_bags"]   = v["total_in_bags"] - v["total_out_bags"] + v["adj_bags"]
        v["current_kg"]     = v["current_bags"] * bpk

    return inv

@st.cache_data(ttl=60)
def calc_supply_inv(sup_t, log_t):
    if not sup_t:
        return []
    inv = {
        s["supply_id"]: {
            **s,
            "initial": float(s.get("initial_stock") or 0),
            "in_out":  0.0,
        }
        for s in sup_t if s.get("supply_id")
    }
    for lg in log_t:
        sid = lg.get("supply_id", "")
        if sid in inv:
            amt = float(lg.get("amount") or 0)
            inv[sid]["in_out"] += amt if "入荷" in lg.get("action_type", "") else -amt
    result = []
    for sid, v in inv.items():
        v["current_stock"] = v["initial"] + v["in_out"]
        result.append(v)
    return result


inventory_data  = calc_inventory(arrivals, brewing, adjustments)
supply_inventory= calc_supply_inv(supplies, supply_logs)

# 原料種別ごとの在庫合計
type_totals: dict[str, float] = {}
for v in inventory_data.values():
    type_totals[v["material_type"]] = type_totals.get(v["material_type"], 0) + v["current_bags"]

alerts = [
    f"⚠️ {m}：在庫 {c:,.1f}袋 ＜ 発注点 {order_points[m]:,.1f}袋"
    for m, c in type_totals.items()
    if m in order_points and c < order_points[m]
]


# ═══════════════════════════════════════════════════════════════
# ヘルパー
# ═══════════════════════════════════════════════════════════════
def ph(icon, title, sub=""):
    st.markdown(
        f'<div class="ph"><div class="ph-icon">{icon}</div>'
        f'<div><h1>{title}</h1><p>{sub}</p></div></div>',
        unsafe_allow_html=True
    )

def kpi(val, label, cls=""):
    st.markdown(
        f'<div class="kpi {cls}"><div class="kpi-v">{val}</div>'
        f'<div class="kpi-l">{label}</div></div>',
        unsafe_allow_html=True
    )

def refresh():
    st.cache_data.clear()
    st.rerun()

def _lot_display(lot: str) -> str:
    return lot if lot else "（ロットなし）"

# 入荷Noまたはロット番号でヒットする入荷レコードを返す
def find_arrival(query: str) -> list[dict]:
    q = query.strip().lower()
    if not q:
        return []
    result = []
    for a in arrivals:
        if (q in str(a.get("arrival_no","")).lower() or
            q in str(a.get("lot_no","")).lower()):
            result.append(a)
    return result


# ═══════════════════════════════════════════════════════════════
# ダッシュボード
# ═══════════════════════════════════════════════════════════════
if page == "🏠 ダッシュボード":
    ph("📊", "ERP ダッシュボード", "工場の稼働状況・在庫・アラートをリアルタイムで把握")

    if alerts:
        for al in alerts:
            st.markdown(f'<div class="alng">{al}</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    today_brew = [b for b in brewing if b.get("brew_date") == str(date.today())]
    week_ago   = str(date.today() - timedelta(days=7))
    week_brew  = [b for b in brewing if str(b.get("brew_date","")) >= week_ago]
    week_kg    = sum(float(b.get("brew_amount") or 0) for b in week_brew)
    total_bags = sum(max(v["current_bags"], 0) for v in inventory_data.values())

    with c1: kpi(len(today_brew),       "本日の仕込み回数")
    with c2: kpi(f"{week_kg:,.0f} kg",  "直近7日 仕込量", "green")
    with c3: kpi(f"{total_bags:,.0f} 袋","全原料 総在庫")
    with c4: kpi(len(alerts),            "要発注アラート", "red" if alerts else "")

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="st2">📦 最近の入荷（10件）</div>', unsafe_allow_html=True)
        if arrivals:
            df = pd.DataFrame(arrivals[-10:][::-1])
            disp = df.reindex(columns=["arrival_no","arrival_date","maker","lot_no","material_type","bags","appearance"])
            disp.columns = ["入荷No","入荷日","メーカー","ロットNo","原料種別","袋数","外観"]
            st.dataframe(disp, use_container_width=True, hide_index=True, height=280)
        else:
            st.info("入荷記録がありません")

    with col2:
        st.markdown('<div class="st2">🧪 最近の仕込み（10件）</div>', unsafe_allow_html=True)
        if brewing:
            df = pd.DataFrame(brewing[-10:][::-1])
            disp = df.reindex(columns=["no","brew_date","product_name","lot_no","brew_amount","material_kg"])
            disp.columns = ["No","仕込日","品名","主ロット","仕込量(kg)","精粉(kg)"]
            st.dataframe(disp, use_container_width=True, hide_index=True, height=280)
        else:
            st.info("仕込み記録がありません")

    # 在庫アラートサマリー
    if inventory_data:
        st.markdown('<div class="st2">🏭 在庫サマリー（原料種別）</div>', unsafe_allow_html=True)
        rows = []
        for mat, bags in sorted(type_totals.items()):
            op = order_points.get(mat, 0)
            status = "🔴 要発注" if op > 0 and bags < op else ("🟡 注意" if op > 0 and bags < op * 1.2 else "🟢 正常")
            rows.append({"原料種別": mat, "現在庫(袋)": round(bags, 1), "発注点(袋)": op, "状態": status})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=280)


# ═══════════════════════════════════════════════════════════════
# 入荷記録
# ═══════════════════════════════════════════════════════════════
elif page == "📦 入荷記録":
    ph("📦", "原料入荷記録", "入荷時の品質検査と担当者記録")

    tab1, tab2 = st.tabs(["➕ 新規登録", "📋 入荷履歴・帳票"])

    # ─── 新規登録 ────────────────────────────────────────────────
    with tab1:
        new_no = next_arrival_no(arrivals)

        st.markdown('<div class="fc"><div class="fc-title">📋 基本情報</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: st.text_input("入荷No（自動）", value=new_no, disabled=True)
        with c2: a_date = st.date_input("入荷日", value=date.today())
        with c3:
            maker = st.selectbox("メーカー", makers + ["その他"])
            if maker == "その他":
                maker = st.text_input("メーカー名を入力", key="maker_free")

        c4, c5, c6 = st.columns(3)
        with c4: mat_type = st.selectbox("原料種別", materials)
        with c5: lot_no   = st.text_input("ロットNo", placeholder="空欄でも登録可能")
        with c6: inspector= st.selectbox("担当者 ＊", inspectors)

        c7, c8 = st.columns(2)
        with c7: bags     = st.number_input("袋数", min_value=0, step=1)
        with c8: bags_per = st.number_input("1袋あたり(kg)", min_value=0.0, value=20.0, step=0.5)

        total_kg = bags * bags_per
        if bags > 0:
            st.info(f"📦 総量: **{total_kg:,.1f} kg**（{bags}袋 × {bags_per}kg）")

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="fc"><div class="fc-title">🔍 入荷時検査チェック</div>', unsafe_allow_html=True)

        CHECKS = {
            "transport_temp": ("① 搬入温度",    ["OK（基準内）","NG（基準外）","未確認"]),
            "appearance":     ("② 外観",        ["OK（正常）","NG（異常あり）","要確認"]),
            "odor":           ("③ 臭い",        ["OK（正常）","NG（異常あり）","未確認"]),
            "packaging":      ("④ 包装状態",    ["OK（良好）","NG（破損あり）","要確認"]),
            "color_check":    ("⑤ 色調",        ["OK（正常）","NG（異常あり）","未確認"]),
            "contamination":  ("⑥ 異物混入",    ["なし（正常）","あり（要報告）","未確認"]),
            "moisture":       ("⑦ 水分状態",    ["OK（乾燥良好）","NG（湿気あり）","要確認"]),
            "expiry_check":   ("⑧ 賞味期限",    ["OK（期限内）","NG（期限切/不明）","未確認"]),
        }

        check_vals = {}
        keys = list(CHECKS.keys())
        for i in range(0, len(keys), 2):
            cols = st.columns(2)
            for j, col in enumerate(cols):
                if i + j < len(keys):
                    k = keys[i + j]
                    lbl, opts = CHECKS[k]
                    with col:
                        check_vals[k] = st.selectbox(lbl, opts, key=f"chk_{k}")

        has_ng = any("NG" in v or "あり（要" in v for v in check_vals.values())
        abnormal = ""
        if has_ng:
            st.error("⚠️ 異常が検出されました。詳細を記録してください。")
            abnormal = st.text_area("異常内容・措置方法 ＊", placeholder="異常詳細と対応措置を記入")

        remarks = st.text_input("備考", placeholder="例：製造年月日 R7/10/18")
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("✅ Google Sheets に保存", type="primary", use_container_width=True):
            if not inspector:
                st.error("担当者を選択してください")
            elif has_ng and not abnormal:
                st.error("異常内容を記入してください")
            else:
                rec = {
                    "arrival_no": new_no, "arrival_date": str(a_date),
                    "maker": maker, "lot_no": lot_no, "material_type": mat_type,
                    "bags": bags, "bags_per_kg": bags_per, "total_kg": total_kg,
                    **check_vals,
                    "abnormal_detail": abnormal, "inspector": inspector,
                    "remarks": remarks, "registered_at": datetime.now().isoformat()
                }
                with st.spinner("保存中..."):
                    append_arrival(rec)
                st.success(f"✅ **{new_no}** を登録しました！")
                refresh()

    # ─── 入荷履歴 ────────────────────────────────────────────────
    with tab2:
        st.markdown('<div class="st2">📋 入荷記録一覧</div>', unsafe_allow_html=True)

        fc1, fc2, fc3 = st.columns(3)
        with fc1: f_maker = st.selectbox("メーカー", ["全て"] + makers, key="hf_m")
        with fc2: f_lot   = st.text_input("ロットNo / 入荷No 検索", key="hf_l")
        with fc3: f_app   = st.selectbox("外観", ["全て","OK（正常）","NG（異常あり）","要確認"], key="hf_a")

        filt = arrivals[:]
        if f_maker != "全て": filt = [a for a in filt if a.get("maker") == f_maker]
        if f_lot:             filt = [a for a in filt if f_lot.lower() in str(a.get("lot_no","")).lower()
                                      or f_lot.lower() in str(a.get("arrival_no","")).lower()]
        if f_app   != "全て": filt = [a for a in filt if a.get("appearance") == f_app]

        if filt:
            df = pd.DataFrame(filt[::-1])
            disp_cols = {
                "arrival_no":"入荷No","arrival_date":"入荷日","maker":"メーカー",
                "lot_no":"ロットNo","material_type":"原料種別","bags":"袋数",
                "total_kg":"総量(kg)","appearance":"外観","transport_temp":"搬入温度",
                "inspector":"担当者","remarks":"備考"
            }
            df_show = df.reindex(columns=list(disp_cols)).rename(columns=disp_cols)
            st.dataframe(df_show, use_container_width=True, hide_index=True, height=400)

            if st.button("📄 Excel帳票を出力"):
                from report_generator import generate_arrival_report
                path = generate_arrival_report(filt)
                with open(path, "rb") as f:
                    st.download_button("⬇️ ダウンロード", f,
                        file_name=f"入荷記録_{date.today()}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("該当する記録がありません")


# ═══════════════════════════════════════════════════════════════
# 仕込み記録
# ═══════════════════════════════════════════════════════════════
elif page == "🧪 仕込み記録":
    ph("🧪", "仕込み記録", "品目別の原料使用量と仕込み量を記録")

    tab1, tab2 = st.tabs(["➕ 新規登録", "📋 仕込み履歴・帳票"])

    with tab1:
        st.markdown('<div class="fc"><div class="fc-title">📋 基本情報</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: b_date   = st.date_input("仕込日", value=date.today())
        with c2: prod_name= st.text_input("品名 ＊", placeholder="例: つきこん（黒）")
        with c3: b_maker  = st.selectbox("メーカー", makers + ["その他"], key="bm")

        # 入荷済みロットの選択肢（入荷No と ロットNo を両方表示）
        lot_options_map = {}  # 表示文字列 → {"lot_no": ..., "arrival_no": ...}
        for a in arrivals:
            lot  = a.get("lot_no","")
            ano  = a.get("arrival_no","")
            mat  = a.get("material_type","")
            disp = f"{ano} / ロット:{lot if lot else '未設定'} [{mat}]"
            lot_options_map[disp] = {"lot_no": lot, "arrival_no": ano, "material_type": mat}
        lot_labels = ["─ 選択してください（任意）─"] + list(lot_options_map.keys())

        c4, c5 = st.columns(2)
        with c4:
            sel_lot = st.selectbox("主原料 入荷No / ロットNo", lot_labels, key="bl")
        with c5:
            brew_amount = st.number_input("仕込量 (kg)", min_value=0.0, step=50.0)

        lot_no_val  = ""
        arrival_info= None
        if sel_lot != "─ 選択してください（任意）─":
            d = lot_options_map.get(sel_lot, {})
            lot_no_val = d.get("lot_no", "")
            ano_val    = d.get("arrival_no", "")
            arrival_info = next((a for a in arrivals if a.get("arrival_no") == ano_val), None)
            if arrival_info:
                st.info(f"📦 {arrival_info['arrival_no']} ／ {arrival_info['maker']} ／ 入荷日:{arrival_info['arrival_date']} ／ 外観:{arrival_info.get('appearance','')}")

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="fc"><div class="fc-title">⚗️ 原料使用量</div>', unsafe_allow_html=True)

        c6, c7, c8 = st.columns(3)
        with c6:
            mat_kg = st.number_input("こんにゃく精粉 (kg)", min_value=0.0, step=0.1, format="%.2f")
        with c7:
            sea_kg  = st.number_input("海藻粉 (kg)", min_value=0.0, step=0.1, format="%.2f")
            # 海藻粉のロット
            sea_lot_label = st.selectbox("海藻粉 ロット/入荷No", lot_labels, key="sl")
            sea_lot = lot_options_map.get(sea_lot_label, {}).get("lot_no", "") if sea_lot_label != "─ 選択してください（任意）─" else ""
        with c8:
            sta_kg  = st.number_input("加工デンプン (kg)", min_value=0.0, step=0.1, format="%.2f")
            sta_type= st.selectbox("デンプン種別", ["─","ゆり8","VA70","その他"])
            sta_lot_label = st.selectbox("デンプン ロット/入荷No", lot_labels, key="stl")
            sta_lot = lot_options_map.get(sta_lot_label, {}).get("lot_no", "") if sta_lot_label != "─ 選択してください（任意）─" else ""

        c9, c10 = st.columns(2)
        with c9: lime_kg = st.number_input("石灰 (kg)", min_value=0.0, step=0.1, format="%.2f")
        with c10: lime_l = st.number_input("石灰水 (ℓ)", min_value=0.0, step=10.0, format="%.1f")

        # その他添加物（動的追加）
        st.markdown('<div class="fc-title" style="margin-top:12px">🧂 その他添加物（任意・複数追加可）</div>', unsafe_allow_html=True)
        if "other_rows" not in st.session_state:
            st.session_state.other_rows = []

        for i, row in enumerate(st.session_state.other_rows):
            oc1, oc2, oc3, oc4 = st.columns([3, 2, 2, 1])
            row["name"] = oc1.text_input("添加物名", value=row.get("name",""), key=f"on_{i}")
            row["kg"]   = oc2.number_input("使用量(kg)", value=float(row.get("kg",0)), min_value=0.0, step=0.1, format="%.3f", key=f"ok_{i}")
            other_lot_lbl = oc3.selectbox("ロット/入荷No", lot_labels, key=f"ol_{i}")
            row["lot"]  = lot_options_map.get(other_lot_lbl, {}).get("lot_no","") if other_lot_lbl != "─ 選択してください（任意）─" else ""
            if oc4.button("🗑", key=f"odel_{i}"):
                st.session_state.other_rows.pop(i); st.rerun()

        if st.button("＋ 添加物を追加"):
            st.session_state.other_rows.append({"name":"","kg":0,"lot":""}); st.rerun()

        notes_b = st.text_area("備考・メモ", placeholder="特記事項があれば入力")
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("✅ Google Sheets に保存", type="primary", use_container_width=True, key="save_brew"):
            if not prod_name:
                st.error("品名を入力してください")
            else:
                oa = json.dumps(st.session_state.other_rows, ensure_ascii=False) if st.session_state.other_rows else ""
                rec = {
                    "no": next_brewing_no(brewing), "brew_date": str(b_date),
                    "product_name": prod_name, "maker": b_maker, "lot_no": lot_no_val,
                    "brew_amount": brew_amount, "material_kg": mat_kg,
                    "seaweed_kg": sea_kg, "seaweed_lot": sea_lot,
                    "starch_kg": sta_kg, "starch_lot": sta_lot, "starch_type": sta_type if sta_type != "─" else "",
                    "lime_kg": lime_kg, "lime_water_l": lime_l,
                    "other_additives": oa, "notes": notes_b,
                    "registered_at": datetime.now().isoformat()
                }
                with st.spinner("保存中..."):
                    append_brewing(rec)
                st.session_state.other_rows = []
                st.success(f"✅ 仕込み No.{rec['no']} を保存しました！")
                refresh()

    with tab2:
        st.markdown('<div class="st2">📋 仕込み記録一覧</div>', unsafe_allow_html=True)
        fc1, fc2, fc3 = st.columns(3)
        with fc1: bf_from = st.date_input("開始日", value=None, key="bf_from")
        with fc2: bf_to   = st.date_input("終了日", value=None, key="bf_to")
        with fc3: bf_lot  = st.text_input("ロット / 品名 検索", key="bf_lot")

        filt_b = brewing[:]
        if bf_from: filt_b = [b for b in filt_b if str(b.get("brew_date","")) >= str(bf_from)]
        if bf_to:   filt_b = [b for b in filt_b if str(b.get("brew_date","")) <= str(bf_to)]
        if bf_lot:
            q = bf_lot.lower()
            filt_b = [b for b in filt_b
                      if q in str(b.get("lot_no","")).lower()
                      or q in str(b.get("product_name","")).lower()]

        if filt_b:
            df = pd.DataFrame(filt_b[::-1])
            disp_cols = {
                "no":"No","brew_date":"仕込日","product_name":"品名","maker":"メーカー",
                "lot_no":"主ロット","brew_amount":"仕込量(kg)",
                "material_kg":"精粉(kg)","seaweed_kg":"海藻粉(kg)",
                "starch_kg":"デンプン(kg)","lime_kg":"石灰(kg)"
            }
            df_show = df.reindex(columns=list(disp_cols)).rename(columns=disp_cols)
            st.dataframe(df_show, use_container_width=True, hide_index=True, height=400)

            if st.button("📄 Excel帳票を出力", key="exp_brew"):
                from report_generator import generate_brewing_report
                path = generate_brewing_report(filt_b)
                with open(path,"rb") as f:
                    st.download_button("⬇️ ダウンロード", f,
                        file_name=f"仕込み記録_{date.today()}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("該当記録なし")


# ═══════════════════════════════════════════════════════════════
# 原料在庫管理
# ═══════════════════════════════════════════════════════════════
elif page == "🏭 原料在庫":
    ph("🏭", "原料在庫管理", "入荷・使用・調整に基づくリアルタイム在庫")

    if not inventory_data:
        st.info("入荷記録がありません")
        st.stop()

    # 集計
    rows = []
    for v in inventory_data.values():
        op = order_points.get(v["material_type"], 0)
        status = "🔴 要発注" if op > 0 and v["current_bags"] < op else "🟢 正常"
        rows.append({
            "入荷No":      v["arrival_no"],
            "ロットNo":    v["lot_no"] or "（未設定）",
            "原料種別":    v["material_type"],
            "メーカー":    v["maker"],
            "入荷(袋)":    v["total_in_bags"],
            "使用済(袋)":  round(v["total_out_bags"], 2),
            "調整(袋)":    v["adj_bags"],
            "現在庫(袋)":  round(v["current_bags"], 2),
            "現在庫(kg)":  round(v["current_kg"], 1),
            "状態":        status,
        })

    df_inv = pd.DataFrame(rows)

    # フィルター
    fc1, fc2 = st.columns(2)
    with fc1:
        f_mat = st.selectbox("原料種別", ["全て"] + sorted(df_inv["原料種別"].unique()), key="inv_m")
    with fc2:
        f_zero = st.checkbox("在庫ゼロ以下を除外", value=False)

    if f_mat != "全て": df_inv = df_inv[df_inv["原料種別"] == f_mat]
    if f_zero: df_inv = df_inv[df_inv["現在庫(袋)"] > 0]

    st.dataframe(
        df_inv.sort_values("入荷No", ascending=False).reset_index(drop=True),
        use_container_width=True, hide_index=True, height=420
    )

    # 在庫棒グラフ
    summary = df_inv.groupby("原料種別")["現在庫(袋)"].sum().reset_index()
    if not summary.empty:
        fig = px.bar(summary, x="原料種別", y="現在庫(袋)", color="現在庫(袋)",
                     color_continuous_scale="Blues", title="原料種別 在庫量（袋）")
        fig.update_layout(height=320, plot_bgcolor="#f8faff", paper_bgcolor="#fff",
                          xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)

    # 在庫調整フォーム
    with st.expander("🔧 在庫調整（棚卸・破損・廃棄など）"):
        adj_cols = st.columns(3)
        arr_opts = [f"{a['arrival_no']} / ロット:{a.get('lot_no','未設定')}" for a in arrivals]
        sel_arr  = adj_cols[0].selectbox("対象入荷No", arr_opts, key="adj_sel")
        diff_bags= adj_cols[1].number_input("調整袋数（マイナスは減少）", step=1.0, format="%.1f", key="adj_diff")
        adj_reason = adj_cols[2].text_input("理由", placeholder="例：棚卸差異", key="adj_reason")
        adj_ins  = st.selectbox("担当者", inspectors, key="adj_ins")
        if st.button("調整を記録", key="adj_save"):
            ano = sel_arr.split(" / ")[0]
            append_adjustment({
                "adj_id": f"ADJ-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "arrival_no": ano, "adj_date": str(date.today()),
                "diff_bags": diff_bags, "reason": adj_reason,
                "inspector": adj_ins, "registered_at": datetime.now().isoformat()
            })
            st.success("調整を記録しました"); refresh()


# ═══════════════════════════════════════════════════════════════
# 資材在庫
# ═══════════════════════════════════════════════════════════════
elif page == "🧹 資材在庫":
    ph("🧹", "資材・衛生備品 管理", "消耗品・備品の入出庫管理")

    st.markdown('<div class="fc"><div class="fc-title">📝 入出庫 登録</div>', unsafe_allow_html=True)
    if not supplies:
        st.warning("資材マスターが未登録です。「⚙️ マスター設定」から追加してください。")
    else:
        sc1, sc2, sc3, sc4 = st.columns(4)
        sup_sel = sc1.selectbox("資材", [s["name"] for s in supplies])
        act_sel = sc2.selectbox("処理", ["➖ 使用(出庫)", "➕ 補充(入荷)"])
        amt_val = sc3.number_input("数量", min_value=1, step=1)
        ins_sel = sc4.selectbox("作業者", inspectors)
        if st.button("✅ 記録", type="primary"):
            target_id = next((s["supply_id"] for s in supplies if s["name"] == sup_sel), None)
            append_supply_log({
                "log_id": f"SL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "date": str(date.today()), "supply_id": target_id,
                "action_type": "入荷" if "➕" in act_sel else "使用",
                "amount": amt_val, "inspector": ins_sel, "note": "",
                "registered_at": datetime.now().isoformat()
            })
            st.success(f"{sup_sel} {amt_val}個 を記録しました"); refresh()
    st.markdown('</div>', unsafe_allow_html=True)

    if supply_inventory:
        st.markdown('<div class="st2">📦 現在庫一覧</div>', unsafe_allow_html=True)
        df_s = pd.DataFrame(supply_inventory)
        show_cols = ["image_url","name","category","current_stock"]
        df_s = df_s[[c for c in show_cols if c in df_s.columns]]
        st.dataframe(
            df_s.rename(columns={"image_url":"画像","name":"資材名","category":"カテゴリ","current_stock":"現在庫"}),
            column_config={"画像": st.column_config.ImageColumn("画像", width="small"),
                           "現在庫": st.column_config.NumberColumn("現在庫", format="%d")},
            use_container_width=True, hide_index=True, height=450
        )


# ═══════════════════════════════════════════════════════════════
# 双方向トレース
# ═══════════════════════════════════════════════════════════════
elif page == "🔍 双方向トレース":
    ph("🔍", "双方向原料トレース", "HACCP対応 ／ 原料→製品（フォワード）・製品→原料（バックワード）")

    tab_fwd, tab_bwd, tab_batch = st.tabs([
        "➡️ 原料から製品を追跡",
        "⬅️ 製品から原料を遡る",
        "📋 一括トレースレポート"
    ])

    # ─── フォワードトレース ─────────────────────────────────────
    with tab_fwd:
        st.info("🔎 特定の原料が **いつ・どの製品に・どれだけ** 使われたかを特定します（不良原料の影響範囲調査）")

        st.markdown('<div class="fc">', unsafe_allow_html=True)
        kw = st.text_input("ロットNo または 入荷No を入力",
                           placeholder="例: 1-109　または　A-0012",
                           key="fwd_kw")
        st.markdown('</div>', unsafe_allow_html=True)

        if kw and st.button("➡️ 追跡開始", type="primary", key="btn_fwd"):
            kw_l = kw.strip().lower()

            # 対応する入荷記録を表示
            arr_hits = find_arrival(kw)
            if arr_hits:
                st.markdown('<div class="st2">📦 対象の入荷記録</div>', unsafe_allow_html=True)
                df_a = pd.DataFrame(arr_hits)
                disp = df_a.reindex(columns=["arrival_no","arrival_date","maker","material_type","lot_no","bags","total_kg","appearance"])
                disp.columns = ["入荷No","入荷日","メーカー","原料種別","ロットNo","袋数","総量(kg)","外観"]
                st.dataframe(disp, use_container_width=True, hide_index=True)

                # 対応入荷Noを取得（在庫計算との照合用）
                hit_lot_nos  = {str(a.get("lot_no","")).strip() for a in arr_hits}
                hit_arr_nos  = {str(a.get("arrival_no","")).strip() for a in arr_hits}
            else:
                st.warning("入荷記録が見つかりません。ロットNoまたは入荷Noを確認してください。")
                hit_lot_nos = {kw_l}
                hit_arr_nos = set()

            # 仕込み記録を検索（ロットNo・入荷Noどちらでもヒット）
            res = []
            for b in brewing:
                matched_roles = []

                def _check_field(lot_field: str, role: str, kg_field: str = ""):
                    val = str(b.get(lot_field, "")).strip()
                    if not val or val in ("─",""):
                        return
                    if val.lower() in hit_lot_nos or val.lower() in hit_arr_nos or kw_l in val.lower():
                        kg = float(b.get(kg_field, 0) or 0) if kg_field else 0
                        matched_roles.append({"役割": role, "使用ロット": val, "使用量(kg)": kg})

                _check_field("lot_no",      "主原料（精粉）",   "material_kg")
                _check_field("seaweed_lot", "海藻粉",           "seaweed_kg")
                _check_field("starch_lot",  "加工デンプン",     "starch_kg")

                oa = b.get("other_additives", "")
                if oa:
                    try:
                        for o in json.loads(oa):
                            olt = str(o.get("lot","")).strip()
                            if olt and (olt.lower() in hit_lot_nos or olt.lower() in hit_arr_nos or kw_l in olt.lower()):
                                matched_roles.append({
                                    "役割": o.get("name","添加物"),
                                    "使用ロット": olt,
                                    "使用量(kg)": float(o.get("kg",0) or 0)
                                })
                    except Exception:
                        pass

                if matched_roles:
                    for mr in matched_roles:
                        res.append({
                            "仕込No":    b.get("no",""),
                            "仕込日":    b.get("brew_date",""),
                            "品名":      b.get("product_name",""),
                            "仕込量(kg)":b.get("brew_amount",0),
                            "役割":      mr["役割"],
                            "使用ロット":mr["使用ロット"],
                            "使用量(kg)":mr["使用量(kg)"],
                        })

            if res:
                st.success(f"✅ **{len(res)}件** の使用記録が見つかりました")
                st.dataframe(pd.DataFrame(res), use_container_width=True, hide_index=True)
                if st.button("📄 トレース帳票を出力", key="exp_fwd"):
                    from report_generator import generate_trace_report
                    path = generate_trace_report(res, "フォワード", kw)
                    with open(path,"rb") as f:
                        st.download_button("⬇️ Excelダウンロード", f,
                            file_name=f"トレース_FWD_{date.today()}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.warning("この原料はまだ仕込みに使用されていません。")

    # ─── バックワードトレース ───────────────────────────────────
    with tab_bwd:
        st.info("🔎 特定の仕込みに使われた **すべての原料・メーカー・入荷検査結果** を特定します（クレーム調査用）")

        st.markdown('<div class="fc">', unsafe_allow_html=True)
        bc1, bc2, bc3 = st.columns(3)
        bwd_date = bc1.date_input("仕込日（任意）", value=None, key="bwd_date")
        bwd_prod = bc2.text_input("品名（部分一致）", placeholder="例: つきこん", key="bwd_prod")
        bwd_no   = bc3.text_input("仕込みNo（任意）", placeholder="例: 42", key="bwd_no")
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("⬅️ 遡及調査", type="primary", key="btn_bwd"):
            t_brews = brewing[:]
            if bwd_date: t_brews = [b for b in t_brews if b.get("brew_date") == str(bwd_date)]
            if bwd_prod: t_brews = [b for b in t_brews if bwd_prod.lower() in str(b.get("product_name","")).lower()]
            if bwd_no:
                try: t_brews = [b for b in t_brews if int(b.get("no",0)) == int(bwd_no)]
                except: pass

            if not t_brews:
                st.warning("該当する仕込み記録が見つかりません")
            else:
                st.success(f"✅ **{len(t_brews)}件** の仕込み記録が見つかりました")
                for tb in t_brews:
                    with st.expander(
                        f"🧪 仕込No.{tb.get('no')} ／ {tb.get('brew_date')} ／ 【{tb.get('product_name')}】 {tb.get('brew_amount',0):,.0f}kg",
                        expanded=len(t_brews) == 1
                    ):
                        # 使用原料を収集
                        used = []
                        for lot_k, role in [
                            ("lot_no","主原料（精粉）"),
                            ("seaweed_lot","海藻粉"),
                            ("starch_lot","加工デンプン"),
                        ]:
                            lot_v = str(tb.get(lot_k,"")).strip()
                            if lot_v and lot_v != "─":
                                used.append({"役割": role, "ロットNo": lot_v})

                        oa = tb.get("other_additives","")
                        if oa:
                            try:
                                for o in json.loads(oa):
                                    olt = str(o.get("lot","")).strip()
                                    if olt and olt != "─":
                                        used.append({"役割": o.get("name","添加物"), "ロットNo": olt})
                            except Exception:
                                pass

                        if not used:
                            st.info("ロット情報が記録されていません（ロットなし登録）")
                            continue

                        # 各ロットの入荷情報を結合
                        bwd_rows = []
                        for u in used:
                            lot_v = u["ロットNo"]
                            # ロットNoで検索、次に入荷Noで検索
                            arr_m = next(
                                (a for a in arrivals if str(a.get("lot_no","")).strip() == lot_v
                                 or str(a.get("arrival_no","")).strip() == lot_v),
                                None
                            )
                            bwd_rows.append({
                                "役割":       u["役割"],
                                "ロットNo":   lot_v,
                                "入荷No":     arr_m.get("arrival_no","─") if arr_m else "不明",
                                "メーカー":   arr_m.get("maker","不明") if arr_m else "不明",
                                "入荷日":     arr_m.get("arrival_date","─") if arr_m else "─",
                                "外観検査":   arr_m.get("appearance","─") if arr_m else "─",
                                "担当者":     arr_m.get("inspector","─") if arr_m else "─",
                            })

                        st.dataframe(pd.DataFrame(bwd_rows), use_container_width=True, hide_index=True)

    # ─── 一括トレースレポート ───────────────────────────────────
    with tab_batch:
        st.info("📋 全仕込み記録の原料トレース表を一括出力します（HACCP記録として使用可）")
        if st.button("📄 一括トレースレポートを生成", type="primary"):
            from report_generator import generate_full_trace_report
            path = generate_full_trace_report(arrivals, brewing)
            with open(path,"rb") as f:
                st.download_button("⬇️ Excelダウンロード", f,
                    file_name=f"全件トレース_{date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ═══════════════════════════════════════════════════════════════
# 生産分析
# ═══════════════════════════════════════════════════════════════
elif page == "📊 生産分析":
    ph("📊", "生産分析・歩留まり", "使用量・仕込量の推移と歩留まり指標")

    if not brewing:
        st.info("仕込み記録がありません")
        st.stop()

    df = pd.DataFrame(brewing)
    df["brew_date"] = pd.to_datetime(df["brew_date"], errors="coerce")
    for c in ["brew_amount","material_kg","seaweed_kg","starch_kg"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    pt = st.radio("集計単位", ["日別","月別","年間"], horizontal=True)
    if pt == "日別":   df["period"] = df["brew_date"].dt.date.astype(str)
    elif pt == "月別": df["period"] = df["brew_date"].dt.to_period("M").astype(str)
    else:              df["period"] = df["brew_date"].dt.to_period("Y").astype(str)

    grp = df.groupby("period").agg(
        件数     =("no","count"),
        仕込量   =("brew_amount","sum"),
        精粉     =("material_kg","sum"),
        海藻粉   =("seaweed_kg","sum"),
        デンプン =("starch_kg","sum"),
    ).reset_index()
    grp["歩留まり(倍)"] = (grp["仕込量"] / grp["精粉"].replace(0, float("nan"))).round(2)

    # KPI
    k1, k2, k3, k4 = st.columns(4)
    with k1: kpi(f"{grp['件数'].sum():,}", "総仕込み回数")
    with k2: kpi(f"{grp['仕込量'].sum():,.0f} kg", "総仕込量", "green")
    with k3: kpi(f"{grp['精粉'].sum():,.1f} kg", "総精粉使用量")
    with k4: kpi(f"{grp['歩留まり(倍)'].mean():.2f} 倍", "平均歩留まり", "amber")

    # グラフ
    fig = go.Figure()
    fig.add_bar(x=grp["period"], y=grp["仕込量"], name="仕込量(kg)", marker_color="#1565c0")
    fig.add_bar(x=grp["period"], y=grp["精粉"],   name="精粉(kg)",   marker_color="#43a047")
    fig.add_trace(go.Scatter(x=grp["period"], y=grp["歩留まり(倍)"],
                             name="歩留まり(倍)", yaxis="y2",
                             line=dict(color="#fb8c00", width=2.5), mode="lines+markers"))
    fig.update_layout(
        barmode="group", height=380, plot_bgcolor="#f8faff",
        yaxis=dict(title="量 (kg)"),
        yaxis2=dict(title="歩留まり(倍)", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", y=-0.2)
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        grp.style.format({"仕込量":"{:.1f}","精粉":"{:.1f}",
                          "海藻粉":"{:.1f}","デンプン":"{:.1f}","歩留まり(倍)":"{:.2f}"}),
        use_container_width=True
    )

    if st.button("📄 集計帳票を出力"):
        from report_generator import generate_monthly_report
        path = generate_monthly_report(grp.to_dict("records"), brewing)
        with open(path,"rb") as f:
            st.download_button("⬇️ Excelダウンロード", f,
                file_name=f"生産分析_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ═══════════════════════════════════════════════════════════════
# マスター設定
# ═══════════════════════════════════════════════════════════════
elif page == "⚙️ マスター設定":
    ph("⚙️", "マスター設定", "原料・メーカー・担当者・発注点・資材を管理")

    t1, t2, t3, t4, t5 = st.tabs(["🧴 原料","🏭 メーカー","👤 担当者","⚠️ 発注点","🧹 資材登録"])

    with t1:
        m1 = st.text_area("原料リスト（1行1件、最大20種）", "\n".join(materials), height=320)
        new_mats = [x.strip() for x in m1.splitlines() if x.strip()]
        if len(new_mats) > 20: st.warning(f"20種類まで登録可能です（現在{len(new_mats)}種）")
        if st.button("💾 保存", key="b1"):
            save_materials(new_mats[:20]); st.cache_data.clear(); st.rerun()

    with t2:
        m2 = st.text_area("メーカーリスト", "\n".join(makers), height=200)
        if st.button("💾 保存", key="b2"):
            save_makers([x.strip() for x in m2.splitlines() if x.strip()])
            st.cache_data.clear(); st.rerun()

    with t3:
        m3 = st.text_area("担当者リスト", "\n".join(inspectors), height=200)
        if st.button("💾 保存", key="b3"):
            save_inspectors([x.strip() for x in m3.splitlines() if x.strip()])
            st.cache_data.clear(); st.rerun()

    with t4:
        st.info("原料ごとの発注点（袋数）。0は未設定。")
        op_df = pd.DataFrame([{"原料名": m, "発注点(袋)": order_points.get(m, 0.0)} for m in materials])
        e_op  = st.data_editor(op_df, use_container_width=True, hide_index=True)
        if st.button("💾 保存", key="b4"):
            save_order_points({r["原料名"]: float(r["発注点(袋)"]) for _, r in e_op.iterrows() if float(r["発注点(袋)"]) > 0})
            st.cache_data.clear(); st.rerun()

    with t5:
        st.info("衛生備品・梱包資材のマスター（画像URLはネット上の画像リンク）")
        sup_df = (pd.DataFrame(supplies) if supplies
                  else pd.DataFrame(columns=["supply_id","name","category","image_url","initial_stock"]))
        e_sup = st.data_editor(sup_df, num_rows="dynamic", use_container_width=True, hide_index=True)
        if st.button("💾 資材マスター保存", key="b5"):
            save_supplies(e_sup.to_dict("records"))
            st.cache_data.clear(); st.rerun()
