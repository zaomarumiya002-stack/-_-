import streamlit as st
import pandas as pd
import json
import time
import base64
import re
import hashlib
from io import BytesIO
from datetime import datetime, date, timedelta, timezone
import traceback
import plotly.graph_objects as go
import plotly.express as px

try:
    import sheets as _sheets_mod
    _SHEETS_IMPORT_ERROR = None
except Exception as _e:  # sheets.py が無い/壊れている場合も画面にエラーを出す
    _sheets_mod = None
    _SHEETS_IMPORT_ERROR = _e

# Excel出力用
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

# 資材画像アップロード用
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

st.set_page_config(page_title="食品工場 製造ERP", page_icon="🏭", layout="wide", initial_sidebar_state="expanded")

# ════════════════════════════════════════════════════════════════
#  日本時間(JST)ヘルパー  ※サーバーのタイムゾーンに依存しない
# ════════════════════════════════════════════════════════════════
JST = timezone(timedelta(hours=9))

def now_jst():
    return datetime.now(JST).replace(tzinfo=None)

def today_jst():
    return now_jst().date()

# ════════════════════════════════════════════════════════════════
#  UI/UX CSS & 共通ヘルパー
# ════════════════════════════════════════════════════════════════
st.markdown("""
<style>
:root {
    --c-bg: #f4f6f7; --c-surface: #ffffff; --c-primary: #0f766e; --c-primary-hover: #0b5c56;
    --c-primary-soft: #e6f2f1; --c-secondary: #1e293b; --c-muted: #64748b; --c-border: #dbe2e6;
    --c-input-border: #a8b3ba; --c-danger: #b91c1c; --c-danger-bg: #fdf1f1; --c-success: #15803d;
    --c-warn: #b45309; --c-warn-bg: #fffbeb;
    --c-water: #94a3b8; --radius-lg: 16px; --radius-md: 10px; --radius-sm: 8px;
    --shadow-card: 0 2px 6px -1px rgba(15,23,42,0.08);
}
html, body, .stApp { background-color: var(--c-bg) !important; font-family: -apple-system, "Hiragino Sans", "Yu Gothic UI", "Meiryo", sans-serif !important; }
h1, h2, h3, h4, p, span, div, label { color: var(--c-secondary); }
.block-container { padding-top: 1.5rem !important; max-width: 1280px; }
.main-header { background: var(--c-surface); padding: 18px 24px; border-radius: var(--radius-lg); margin-bottom: 24px; box-shadow: var(--shadow-card); border-left: 8px solid var(--c-primary); }
.main-header h1 { font-size: 1.6rem !important; margin: 0 0 6px 0 !important; font-weight: 900 !important; }
.main-header p { margin: 0; color: var(--c-muted); }
.form-card { background: var(--c-surface); border-radius: var(--radius-lg); padding: 24px; margin-bottom: 24px; box-shadow: var(--shadow-card); border: 1px solid #e2e8f0; }
.section-title { font-size: 1.25rem; font-weight: 900; margin-bottom: 20px; border-bottom: 3px solid var(--c-border); padding-bottom: 8px; }
.step-label { font-weight: 800; color: var(--c-muted); margin: 18px 0 8px 0; }
.alert-box { border-radius: 12px; padding: 12px 16px; margin: 8px 0; font-weight: 700; }
.alert-danger { background: var(--c-danger-bg); border: 2px solid var(--c-danger); color: #7f1d1d; }
.alert-warn { background: var(--c-warn-bg); border: 2px solid #f59e0b; color: #78350f; }
.alert-ok { background: #dcfce7; border: 2px solid #22c55e; color: #14532d; }
div[data-testid="stRadio"] > div { display: flex; flex-wrap: wrap; gap: 8px !important; }
div[data-testid="stRadio"] label { background-color: #ffffff; padding: 10px 16px !important; border-radius: var(--radius-sm); border: 2px solid var(--c-border) !important; cursor: pointer; text-align: center; flex: 1 1 auto; justify-content: center; min-width: 80px; transition: all 0.15s ease; }
div[data-testid="stRadio"] label p { font-size: 1.0rem !important; font-weight: 700 !important; color: var(--c-secondary) !important; }
div[data-testid="stRadio"] label:has(input:checked) { background-color: var(--c-primary) !important; border-color: var(--c-primary-hover) !important; box-shadow: 0 3px 10px rgba(15,118,110,0.25) !important; transform: translateY(-1px); }
div[data-testid="stRadio"] label:has(input:checked) * { color: #ffffff !important; font-weight: 900 !important; fill: #ffffff !important; }
div[data-baseweb="input"] { background-color: #ffffff !important; border: 3px solid var(--c-input-border) !important; border-radius: var(--radius-md) !important; }
div[data-baseweb="input"]:focus-within { border-color: var(--c-primary) !important; box-shadow: 0 0 0 5px rgba(15,118,110,0.18) !important; }
div[data-baseweb="select"] > div { min-height: 48px !important; border-width: 2px !important; }
div[data-testid="stNumberInputContainer"] { min-height: 50px !important; background-color: #f8fafc !important; }
div[data-testid="stNumberInputContainer"] input { font-size: 1.2rem !important; font-weight: 800 !important; text-align: center !important; }
.stButton button, .stDownloadButton button, .stFormSubmitButton button { border-radius: var(--radius-sm) !important; font-weight: 800 !important; padding: 14px 20px !important; min-height: 52px !important; border: 2px solid var(--c-input-border) !important; }
.stButton button[kind="primary"], .stDownloadButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] { background: var(--c-primary) !important; color: #ffffff !important; border: none !important; box-shadow: 0 4px 12px rgba(15,118,110,0.3) !important; }
.stButton button[kind="primary"]:hover { background: var(--c-primary-hover) !important; transform: translateY(-2px); }
.stButton button:disabled { opacity: 0.45 !important; }
.ratio-btn-container .stButton button { min-height: 38px !important; padding: 4px 6px !important; font-size: 0.95rem !important; background: #f8fafc !important; border: 1px solid #cbd5e1 !important; border-radius: 6px !important; }
.ratio-btn-container .stButton button:hover { background: var(--c-primary-soft) !important; border-color: var(--c-primary) !important; color: var(--c-primary) !important; }
.ratio-btn-container .stButton button[kind="primary"] { background: var(--c-primary) !important; border: none !important; color: #ffffff !important; }
[data-testid="stSidebar"] { background-color: #f8fafc !important; border-right: 2px solid var(--c-border); padding-top: 1rem; }
[data-testid="stSidebar"] div[role="radiogroup"] label { background: #ffffff !important; border: 2px solid var(--c-border) !important; padding: 14px 16px !important; border-radius: var(--radius-md) !important; margin-bottom: 0 !important; }
@media (max-width: 640px) {
    .block-container { padding: 0.8rem 0.5rem !important; }
    div[data-testid="stColumn"] { min-width: calc(50% - 1rem) !important; }
    .form-card { padding: 14px; }
}
</style>
""", unsafe_allow_html=True)

def card_start(): st.markdown('<div class="form-card">', unsafe_allow_html=True)
def card_end(): st.markdown('</div>', unsafe_allow_html=True)
def sec_title(title): st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
def step_label(txt): st.markdown(f'<div class="step-label">{txt}</div>', unsafe_allow_html=True)
def alert_box(msg, kind="danger"): st.markdown(f'<div class="alert-box alert-{kind}">{msg}</div>', unsafe_allow_html=True)
def page_header(title, sub=""):
    st.markdown(f'<div class="main-header"><h1>{title}</h1>{f"<p>{sub}</p>" if sub else ""}</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
#  安全な保存層 (SafeSheets)
#   * 一時的な通信エラー(429/タイムアウト等)は自動リトライ
#   * 保存に失敗したらトレースバックではなく分かりやすいエラーを表示して処理を止める
#   * 製造記録・入荷記録の「同一内容の連続登録(ダブルタップ)」を防止
# ════════════════════════════════════════════════════════════════
_TRANSIENT_KEYS = ("429", "quota", "rate", "timeout", "timed out", "503", "500", "502", "504", "connection", "temporar", "reset by peer")

def _is_transient(e):
    s = str(e).lower()
    return any(k in s for k in _TRANSIENT_KEYS)

def _write_signature(name, args, kwargs):
    skip = ("ID", "No", "登録日時")
    def clean(o):
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items() if not str(k).endswith(skip)}
        if isinstance(o, (list, tuple)):
            return [clean(x) for x in o]
        return o
    try:
        return hashlib.md5(json.dumps([name, clean(list(args)), clean(kwargs)], ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()
    except Exception:
        return None

class _SafeSheets:
    DEDUP_WRITES = ("append_brewing", "append_arrival")
    DEDUP_SECONDS = 10

    def __init__(self, mod):
        self._m = mod

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        if self._m is None or not hasattr(self._m, name):
            raise AttributeError(name)
        fn = getattr(self._m, name)
        if not callable(fn):
            return fn
        is_write = name.startswith(("append_", "save_", "delete_", "update_"))

        def wrapper(*a, **k):
            if name in self.DEDUP_WRITES:
                sig = _write_signature(name, a, k)
                last = st.session_state.get("_last_write")
                if sig and last and last[0] == sig and time.time() - last[1] < self.DEDUP_SECONDS:
                    st.warning("⚠️ 直前に同じ内容を登録済みのため、二重登録を防止しました。")
                    st.stop()
                if sig:
                    st.session_state["_last_write"] = (sig, time.time())
            last_err = None
            for attempt in range(3):
                try:
                    return fn(*a, **k)
                except Exception as e:  # noqa
                    last_err = e
                    if attempt < 2 and _is_transient(e):
                        time.sleep(0.8 * (attempt + 1))
                        continue
                    break
            if is_write:
                st.session_state.pop("_last_write", None)
                st.error(f"💥 保存に失敗しました（{name}）。入力内容は消えていません。通信状態を確認してもう一度お試しください。")
                with st.expander("エラー詳細（管理者向け）"):
                    st.code("".join(traceback.format_exception(type(last_err), last_err, last_err.__traceback__)))
                st.stop()
            raise last_err
        return wrapper

sheets = _SafeSheets(_sheets_mod)

# ════════════════════════════════════════════════════════════════
#  データロード & パーサー
# ════════════════════════════════════════════════════════════════
def flash(msg, kind="success"):
    """次回の再描画で画面上部に表示するメッセージ（sleepで待たずに済む）"""
    st.session_state["_flash"] = (msg, kind)

def refresh():
    st.cache_data.clear()
    st.rerun()

def done(msg, kind="success"):
    flash(msg, kind)
    refresh()

@st.cache_data(ttl=60, show_spinner="データを読み込み中...")
def load_all_datasets():
    required = {
        "arrivals": "load_arrivals", "brewing": "load_brewing", "adjustments": "load_adjustments",
        "supplies": "load_supplies", "supply_logs": "load_supply_logs", "materials": "load_materials",
        "makers": "load_makers", "inspectors": "load_inspectors", "order_points": "load_order_points",
        "recipes": "load_recipes", "recipe_logs": "load_recipe_logs",
    }
    optional = {"grades": "load_grades", "purchase_orders": "load_purchase_orders"}
    out = {}
    for key, fn in required.items():
        out[key] = getattr(sheets, fn)()           # 失敗時は例外 → キャッシュされない
    for key, fn in optional.items():
        out[key] = getattr(sheets, fn)() if hasattr(sheets, fn) else None
    out["_loaded_at"] = now_jst().strftime("%H:%M:%S")
    return out

if _sheets_mod is None:
    st.error("🚨 sheets.py を読み込めませんでした。app.py と同じフォルダに sheets.py があるか確認してください。")
    with st.expander("エラー詳細（管理者向け）"):
        st.code(str(_SHEETS_IMPORT_ERROR))
    st.stop()

try:
    dataset = load_all_datasets()
except Exception as _load_err:
    st.error("🚨 データの読み込みに失敗しました。通信状態を確認し、「再読み込み」を押してください。")
    if st.button("🔄 再読み込み", type="primary"):
        st.cache_data.clear(); st.rerun()
    with st.expander("エラー詳細（管理者向け）"):
        st.code("".join(traceback.format_exception(type(_load_err), _load_err, _load_err.__traceback__)))
    st.stop()

arrivals = dataset.get("arrivals") or []
brewing = dataset.get("brewing") or []
adjustments = dataset.get("adjustments") or []
supplies = dataset.get("supplies") or []
supply_logs = dataset.get("supply_logs") or []
materials = dataset.get("materials") or []
makers = dataset.get("makers") or []
inspectors = dataset.get("inspectors") or []
order_points = dataset.get("order_points") or {}
recipes_raw = dataset.get("recipes") or []
recipe_logs = dataset.get("recipe_logs") or []
grades_data = dataset.get("grades")
purchase_orders_data = dataset.get("purchase_orders")

def parse_op_data(raw_val):
    pt, wt = 0, 20
    try:
        if isinstance(raw_val, str):
            if raw_val.strip().startswith("{"):
                d = json.loads(raw_val)
                pt, wt = int(float(d.get("pt", 0))), int(float(d.get("wt", 20)))
            else:
                m_pt = re.search(r"発注点:([\d\.]+)袋", raw_val); m_wt = re.search(r"重量:([\d\.]+)kg", raw_val)
                if m_pt: pt = int(float(m_pt.group(1)))
                if m_wt: wt = int(float(m_wt.group(1)))
        else: pt = int(float(raw_val))
    except Exception: pass
    return pt, wt

def get_material_image(op_dict, mat_name): return op_dict.get(f"__IMAGE_{mat_name}__", "")
def get_active_lots_from_master(op_dict, mat_name):
    v = op_dict.get(f"__ACTIVE_LOTS_{mat_name}__", "")
    if v:
        try: return json.loads(v)
        except Exception: pass
    return []

def parse_lime_config(op_dict, product_name=None):
    c = {"start_month": 6, "end_month": 9, "add_ratio": 0.01, "reason": "夏場の高温対策"}
    try:
        v = op_dict.get(f"__LIME_CONFIG_{product_name}__", "") if product_name else ""
        if not v: v = op_dict.get("__LIME_CONFIG__", "")
        if v:
            m_s = re.search(r"開始:(\d+)月", v); m_e = re.search(r"終了:(\d+)月", v); m_r = re.search(r"割合:([\d\.]+)", v); m_reason = re.search(r"理由:(.+?)(?:,|$)", v)
            if m_s: c["start_month"] = int(m_s.group(1))
            if m_e: c["end_month"] = int(m_e.group(1))
            if m_r: c["add_ratio"] = float(m_r.group(1))
            if m_reason: c["reason"] = m_reason.group(1).strip()
    except Exception: pass
    return c

def parse_grade_list(op_dict):
    if grades_data is not None: return grades_data
    try:
        v = op_dict.get("__GRADE_LIST__", "")
        if v: return [str(x).strip() for x in json.loads(v)] if v.strip().startswith("[") else [str(x).strip() for x in v.split(",") if str(x).strip()]
    except Exception: pass
    return []

def safe_parse_recipe(r_val):
    if not r_val: return []
    if isinstance(r_val, str) and r_val.strip().startswith("["):
        try: return json.loads(r_val)
        except Exception: pass
    items = []
    if isinstance(r_val, str):
        for p in r_val.split(","):
            if ":" in p:
                mat, rat = p.split(":", 1)
                try: items.append({"原料名": mat.strip(), "比率": float(rat.replace("%", "").strip())})
                except Exception: pass
    return items

def safe_parse_seasoning_recipe(r_val):
    if not r_val: return []
    if isinstance(r_val, str) and r_val.strip().startswith("["):
        try: return json.loads(r_val)
        except Exception: pass
    items = []
    if isinstance(r_val, str):
        for p in r_val.split(","):
            if ":" in p:
                mat, rat = p.split(":", 1)
                try: items.append({"原料名": mat.strip(), "希釈倍率": float(rat.replace("倍", "").strip())})
                except Exception: pass
    return items

# ── 製造記録の「その他添加物」(原料ごとの投入量+ロット) の解析 ───────────────
#   保存形式: 「原料名:5.0kg(ロット), 原料名:1.0kg(ロット(50%))」
_ING_SPLIT = re.compile(r",\s*(?=[^,]+?:[\d\.]+kg\()")
_ING_ITEM = re.compile(r"^(.+?):([\d\.]+)kg\((.*)\)$")
_LOT_RATIO_TAIL = re.compile(r"\(\s*[\d\.]+\s*%\s*\)?\s*$")

def clean_lot(x):
    """ロット表記から「(50%)」「(50.0%)」「(50.0%」などのブレンド比率を取り除く"""
    return _LOT_RATIO_TAIL.sub("", str(x).strip()).strip()

def split_lots(lot_str):
    out = []
    for x in str(lot_str or "").split(","):
        l = clean_lot(x)
        if l and l != "─": out.append(l)
    return out

def sanitize_lot(s):
    """ロットNo入力の安全化（カンマ・括弧・改行は記録形式を壊すため置換）"""
    s = str(s or "").strip()
    s = re.sub(r"[,，、\r\n]", "-", s)
    s = s.replace("(", "（").replace(")", "）")
    return s

def parse_brewing_ingredients(r_val):
    if not r_val: return []
    if isinstance(r_val, str) and r_val.strip().startswith("["):
        try: return json.loads(r_val)
        except Exception: pass
    items = []
    if isinstance(r_val, str):
        for p in _ING_SPLIT.split(r_val.strip()):
            m = _ING_ITEM.match(p.strip())
            if m: items.append({"原料名": m.group(1).strip(), "kg": float(m.group(2)), "lot": m.group(3).strip()})
    return items

def format_ingredient_breakdown(r_val):
    """製造記録の「その他添加物」欄から、原料ごとの投入量を人が読みやすい形式に整形する。
    例: 「こんにゃく精粉 5kg(L100) / 海藻粉 1kg(L300) / 水 94kg」"""
    items = parse_brewing_ingredients(r_val)
    if not items: return ""
    parts = []
    for it in items:
        n = str(it.get("原料名", "")).strip()
        kg = it.get("kg", 0)
        lot = str(it.get("lot", "")).strip()
        if not n: continue
        lot_txt = f"({lot})" if lot and lot != "─" else ""
        parts.append(f"{n} {fmt_kg(kg)}kg{lot_txt}")
    return " / ".join(parts)

def is_lime_boost_active(cfg, t_date=None):
    if t_date is None: t_date = today_jst()
    m, s, e = t_date.month, int(cfg.get("start_month", 6)), int(cfg.get("end_month", 9))
    return s <= m <= e if s <= e else (m >= s or m <= e)

def save_grade_list(op_dict, g_list):
    if hasattr(sheets, "save_grades"): sheets.save_grades(g_list)
    else: d = dict(op_dict); d["__GRADE_LIST__"] = ", ".join(g_list); sheets.save_order_points(d)

def is_konjac_material(name):
    s = str(name); s_hira = "".join(chr(ord(c)-0x60) if "ァ"<=c<="ヶ" else c for c in s)
    return ("こんにゃく" in s_hira) or ("蒟蒻" in s) or ("konnyaku" in s.lower())

def parse_purchase_orders(op_dict):
    if purchase_orders_data is not None: return purchase_orders_data
    try:
        v = op_dict.get("__PURCHASE_ORDERS__", "")
        if v and v.startswith("["): return json.loads(v)
    except Exception: pass
    return []

def fresh_purchase_orders():
    """保存直前に最新の発注一覧を取り直す（複数端末の同時操作で上書きしないため）"""
    try:
        if hasattr(sheets, "load_purchase_orders"):
            return list(sheets.load_purchase_orders() or [])
        d = sheets.load_order_points() or {}
        v = d.get("__PURCHASE_ORDERS__", "")
        return json.loads(v) if v and v.startswith("[") else []
    except Exception:
        return [dict(o) for o in parse_purchase_orders(order_points)]

def save_purchase_orders(op_dict, o_list):
    if hasattr(sheets, "save_purchase_orders"): sheets.save_purchase_orders(o_list)
    else: d = dict(op_dict); d["__PURCHASE_ORDERS__"] = json.dumps(o_list, ensure_ascii=False); sheets.save_order_points(d)

BIG_CAT_ICONS = {"プラント": "🏭", "OKM": "🟦", "手詰め": "✋"}
SUB_CAT_ICONS = {"白": "⚪", "黒": "⚫", "耐冷": "❄️", "ショクカイ": "🍽️", "めん": "🍜", "おでん": "🍢", "その他": "📦"}
_ICON_POOL = ["🔵", "🟢", "🟡", "🟣", "🟠", "🔴", "🟤", "🔷", "🔶", "🔹", "🔸", "⬛", "⬜", "🟥", "🟩", "🟦"]
_PRODUCT_ICON_POOL = ["🍥", "🥢", "🌿", "🎍", "🧊", "🍡", "🧵", "🏷️", "📌", "🧺", "🔖", "🧫"]

def _deterministic_icon(name, pool): return pool[sum(ord(ch) for ch in str(name)) % len(pool)]
def big_cat_icon(name): return BIG_CAT_ICONS.get(name, _deterministic_icon(name, _ICON_POOL))
def sub_cat_icon(name): return SUB_CAT_ICONS.get(name, _deterministic_icon(name, _ICON_POOL))
def product_icon(name): return _deterministic_icon(name, _PRODUCT_ICON_POOL)

def to_float(v, default=0.0):
    if v is None: return default
    if isinstance(v, (int, float)):
        try:
            if v != v:  # NaN
                return default
        except Exception:
            pass
        return float(v)
    s = str(v).strip()
    if s == "" or s.lower() in ("nan", "none"): return default
    trans = str.maketrans("０１２３４５６７８９．－", "0123456789.-")
    s = s.translate(trans).replace(",", "").replace("袋", "").replace("kg", "").strip()
    try:
        return float(s)
    except Exception:
        return default

# 棚卸で確実に0にするための許容誤差 (0.05袋 ≒ 1kg未満、0.05個未満は確実にゼロとみなす)
EPS_BAGS = 0.05
EPS_QTY = 0.05

def snap_zero(v, eps=EPS_BAGS):
    v = to_float(v)
    return 0.0 if abs(v) < eps else v

def fmt_kg(val):
    if val is None or val == "": return "0"
    try: v = float(val); return f"{int(v)}" if v.is_integer() else f"{v:.2f}".rstrip('0').rstrip('.')
    except Exception: return str(val)

def fmt_df_numeric(df, cols):
    d = df.copy()
    for c in cols:
        if c in d.columns: d[c] = d[c].apply(fmt_kg)
    return d

def ensure_cols(df, cols, fill=""):
    """DataFrameに無い列を空で補う（空シート・列欠けでも落ちないように）"""
    d = df.copy()
    for c in cols:
        if c not in d.columns: d[c] = fill
    return d

def _lot_date_sort_key(d_str):
    try:
        return datetime.strptime(str(d_str).strip(), "%Y-%m-%d")
    except Exception:
        return datetime.max

# ════════════════════════════════════════════════════════════════
#  在庫計算 (誤差丸めによる完全0化)
#   * ロットNo＋原料名で使用量を引き当て（ブレンド比率付きロットも正しく解釈）
#   * 同一ロットNoの入荷が複数ある場合は「古い入荷から順に」引き当て（二重控除しない）
# ════════════════════════════════════════════════════════════════
def get_inventory():
    inv = {}
    for a in arrivals:
        ano = str(a.get("入荷No", "")).strip()
        if not ano: continue
        inv[ano] = {
            "入荷No": ano, "入荷日": str(a.get("入荷日", "")).strip() or "-", "ロットNo": str(a.get("ロットNo", "")).strip(), "原料種別": str(a.get("原料種別", "")).strip(),
            "メーカー": str(a.get("メーカー", "")).strip(), "グレード": str(a.get("グレード", "")).strip(),
            "1袋重量": round(to_float(a.get("1袋重量(kg)"), 20.0) or 20.0, 3), "入荷袋数": round(to_float(a.get("袋数")), 3), "使用量(kg)": 0.0, "調整袋数": 0.0
        }

    for adj in adjustments:
        ano = str(adj.get("入荷No", "")).strip()
        if ano in inv:
            inv[ano]["調整袋数"] += to_float(adj.get("調整袋数"))

    idx_key, idx_lot = {}, {}
    for ano, v in sorted(inv.items(), key=lambda kv: (_lot_date_sort_key(kv[1]["入荷日"]), kv[0])):
        idx_key.setdefault((v["原料種別"], v["ロットNo"]), []).append(ano)
        idx_lot.setdefault(v["ロットNo"], []).append(ano)

    def _allocate(targets, kg):
        remaining = kg
        for i, ano in enumerate(targets):
            v = inv[ano]
            cap = (v["入荷袋数"] + v["調整袋数"]) * v["1袋重量"] - v["使用量(kg)"]
            take = remaining if i == len(targets) - 1 else min(max(cap, 0.0), remaining)
            v["使用量(kg)"] += take
            remaining -= take
            if remaining <= 1e-9: break

    for b in brewing:
        for item in parse_brewing_ingredients(b.get("その他添加物", "")):
            name = str(item.get("原料名", "")).strip()
            kg = to_float(item.get("kg"))
            lots = split_lots(item.get("lot", ""))
            if kg <= 0 or not lots: continue
            share = kg / len(lots)
            for l in lots:
                targets = idx_key.get((name, l)) or idx_lot.get(l) or []
                if targets: _allocate(targets, share)

    for v in inv.values():
        bpk = v["1袋重量"] if v["1袋重量"] > 0 else 20.0
        v["使用袋数"] = v["使用量(kg)"] / bpk
        raw_bags = round(v["入荷袋数"] - v["使用袋数"] + v["調整袋数"], 4)
        v["理論残(袋)"] = raw_bags
        raw_bags = snap_zero(raw_bags, EPS_BAGS)
        v["現在庫(袋)"] = max(raw_bags, 0.0)
        v["現在庫(kg)"] = round(v["現在庫(袋)"] * bpk, 3)
    return inv

inventory_data = get_inventory()
type_totals_kg, type_totals_bag = {}, {}
for _v in inventory_data.values():
    _m = _v["原料種別"]
    type_totals_kg[_m] = type_totals_kg.get(_m, 0.0) + _v["現在庫(kg)"]
    type_totals_bag[_m] = type_totals_bag.get(_m, 0.0) + _v["現在庫(袋)"]

def negative_stock_lots():
    """記録上マイナス(入荷より使用が多い)のロット = 入荷登録漏れ・ロット誤入力の疑い"""
    return [v for v in inventory_data.values() if v["理論残(袋)"] < -EPS_BAGS]

def _get_active_lots(mat):
    """完全に在庫が0になったものは除外する"""
    o = []
    for v in inventory_data.values():
        if v["原料種別"] == mat and v["現在庫(袋)"] > 0 and v["ロットNo"] not in o:
            o.append(v["ロットNo"])
    return o

def lot_stock(mat, lot):
    """(原料, ロット) の現在庫 → (袋, kg)"""
    bags = kg = 0.0
    for v in inventory_data.values():
        if v["原料種別"] == mat and v["ロットNo"] == lot:
            bags += v["現在庫(袋)"]; kg += v["現在庫(kg)"]
    return bags, kg

def sorted_supplies(sup_list=None):
    sup_list = supplies if sup_list is None else sup_list
    def _key(s):
        o = s.get("表示順", "")
        o = to_float(o, default=None) if str(o).strip() != "" else None
        return (o is None, o if o is not None else 0.0)
    return sorted(sup_list, key=_key)

def sorted_materials():
    return [m for m in materials if not str(m).startswith("__")]

def get_lots_for_material(mat):
    l = [v for v in inventory_data.values() if v["原料種別"] == mat and v["現在庫(袋)"] > 0]
    l.sort(key=lambda v: v["現在庫(袋)"], reverse=True)
    return l

def get_supply_inventory():
    inv = {s.get("資材ID"): to_float(s.get("初期在庫")) for s in supplies}
    for log in supply_logs:
        sid, qty, act = log.get("資材ID"), to_float(log.get("数量")), log.get("処理")
        if sid in inv:
            if act == "入荷": inv[sid] += qty
            elif act == "使用": inv[sid] -= qty

    for sid in list(inv.keys()):
        inv[sid] = max(snap_zero(inv[sid], EPS_QTY), 0.0)
    return inv

def low_stock_materials():
    """発注点を下回っている原料 → [(原料名, 現在袋, 発注点)]"""
    out = []
    for m in sorted_materials():
        pt, _ = parse_op_data(order_points.get(m, 0.0))
        cur = type_totals_bag.get(m, 0.0)
        if pt > 0 and cur < pt: out.append((m, cur, pt))
    return out

def low_stock_supplies():
    inv = get_supply_inventory()
    out = []
    for s in sorted_supplies():
        pt = to_float(s.get("発注点"), 0.0)
        cur = inv.get(s.get("資材ID"), 0.0)
        if pt > 0 and cur <= pt: out.append((s.get("資材名"), cur, pt))
    return out

def pending_orders_list():
    return [o for o in parse_purchase_orders(order_points) if o.get("ステータス") not in ("入荷済み", "取消")]

def overdue_orders_list():
    t = str(today_jst())
    return [o for o in pending_orders_list() if o.get("納品予定日") and str(o["納品予定日"]) < t]

# ════════════════════════════════════════════════════════════════
#  カスタムUIコンポーネント
# ════════════════════════════════════════════════════════════════
def render_amount_adjuster(title, calc_val, p_key):
    lst_key = f"last_calc_{p_key}"
    last_calc, calc_val = st.session_state.get(lst_key, None), round(calc_val, 2)
    if (last_calc is None) or (abs(float(last_calc) - float(calc_val)) > 1e-6):
        st.session_state[p_key] = st.session_state[lst_key] = calc_val
    if p_key not in st.session_state: st.session_state[p_key] = calc_val

    return st.number_input(f"{title}（自動計算値・必要なら変更可）", min_value=0.0, step=0.1, key=p_key, format="%.2f")


def render_lot_selector(mat_name, lot_key):
    d_map = {}
    for v in inventory_data.values():
        if v["原料種別"] == mat_name:
            d_map.setdefault(v["ロットNo"], v["入荷日"])
    master_lots = set(get_active_lots_from_master(order_points, mat_name))
    all_active_lots = _get_active_lots(mat_name)

    ordered_lots = sorted(all_active_lots, key=lambda l: _lot_date_sort_key(d_map.get(l, "")))

    MANUAL_OPT = "✏️ 手入力する"
    label_of = {}
    for l in ordered_lots:
        bags, _kg = lot_stock(mat_name, l)
        label_of[l] = f"{'📌 ' if l in master_lots else ''}{l} (入荷:{d_map.get(l, '不明')} / 残{fmt_kg(round(bags, 2))}袋)"
    options = [label_of[l] for l in ordered_lots] + [MANUAL_OPT]
    rev_label = {v: k for k, v in label_of.items()}

    widget_key = f"{lot_key}_select"
    if widget_key not in st.session_state or st.session_state[widget_key] not in options:
        st.session_state[widget_key] = options[0] if ordered_lots else MANUAL_OPT

    chosen_label = st.selectbox(f"📦 {mat_name} のロット（在庫あり・古い順）", options, key=widget_key)

    if chosen_label == MANUAL_OPT:
        m_in = st.text_input("✏️ ロットNoを入力", key=f"{lot_key}_manual_txt", placeholder="例: L12345")
        final_lot = sanitize_lot(m_in) if m_in.strip() else "─"
        if final_lot != "─" and not any(v["原料種別"] == mat_name and v["ロットNo"] == final_lot for v in inventory_data.values()):
            st.caption("⚠️ このロットは入荷登録されていません（在庫は引かれません）。")
    else:
        final_lot = rev_label.get(chosen_label, "─")

    st.session_state[lot_key] = final_lot
    return final_lot


def render_operator_selector(operator_key):
    if not inspectors:
        st.caption("⚠️ 担当者が登録されていません。「担当者」タブで登録してください。")
        st.session_state[operator_key] = "未登録"
        return "未登録"

    if operator_key not in st.session_state or st.session_state[operator_key] not in inspectors:
        last_op = st.session_state.get("_last_operator")
        st.session_state[operator_key] = last_op if last_op in inspectors else inspectors[0]

    selected = st.selectbox("👨‍🏭 担当者", inspectors, key=operator_key)
    st.session_state["_last_operator"] = selected   # 端末ごとに前回の担当者を記憶
    return selected


def render_excel_history_editor(full_records, filtered_df, id_col, editable_cols, numeric_cols, save_func, key_prefix, reload_func=None):
    if filtered_df.empty:
        st.info("データがありません。")
        return
    edit_df = filtered_df[[id_col] + [c for c in editable_cols if c != id_col]].copy().reset_index(drop=True)
    for c in numeric_cols:
        if c in edit_df.columns: edit_df[c] = pd.to_numeric(edit_df[c], errors="coerce").fillna(0.0)
    edit_df[id_col] = edit_df[id_col].astype(str)

    st.caption("💡 セルをタップして直接編集できます。行左端のチェックで選択し🗑️で削除できます。")
    col_cfg = {id_col: st.column_config.TextColumn(id_col, disabled=True)}
    for c in numeric_cols:
        if c in edit_df.columns: col_cfg[c] = st.column_config.NumberColumn(c, format="%.2f")

    edited_df = st.data_editor(edit_df, num_rows="dynamic", use_container_width=True, hide_index=True, key=f"{key_prefix}_editor", column_config=col_cfg)
    diff_key = f"{key_prefix}_diff_pending"

    c_check, c_cancel = st.columns([2, 1])
    if c_check.button("🔍 変更内容を確認する", key=f"{key_prefix}_check_btn", use_container_width=True):
        orig_ids = set(edit_df[id_col])
        edited_clean = edited_df.copy()
        edited_clean[id_col] = edited_clean[id_col].astype(str).str.strip()
        valid_edited = edited_clean[edited_clean[id_col] != ""]
        orig_idx = edit_df.set_index(id_col)
        changed_rows = [row[id_col] for _, row in valid_edited.iterrows()
                        if row[id_col] in orig_ids and any(str(row[c]) != str(orig_idx.loc[row[id_col], c]) for c in editable_cols if c != id_col)]

        st.session_state[diff_key] = {
            "changed": changed_rows, "deleted": sorted(orig_ids - set(valid_edited[id_col])),
            "blank_new_rows": len(edited_clean) - len(valid_edited), "edited_df": edited_clean
        }
        st.rerun()

    if c_cancel.button("❌ 取消", key=f"{key_prefix}_cancel_btn", use_container_width=True):
        st.session_state.pop(diff_key, None)
        st.rerun()

    diff = st.session_state.get(diff_key)
    if diff:
        n_c, n_d, n_b = len(diff["changed"]), len(diff["deleted"]), diff["blank_new_rows"]
        if n_c == 0 and n_d == 0 and n_b == 0: st.info("変更はありませんでした。")
        else:
            msg = []
            if n_c: msg.append(f"✏️ 更新 {n_c}件：{', '.join(diff['changed'][:8])}{' ...' if n_c > 8 else ''}")
            if n_d: msg.append(f"🗑️ 削除 {n_d}件：{', '.join(diff['deleted'][:8])}{' ...' if n_d > 8 else ''}")
            st.markdown(f'<div style="background:{"#fdf1f1" if n_d else "#e6f2f1"}; border:2px solid {"#b91c1c" if n_d else "#0f766e"}; border-radius:10px; padding:14px; margin:10px 0;">{"<br>".join(msg)}</div>', unsafe_allow_html=True)

            del_ok = True
            if n_d:
                st.warning("削除した記録は元に戻せません。在庫・トレースの計算にも影響します。")
                del_ok = st.checkbox("削除内容を確認しました", key=f"{key_prefix}_del_ok")

            if (n_c or n_d) and st.button("✅ この内容で確定保存する", type="primary", key=f"{key_prefix}_confirm_btn", use_container_width=True, disabled=not del_ok):
                base_records = full_records
                if reload_func is not None:
                    try: base_records = reload_func() or full_records   # 他端末の更新を上書きしないよう最新を取り直す
                    except Exception: base_records = full_records
                id_to_record = {str(r.get(id_col)): dict(r) for r in base_records}
                valid_edited = diff["edited_df"][diff["edited_df"][id_col] != ""]
                for _, row in valid_edited.iterrows():
                    if row[id_col] in id_to_record:
                        for c in editable_cols:
                            if c != id_col: id_to_record[row[id_col]][c] = to_float(row[c]) if c in numeric_cols else ("" if pd.isna(row[c]) else row[c])
                for rid in diff["deleted"]: id_to_record.pop(rid, None)
                save_func(list(id_to_record.values()))
                st.session_state.pop(diff_key, None)
                done("保存しました。")


def render_lot_inventory_manager(active_inv):
    st.caption("💡 棚卸し・在庫調整はこの表で行います。「現在庫(袋)」の数値を実際の数に書き換えてください。**「0」にすれば確実にゼロになります。**")

    mats = sorted({v["原料種別"] for v in active_inv})
    c_f1, c_f2 = st.columns([1, 1])
    f_mat = c_f1.selectbox("🔎 原料で絞り込み", ["すべて"] + mats, key="lot_inv_mat_filter")
    f_kw = c_f2.text_input("🔎 ロットNo検索", key="lot_inv_kw", placeholder="例: L123")
    rows = [v for v in active_inv if (f_mat == "すべて" or v["原料種別"] == f_mat) and (not f_kw.strip() or f_kw.strip().lower() in v["ロットNo"].lower())]
    rows = sorted(rows, key=lambda v: (v["原料種別"], v["入荷日"]))
    if not rows:
        st.info("条件に合う在庫がありません。")
        return
    orig_map = {v["入荷No"]: v for v in rows}

    df_edit = pd.DataFrame([{"入荷No": v["入荷No"], "入荷日": v["入荷日"], "原料種別": v["原料種別"], "メーカー": v["メーカー"], "ロットNo": v["ロットNo"], "現在庫(袋)": round(v["現在庫(袋)"], 3), "🗑️ 削除(在庫0に)": False} for v in rows])
    col_cfg = {c: st.column_config.TextColumn(c, disabled=True) for c in ["入荷No", "入荷日", "原料種別", "メーカー", "ロットNo"]}
    col_cfg["現在庫(袋)"] = st.column_config.NumberColumn("現在庫(袋)【編集可】", format="%.3f", min_value=0.0, step=0.1)

    edited_df = st.data_editor(df_edit, use_container_width=True, hide_index=True, num_rows="fixed", key=f"lot_inv_editor_{f_mat}_{f_kw}", column_config=col_cfg)
    diff_key = "lot_inv_diff_pending"

    c_check, c_cancel = st.columns([2, 1])
    if c_check.button("🔍 変更内容を確認する", key="lot_inv_check_btn", use_container_width=True):
        changes = []
        for _, r in edited_df.iterrows():
            ano = str(r["入荷No"])
            orig = orig_map.get(ano)
            if not orig: continue
            del_flag = bool(r.get("🗑️ 削除(在庫0に)", False))
            theo = to_float(orig["現在庫(袋)"])

            if del_flag:
                diff = -theo
                new_bags = 0.0
            else:
                new_bags = max(0.0, to_float(r["現在庫(袋)"]))
                if new_bags < EPS_BAGS:
                    new_bags = 0.0
                diff = new_bags - theo

            if del_flag or abs(diff) > 0.005:
                diff = round(diff, 4)
                if abs(diff) < 1e-9: continue
                changes.append({"入荷No": ano, "ロットNo": orig["ロットNo"], "原料種別": orig["原料種別"], "旧在庫": theo, "新在庫": new_bags, "差分": diff, "削除": del_flag})
        st.session_state[diff_key] = changes
        st.rerun()

    if c_cancel.button("❌ 取消", key="lot_inv_cancel_btn", use_container_width=True):
        st.session_state.pop(diff_key, None); st.rerun()

    changes = st.session_state.get(diff_key)
    if changes is not None:
        if not changes: st.info("変更はありませんでした。")
        else:
            msg_lines = [f"{'🗑️ 0設定' if c['削除'] or c['新在庫']==0 else '✏️ 編集'} {c['原料種別']} ロット:{c['ロットNo']} {fmt_kg(c['旧在庫'])}袋 → {fmt_kg(c['新在庫'])}袋" for c in changes]
            st.markdown(f'<div style="background:#fdf1f1; border:2px solid #b91c1c; border-radius:10px; padding:14px; margin:10px 0;">{"<br>".join(msg_lines)}</div>', unsafe_allow_html=True)
            reason_txt = st.text_input("変更理由 (任意)", key="lot_inv_reason")
            op = render_operator_selector("lot_inv_op")
            if st.button("✅ 確定保存する（履歴に記録）", type="primary", key="lot_inv_confirm_btn", use_container_width=True):
                if not hasattr(sheets, "append_adjustment"):
                    st.error("sheets.append_adjustment が見つかりません。")
                else:
                    for i, c in enumerate(changes):
                        sheets.append_adjustment({
                            "調整ID": f"ADJ-{now_jst().strftime('%Y%m%d%H%M%S%f')}-{i}", "入荷No": c["入荷No"], "調整日": str(today_jst()),
                            "調整袋数": c["差分"], "理由": f"【棚卸】{fmt_kg(c['旧在庫'])}→{fmt_kg(c['新在庫'])} {reason_txt}".strip(),
                            "担当者": op, "登録日時": now_jst().isoformat()
                        })
                    st.session_state.pop(diff_key, None)
                    done(f"{len(changes)}件の棚卸変更を保存しました。")


# ════════════════════════════════════════════════════════════════
#  記録確認・帳票ヘルパー
# ════════════════════════════════════════════════════════════════
PERIOD_CHOICES = ["今日", "昨日", "今週", "今月", "先月", "直近30日", "全期間", "期間を指定"]

def period_picker(key, default="今月"):
    """期間のワンタッチ選択 → (開始日, 終了日)。全期間は (None, None)"""
    sel = st.radio("📅 期間", PERIOD_CHOICES, index=PERIOD_CHOICES.index(default), horizontal=True, key=f"{key}_period")
    t = today_jst()
    if sel == "今日": return t, t
    if sel == "昨日": y = t - timedelta(days=1); return y, y
    if sel == "今週": return t - timedelta(days=t.weekday()), t
    if sel == "今月": return t.replace(day=1), t
    if sel == "先月":
        last_end = t.replace(day=1) - timedelta(days=1)
        return last_end.replace(day=1), last_end
    if sel == "直近30日": return t - timedelta(days=29), t
    if sel == "全期間": return None, None
    c1, c2 = st.columns(2)
    s = c1.date_input("開始日", value=t.replace(day=1), key=f"{key}_ps")
    e = c2.date_input("終了日", value=t, key=f"{key}_pe")
    if s > e: st.warning("開始日が終了日より後になっています。"); s, e = e, s
    return s, e

def in_period(series, s, e):
    dt = pd.to_datetime(series, errors="coerce")
    if s is None: return pd.Series(True, index=series.index)
    return (dt >= pd.Timestamp(s)) & (dt < pd.Timestamp(e) + pd.Timedelta(days=1))

def keyword_mask(df, cols, kw):
    kw = str(kw or "").strip().lower()
    if not kw: return pd.Series(True, index=df.index)
    m = pd.Series(False, index=df.index)
    for c in cols:
        if c in df.columns: m = m | df[c].astype(str).str.lower().str.contains(re.escape(kw), na=False)
    return m

def build_usage_df(brew_records):
    """製造記録 → 原料ごとの使用明細（ロットの入荷日・メーカー・グレード付き）"""
    arr_by_key, arr_by_lot = {}, {}
    for a in arrivals:
        lot = str(a.get("ロットNo", "")).strip()
        if not lot: continue
        arr_by_key.setdefault((str(a.get("原料種別", "")).strip(), lot), a)
        arr_by_lot.setdefault(lot, a)
    rows = []
    for b in brew_records:
        for it in parse_brewing_ingredients(b.get("その他添加物", "")):
            name = str(it.get("原料名", "")).strip()
            lots = split_lots(it.get("lot", "")) or ["─"]
            kg = to_float(it.get("kg")) / len(lots)
            for l in lots:
                a = arr_by_key.get((name, l)) or arr_by_lot.get(l) or {}
                rows.append({
                    "仕込日": b.get("仕込日", ""), "仕込No": b.get("仕込No", ""), "品名": b.get("品名", ""), "担当者": b.get("メーカー", ""),
                    "原料名": name, "投入量(kg)": round(kg, 3), "ロットNo": l,
                    "入荷No": a.get("入荷No", ""), "入荷日": a.get("入荷日", ""), "入荷メーカー": a.get("メーカー", ""), "グレード": a.get("グレード", ""),
                })
    cols = ["仕込日", "仕込No", "品名", "担当者", "原料名", "投入量(kg)", "ロットNo", "入荷No", "入荷日", "入荷メーカー", "グレード"]
    return pd.DataFrame(rows, columns=cols)

def _py(v):
    try:
        if v is None or (isinstance(v, float) and v != v): return ""
        if hasattr(v, "item"): return v.item()
        if isinstance(v, (pd.Timestamp, datetime)): return v.strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    return v

def make_excel(sheets_dict, title=None):
    """{シート名: DataFrame} → 見やすく整形したxlsxのbytes。openpyxl未導入ならNone"""
    if not HAS_OPENPYXL: return None
    wb = Workbook(); first = True
    head_fill = PatternFill("solid", fgColor="0F766E")
    thin = Side(style="thin", color="CBD5E1")
    for name, df in sheets_dict.items():
        ws = wb.active if first else wb.create_sheet()
        first = False
        ws.title = str(name)[:31]
        cols = list(df.columns)
        for ci, h in enumerate(cols, 1):
            c = ws.cell(row=1, column=ci, value=str(h))
            c.font = Font(bold=True, color="FFFFFF"); c.fill = head_fill
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            c.border = Border(top=thin, bottom=thin, left=thin, right=thin)
        for ri, row in enumerate(df.itertuples(index=False), 2):
            for ci, v in enumerate(row, 1):
                c = ws.cell(row=ri, column=ci, value=_py(v))
                c.border = Border(top=thin, bottom=thin, left=thin, right=thin)
                c.alignment = Alignment(vertical="top", wrap_text=isinstance(c.value, str) and len(c.value) > 40)
        for ci, h in enumerate(cols, 1):
            width = max([len(str(h)) * 2] + [min(len(str(_py(x))), 60) for x in df[h].head(200).tolist()] + [8]) + 2
            ws.column_dimensions[get_column_letter(ci)].width = min(max(width, 10), 70)
        ws.freeze_panes = "A2"
        if len(df): ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{len(df) + 1}"
    buf = BytesIO(); wb.save(buf)
    return buf.getvalue()

def download_buttons(sheets_dict, base_name, key):
    """Excel + CSV の出力ボタンを横並びで表示"""
    c1, c2 = st.columns(2)
    xl = make_excel(sheets_dict)
    first_df = next(iter(sheets_dict.values()))
    if xl: c1.download_button("🖨️ Excel帳票をダウンロード", data=xl, file_name=f"{base_name}.xlsx", type="primary", use_container_width=True, key=f"{key}_xlsx",
                              mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else: c1.caption("Excel出力には openpyxl が必要です。")
    c2.download_button("📄 CSVでダウンロード", data=first_df.to_csv(index=False).encode("utf-8-sig"), file_name=f"{base_name}.csv", use_container_width=True, key=f"{key}_csv", mime="text/csv")

def brewing_view_df(df):
    """製造記録の一覧表示用に整形"""
    d = ensure_cols(df, ["仕込日", "仕込No", "品名", "メーカー", "仕込量(kg)", "石灰水(L)", "その他添加物", "備考", "登録日時"])
    d["仕込量(kg)"] = d["仕込量(kg)"].apply(to_float)
    d["石灰水(L)"] = d["石灰水(L)"].apply(to_float)
    d["原料内訳（全原料の投入量）"] = d["その他添加物"].apply(format_ingredient_breakdown)
    d = d.rename(columns={"メーカー": "担当者"})
    return d

# ════════════════════════════════════════════════════════════════
#  サイドバー
# ════════════════════════════════════════════════════════════════
PAGES = ["🏭 製造仕込み", "📊 ダッシュボード", "📝 発注管理", "📥 入荷登録", "📦 在庫・棚卸",
         "🧹 資材管理", "🔍 トレース", "📋 履歴・帳票", "📈 分析", "⚙️ マスタ設定"]

def _goto(p):
    st.session_state["page"] = p

with st.sidebar:
    st.markdown('<div style="font-size:1.6rem; font-weight:900; margin-bottom:1.5rem; color:#0f172a;">🏭 製造ERP</div>', unsafe_allow_html=True)
    page = st.radio("メニュー", PAGES, key="page", label_visibility="collapsed")
    st.markdown("---")
    _n_low, _n_over, _n_neg = len(low_stock_materials()), len(overdue_orders_list()), len(negative_stock_lots())
    if _n_low or _n_over or _n_neg:
        _lines = []
        if _n_low: _lines.append(f"⚠️ 在庫不足の原料 {_n_low}件")
        if _n_over: _lines.append(f"⏰ 納品遅れの発注 {_n_over}件")
        if _n_neg: _lines.append(f"❓ 在庫マイナスのロット {_n_neg}件")
        alert_box("<br>".join(_lines), "warn")
    if st.button("🔄 最新データに更新", use_container_width=True): refresh()
    st.caption(f"データ取得 {dataset.get('_loaded_at', '')}（日本時間）／ 1分ごとに自動更新")

# 保存完了などのメッセージ（直前の操作結果）
_fl = st.session_state.pop("_flash", None)
if _fl:
    _msg, _kind = _fl
    st.toast(_msg, icon="✅" if _kind == "success" else "⚠️")
    (st.success if _kind == "success" else st.warning)(_msg)


# ═══════════════════════════════════════════════════════════════
#  🏭 製造仕込み
# ═══════════════════════════════════════════════════════════════
def _stock_caption(mat, lot, kg):
    """投入量に対するロット残量を1行で表示"""
    if lot in ("─", "", None):
        st.markdown("<div style='color:#b45309; font-weight:700; font-size:0.9rem;'>⚠️ ロット未指定</div>", unsafe_allow_html=True); return
    known = any(v["原料種別"] == mat and v["ロットNo"] == lot for v in inventory_data.values())
    if not known:
        st.markdown("<div style='color:#b45309; font-weight:700; font-size:0.9rem;'>⚠️ 入荷登録のないロット</div>", unsafe_allow_html=True); return
    _, skg = lot_stock(mat, lot)
    after = skg - kg
    if after < -0.01:
        st.markdown(f"<div style='color:#b91c1c; font-weight:800; font-size:0.9rem;'>❌ 在庫不足：残 {fmt_kg(round(skg, 2))}kg ＜ 投入 {fmt_kg(kg)}kg</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='color:#15803d; font-weight:700; font-size:0.9rem;'>✅ 残 {fmt_kg(round(skg, 2))}kg → 投入後 {fmt_kg(round(max(after, 0), 2))}kg</div>", unsafe_allow_html=True)

def _ing_row(title, calc_kg, adj_key, mat, lot_key):
    c_amt, c_lot = st.columns([1, 1])
    with c_amt: act = render_amount_adjuster(title, calc_kg, adj_key)
    with c_lot: lot = render_lot_selector(mat, lot_key)
    _stock_caption(mat, lot, act)
    return act, lot

def next_brewing_no_fresh():
    if hasattr(sheets, "next_brewing_no"):
        try: base = sheets.load_brewing()
        except Exception: base = brewing
        return sheets.next_brewing_no(base)
    return f"BRW-{now_jst().strftime('%Y%m%d%H%M%S')}"

def next_arrival_no_fresh():
    if hasattr(sheets, "next_arrival_no"):
        try: base = sheets.load_arrivals()
        except Exception: base = arrivals
        return sheets.next_arrival_no(base)
    return f"ARR-{now_jst().strftime('%Y%m%d%H%M%S')}"

if page == "🏭 製造仕込み":
    page_header("🏭 製造仕込み記録", "投入量は完全自動計算されます。微調整も可能です。保存前に在庫とロットを自動チェックします。")
    card_start()
    brew_date = st.date_input("📅 仕込日", value=today_jst())
    st.markdown("<br>", unsafe_allow_html=True)

    p_recipes = {r.get("品名", "未定義"): {"大カテゴリ": r.get("大カテゴリ", "その他"), "中カテゴリ": r.get("中カテゴリ", "その他"), "成分": safe_parse_recipe(r.get("配合JSON"))} for r in recipes_raw if r.get("大カテゴリ") != "調味料"}
    seasoning_recipes_all = [r for r in recipes_raw if r.get("大カテゴリ") == "調味料"]

    sec_title("🏭 ライン・製品選択")
    step_label("① ラインを選択")
    BASE_BIG_CAT_ORDER = ["プラント", "OKM", "手詰め"]
    dynamic_cats = {v["大カテゴリ"] for v in p_recipes.values() if v.get("大カテゴリ")}
    big_cats = list(BASE_BIG_CAT_ORDER) + sorted(dynamic_cats - set(BASE_BIG_CAT_ORDER))
    big_cat_labels = [f"{big_cat_icon(c)} {c}" for c in big_cats]
    sel_big_label = st.radio("ライン", big_cat_labels, horizontal=True, label_visibility="collapsed") if big_cats else None
    big_cat = big_cats[big_cat_labels.index(sel_big_label)] if sel_big_label else None

    SUB_CAT_ORDER = ["黒", "白", "耐冷", "ショクカイ", "めん", "その他"]
    sub_cats_set = {v["中カテゴリ"] for v in p_recipes.values() if v.get("大カテゴリ") == big_cat and v.get("中カテゴリ")} if big_cat else set()
    sub_cats = sorted(sub_cats_set, key=lambda c: (SUB_CAT_ORDER.index(c) if c in SUB_CAT_ORDER else len(SUB_CAT_ORDER), c))
    sub_str = None
    if big_cat and len(sub_cats) > 1:
        step_label("② 種別を選択")
        sub_cat_labels = [f"{sub_cat_icon(c)} {c}" for c in sub_cats]
        sel_sub_label = st.radio("種別", sub_cat_labels, horizontal=True, label_visibility="collapsed")
        sub_str = sub_cats[sub_cat_labels.index(sel_sub_label)]
    elif sub_cats: sub_str = sub_cats[0]

    step_label("③ 製品品番を選択")
    filtered_opts = [k for k, v in p_recipes.items() if v.get("大カテゴリ") == big_cat and v.get("中カテゴリ") == sub_str] if big_cat and sub_str else []
    selected_p = None
    active_recipe = []
    if filtered_opts:
        opt_labels = [f"{product_icon(k)} {k}" for k in filtered_opts]
        sel_label = st.radio("製品", opt_labels, horizontal=True, label_visibility="collapsed")
        selected_p = filtered_opts[opt_labels.index(sel_label)]
        active_recipe = p_recipes.get(selected_p, {}).get("成分", [])
    card_end()

    if not active_recipe: st.info("👆 製品を選択してください。（レシピ未登録の場合は「マスタ設定 → レシピ」で登録）")
    else:
        card_start()
        sec_title(f"⚖️ 希望仕込量と石灰水量　― {selected_p}")

        col_in1, col_in2 = st.columns(2)
        with col_in1:
            target_size = st.number_input("🏭 希望仕込製品量 (kg)", min_value=0.0, value=100.0, step=10.0, key="t_size", format="%.0f")
        with col_in2:
            lime_water_size = st.number_input("💧 石灰水作成量 (kg)", min_value=0.0, value=0.0, step=1.0, key="l_size", format="%.1f")

        st.markdown("<br>", unsafe_allow_html=True)
        c_op1, c_op2 = st.columns(2)
        with c_op1: operator = render_operator_selector("op_key")
        with c_op2: brew_remarks = st.text_input("📝 備考（任意）", placeholder="特記事項があれば入力", key="brew_remarks")
        card_end()

        if target_size > 0:
            st.markdown('<div class="section-title" style="margin-top:32px;">📦 準備する原料・ロット</div>', unsafe_allow_html=True)
            submitted_ingredients, water_items = [], []
            blend_errors = []
            lime_cfg = parse_lime_config(order_points, product_name=selected_p)
            lime_boost_active = is_lime_boost_active(lime_cfg, brew_date)

            for i, item in enumerate(active_recipe[:15]):
                r_name = str(item.get("原料名", "")).strip()
                base_ratio = to_float(item.get("比率", 0.0))
                is_water, is_lime, is_konjac = ("水" in r_name or "お湯" in r_name), ("石灰" in r_name or "カルシウム" in r_name), ("こんにゃく" in r_name)
                icon = "🧂" if is_lime else ("📦" if is_konjac else "🔹")

                lime_msg = ""
                if is_water:
                    calc_kg = max(0.0, target_size * (base_ratio / 100.0) - lime_water_size)
                elif is_lime:
                    eff_ratio = base_ratio
                    if lime_boost_active:
                        add_r = float(lime_cfg.get("add_ratio", 0.01))
                        eff_ratio += add_r
                        lime_msg = f"🌡️ 期間増量中 ({lime_cfg.get('start_month', 6)}月〜{lime_cfg.get('end_month', 9)}月: +{add_r}% / 理由: {lime_cfg.get('reason', '')})"
                    calc_kg = lime_water_size * (eff_ratio / 10.0)
                else: calc_kg = target_size * (base_ratio / 100.0)

                if is_water:
                    water_items.append({"原料名": r_name, "kg": round(calc_kg, 2), "配合比": base_ratio})
                    submitted_ingredients.append({"原料名": r_name, "kg": round(calc_kg, 2), "lot": "─", "水": True})
                    continue

                with st.container(border=True):
                    st.markdown(f"<div style='font-size:1.3rem; font-weight:900;'>{icon} {r_name}</div>", unsafe_allow_html=True)
                    if is_lime and lime_msg: st.markdown(f"<div style='font-size:0.9rem; color:#b45309; font-weight:800; margin-top:4px;'>{lime_msg}</div>", unsafe_allow_html=True)

                    if is_konjac:
                        blend_mode = st.radio("ブレンドモード", ["単一 (1種)", "2種ブレンド", "3種ブレンド"], key=f"kb_{selected_p}_{i}", horizontal=True, label_visibility="collapsed")
                        konjac_mats = [m for m in sorted_materials() if "こんにゃく" in m] or [r_name]

                        if blend_mode in ["2種ブレンド", "3種ブレンド"]:
                            is_3 = (blend_mode == "3種ブレンド")
                            k_a, k_b, k_c = f"kr_a_{selected_p}_{i}", f"kr_b_{selected_p}_{i}", f"kr_c_{selected_p}_{i}"
                            if k_a not in st.session_state: st.session_state[k_a] = 50.0 if not is_3 else 34.0
                            if k_b not in st.session_state: st.session_state[k_b] = 50.0 if not is_3 else 33.0
                            if k_c not in st.session_state: st.session_state[k_c] = 33.0

                            st.markdown("<div style='font-size:0.9rem; font-weight:800; color:#475569; margin:8px 0;'>🎯 ワンタッチ比率入力パネル</div>", unsafe_allow_html=True)

                            target_key = f"blend_tgt_{selected_p}_{i}"
                            if target_key not in st.session_state: st.session_state[target_key] = "🅰️"
                            st.radio("入力対象を選択", ["🅰️", "🅱️", "🅲"] if is_3 else ["🅰️", "🅱️"], horizontal=True, key=target_key, label_visibility="collapsed")

                            st.markdown("<div class='ratio-btn-container' style='margin-top:8px;'>", unsafe_allow_html=True)
                            btn_cols = st.columns(9)
                            def update_ratio(v, tgt, ka, kb, kc, is_three):
                                if tgt == "🅰️": st.session_state[ka] = float(v); st.session_state[kb] = 100.0 - float(v) if not is_three else st.session_state[kb]
                                elif tgt == "🅱️": st.session_state[kb] = float(v); st.session_state[ka] = 100.0 - float(v) if not is_three else st.session_state[ka]
                                elif tgt == "🅲" and is_three: st.session_state[kc] = float(v)

                            for pidx, pv in enumerate(range(10, 100, 10)):
                                curr_tgt = st.session_state[target_key]
                                curr_val = st.session_state.get(k_a) if curr_tgt == "🅰️" else (st.session_state.get(k_b) if curr_tgt == "🅱️" else st.session_state.get(k_c))
                                btn_cols[pidx].button(f"{pv}%", key=f"rbtn_{selected_p}_{i}_{pv}", on_click=update_ratio, args=(pv, curr_tgt, k_a, k_b, k_c, is_3), type="primary" if (curr_val == float(pv)) else "secondary", use_container_width=True)
                            st.markdown("</div>", unsafe_allow_html=True)

                            cols_ratio = st.columns(3 if is_3 else 2)
                            ratio_a = cols_ratio[0].number_input("🅰️ 比率(%)", min_value=0.0, max_value=100.0, step=1.0, key=k_a)
                            ratio_b = cols_ratio[1].number_input("🅱️ 比率(%)", min_value=0.0, max_value=100.0, step=1.0, key=k_b)
                            ratio_c = cols_ratio[2].number_input("🅲 比率(%)", min_value=0.0, max_value=100.0, step=1.0, key=k_c) if is_3 else 0.0
                            ratio_sum = ratio_a + ratio_b + ratio_c
                            if abs(ratio_sum - 100.0) > 0.01:
                                alert_box(f"❌ ブレンド比率の合計が {fmt_kg(ratio_sum)}% です（100%にしてください）", "danger")
                                blend_errors.append(f"{r_name}：ブレンド比率の合計が{fmt_kg(ratio_sum)}%")
                            else:
                                st.caption(f"✅ 比率合計 100%（{fmt_kg(ratio_a)} / {fmt_kg(ratio_b)}{' / ' + fmt_kg(ratio_c) if is_3 else ''}）")

                            mat_a = st.radio("🅰️ 原料種別", konjac_mats, key=f"kma_{selected_p}_{i}", horizontal=True, label_visibility="collapsed")
                            act_a, lot_a = _ing_row("🅰️ 投入量", calc_kg * ratio_a / 100.0, f"adj_a_{selected_p}_{i}", mat_a, f"lot_a_{selected_p}_{i}_{mat_a}")
                            st.markdown("<hr style='margin:16px 0; border-top:1px dashed #cbd5e1;'>", unsafe_allow_html=True)

                            mat_b = st.radio("🅱️ 原料種別", konjac_mats, index=1 if len(konjac_mats) > 1 else 0, key=f"kmb_{selected_p}_{i}", horizontal=True, label_visibility="collapsed")
                            act_b, lot_b = _ing_row("🅱️ 投入量", calc_kg * ratio_b / 100.0, f"adj_b_{selected_p}_{i}", mat_b, f"lot_b_{selected_p}_{i}_{mat_b}")

                            submitted_ingredients.extend([{"原料名": mat_a, "kg": act_a, "lot": f"{lot_a}({fmt_kg(ratio_a)}%)" if lot_a != "─" else "─"},
                                                          {"原料名": mat_b, "kg": act_b, "lot": f"{lot_b}({fmt_kg(ratio_b)}%)" if lot_b != "─" else "─"}])

                            if is_3:
                                st.markdown("<hr style='margin:16px 0; border-top:1px dashed #cbd5e1;'>", unsafe_allow_html=True)
                                mat_c = st.radio("🅲 原料種別", konjac_mats, index=2 if len(konjac_mats) > 2 else 0, key=f"kmc_{selected_p}_{i}", horizontal=True, label_visibility="collapsed")
                                act_c, lot_c = _ing_row("🅲 投入量", calc_kg * ratio_c / 100.0, f"adj_c_{selected_p}_{i}", mat_c, f"lot_c_{selected_p}_{i}_{mat_c}")
                                submitted_ingredients.append({"原料名": mat_c, "kg": act_c, "lot": f"{lot_c}({fmt_kg(ratio_c)}%)" if lot_c != "─" else "─"})
                        else:
                            act_kg, final_lot = _ing_row(f"投入量（配合比 {fmt_kg(base_ratio)}%）", calc_kg, f"adj_{selected_p}_{i}", r_name, f"lot_{selected_p}_{i}")
                            submitted_ingredients.append({"原料名": r_name, "kg": act_kg, "lot": final_lot})
                    else:
                        act_kg, final_lot = _ing_row(f"投入量（配合比 {fmt_kg(base_ratio)}%）", calc_kg, f"adj_{selected_p}_{i}", r_name, f"lot_{selected_p}_{i}")
                        submitted_ingredients.append({"原料名": r_name, "kg": act_kg, "lot": final_lot})

            if seasoning_recipes_all:
                st.markdown('<div class="section-title" style="margin-top:32px;">🌶️ 調味料の希釈計算・投入記録</div>', unsafe_allow_html=True)
                for sr_idx, sr in enumerate(seasoning_recipes_all):
                    sr_items = safe_parse_seasoning_recipe(sr.get("配合JSON"))
                    if not sr_items: continue
                    with st.container(border=True):
                        if st.checkbox(f"🌶️ {sr.get('品名')} を使用する", key=f"use_season_{selected_p}_{sr_idx}"):
                            target_vol_key = f"season_vol_{selected_p}_{sr_idx}"
                            target_vol = st.number_input("希釈対象量（できあがり量・kg）", min_value=0.0, value=st.session_state.get(target_vol_key, 0.0), step=0.1, key=target_vol_key)
                            for si, sitem in enumerate(sr_items):
                                s_mat, s_dil = sitem["原料名"], to_float(sitem["希釈倍率"])
                                need_kg = target_vol / s_dil if s_dil > 0 else 0.0
                                s_act_kg, s_lot = _ing_row(f"投入量（{s_mat}）", need_kg, f"adj_season_{selected_p}_{sr_idx}_{si}", s_mat, f"lot_season_{selected_p}_{sr_idx}_{si}")
                                submitted_ingredients.append({"原料名": s_mat, "kg": s_act_kg, "lot": s_lot})

            # ── 保存前チェック ─────────────────────────────────────
            errors, warns = list(blend_errors), []
            if operator == "未登録": errors.append("担当者が未登録です（マスタ設定 → 担当者）")
            agg_use = {}
            for ing in submitted_ingredients:
                if ing.get("水") or ing["kg"] <= 0: continue
                lots = split_lots(ing["lot"])
                if not lots:
                    warns.append(f"ロット未指定：{ing['原料名']}（トレースできなくなります）")
                    continue
                for l in lots:
                    agg_use[(ing["原料名"], l)] = agg_use.get((ing["原料名"], l), 0.0) + ing["kg"] / len(lots)
            for (mname, l), kg_need in agg_use.items():
                known = any(v["原料種別"] == mname and v["ロットNo"] == l for v in inventory_data.values())
                _, skg = lot_stock(mname, l)
                if not known: warns.append(f"入荷登録のないロット：{mname} / {l}（在庫は引かれません）")
                elif kg_need > skg + 0.01: warns.append(f"在庫不足：{mname} / {l}（残{fmt_kg(round(skg, 2))}kg ＜ 投入{fmt_kg(round(kg_need, 2))}kg）")

            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("📋 投入内容の最終確認（保存前にご確認ください）", expanded=True):
                prev = []
                for ing in submitted_ingredients:
                    lots = split_lots(ing["lot"])
                    stock_txt = "─"
                    if lots and not ing.get("水"):
                        stock_txt = " / ".join(f"{fmt_kg(round(lot_stock(ing['原料名'], l)[1], 2))}kg" for l in lots)
                    prev.append({"原料": ing["原料名"], "投入量(kg)": fmt_kg(ing["kg"]), "ロット": ing["lot"], "ロット現在庫": stock_txt})
                st.dataframe(pd.DataFrame(prev), use_container_width=True, hide_index=True)

            total_in = sum(ing["kg"] for ing in submitted_ingredients)
            st.markdown(f"""
            <div style="background-color: var(--c-primary-soft); border: 2px solid var(--c-primary); border-radius: 12px; padding: 16px; margin-bottom: 16px; text-align: center;">
                <div style="font-weight: 800; color: var(--c-muted); font-size: 1.1rem;">💡 合計投入予定量（全原料・水を含む）</div>
                <div style="font-size: 2.2rem; font-weight: 900; color: var(--c-secondary);">{fmt_kg(round(total_in, 2))} <span style="font-size:1.2rem; color:var(--c-muted);">kg</span></div>
            </div>
            """, unsafe_allow_html=True)

            for e_msg in errors: alert_box(f"❌ {e_msg}", "danger")
            ack_ok = True
            if warns:
                alert_box("⚠️ 保存前の確認事項<br>" + "<br>".join(f"・{w}" for w in warns), "warn")
                ack_ok = st.checkbox("上記を確認した上で保存する", key="brew_ack_warn")

            if st.button("💾 この内容で製造記録を保存する", type="primary", use_container_width=True, disabled=bool(errors) or not ack_ok):
                k_kg = s_kg = st_kg = lime_kg = 0.0
                k_lot = s_lot = st_lot = "─"
                for ing in submitted_ingredients:
                    n, amt, lot = ing["原料名"], ing["kg"], ing["lot"]
                    if "こんにゃく" in n: k_kg += amt; k_lot = lot if k_lot == "─" else (k_lot if lot in k_lot else f"{k_lot} / {lot}")
                    elif "海藻" in n: s_kg += amt; s_lot = lot if s_lot == "─" else (s_lot if lot in s_lot else f"{s_lot} / {lot}")
                    elif "デンプン" in n or "でんぷん" in n: st_kg += amt; st_lot = lot if st_lot == "─" else (st_lot if lot in st_lot else f"{st_lot} / {lot}")
                    elif "石灰" in n or "カルシウム" in n: lime_kg += amt

                if not hasattr(sheets, "append_brewing"):
                    st.error("sheets.append_brewing が見つからないため保存できません。")
                    st.stop()

                next_no = next_brewing_no_fresh()
                text_ing = ", ".join([f"{ing['原料名']}:{round(ing['kg'], 3)}kg({ing['lot']})" for ing in submitted_ingredients])

                sheets.append_brewing({
                    "仕込No": next_no, "仕込日": str(brew_date), "品名": selected_p,
                    "メーカー": operator, "主原料ロット": k_lot, "仕込量(kg)": round(target_size, 2),
                    "こんにゃく精粉(kg)": round(k_kg, 2), "海藻粉(kg)": round(s_kg, 2), "海藻粉ロット": s_lot,
                    "デンプン(kg)": round(st_kg, 2), "デンプンロット": st_lot, "デンプン種別": "-",
                    "石灰(kg)": round(lime_kg, 2), "石灰水(L)": round(lime_water_size, 2),
                    "その他添加物": text_ing, "備考": f"{brew_remarks}", "登録日時": now_jst().isoformat()
                })

                for key in list(st.session_state.keys()):
                    if any(key.startswith(p) for p in ["adj_", "last_calc_", "lot_", "btn_", "kb_", "kr_", "km", "blend_tgt_", "use_season_", "season_vol_", "rbtn_", "brew_ack", "brew_remarks"]):
                        del st.session_state[key]

                done(f"✅ 製造記録を登録しました（仕込No. {next_no} ／ {selected_p} {fmt_kg(target_size)}kg ／ 担当 {operator}）")

    # ── 本日の製造記録（登録できたかをその場で確認） ──────────────
    card_start()
    sec_title(f"📅 本日の製造記録（{today_jst()}）")
    if brewing:
        df_today = pd.DataFrame(brewing)
        df_today = df_today[in_period(df_today.get("仕込日", pd.Series(dtype=str)), today_jst(), today_jst())] if "仕込日" in df_today.columns else df_today.iloc[0:0]
        if df_today.empty:
            st.caption("本日の製造記録はまだありません。")
        else:
            v_today = brewing_view_df(df_today)
            c_m1, c_m2 = st.columns(2)
            c_m1.metric("本日の製造件数", f"{len(v_today)} 件")
            c_m2.metric("本日の製造量", f"{fmt_kg(round(v_today['仕込量(kg)'].sum(), 2))} kg")
            v_today = v_today.sort_values("登録日時", ascending=False)
            st.dataframe(fmt_df_numeric(v_today[["仕込No", "品名", "担当者", "仕込量(kg)", "原料内訳（全原料の投入量）", "備考"]], ["仕込量(kg)"]), use_container_width=True, hide_index=True)
    else:
        st.caption("製造記録はまだありません。")
    card_end()


# ═══════════════════════════════════════════════════════════════
#  📊 ダッシュボード
# ═══════════════════════════════════════════════════════════════
elif page == "📊 ダッシュボード":
    page_header("📊 サマリーと在庫モニター", f"{today_jst():%Y年%m月%d日}（日本時間）")
    df_brw_global = pd.DataFrame(brewing)
    today_total_kg = today_count = 0
    if not df_brw_global.empty and "仕込日" in df_brw_global.columns:
        df_brw_today = df_brw_global[in_period(df_brw_global["仕込日"], today_jst(), today_jst())]
        today_total_kg = pd.to_numeric(df_brw_today.get("仕込量(kg)", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
        today_count = len(df_brw_today)

    low_m, low_s = low_stock_materials(), low_stock_supplies()
    po_pending, po_overdue_list = pending_orders_list(), overdue_orders_list()
    neg_lots = negative_stock_lots()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📦 本日の総製造量", f"{fmt_kg(today_total_kg)} kg", f"{today_count} 件製造")
    c2.metric("⚠️ 在庫不足原料", f"{len(low_m)} 品目")
    c3.metric("📝 未入荷の発注", f"{len(po_pending)} 件", f"うち超過 {len(po_overdue_list)} 件" if po_overdue_list else None, delta_color="inverse")
    c4.metric("🧹 要発注の資材", f"{len(low_s)} 品目")

    nav = st.columns(4)
    nav[0].button("🏭 製造仕込みへ", on_click=_goto, args=("🏭 製造仕込み",), use_container_width=True, key="nav_brew")
    nav[1].button("📥 入荷登録へ", on_click=_goto, args=("📥 入荷登録",), use_container_width=True, key="nav_arr")
    nav[2].button("📦 在庫・棚卸へ", on_click=_goto, args=("📦 在庫・棚卸",), use_container_width=True, key="nav_inv")
    nav[3].button("📋 履歴・帳票へ", on_click=_goto, args=("📋 履歴・帳票",), use_container_width=True, key="nav_hist")

    # ── 要対応アラート ─────────────────────────────────────
    if low_m or low_s or po_overdue_list or neg_lots:
        sec_title("🚨 要対応")
        if low_m: alert_box("⚠️ 発注点以下の原料：" + "、".join(f"{m}（{fmt_kg(round(c, 1))}袋 / 発注点{fmt_kg(p)}袋）" for m, c, p in low_m), "danger")
        if low_s: alert_box("🧹 発注点以下の資材：" + "、".join(f"{n}（{fmt_kg(c)} / 発注点{fmt_kg(p)}）" for n, c, p in low_s), "warn")
        if po_overdue_list: alert_box("⏰ 納品予定日を過ぎた発注：" + "、".join(f"{o.get('原料名')}（予定{o.get('納品予定日')}）" for o in po_overdue_list), "danger")
        if neg_lots: alert_box("❓ 入荷量より使用量が多いロット（入荷登録漏れ・ロット誤入力の疑い）：" + "、".join(f"{v['原料種別']}/{v['ロットNo']}" for v in neg_lots), "warn")
    else:
        alert_box("✅ 現在、対応が必要なアラートはありません。", "ok")

    # ── 本日の製造 ─────────────────────────────────────────
    if today_count:
        with st.expander(f"📅 本日の製造記録（{today_count}件）", expanded=False):
            v_t = brewing_view_df(df_brw_today).sort_values("登録日時", ascending=False)
            st.dataframe(fmt_df_numeric(v_t[["仕込No", "品名", "担当者", "仕込量(kg)", "原料内訳（全原料の投入量）"]], ["仕込量(kg)"]), use_container_width=True, hide_index=True)

    st.markdown("---")
    sec_title("📦 主要原料 現在庫とアラート")
    st.caption("※ 棚卸し等の在庫調整は各カードの「棚卸修正」または「📦 在庫・棚卸」ページから行えます。")
    mat_list = sorted_materials()
    cols = st.columns(min(3, len(mat_list) if mat_list else 1))

    def _dash_adj(ano, delta_bags, reason_text, op_name):
        if not hasattr(sheets, "append_adjustment"):
            st.error("sheets.append_adjustment が見つかりません。"); st.stop()
        sheets.append_adjustment({
            "調整ID": f"ADJ-{now_jst().strftime('%Y%m%d%H%M%S%f')}", "入荷No": ano,
            "調整日": str(today_jst()), "調整袋数": delta_bags, "理由": reason_text,
            "担当者": op_name, "登録日時": now_jst().isoformat()
        })

    for idx, m in enumerate(mat_list):
        pt, wt = parse_op_data(order_points.get(m, 0.0))
        curr_kg = type_totals_kg.get(m, 0.0)
        curr_bag = curr_kg / wt if wt > 0 else 0
        is_alert = (pt > 0 and curr_bag < pt)
        bg_col, b_col = ("#fef2f2", "#ef4444") if is_alert else ("#ffffff", "#cbd5e1")
        alert_msg = f"<div style='font-size:0.9rem; color:#ef4444; font-weight:bold; margin-top:8px;'>⚠️ 発注点({fmt_kg(pt)}袋) 以下</div>" if is_alert else f"<div style='font-size:0.9rem; color:#64748b; font-weight:bold; margin-top:8px;'>✅ 発注点: {fmt_kg(pt)}袋</div>"

        img_b64 = get_material_image(order_points, m)
        img_html = f'<img src="{img_b64}" style="width:50px; height:50px; object-fit:cover; border-radius:6px; margin-right:12px; border:1px solid #e2e8f0;">' if img_b64 else f'<div style="width:50px; height:50px; background:#e2e8f0; border-radius:6px; margin-right:12px; display:flex; align-items:center; justify-content:center; font-size:20px;">🥦</div>'

        with cols[idx % 3]:
            st.markdown(f"""
            <div style="background:{bg_col}; border:2px solid {b_col}; border-radius:12px; padding:18px; margin-bottom:8px;">
                <div style="display:flex; align-items:center; margin-bottom:8px;">
                    {img_html}
                    <div style="font-weight:900; color:#0f172a; font-size:1.15rem;">{m}</div>
                </div>
                <div class="mat-card-value" style="font-size:2.2rem; font-weight:900; color:#0f766e; margin:6px 0 2px 0;">
                    {fmt_kg(round(curr_kg, 2))}<span style="font-size:1.1rem; color:#64748b; margin-right:8px;">kg</span>
                    <span style="font-size:1.6rem; color:#0f172a;">({fmt_kg(round(curr_bag, 2))}袋)</span>
                </div>
                <div style="font-size:0.85rem; color:#64748b; margin-bottom:4px;">1袋 = {fmt_kg(wt)} kg 換算</div>
                {alert_msg}
            </div>
            """, unsafe_allow_html=True)

            mat_lots = get_lots_for_material(m)
            with st.popover(f"🔧 {m} の在庫を棚卸修正", use_container_width=True):
                if not mat_lots: st.info("この原料の入荷記録がありません。")
                else:
                    lot_opts = {f"{v['ロットNo']} (現在庫:{fmt_kg(round(v['現在庫(袋)'], 2))}袋)": v["入荷No"] for v in mat_lots}
                    sel_lot = st.selectbox("対象ロット", list(lot_opts.keys()), key=f"dash_lot_{m}")
                    target_ano = lot_opts[sel_lot]
                    target_lot_data = next(v for v in mat_lots if v["入荷No"] == target_ano)
                    op_q = render_operator_selector(f"dash_qop_{m}")

                    st.caption("実際に数えた袋数を入力してください。")
                    actual = st.number_input("実在庫数量(袋)", min_value=0.0, value=float(round(target_lot_data["現在庫(袋)"], 2)), step=1.0, key=f"dash_act_{m}_{target_ano}")
                    if actual < EPS_BAGS: actual = 0.0
                    diff = round(actual - target_lot_data["現在庫(袋)"], 4)
                    if abs(diff) > 0.005: st.caption(f"差分: {diff:+g} 袋")
                    if st.button("💾 この実地数量で確定", type="primary", key=f"dash_save_{m}", use_container_width=True, disabled=abs(diff) < 0.005):
                        _dash_adj(target_ano, diff, f"【実地棚卸で {fmt_kg(actual)}袋 に更新】", op_q)
                        done(f"{m}（{target_lot_data['ロットNo']}）を {fmt_kg(actual)}袋 で確定しました")

            if is_konjac_material(m) and mat_lots:
                breakdown = {}
                for v in mat_lots:
                    breakdown.setdefault((v["メーカー"], v["グレード"]), {"kg": 0.0, "bag": 0.0})
                    breakdown[(v["メーカー"], v["グレード"])]["kg"] += v["現在庫(kg)"]
                    breakdown[(v["メーカー"], v["グレード"])]["bag"] += v["現在庫(袋)"]
                with st.expander(f"🏷️ {m} のメーカー・グレード別内訳"):
                    for (mk, gr), vals in sorted(breakdown.items()):
                        if vals["kg"] > 0.01:
                            st.markdown(f'<div style="display:flex; justify-content:space-between; align-items:center; padding:8px 10px; border-bottom:1px solid #e2e8f0;"><div style="font-weight:800; font-size:0.85rem;">🏢 {mk} / 🏷️ {gr}</div><div style="font-weight:900; color:#0f766e;">{fmt_kg(round(vals["kg"], 2))} kg（{fmt_kg(round(vals["bag"], 2))}袋）</div></div>', unsafe_allow_html=True)
            st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  📝 発注管理
# ═══════════════════════════════════════════════════════════════
elif page == "📝 発注管理":
    page_header("📝 原料・資材 発注管理", "納品予定日を過ぎた発注は赤字で表示されます。")
    all_orders = parse_purchase_orders(order_points)
    pending_orders = [o for o in all_orders if o.get("ステータス") not in ("入荷済み", "取消")]
    done_orders = [o for o in all_orders if o.get("ステータス") == "入荷済み"]
    cancelled_orders = [o for o in all_orders if o.get("ステータス") == "取消"]

    def _update_order(oid, **upd):
        orders = fresh_purchase_orders()
        for oo in orders:
            if oo.get("発注ID") == oid: oo.update(upd)
        save_purchase_orders(order_points, orders)

    t_new, t_list = st.tabs(["➕ 新規発注登録", f"📋 発注一覧・入荷処理（未入荷 {len(pending_orders)}件）"])
    with t_new:
        card_start()
        order_category = st.radio("🏷️ 発注区分", ["🥦 原材料", "🧻 衛生資材・消耗品"], horizontal=True)
        is_raw_mat = "原材料" in order_category
        item_opts = sorted_materials() if is_raw_mat else [s.get("資材名") for s in sorted_supplies() if s.get("資材名")]
        with st.form("new_order_form"):
            o_mat = st.selectbox("発注品目", item_opts if item_opts else ["未登録"])
            o_maker = st.selectbox("メーカー/発注先", makers if makers else ["未登録"])
            c_a, c_b = st.columns(2)
            o_date = c_a.date_input("発注日", value=today_jst())
            o_due = c_b.date_input("納品予定日", value=today_jst() + timedelta(days=7))
            o_qty = st.number_input("発注個数 (袋/箱など)", min_value=1, value=10, step=1)
            o_note = st.text_input("備考（任意）")
            if st.form_submit_button("💾 発注を登録する", type="primary", use_container_width=True):
                if not item_opts: st.error("発注品目が登録されていません。マスタ設定で登録してください。")
                elif o_due < o_date: st.error("納品予定日が発注日より前になっています。")
                else:
                    orders = fresh_purchase_orders()
                    orders.append({
                        "発注ID": f"PO-{now_jst().strftime('%Y%m%d%H%M%S%f')}", "発注区分": "原材料" if is_raw_mat else "衛生資材",
                        "発注日": str(o_date), "原料名": o_mat, "メーカー": o_maker, "個数": o_qty, "納品予定日": str(o_due), "ステータス": "未入荷",
                        "紐づく入荷No": "", "備考": o_note, "登録日時": now_jst().isoformat()
                    })
                    save_purchase_orders(order_points, orders)
                    done(f"発注を登録しました（{o_mat} × {o_qty}）")
        card_end()

    with t_list:
        if not pending_orders:
            st.info("未入荷の発注はありません。")
        today_s = str(today_jst())
        for o in sorted(pending_orders, key=lambda x: str(x.get("納品予定日", ""))):
            is_raw_order = (o.get("発注区分", "原材料") == "原材料")
            due = str(o.get("納品予定日", ""))
            is_over = bool(due) and due < today_s
            with st.container(border=True):
                c_i, c_b, c_x = st.columns([4, 1.3, 1])
                with c_i:
                    st.markdown(f"**{'🥦' if is_raw_order else '🧻'} {o.get('原料名')}**　🏢 {o.get('メーカー')}　📦 {fmt_kg(o.get('個数'))}")
                    due_html = f"<span style='color:#b91c1c; font-weight:800;'>⏰ 納品予定日: {due}（超過）</span>" if is_over else f"納品予定日: {due}"
                    st.markdown(f"<div style='font-size:0.85rem; color:#64748b;'>発注日: {o.get('発注日')} ／ {due_html}{' ／ 備考: ' + str(o.get('備考')) if o.get('備考') else ''}</div>", unsafe_allow_html=True)
                with c_b:
                    with st.popover("✅ 入荷処理", use_container_width=True):
                        oid = o.get("発注ID")
                        st.markdown(f"#### ✅ {o.get('原料名')} の入荷")
                        ord_qty = max(1, int(to_float(o.get("個数"), 1)))
                        if is_raw_order:
                            arr_lot = st.text_input("ロットNo ＊必須", key=f"po_lot_{oid}")
                            grade_list = parse_grade_list(order_points)
                            po_grade = st.selectbox("🏷️ グレード", grade_list, key=f"po_grade_{oid}") if is_konjac_material(o.get("原料名")) and grade_list else "-"
                            _, po_default_wt = parse_op_data(order_points.get(o.get("原料名"), 0))
                            pc1, pc2 = st.columns(2)
                            po_bags = pc1.number_input("入荷袋数", min_value=1, value=ord_qty, step=1, key=f"po_bags_{oid}")
                            po_wpb = pc2.number_input("1袋重量(kg)", min_value=0.1, value=float(max(po_default_wt, 1)), step=1.0, key=f"po_wpb_{oid}")

                            st.markdown("**🔍 受入品質検査**")
                            po_chk = {k: st.radio(v, ["未確認", "✅ 正常", "❌ 異常あり"], horizontal=True, key=f"po_chk_{oid}_{k}") for k, v in [("外観", "📦 外観"), ("品名", "🏷️ 品名"), ("賞味期限", "📅 賞味期限"), ("異物", "🔍 異物")]}
                            po_op = render_operator_selector(f"po_op_{oid}")
                            if st.button("💾 入荷を登録", type="primary", use_container_width=True, key=f"po_save_{oid}"):
                                lot_clean = sanitize_lot(arr_lot)
                                if not lot_clean: st.error("ロットNoは必須です")
                                elif any(v == "未確認" for v in po_chk.values()): st.error("検査が未完了です")
                                elif not hasattr(sheets, "append_arrival"): st.error("sheets.append_arrival が見つかりません。")
                                else:
                                    new_ano = next_arrival_no_fresh()
                                    sheets.append_arrival({
                                        "入荷No": new_ano, "入荷日": str(today_jst()), "メーカー": o.get("メーカー"), "ロットNo": lot_clean,
                                        "原料種別": o.get("原料名"), "グレード": po_grade, "袋数": po_bags, "1袋重量(kg)": po_wpb, "総量(kg)": po_bags * po_wpb,
                                        "外観": po_chk["外観"], "品名・規格確認": po_chk["品名"], "賞味期限": po_chk["賞味期限"], "異物": po_chk["異物"],
                                        "担当者": po_op, "備考": f"発注ID:{oid}", "登録日時": now_jst().isoformat()
                                    })
                                    _update_order(oid, **{"ステータス": "入荷済み", "紐づく入荷No": new_ano, "入荷処理日": str(today_jst())})
                                    done(f"入荷しました（入荷No. {new_ano} ／ {o.get('原料名')} {po_bags}袋）")
                        else:
                            po_bags = st.number_input("入荷個数", min_value=1, value=ord_qty, step=1, key=f"po_bags_sup_{oid}")
                            po_op = render_operator_selector(f"po_op_sup_{oid}")
                            if st.button("💾 資材在庫に追加", type="primary", use_container_width=True, key=f"po_save_sup_{oid}"):
                                sid = next((s.get("資材ID") for s in supplies if s.get("資材名") == o.get("原料名")), None)
                                if not sid: st.error("資材マスタに該当資材が見つかりません。")
                                elif not hasattr(sheets, "append_supply_log"): st.error("sheets.append_supply_log が見つかりません。")
                                else:
                                    sheets.append_supply_log({
                                        "ログID": f"LOG-{now_jst().strftime('%Y%m%d%H%M%S%f')}", "登録日": str(today_jst()), "資材ID": sid,
                                        "処理": "入荷", "数量": po_bags, "作業者": po_op, "備考": f"発注:{oid}", "登録日時": now_jst().isoformat()
                                    })
                                    _update_order(oid, **{"ステータス": "入荷済み", "紐づく入荷No": "資材入荷", "入荷処理日": str(today_jst())})
                                    done(f"資材を入荷しました（{o.get('原料名')} × {po_bags}）")
                with c_x:
                    with st.popover("🗑️ 取消", use_container_width=True):
                        st.warning("この発注を取り消します（履歴には「取消」として残ります）。")
                        if st.button("取り消す", key=f"po_cancel_{o.get('発注ID')}", type="primary", use_container_width=True):
                            _update_order(o.get("発注ID"), **{"ステータス": "取消", "入荷処理日": str(today_jst())})
                            done("発注を取り消しました。", "warn")

        if done_orders:
            sec_title("✅ 入荷済みの発注（履歴）")
            df_done = pd.DataFrame(sorted(done_orders, key=lambda x: str(x.get("入荷処理日", "")), reverse=True))
            st.dataframe(fmt_df_numeric(df_done[[c for c in ["発注区分", "発注日", "原料名", "メーカー", "個数", "入荷処理日", "紐づく入荷No"] if c in df_done.columns]].head(50), ["個数"]), use_container_width=True, hide_index=True)
        if cancelled_orders:
            with st.expander(f"🗑️ 取消した発注（{len(cancelled_orders)}件）"):
                df_c = pd.DataFrame(cancelled_orders)
                st.dataframe(df_c[[c for c in ["発注区分", "発注日", "原料名", "メーカー", "個数", "入荷処理日"] if c in df_c.columns]], use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════
#  📥 入荷登録
# ═══════════════════════════════════════════════════════════════
elif page == "📥 入荷登録":
    page_header("📥 原料入荷品質記録", "ロットNoと受入検査（外観・品名・賞味期限・異物）を記録します。")
    def _save_arrivals_recalc(records):
        for r in records:
            try: r["総量(kg)"] = to_float(r.get("袋数", 0)) * to_float(r.get("1袋重量(kg)", 0))
            except Exception: pass
        if hasattr(sheets, "save_arrivals"): sheets.save_arrivals(records)
        else: st.error("sheets.save_arrivals が見つかりません。"); st.stop()

    CHK_ITEMS = [("外観", "📦 外観"), ("品名・規格確認", "🏷️ 品名・規格"), ("賞味期限", "📅 賞味期限"), ("異物", "🔍 異物混入")]
    def _all_ok():
        for k_n, _ in CHK_ITEMS: st.session_state[f"chk_{k_n}"] = "✅ 正常"

    t_in, t_hist = st.tabs(["➕ 新規入荷登録", "📋 入荷履歴・編集"])
    with t_in:
        card_start()
        arr_date = st.date_input("入荷日", value=today_jst())
        maker_sel = st.selectbox("メーカー", makers if makers else ["未登録"])
        lot_val = st.text_input("ロットNo ＊必須", placeholder="例: L12345", key="arr_lot_val")

        m_type = st.selectbox("原料種別", sorted_materials() if sorted_materials() else ["未登録"])
        _, default_wt = parse_op_data(order_points.get(m_type, 0))
        grade_list_a = parse_grade_list(order_points)
        grade_val = st.selectbox("🏷️ グレード", grade_list_a) if is_konjac_material(m_type) and grade_list_a else "-"

        c1, c2 = st.columns(2)
        bags_qty = c1.number_input("入荷袋数", min_value=1, value=10, step=1)
        weight_per_bag = c2.number_input("1袋重量 (kg) ※自動セット済", min_value=0.1, value=float(max(default_wt, 1)), step=1.0, key=f"arr_wpb_{m_type}")
        st.caption(f"総量: {fmt_kg(bags_qty * weight_per_bag)} kg")

        sec_title("🔍 受入品質検査")
        st.button("✅ 4項目すべて「正常」にする（問題がない場合）", on_click=_all_ok, use_container_width=True, key="arr_all_ok")
        chk_results = {}
        cols_chk = st.columns(2)
        for idx, (k_n, lbl) in enumerate(CHK_ITEMS):
            with cols_chk[idx % 2]:
                with st.container(border=True):
                    st.markdown(f"**{lbl}**")
                    chk_results[k_n] = st.radio(lbl, ["未確認", "✅ 正常", "❌ 異常あり"], index=0, key=f"chk_{k_n}", horizontal=True, label_visibility="collapsed")

        chk_note = st.text_input("備考（異常ありの場合は内容を必ず記入）", key="arr_note")
        operator = render_operator_selector("arr_op")

        lot_clean = sanitize_lot(lot_val)
        dup = [v for v in inventory_data.values() if lot_clean and v["原料種別"] == m_type and v["ロットNo"] == lot_clean]
        dup_ok = True
        if dup:
            alert_box(f"⚠️ 同じ原料・同じロットNoが既に登録されています（入荷No. {', '.join(d['入荷No'] for d in dup)}）。二重登録でないか確認してください。", "warn")
            dup_ok = st.checkbox("別便の入荷として登録する", key="arr_dup_ok")
        has_abnormal = any(v == "❌ 異常あり" for v in chk_results.values())
        if has_abnormal: alert_box("❌ 異常ありの項目があります。備考に状況と対応（返品・隔離など）を記入してください。", "danger")

        if st.button("💾 入荷記録を登録する", type="primary", use_container_width=True, disabled=not dup_ok):
            if not lot_clean: st.error("ロットNoは必須項目です。")
            elif any(v == "未確認" for v in chk_results.values()): st.error("受入品質検査が未完了です。")
            elif has_abnormal and not chk_note.strip(): st.error("異常ありの場合は備考の記入が必須です。")
            elif m_type == "未登録": st.error("原料マスタが未登録です。")
            elif not hasattr(sheets, "append_arrival"): st.error("sheets.append_arrival が見つかりません。")
            else:
                new_no = next_arrival_no_fresh()
                sheets.append_arrival({
                    "入荷No": new_no, "入荷日": str(arr_date), "メーカー": maker_sel, "ロットNo": lot_clean,
                    "原料種別": m_type, "グレード": grade_val, "袋数": bags_qty, "1袋重量(kg)": weight_per_bag, "総量(kg)": bags_qty * weight_per_bag,
                    "外観": chk_results["外観"], "品名・規格確認": chk_results["品名・規格確認"], "賞味期限": chk_results["賞味期限"], "異物": chk_results["異物"],
                    "担当者": operator, "備考": chk_note, "登録日時": now_jst().isoformat()
                })
                for k in ["arr_lot_val", "arr_note", "arr_dup_ok"] + [f"chk_{k_n}" for k_n, _ in CHK_ITEMS]:
                    st.session_state.pop(k, None)
                done(f"入荷記録を保存しました（入荷No. {new_no} ／ {m_type} ／ ロット {lot_clean} ／ {bags_qty}袋）")
        card_end()

        if arrivals:
            card_start()
            sec_title("🕒 直近の入荷登録（登録できたか確認）")
            df_recent = pd.DataFrame(arrivals)
            df_recent = ensure_cols(df_recent, ["入荷No", "入荷日", "原料種別", "ロットNo", "袋数", "メーカー", "担当者", "登録日時"])
            df_recent = df_recent.sort_values(["登録日時", "入荷No"], ascending=False).head(5)
            st.dataframe(df_recent[["入荷No", "入荷日", "原料種別", "ロットNo", "袋数", "メーカー", "担当者"]], use_container_width=True, hide_index=True)
            card_end()

    with t_hist:
        if not arrivals:
            st.info("入荷記録がありません。")
        else:
            card_start()
            sec_title("🔎 入荷履歴の検索")
            df_arr_all = ensure_cols(pd.DataFrame(arrivals), ["入荷No", "入荷日", "原料種別", "メーカー", "ロットNo", "グレード", "袋数", "1袋重量(kg)", "総量(kg)", "外観", "品名・規格確認", "賞味期限", "異物", "担当者", "備考", "登録日時"])
            s_a, e_a = period_picker("arr_hist", default="直近30日")
            f1, f2, f3 = st.columns([2, 2, 1])
            mat_sel = f1.multiselect("原料", sorted(df_arr_all["原料種別"].astype(str).unique()), key="arr_hist_mat")
            kw_a = f2.text_input("キーワード（ロット・メーカー・備考）", key="arr_hist_kw")
            only_ab = f3.checkbox("異常ありのみ", key="arr_hist_ab")
            m = in_period(df_arr_all["入荷日"], s_a, e_a) & keyword_mask(df_arr_all, ["ロットNo", "メーカー", "備考", "入荷No"], kw_a)
            if mat_sel: m &= df_arr_all["原料種別"].isin(mat_sel)
            chk_cols = ["外観", "品名・規格確認", "賞味期限", "異物"]
            df_arr_all["検査判定"] = df_arr_all[chk_cols].apply(lambda r: "⚠️ 異常あり" if any("異常" in str(x) for x in r) else ("未確認あり" if any("未確認" in str(x) or str(x) == "" for x in r) else "✅ 正常"), axis=1)
            if only_ab: m &= (df_arr_all["検査判定"] == "⚠️ 異常あり")
            df_arr = df_arr_all[m].sort_values(["入荷日", "入荷No"], ascending=False).reset_index(drop=True)
            c_k1, c_k2, c_k3 = st.columns(3)
            c_k1.metric("入荷件数", f"{len(df_arr)} 件")
            c_k2.metric("入荷総量", f"{fmt_kg(round(df_arr['総量(kg)'].apply(to_float).sum(), 1))} kg")
            c_k3.metric("検査 異常あり", f"{int((df_arr['検査判定'] == '⚠️ 異常あり').sum())} 件")
            show_cols = ["入荷日", "入荷No", "原料種別", "グレード", "メーカー", "ロットNo", "袋数", "1袋重量(kg)", "総量(kg)", "検査判定", "外観", "品名・規格確認", "賞味期限", "異物", "担当者", "備考"]
            st.dataframe(fmt_df_numeric(df_arr[show_cols], ["袋数", "1袋重量(kg)", "総量(kg)"]), use_container_width=True, hide_index=True)
            if not df_arr.empty: download_buttons({"入荷記録": df_arr[show_cols]}, f"入荷記録_{today_jst()}", "arr_dl")
            card_end()

            with st.expander("✏️ 入荷記録の修正・削除（Excel風・管理者向け）"):
                arr_editable_cols = [c for c in ["入荷日", "原料種別", "メーカー", "ロットNo", "袋数", "1袋重量(kg)", "備考"] if c in df_arr.columns]
                if "グレード" in df_arr.columns: arr_editable_cols.insert(2, "グレード")
                render_excel_history_editor(full_records=arrivals, filtered_df=df_arr.head(200), id_col="入荷No", editable_cols=arr_editable_cols, numeric_cols=["袋数", "1袋重量(kg)"], save_func=_save_arrivals_recalc, key_prefix="arr_hist", reload_func=sheets.load_arrivals)


# ═══════════════════════════════════════════════════════════════
#  📦 在庫・棚卸
# ═══════════════════════════════════════════════════════════════
elif page == "📦 在庫・棚卸":
    page_header("📦 在庫・棚卸管理", "ロット別の現在庫を確認し、実数に合わせて調整できます。調整はすべて履歴に残ります。")
    neg = negative_stock_lots()
    if neg:
        alert_box("❓ 入荷量より使用量が多いロットがあります（入荷登録漏れ・ロット誤入力の疑い）：<br>" +
                  "<br>".join(f"・{v['原料種別']} / {v['ロットNo']}（入荷{fmt_kg(v['入荷袋数'])}袋 ＜ 使用{fmt_kg(round(v['使用袋数'], 2))}袋）" for v in neg), "warn")
    t_inv, t_sum, t_hist = st.tabs(["📋 在庫一覧・棚卸し", "🧮 原料別サマリー", "🕒 変更履歴"])

    with t_inv:
        card_start()
        active_inv = [v for v in inventory_data.values() if v["現在庫(袋)"] > 0]
        if active_inv: render_lot_inventory_manager(active_inv)
        else: st.info("在庫データがありません。")
        card_end()

    with t_sum:
        card_start()
        rows = []
        for m in sorted_materials():
            pt, wt = parse_op_data(order_points.get(m, 0.0))
            bags = type_totals_bag.get(m, 0.0)
            rows.append({"原料": m, "現在庫(kg)": round(type_totals_kg.get(m, 0.0), 2), "現在庫(袋)": round(bags, 2), "発注点(袋)": pt,
                         "状態": "⚠️ 発注点以下" if (pt > 0 and bags < pt) else "✅ OK",
                         "在庫ロット数": len({v["ロットNo"] for v in inventory_data.values() if v["原料種別"] == m and v["現在庫(袋)"] > 0})})
        df_sum = pd.DataFrame(rows)
        st.dataframe(fmt_df_numeric(df_sum, ["現在庫(kg)", "現在庫(袋)", "発注点(袋)"]), use_container_width=True, hide_index=True)
        lot_rows = [{"原料": v["原料種別"], "ロットNo": v["ロットNo"], "入荷日": v["入荷日"], "入荷No": v["入荷No"], "メーカー": v["メーカー"], "グレード": v["グレード"],
                     "入荷袋数": v["入荷袋数"], "使用量(kg)": round(v["使用量(kg)"], 2), "調整袋数": round(v["調整袋数"], 3), "現在庫(袋)": round(v["現在庫(袋)"], 2), "現在庫(kg)": round(v["現在庫(kg)"], 2)}
                    for v in sorted(inventory_data.values(), key=lambda x: (x["原料種別"], x["入荷日"])) if v["現在庫(袋)"] > 0]
        if lot_rows:
            download_buttons({"原料別在庫": df_sum, "ロット別在庫": pd.DataFrame(lot_rows)}, f"在庫表_{today_jst()}", "inv_dl")
        card_end()

    with t_hist:
        if not adjustments:
            st.info("棚卸・調整の履歴はありません。")
        else:
            df_adj = ensure_cols(pd.DataFrame(adjustments), ["登録日時", "調整日", "入荷No", "調整袋数", "理由", "担当者"])
            ano_lot_map = {str(a.get("入荷No", "")).strip(): (str(a.get("原料種別", "")).strip(), str(a.get("ロットNo", "")).strip()) for a in arrivals}
            df_adj["原料種別"] = df_adj["入荷No"].astype(str).map(lambda x: ano_lot_map.get(x, ("", ""))[0])
            df_adj["ロットNo"] = df_adj["入荷No"].astype(str).map(lambda x: ano_lot_map.get(x, ("", ""))[1])
            s_j, e_j = period_picker("adj_hist", default="直近30日")
            kw_j = st.text_input("キーワード（ロット・理由・担当者）", key="adj_hist_kw")
            m = in_period(df_adj["調整日"], s_j, e_j) & keyword_mask(df_adj, ["ロットNo", "理由", "担当者", "原料種別"], kw_j)
            df_adj_v = df_adj[m].sort_values("登録日時", ascending=False)
            cols_adj = ["登録日時", "調整日", "原料種別", "ロットNo", "入荷No", "調整袋数", "理由", "担当者"]
            st.dataframe(fmt_df_numeric(df_adj_v[cols_adj].head(300), ["調整袋数"]), use_container_width=True, hide_index=True)
            if not df_adj_v.empty: download_buttons({"棚卸・調整履歴": df_adj_v[cols_adj]}, f"棚卸調整履歴_{today_jst()}", "adj_dl")


# ═══════════════════════════════════════════════════════════════
#  🧹 資材管理
# ═══════════════════════════════════════════════════════════════
elif page == "🧹 資材管理":
    page_header("🧹 資材・消耗品管理", "発注点以下の資材は赤枠で表示されます。")

    def supply_adjust(s_id, delta, op_name, reason):
        if not hasattr(sheets, "append_supply_log"):
            st.error("sheets.append_supply_log が見つかりません。"); st.stop()
        sheets.append_supply_log({"ログID": f"LOG-{now_jst().strftime('%Y%m%d%H%M%S%f')}", "登録日": str(today_jst()), "資材ID": s_id, "処理": "入荷" if delta > 0 else "使用", "数量": abs(delta), "作業者": op_name, "備考": reason, "登録日時": now_jst().isoformat()})

    t_s1, t_s2 = st.tabs(["📋 在庫一覧・入出庫・棚卸", "🕒 ログ管理"])

    with t_s1:
        if not supplies: st.warning("資材が未登録です。マスタ設定よりご登録ください。")
        else:
            supply_inventory = get_supply_inventory()
            supplies_ordered = sorted_supplies()
            cat_list = sorted(list(set([str(s.get("カテゴリ") or "").strip() or "未分類" for s in supplies_ordered])))
            cat_options = ["📋 すべて表示"] + [f"{_deterministic_icon(c, _ICON_POOL)} {c}" for c in cat_list]

            st.markdown('<div style="font-weight:900; margin-bottom:8px;">① カテゴリを選択</div>', unsafe_allow_html=True)
            sel_cat_label = st.radio("カテゴリ", cat_options, horizontal=True, key="supply_cat_filter", label_visibility="collapsed")
            filtered_supplies = supplies_ordered if sel_cat_label == "📋 すべて表示" else [s for s in supplies_ordered if (str(s.get("カテゴリ") or "").strip() or "未分類") == cat_list[cat_options.index(sel_cat_label) - 1]]
            f_c1, f_c2 = st.columns([2, 1])
            sup_kw = f_c1.text_input("🔎 資材名で検索", key="sup_kw")
            only_low = f_c2.checkbox("🚨 要発注のみ", key="sup_only_low")
            if sup_kw.strip(): filtered_supplies = [s for s in filtered_supplies if sup_kw.strip().lower() in str(s.get("資材名", "")).lower()]
            if only_low: filtered_supplies = [s for s in filtered_supplies if to_float(s.get("発注点"), 0.0) > 0 and supply_inventory.get(s.get("資材ID"), 0.0) <= to_float(s.get("発注点"), 0.0)]
            if not filtered_supplies: st.info("該当する資材がありません。")

            cols_grid = st.columns(min(3, len(filtered_supplies))) if filtered_supplies else []
            for idx, s in enumerate(filtered_supplies):
                sid = s.get("資材ID"); curr_qty = supply_inventory.get(sid, 0.0)
                s_pt = to_float(s.get("発注点"), 0.0)
                is_low = s_pt > 0 and curr_qty <= s_pt
                with cols_grid[idx % 3]:
                    with st.container(border=True):
                        img_html = f'<img src="{s.get("画像URL")}" style="width:60px; height:60px; object-fit:cover; border-radius:8px; margin-right:12px; border:1px solid #e2e8f0;">' if s.get("画像URL") else '<div style="width:60px; height:60px; background:#e2e8f0; border-radius:8px; margin-right:12px; display:flex; align-items:center; justify-content:center; font-size:24px;">📦</div>'
                        num_col = "#b91c1c" if is_low else "#0f766e"
                        low_html = f'<div style="text-align:center; color:#b91c1c; font-weight:800; font-size:0.85rem;">🚨 発注点({fmt_kg(s_pt)})以下</div>' if is_low else (f'<div style="text-align:center; color:#64748b; font-size:0.8rem;">発注点: {fmt_kg(s_pt)}</div>' if s_pt > 0 else "")
                        st.markdown(f'<div style="display:flex; align-items:center; margin-bottom:12px;">{img_html}<div><div style="font-weight:900; font-size:1.1rem; color:#0f172a;">{s.get("資材名")}</div><div style="font-size:0.8rem; color:#64748b;">🏷️ {s.get("カテゴリ") or "未分類"}</div></div></div><div style="font-size:2.0rem; font-weight:900; color:{num_col}; margin-bottom:4px; text-align:center;">{fmt_kg(curr_qty)} <span style="font-size:1rem; color:#64748b;">個</span></div>{low_html}', unsafe_allow_html=True)

                        with st.popover("🔧 増減・棚卸調整", use_container_width=True):
                            adj_mode = st.radio("調整方法", ["➕➖ クイック入出庫", "📋 実地数量で確定"], key=f"sup_mode_{sid}", horizontal=True)
                            op_q = render_operator_selector(f"sup_qop_{sid}")

                            if "クイック" in adj_mode:
                                st.caption("数値を入力し入出庫ボタンをタップしてください")
                                c_amt, c_minus, c_plus = st.columns([2, 1, 1])
                                q_val = c_amt.number_input("数量", min_value=1, value=1, step=1, key=f"sq_val_{sid}", label_visibility="collapsed")
                                if c_minus.button("➖ 出庫", key=f"sq_minus_{sid}", use_container_width=True):
                                    if q_val > curr_qty + 1e-9: st.error(f"在庫({fmt_kg(curr_qty)})より多く出庫できません。")
                                    else:
                                        supply_adjust(sid, -q_val, op_q, "【クイック出庫】"); done(f"{s.get('資材名')} を {q_val} 出庫しました")
                                if c_plus.button("➕ 入庫", key=f"sq_plus_{sid}", use_container_width=True):
                                    supply_adjust(sid, q_val, op_q, "【クイック入庫】"); done(f"{s.get('資材名')} を {q_val} 入庫しました")
                            else:
                                actual_qty = st.number_input("実在庫数量", min_value=0.0, value=float(round(curr_qty, 2)), step=1.0, key=f"sup_actual_{sid}")
                                if actual_qty < EPS_QTY: actual_qty = 0.0
                                diff_qty = round(actual_qty - curr_qty, 4)
                                reason_txt = st.text_input("調整理由", key=f"sup_adj_reason_{sid}")
                                if st.button("💾 この実地数量で確定", type="primary", use_container_width=True, key=f"sup_adj_save_{sid}", disabled=abs(diff_qty) <= 0.001):
                                    supply_adjust(sid, diff_qty, op_q, f"【棚卸調整:実地{fmt_kg(actual_qty)}に更新】{reason_txt}")
                                    done(f"{s.get('資材名')} の現在庫を {fmt_kg(actual_qty)} に更新しました。")

    with t_s2:
        if not supply_logs:
            st.info("資材ログはありません。")
        else:
            id_name_map = {s.get("資材ID"): s.get("資材名") for s in supplies}
            df_logs = ensure_cols(pd.DataFrame(supply_logs), ["ログID", "登録日", "資材ID", "処理", "数量", "作業者", "備考", "登録日時"])
            df_logs["資材名"] = df_logs["資材ID"].map(id_name_map).fillna("（削除済み資材）")
            s_l, e_l = period_picker("sup_log", default="直近30日")
            f1, f2 = st.columns(2)
            sup_sel = f1.multiselect("資材", sorted(df_logs["資材名"].unique()), key="sup_log_sel")
            act_sel = f2.multiselect("処理", ["入荷", "使用"], key="sup_log_act")
            m = in_period(df_logs["登録日"], s_l, e_l)
            if sup_sel: m &= df_logs["資材名"].isin(sup_sel)
            if act_sel: m &= df_logs["処理"].isin(act_sel)
            df_logs_sorted = df_logs[m].sort_values(["登録日", "登録日時"], ascending=False)
            cols_log = ["登録日", "資材名", "処理", "数量", "作業者", "備考"]
            st.dataframe(fmt_df_numeric(df_logs_sorted[cols_log].head(200), ["数量"]), use_container_width=True, hide_index=True)
            if not df_logs_sorted.empty: download_buttons({"資材ログ": df_logs_sorted[cols_log]}, f"資材ログ_{today_jst()}", "suplog_dl")

            sec_title("🚨 ログの取り消し・削除")
            log_options = {f"{r.get('登録日','')} / {r.get('資材名','')} / {r.get('処理','')} {fmt_kg(r.get('数量',0))} / {r.get('作業者','')}（{r.get('ログID','')}）": r.get("ログID", "") for _, r in df_logs_sorted.head(30).iterrows()}
            if log_options:
                sel_log = st.selectbox("削除するログを選択（直近30件）", list(log_options.keys()))
                del_ok = st.checkbox("このログを削除すると在庫数が変わることを理解しました", key="sup_log_del_ok")
                if st.button("🗑️ このログを削除", type="primary", disabled=not del_ok):
                    if hasattr(sheets, "delete_supply_log"):
                        sheets.delete_supply_log(log_options[sel_log])
                        done("ログを削除しました。", "warn")
                    else: st.error("sheets.delete_supply_log が見つかりません。")


# ═══════════════════════════════════════════════════════════════
#  🔍 トレース
# ═══════════════════════════════════════════════════════════════
elif page == "🔍 トレース":
    page_header("🔍 双方向原料トレース", "ロットから製品へ（フォワード）／製品から原料ロットへ（バックワード）をワンタッチで追跡します。")
    trace_dir = st.radio("トレース方向", ["➡️ 原料ロットから製品を追跡（フォワード）", "⬅️ 製品から原料を遡及（バックワード）"])
    card_start()
    if not brewing:
        st.info("製造記録がありません。")
    elif "フォワード" in trace_dir:
        pairs = sorted({(str(a.get("原料種別", "")).strip(), str(a.get("ロットNo", "")).strip()) for a in arrivals if str(a.get("ロットNo", "")).strip()}, key=lambda x: (x[1], x[0]), reverse=True)
        lot_kw = st.text_input("🔎 ロットNo・原料名で絞り込み", key="trace_lot_kw")
        pairs = [p for p in pairs if not lot_kw.strip() or lot_kw.strip().lower() in f"{p[0]} {p[1]}".lower()]
        if not pairs:
            st.warning("該当するロットがありません。")
        else:
            def _arr_date(mat, lot):
                ds = [str(a.get("入荷日", "")) for a in arrivals if str(a.get("原料種別", "")).strip() == mat and str(a.get("ロットNo", "")).strip() == lot]
                return min(ds) if ds else "不明"
            labels = {f"{lot}　（{mat} ／ 入荷 {_arr_date(mat, lot)}）": (mat, lot) for mat, lot in pairs}
            sel = st.selectbox("検索する原料ロット", list(labels.keys()))
            t_mat, t_lot = labels[sel]
            usage_all = build_usage_df(brewing)
            use = usage_all[(usage_all["ロットNo"] == t_lot) & (usage_all["原料名"] == t_mat)]
            if use.empty: use = usage_all[usage_all["ロットNo"] == t_lot]

            inv_rows = [v for v in inventory_data.values() if v["ロットNo"] == t_lot and v["原料種別"] == t_mat]
            if inv_rows:
                c1, c2, c3, c4 = st.columns(4)
                in_bags = sum(v["入荷袋数"] for v in inv_rows); wpb = inv_rows[0]["1袋重量"]
                c1.metric("入荷量", f"{fmt_kg(in_bags)} 袋", f"{fmt_kg(round(in_bags * wpb, 1))} kg", delta_color="off")
                c2.metric("使用量", f"{fmt_kg(round(use['投入量(kg)'].sum(), 2))} kg")
                c3.metric("現在庫", f"{fmt_kg(round(sum(v['現在庫(kg)'] for v in inv_rows), 2))} kg")
                c4.metric("製造回数", f"{use['仕込No'].nunique()} 回")
            if use.empty:
                st.warning("このロットを使用した製造記録はありません。")
            else:
                st.markdown(f"**このロットを使用した製品：** {'、'.join(sorted(use['品名'].astype(str).unique()))}")
                bq = {str(b.get("仕込No")): to_float(b.get("仕込量(kg)")) for b in brewing}
                show = use.sort_values(["仕込日", "仕込No"], ascending=False).copy()
                show["仕込量(kg)"] = show["仕込No"].astype(str).map(bq)
                cols_t = ["仕込日", "仕込No", "品名", "原料名", "投入量(kg)", "仕込量(kg)", "担当者"]
                st.dataframe(fmt_df_numeric(show[cols_t], ["投入量(kg)", "仕込量(kg)"]), use_container_width=True, hide_index=True)
                download_buttons({"フォワードトレース": show[cols_t]}, f"トレース_ロット{t_lot}_{today_jst()}", "trace_f_dl")
    else:
        sorted_brw = sorted(brewing, key=lambda b: (str(b.get("仕込日", "")), str(b.get("仕込No", ""))), reverse=True)
        kw_b = st.text_input("🔎 仕込No・品名・日付で絞り込み", key="trace_brw_kw")
        brw_opts = {f"No.{b.get('仕込No')} - {b.get('品名')} ({b.get('仕込日')} / {to_float(b.get('仕込量(kg)')):g}kg)": b for b in sorted_brw
                    if not kw_b.strip() or kw_b.strip().lower() in f"{b.get('仕込No')} {b.get('品名')} {b.get('仕込日')}".lower()}
        if not brw_opts:
            st.warning("該当する製造記録がありません。")
        else:
            sel_b = st.selectbox("対象の製造記録", list(brw_opts.keys()))
            b = brw_opts[sel_b]
            usage = build_usage_df([b])
            c1, c2, c3 = st.columns(3)
            c1.metric("仕込日", str(b.get("仕込日", "")))
            c2.metric("仕込量", f"{fmt_kg(to_float(b.get('仕込量(kg)')))} kg")
            c3.metric("担当者", str(b.get("メーカー", "")))
            if usage.empty:
                st.warning("原料ロットの記録はありません。")
            else:
                arr_chk = {str(a.get("入荷No", "")): a for a in arrivals}
                usage["受入検査"] = usage["入荷No"].map(lambda x: ("⚠️ 異常あり" if any("異常" in str(arr_chk.get(x, {}).get(k, "")) for k in ["外観", "品名・規格確認", "賞味期限", "異物"]) else "✅ 正常") if x in arr_chk else "─")
                cols_b = ["原料名", "投入量(kg)", "ロットNo", "入荷日", "入荷メーカー", "グレード", "入荷No", "受入検査"]
                st.dataframe(fmt_df_numeric(usage[cols_b], ["投入量(kg)"]), use_container_width=True, hide_index=True)
                download_buttons({"バックワードトレース": usage[cols_b]}, f"トレース_仕込{b.get('仕込No')}_{today_jst()}", "trace_b_dl")
    card_end()


# ═══════════════════════════════════════════════════════════════
#  📋 履歴・帳票
# ═══════════════════════════════════════════════════════════════
elif page == "📋 履歴・帳票":
    page_header("📋 製造履歴・帳票出力", "期間・製品・担当者・ロットで絞り込み → 一覧確認 → Excel/CSV出力ができます。")
    if not brewing: st.info("製造記録がありません。")
    else:
        BRW_COLS = ["仕込日", "仕込No", "品名", "メーカー", "仕込量(kg)", "石灰水(L)", "主原料ロット", "その他添加物", "備考", "登録日時"]
        df_b_raw = ensure_cols(pd.DataFrame(brewing), BRW_COLS)

        card_start()
        s_date, e_date = period_picker("brw_hist", default="今月")
        f1, f2, f3 = st.columns([2, 2, 2])
        prod_sel = f1.multiselect("🍥 製品", sorted(df_b_raw["品名"].astype(str).unique()), key="brw_hist_prod")
        op_sel = f2.multiselect("👨‍🏭 担当者", sorted(df_b_raw["メーカー"].astype(str).unique()), key="brw_hist_op")
        kw = f3.text_input("🔎 キーワード（ロット・仕込No・備考・品名）", key="brw_hist_kw")
        m = in_period(df_b_raw["仕込日"], s_date, e_date) & keyword_mask(df_b_raw, ["品名", "仕込No", "備考", "主原料ロット", "その他添加物"], kw)
        if prod_sel: m &= df_b_raw["品名"].isin(prod_sel)
        if op_sel: m &= df_b_raw["メーカー"].isin(op_sel)
        df_f = df_b_raw[m].sort_values(["仕込日", "登録日時", "仕込No"], ascending=False).reset_index(drop=True)
        view = brewing_view_df(df_f)

        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.metric("製造件数", f"{len(view)} 件")
        c_m2.metric("製造量 合計", f"{fmt_kg(round(view['仕込量(kg)'].sum(), 2))} kg")
        c_m3.metric("製造日数", f"{view['仕込日'].nunique()} 日")
        card_end()

        t_list, t_detail, t_daily = st.tabs(["📄 一覧・帳票出力", "🔬 1件ずつ詳細確認", "📆 日別・製品別集計"])

        with t_list:
            card_start()
            list_cols = ["仕込日", "仕込No", "品名", "担当者", "仕込量(kg)", "石灰水(L)", "原料内訳（全原料の投入量）", "備考"]
            if view.empty:
                st.info("条件に合う製造記録がありません。")
            else:
                usage_df = build_usage_df(df_f.to_dict("records"))
                daily = view.groupby("仕込日", as_index=False).agg(件数=("仕込No", "count"), 製造量kg=("仕込量(kg)", "sum")).sort_values("仕込日")
                xl_sheets = {"製造記録": view[list_cols], "原料使用明細": usage_df, "日別集計": daily}
                download_buttons(xl_sheets, f"製造記録_{s_date or '全期間'}_{e_date or ''}".rstrip("_"), "brw_dl")
                st.dataframe(fmt_df_numeric(view[list_cols], ["仕込量(kg)", "石灰水(L)"]), use_container_width=True, hide_index=True)
                st.caption("※ Excelには「製造記録」「原料使用明細（ロット・入荷日・メーカー付き）」「日別集計」の3シートが入ります。")
            card_end()

        with t_detail:
            card_start()
            if view.empty:
                st.info("条件に合う製造記録がありません。")
            else:
                opts = {f"{r['仕込日']} ／ No.{r['仕込No']} ／ {r['品名']} ／ {fmt_kg(r['仕込量(kg)'])}kg ／ {r['担当者']}": i for i, r in view.iterrows()}
                sel = st.selectbox("確認する製造記録", list(opts.keys()), key="brw_detail_sel")
                r = view.loc[opts[sel]]
                d1, d2, d3, d4 = st.columns(4)
                d1.metric("仕込日", str(r["仕込日"])); d2.metric("製品", str(r["品名"])); d3.metric("仕込量", f"{fmt_kg(r['仕込量(kg)'])} kg"); d4.metric("担当者", str(r["担当者"]))
                u = build_usage_df([df_f.loc[opts[sel]].to_dict()])
                if u.empty: st.caption("原料内訳の記録がありません。")
                else: st.dataframe(fmt_df_numeric(u[["原料名", "投入量(kg)", "ロットNo", "入荷日", "入荷メーカー", "グレード"]], ["投入量(kg)"]), use_container_width=True, hide_index=True)
                if str(r.get("備考", "")).strip(): st.info(f"📝 備考: {r['備考']}")
                st.caption(f"登録日時: {r.get('登録日時', '')}")
            card_end()

        with t_daily:
            card_start()
            if view.empty:
                st.info("条件に合う製造記録がありません。")
            else:
                dd = view.groupby("仕込日", as_index=False).agg(件数=("仕込No", "count"), 製造量kg=("仕込量(kg)", "sum")).sort_values("仕込日", ascending=False)
                st.markdown("**📆 日別**")
                st.dataframe(fmt_df_numeric(dd, ["製造量kg"]), use_container_width=True, hide_index=True)
                pp = view.groupby("品名", as_index=False).agg(件数=("仕込No", "count"), 製造量kg=("仕込量(kg)", "sum")).sort_values("製造量kg", ascending=False)
                st.markdown("**🍥 製品別**")
                st.dataframe(fmt_df_numeric(pp, ["製造量kg"]), use_container_width=True, hide_index=True)
            card_end()

        with st.expander("✏️ 製造履歴の修正・削除（Excel風・管理者向け）"):
            st.caption("※ 上の絞り込み条件に合う記録が対象です。担当者は「メーカー」列に記録されています。原料内訳(ロット別)の修正はここではできません。")
            brw_editable_cols = [c for c in ["仕込日", "品名", "メーカー", "仕込量(kg)", "主原料ロット", "備考"] if c in df_f.columns]
            render_excel_history_editor(full_records=brewing, filtered_df=df_f, id_col="仕込No", editable_cols=brw_editable_cols, numeric_cols=["仕込量(kg)"], save_func=sheets.save_brewing, key_prefix="brw_hist", reload_func=sheets.load_brewing)

#  📈 分析
# ═══════════════════════════════════════════════════════════════
elif page == "📈 分析":
    st.markdown('<div class="main-header"><h1>📈 製造・原料・資材 分析</h1></div>', unsafe_allow_html=True)

    def build_material_consumption_events():
        events = []
        for b in brewing:
            bdate = str(b.get("仕込日", "")).strip()
            pname = b.get("品名", "")
            for it in parse_brewing_ingredients(b.get("その他添加物", "")):
                n = str(it.get("原料名", "")).strip()
                if not n or n in ("水", "お湯"): continue
                events.append({"日付": bdate, "原料名": n, "kg": to_float(it.get("kg", 0)), "品名": pname, "仕込No": b.get("仕込No", "")})
        return pd.DataFrame(events)

    t_prod, t_konjac, t_supply = st.tabs(["🏭 生産分析", "🌾 こんにゃく粉・原料 消費分析", "🧻 資材 消費分析"])

    # ---------------------------------------------------------------
    # 🏭 生産分析（従来の製造量分析）
    # ---------------------------------------------------------------
    with t_prod:
        df_brw_global = pd.DataFrame(brewing)
        if df_brw_global.empty: st.info("データがありません。")
        else:
            df_brw_global["仕込日_dt"] = pd.to_datetime(df_brw_global["仕込日"], errors="coerce")
            df_brw_global["month"] = df_brw_global["仕込日_dt"].dt.to_period("M").astype(str)
            df_brw_global["仕込量(kg)"] = pd.to_numeric(df_brw_global["仕込量(kg)"], errors="coerce").fillna(0)

            card_start()
            monthly_trend = df_brw_global.groupby("month")["仕込量(kg)"].sum().reset_index().sort_values("month")
            fig = go.Figure(go.Bar(x=monthly_trend["month"], y=monthly_trend["仕込量(kg)"], marker_color="#0f766e"))
            fig.update_layout(title="月間生産推移 (kg)", xaxis_title="年月", yaxis_title="総製造量", plot_bgcolor="#ffffff")
            st.plotly_chart(fig, use_container_width=True)
            card_end()

            c1, c2 = st.columns(2)
            with c1:
                card_start()
                pie_data = df_brw_global.groupby("品名")["仕込量(kg)"].sum().reset_index().sort_values("仕込量(kg)", ascending=False)
                fig_tree = px.treemap(pie_data[pie_data["仕込量(kg)"] > 0], path=["品名"], values="仕込量(kg)", color="仕込量(kg)", color_continuous_scale=["#fde4d0", "#0f766e"], title="製品構成比")
                fig_tree.update_traces(texttemplate="<b>%{label}</b><br>%{value:,.0f} kg", textfont_size=14); fig_tree.update_layout(margin=dict(t=50, l=6, r=6, b=6))
                st.plotly_chart(fig_tree, use_container_width=True)
                card_end()
            with c2:
                card_start()
                topN = pie_data.sort_values("仕込量(kg)", ascending=True).tail(15)
                fig_bar = px.bar(topN, x="仕込量(kg)", y="品名", orientation='h', title="製造量 上位15品目", text="仕込量(kg)")
                fig_bar.update_traces(texttemplate="%{text:,.0f} kg", textposition="outside", marker_color="#0f766e"); fig_bar.update_layout(height=max(380, 34 * len(topN)), plot_bgcolor="#ffffff", yaxis_title="")
                st.plotly_chart(fig_bar, use_container_width=True)
                card_end()

    # ---------------------------------------------------------------
    # 🌾 こんにゃく粉・原料 消費分析
    # ---------------------------------------------------------------
    with t_konjac:
        df_ev = build_material_consumption_events()
        if df_ev.empty:
            st.info("製造記録がまだありません。")
        else:
            df_ev["日付_dt"] = pd.to_datetime(df_ev["日付"], errors="coerce")
            df_ev["month"] = df_ev["日付_dt"].dt.to_period("M").astype(str)
            df_ev["is_konjac"] = df_ev["原料名"].apply(is_konjac_material)

            card_start()
            focus = st.radio("対象", ["🌾 こんにゃく粉のみ", "📦 すべての原料"], horizontal=True, key="konjac_focus")
            df_focus = df_ev[df_ev["is_konjac"]] if "こんにゃく粉のみ" in focus else df_ev
            c_a, c_b = st.columns(2)
            f_start = c_a.date_input("開始日", value=(today_jst() - timedelta(days=180)), key="konjac_start")
            f_end = c_b.date_input("終了日", value=today_jst(), key="konjac_end")
            df_focus = df_focus[(df_focus["日付_dt"].dt.date >= f_start) & (df_focus["日付_dt"].dt.date <= f_end)]
            card_end()

            if df_focus.empty:
                st.info("対象期間内の消費実績がありません。")
            else:
                card_start()
                sec_title("📅 月別 消費量の推移")
                monthly = df_focus.groupby(["month", "原料名"])["kg"].sum().reset_index()
                fig_m = px.bar(monthly, x="month", y="kg", color="原料名", title="原料別 月間消費量 (kg)", barmode="stack")
                fig_m.update_layout(plot_bgcolor="#ffffff", xaxis_title="年月", yaxis_title="消費量(kg)")
                st.plotly_chart(fig_m, use_container_width=True)
                card_end()

                c1, c2 = st.columns(2)
                with c1:
                    card_start()
                    sec_title("🏆 原料別 合計消費量")
                    total_by_mat = df_focus.groupby("原料名")["kg"].sum().reset_index().sort_values("kg", ascending=True)
                    fig_t = px.bar(total_by_mat, x="kg", y="原料名", orientation="h", text="kg", title="合計消費量 (kg)")
                    fig_t.update_traces(texttemplate="%{text:,.0f} kg", textposition="outside", marker_color="#0f766e")
                    fig_t.update_layout(plot_bgcolor="#ffffff", height=max(300, 34 * len(total_by_mat)), yaxis_title="")
                    st.plotly_chart(fig_t, use_container_width=True)
                    card_end()
                with c2:
                    card_start()
                    sec_title("📊 消費実績サマリー")
                    days_span = max(1, (f_end - f_start).days + 1)
                    summary = df_focus.groupby("原料名").agg(合計消費量_kg=("kg", "sum"), 使用回数=("仕込No", "count"), 直近使用日=("日付", "max")).reset_index()
                    summary["1日あたり平均_kg"] = (summary["合計消費量_kg"] / days_span).round(2)
                    summary = summary.sort_values("合計消費量_kg", ascending=False)
                    st.dataframe(fmt_df_numeric(summary, ["合計消費量_kg", "1日あたり平均_kg"]), use_container_width=True, hide_index=True)
                    card_end()

                card_start()
                sec_title("🕒 消費履歴（詳細）")
                detail = df_focus[["日付", "原料名", "kg", "品名", "仕込No"]].sort_values("日付", ascending=False).rename(columns={"kg": "消費量(kg)"})
                st.dataframe(fmt_df_numeric(detail.head(300), ["消費量(kg)"]), use_container_width=True, hide_index=True)
                card_end()

    # ---------------------------------------------------------------
    # 🧻 資材 消費分析
    # ---------------------------------------------------------------
    with t_supply:
        if not supply_logs:
            st.info("資材の入出庫ログがまだありません。")
        else:
            id_name_map_a = {s.get("資材ID"): s.get("資材名") for s in supplies}
            df_sl = pd.DataFrame(supply_logs)
            df_sl["資材名"] = df_sl["資材ID"].map(id_name_map_a)
            df_sl["数量"] = df_sl["数量"].apply(to_float)
            df_use = df_sl[df_sl["処理"] == "使用"].copy()
            df_use["日付_dt"] = pd.to_datetime(df_use["登録日"], errors="coerce")

            if df_use.empty:
                st.info("資材の使用（消費）実績がまだありません。")
            else:
                card_start()
                c_a, c_b = st.columns(2)
                s_start = c_a.date_input("開始日", value=(today_jst() - timedelta(days=180)), key="sup_an_start")
                s_end = c_b.date_input("終了日", value=today_jst(), key="sup_an_end")
                df_use_f = df_use[(df_use["日付_dt"].dt.date >= s_start) & (df_use["日付_dt"].dt.date <= s_end)]
                card_end()

                if df_use_f.empty:
                    st.info("対象期間内の消費実績がありません。")
                else:
                    df_use_f = df_use_f.copy()
                    df_use_f["month"] = df_use_f["日付_dt"].dt.to_period("M").astype(str)

                    card_start()
                    sec_title("📅 月別 消費量の推移")
                    monthly_s = df_use_f.groupby(["month", "資材名"])["数量"].sum().reset_index()
                    fig_ms = px.bar(monthly_s, x="month", y="数量", color="資材名", title="資材別 月間消費数量", barmode="stack")
                    fig_ms.update_layout(plot_bgcolor="#ffffff", xaxis_title="年月", yaxis_title="消費数量")
                    st.plotly_chart(fig_ms, use_container_width=True)
                    card_end()

                    c1, c2 = st.columns(2)
                    with c1:
                        card_start()
                        sec_title("🏆 資材別 合計消費量")
                        total_by_sup = df_use_f.groupby("資材名")["数量"].sum().reset_index().sort_values("数量", ascending=True)
                        fig_ts = px.bar(total_by_sup, x="数量", y="資材名", orientation="h", text="数量", title="合計消費数量")
                        fig_ts.update_traces(texttemplate="%{text:,.0f}", textposition="outside", marker_color="#0f766e")
                        fig_ts.update_layout(plot_bgcolor="#ffffff", height=max(300, 34 * len(total_by_sup)), yaxis_title="")
                        st.plotly_chart(fig_ts, use_container_width=True)
                        card_end()
                    with c2:
                        card_start()
                        sec_title("📊 消費実績サマリー")
                        days_span_s = max(1, (s_end - s_start).days + 1)
                        summary_s = df_use_f.groupby("資材名").agg(合計消費量=("数量", "sum"), 使用回数=("数量", "count"), 直近使用日=("登録日", "max")).reset_index()
                        summary_s["1日あたり平均"] = (summary_s["合計消費量"] / days_span_s).round(2)
                        summary_s = summary_s.sort_values("合計消費量", ascending=False)
                        st.dataframe(fmt_df_numeric(summary_s, ["合計消費量", "1日あたり平均"]), use_container_width=True, hide_index=True)
                        card_end()

                    card_start()
                    sec_title("🕒 消費履歴（詳細）")
                    detail_s = df_use_f[["登録日", "資材名", "数量", "作業者", "備考"]].sort_values("登録日", ascending=False).rename(columns={"数量": "消費数量"})
                    st.dataframe(fmt_df_numeric(detail_s.head(300), ["消費数量"]), use_container_width=True, hide_index=True)
                    card_end()


# ═══════════════════════════════════════════════════════════════
#  ⚙️ マスタ設定
# ═══════════════════════════════════════════════════════════════
elif page == "⚙️ マスタ設定":
    st.markdown('<div class="main-header"><h1>⚙️ マスターデータ管理</h1></div>', unsafe_allow_html=True)
    t1, t2, t3, t4, t5 = st.tabs(["⚗️ 原料マスタ・詳細", "🏢 担当者", "🧪 レシピ・石灰", "📦 資材", "🏷️ グレード"])
    
    with t1:
        card_start()
        sec_title("🥦 原料名の登録・編集・表示順")
        st.caption("💡「表示順」を書き換えて並べ替えられます（小さい数字が先に表示されます）。行を追加すれば新規登録、行を削除すれば削除できます。")
        m_names_only = [m for m in materials if not m.startswith("__")]
        df_m = pd.DataFrame({"表示順": list(range(1, len(m_names_only) + 1)), "原料名": pd.array(m_names_only, dtype="string")})
        ed_m = st.data_editor(df_m, num_rows="dynamic", use_container_width=True, hide_index=True,
                               column_config={"表示順": st.column_config.NumberColumn("表示順", step=1, min_value=0),
                                              "原料名": st.column_config.TextColumn("原料名(必須)", required=True)})
        mat_del_ok = st.checkbox("在庫が残っている原料の削除を許可する（必要な場合のみチェック）", key="mat_del_ok")
        if st.button("💾 原料マスタ保存", type="primary"):
            if hasattr(sheets, "save_materials"):
                clean = ed_m.copy()
                clean["原料名"] = clean["原料名"].astype(str).str.strip()
                clean = clean[(clean["原料名"] != "") & (clean["原料名"].str.lower() != "nan")]
                clean["表示順"] = pd.to_numeric(clean["表示順"], errors="coerce").fillna(9999)
                clean = clean.sort_values(["表示順", "原料名"], kind="stable")
                removed = [m for m in m_names_only if m not in set(clean["原料名"])]
                in_use = [m for m in removed if type_totals_kg.get(m, 0.0) > 0]
                if in_use and not mat_del_ok:
                    st.error(f"在庫が残っている原料が削除されようとしています：{'、'.join(in_use)}。削除してよい場合は上のチェックを入れてから、もう一度保存してください。")
                    st.stop()
                sheets.save_materials(clean["原料名"].tolist())
                done("保存しました。")
        card_end()

        if materials:
            card_start()
            sec_title("🔧 選択した原料の詳細設定")
            sel_m = st.selectbox("詳細を設定する原料", sorted_materials())
            
            if sel_m:
                pt, wt = parse_op_data(order_points.get(sel_m, 0.0))
                active_lots = get_active_lots_from_master(order_points, sel_m)
                
                # 0以上の在庫を持つロットのみを候補に
                hist_lots = [v["ロットNo"] for v in inventory_data.values() if v["原料種別"] == sel_m and v["現在庫(袋)"] > 0.000]
                for l in active_lots:
                    if l not in hist_lots: hist_lots.append(l)

                with st.form("mat_detail_form"):
                    c_pt, c_wt = st.columns(2)
                    new_pt = c_pt.number_input("🚨 発注点 (袋)", value=int(pt), step=1)
                    new_wt = c_wt.number_input("⚖️ 1袋重量 (kg)", value=int(wt), step=1)
                    
                    st.markdown("---")
                    st.markdown("##### 📦 製造で使用するロットの指定")
                    st.caption("仕込み画面で「メインの選択肢」として最前面に表示させたいロットのみを選んでください。指定しなかった在庫は「その他の在庫ありロット」に折りたたまれます。")
                    new_active_lots = st.multiselect("使用可能ロット", hist_lots, default=[x for x in active_lots if x in hist_lots])
                    
                    st.markdown("---")
                    st.markdown("##### 🖼️ 原料の画像")
                    uploaded_file = st.file_uploader("📷 画像 (任意)", type=["jpg", "png", "jpeg"])
                    
                    if st.form_submit_button("💾 詳細設定を保存する", type="primary"):
                        d = dict(order_points)
                        d[sel_m] = f"発注点:{new_pt}袋, 重量:{new_wt}kg"
                        d[f"__ACTIVE_LOTS_{sel_m}__"] = json.dumps(new_active_lots, ensure_ascii=False)
                        
                        if uploaded_file and HAS_PIL:
                            img = Image.open(uploaded_file).convert("RGB"); img.thumbnail((120, 120)); buffered = BytesIO(); img.save(buffered, format="JPEG", quality=70)
                            d[f"__IMAGE_{sel_m}__"] = f"data:image/jpeg;base64,{base64.b64encode(buffered.getvalue()).decode('utf-8')}"
                        
                        # 削除された隠し機能のゴミデータがあれば消す
                        keys_to_remove = [k for k in d.keys() if k.startswith("__HIDDEN_LOTS_")]
                        for k in keys_to_remove: d.pop(k, None)

                        if hasattr(sheets, "save_order_points"):
                            sheets.save_order_points(d)
                            done(f"{sel_m} の詳細設定を保存しました。")
            card_end()

    with t2:
        card_start()
        ed_u = st.data_editor(pd.DataFrame({"担当者名": pd.array(inspectors, dtype="string")}), num_rows="dynamic", use_container_width=True)
        if st.button("💾 担当者保存", type="primary"):
            if hasattr(sheets, "save_inspectors"):
                sheets.save_inspectors([str(x).strip() for x in ed_u["担当者名"].tolist() if x is not None and str(x).strip() and str(x).strip().lower() != "nan"])
                done("保存しました。")
        card_end()

    with t3:
        st.markdown("### 🕒 レシピ変更履歴")
        with st.expander("📝 履歴を確認する"):
            if recipe_logs:
                df_rlog = pd.DataFrame(recipe_logs)
                if "変更日時" in df_rlog.columns: df_rlog = df_rlog.sort_values("変更日時", ascending=False)
                st.dataframe(df_rlog, use_container_width=True, hide_index=True)
            else:
                st.info("変更履歴はありません。")

        recipe_kind = st.radio("レシピ種別を選択", ["🍽️ 通常レシピ（仕込み配合）", "🌶️ 調味料レシピ（希釈）"], horizontal=True)
        op_recipe = render_operator_selector("recipe_op")
        
        if "通常" in recipe_kind:
            card_start()
            sec_title("🍽️ 通常レシピのエクセルライク編集")
            st.caption("Excelのように表を直接編集できます。行を追加して新しいレシピを作成することも可能です。")
            normal_recipes = [r for r in recipes_raw if r.get("大カテゴリ") != "調味料"]
            MAX_ING = 8
            
            rows = []
            for r in normal_recipes:
                row = {"品名": r.get("品名", ""), "大カテゴリ": r.get("大カテゴリ", "プラント"), "中カテゴリ": r.get("中カテゴリ", "黒")}
                items = safe_parse_recipe(r.get("配合JSON"))
                for i in range(MAX_ING):
                    row[f"原料{i+1}"] = items[i]["原料名"] if i < len(items) else None
                    row[f"比率{i+1}(%)"] = float(items[i]["比率"]) if i < len(items) else 0.0
                rows.append(row)
                
            df_recipes = pd.DataFrame(rows)
            col_cfg = {
                "品名": st.column_config.TextColumn("製品名(必須)", required=True),
                "大カテゴリ": st.column_config.SelectboxColumn("大カテゴリ", options=["プラント", "OKM", "手詰め"]),
                "中カテゴリ": st.column_config.SelectboxColumn("中カテゴリ", options=["白", "黒", "耐冷", "ショクカイ", "めん", "その他"]),
            }
            mat_opts = [m for m in materials if not m.startswith("__")] + ["水"]
            for i in range(MAX_ING):
                col_cfg[f"原料{i+1}"] = st.column_config.SelectboxColumn(f"原料{i+1}", options=mat_opts)
                col_cfg[f"比率{i+1}(%)"] = st.column_config.NumberColumn(f"比率{i+1}(%)", min_value=0.0, format="%.2f")

            edited_df = st.data_editor(df_recipes, num_rows="dynamic", use_container_width=True, column_config=col_cfg, key="recipe_editor")
            
            del_ok_n = st.checkbox("レシピの削除を伴う変更を許可する（削除する場合のみチェック）", key="recipe_del_ok_n")
            if st.button("💾 通常レシピを保存し履歴を記録", type="primary", use_container_width=True):
                new_recipes = []
                changes = []
                orig_dict = {r["品名"]: r.get("配合JSON", "") for r in normal_recipes}
                
                for _, row in edited_df.iterrows():
                    pname = str(row.get("品名", "")).strip()
                    if not pname or pname.lower() == "nan": continue
                    
                    items = []
                    for i in range(MAX_ING):
                        m = str(row.get(f"原料{i+1}", "")).strip()
                        rat = float(row.get(f"比率{i+1}(%)", 0.0) or 0.0)
                        if m and m.lower() != "nan" and rat > 0: items.append(f"{m}:{rat}%")
                    new_json = ", ".join(items)
                    
                    new_recipes.append({"品名": pname, "大カテゴリ": row.get("大カテゴリ", "プラント"), "中カテゴリ": row.get("中カテゴリ", "黒"), "配合JSON": new_json})
                    
                    if pname not in orig_dict: changes.append(f"【新規追加】{pname} ({new_json})")
                    elif orig_dict[pname] != new_json: changes.append(f"【変更】{pname} ({orig_dict[pname]} → {new_json})")
                
                new_names = [r["品名"] for r in new_recipes]
                for old_name in orig_dict:
                    if old_name not in new_names: changes.append(f"【削除】{old_name}")
                
                if not changes: st.info("変更はありませんでした。")
                elif any("【削除】" in c for c in changes) and not del_ok_n:
                    st.error("レシピの削除が含まれています。削除してよい場合は上のチェックを入れてから、もう一度保存してください。")
                else:
                    updated_all = [r for r in recipes_raw if r.get("大カテゴリ") == "調味料"] + new_recipes
                    if hasattr(sheets, "save_recipes"): sheets.save_recipes(updated_all)
                    
                    new_logs = recipe_logs.copy() if recipe_logs else []
                    for c in changes:
                        new_logs.append({"ログID": f"RLOG-{now_jst().strftime('%Y%m%d%H%M%S%f')}", "変更日時": now_jst().isoformat(), "担当者": op_recipe, "内容": c})
                    if hasattr(sheets, "save_recipe_logs"): sheets.save_recipe_logs(new_logs)
                    
                    done(f"{len(changes)}件の変更を保存しました。")
            card_end()
            
        else:
            card_start()
            sec_title("🌶️ 調味料レシピ（希釈）のエクセルライク編集")
            st.caption("希釈倍率を設定します。")
            seasoning_recipes = [r for r in recipes_raw if r.get("大カテゴリ") == "調味料"]
            MAX_S_ING = 5
            
            rows_s = []
            for r in seasoning_recipes:
                row = {"品名": r.get("品名", "")}
                items = safe_parse_seasoning_recipe(r.get("配合JSON"))
                for i in range(MAX_S_ING):
                    row[f"原料{i+1}"] = items[i]["原料名"] if i < len(items) else None
                    row[f"希釈倍率{i+1}"] = float(items[i]["希釈倍率"]) if i < len(items) else 0.0
                rows_s.append(row)
            
            df_s = pd.DataFrame(rows_s)
            col_cfg_s = {"品名": st.column_config.TextColumn("調味料名(必須)", required=True)}
            s_mat_opts = [m for m in materials if not m.startswith("__")]
            for i in range(MAX_S_ING):
                col_cfg_s[f"原料{i+1}"] = st.column_config.SelectboxColumn(f"原料{i+1}", options=s_mat_opts)
                col_cfg_s[f"希釈倍率{i+1}"] = st.column_config.NumberColumn(f"希釈倍率{i+1}", min_value=0.0, format="%.2f")
                
            edited_df_s = st.data_editor(df_s, num_rows="dynamic", use_container_width=True, column_config=col_cfg_s, key="season_editor")
            
            del_ok_s = st.checkbox("調味料レシピの削除を伴う変更を許可する（削除する場合のみチェック）", key="recipe_del_ok_s")
            if st.button("💾 調味料レシピを保存し履歴を記録", type="primary", use_container_width=True):
                new_s_recipes = []
                changes_s = []
                orig_s_dict = {r["品名"]: r.get("配合JSON", "") for r in seasoning_recipes}
                
                for _, row in edited_df_s.iterrows():
                    pname = str(row.get("品名", "")).strip()
                    if not pname or pname.lower() == "nan": continue
                    
                    items = []
                    for i in range(MAX_S_ING):
                        m = str(row.get(f"原料{i+1}", "")).strip()
                        rat = float(row.get(f"希釈倍率{i+1}", 0.0) or 0.0)
                        if m and m.lower() != "nan" and rat > 0: items.append(f"{m}:{rat}倍")
                    new_json = ", ".join(items)
                    
                    new_s_recipes.append({"品名": pname, "大カテゴリ": "調味料", "中カテゴリ": "希釈", "配合JSON": new_json})
                    
                    if pname not in orig_s_dict: changes_s.append(f"【新規追加】{pname} ({new_json})")
                    elif orig_s_dict[pname] != new_json: changes_s.append(f"【変更】{pname} ({orig_s_dict[pname]} → {new_json})")
                
                new_names = [r["品名"] for r in new_s_recipes]
                for old_name in orig_s_dict:
                    if old_name not in new_names: changes_s.append(f"【削除】{old_name}")
                
                if not changes_s: st.info("変更はありませんでした。")
                elif any("【削除】" in c for c in changes_s) and not del_ok_s:
                    st.error("調味料レシピの削除が含まれています。削除してよい場合は上のチェックを入れてから、もう一度保存してください。")
                else:
                    updated_all = [r for r in recipes_raw if r.get("大カテゴリ") != "調味料"] + new_s_recipes
                    if hasattr(sheets, "save_recipes"): sheets.save_recipes(updated_all)
                    
                    new_logs = recipe_logs.copy() if recipe_logs else []
                    for c in changes_s:
                        new_logs.append({"ログID": f"RLOG-{now_jst().strftime('%Y%m%d%H%M%S%f')}", "変更日時": now_jst().isoformat(), "担当者": op_recipe, "内容": c})
                    if hasattr(sheets, "save_recipe_logs"): sheets.save_recipe_logs(new_logs)
                    
                    done(f"{len(changes_s)}件の変更を保存しました。")
            card_end()
            
        card_start()
        sec_title("🌡️ 石灰の季節増量・調整ルール設定")
        lime_rows = [{"対象製品": "(全体デフォルト)", "開始月": int(parse_lime_config(order_points).get("start_month", 6)), "終了月": int(parse_lime_config(order_points).get("end_month", 9)), "増量割合(%)": float(parse_lime_config(order_points).get("add_ratio", 0.01)) * 100, "理由": parse_lime_config(order_points).get("reason", "夏場の高温対策")}]
        p_names = sorted([r.get("品名") for r in recipes_raw if r.get("大カテゴリ") != "調味料" and r.get("品名")])
        for p in p_names:
            if f"__LIME_CONFIG_{p}__" in order_points:
                cfg = parse_lime_config(order_points, product_name=p)
                lime_rows.append({"対象製品": p, "開始月": int(cfg.get("start_month", 6)), "終了月": int(cfg.get("end_month", 9)), "増量割合(%)": float(cfg.get("add_ratio", 0.01)) * 100, "理由": cfg.get("reason", "個別設定")})
        
        ed_lime = st.data_editor(pd.DataFrame(lime_rows), num_rows="dynamic", use_container_width=True, column_config={"対象製品": st.column_config.SelectboxColumn("対象製品", options=["(全体デフォルト)"] + p_names, required=True), "開始月": st.column_config.NumberColumn("開始月", min_value=1, max_value=12, step=1, required=True), "終了月": st.column_config.NumberColumn("終了月", min_value=1, max_value=12, step=1, required=True), "増量割合(%)": st.column_config.NumberColumn("増量割合(%)", min_value=0.0, step=0.1, required=True)})
        
        if st.button("💾 石灰ルールを保存", type="primary"):
            new_dict = {k: v for k, v in order_points.items() if not k.startswith("__LIME_CONFIG")}
            for _, r in ed_lime.iterrows():
                tgt = str(r.get("対象製品", "")).strip()
                if tgt and str(tgt).lower() != "nan":
                    new_dict["__LIME_CONFIG__" if tgt == "(全体デフォルト)" else f"__LIME_CONFIG_{tgt}__"] = f"開始:{int(r.get('開始月', 6))}月, 終了:{int(r.get('終了月', 9))}月, 割合:{float(r.get('増量割合(%)', 1.0)) / 100.0}, 理由:{str(r.get('理由', '夏場対策'))}"
            if hasattr(sheets, "save_order_points"): sheets.save_order_points(new_dict); done("更新しました。")
        card_end()

    with t4:
        card_start()
        sec_title("📦 資材マスタの編集・並び替え")
        st.caption("💡 セルを直接編集できます。「表示順」の数字が小さいほど先に表示されます。行を追加すれば新規登録、チェックして削除すれば資材そのものを削除できます（資材IDは自動発行され、変更できません）。")
        sup_rows = []
        for s in sorted_supplies():
            sup_rows.append({
                "資材ID": s.get("資材ID", ""), "表示順": to_float(s.get("表示順", ""), default=None) if str(s.get("表示順", "")).strip() != "" else None,
                "資材名": s.get("資材名", ""), "カテゴリ": s.get("カテゴリ", ""),
                "発注点": to_float(s.get("発注点", 10)), "初期在庫": to_float(s.get("初期在庫", 0)),
            })
        df_sup = pd.DataFrame(sup_rows, columns=["資材ID", "表示順", "資材名", "カテゴリ", "発注点", "初期在庫"])
        ed_sup = st.data_editor(
            df_sup, num_rows="dynamic", use_container_width=True, hide_index=True, key="supply_master_editor",
            column_config={
                "資材ID": st.column_config.TextColumn("資材ID", disabled=True, help="空欄のまま行を追加すると新規登録されます"),
                "表示順": st.column_config.NumberColumn("表示順", step=1, min_value=0),
                "資材名": st.column_config.TextColumn("資材名(必須)", required=True),
                "カテゴリ": st.column_config.TextColumn("カテゴリ(例: 包材)"),
                "発注点": st.column_config.NumberColumn("発注点", min_value=0.0, step=1.0),
                "初期在庫": st.column_config.NumberColumn("初期在庫", min_value=0.0, step=1.0),
            })

        if st.button("💾 資材マスタを保存", type="primary", use_container_width=True, key="save_supply_master"):
            id_to_orig = {s.get("資材ID"): s for s in supplies}
            new_supplies = []
            for _, row in ed_sup.iterrows():
                name = str(row.get("資材名", "")).strip()
                if not name or name.lower() == "nan": continue
                sid = str(row.get("資材ID", "")).strip()
                orig = id_to_orig.get(sid) if sid and sid.lower() != "nan" else None
                rec = dict(orig) if orig else {"資材ID": f"SUP-{now_jst().strftime('%Y%m%d%H%M%S%f')}", "画像URL": "", "登録日": str(today_jst())}
                rec["資材名"] = name
                rec["カテゴリ"] = str(row.get("カテゴリ", "") or "").strip()
                rec["発注点"] = to_float(row.get("発注点", 10))
                rec["初期在庫"] = to_float(row.get("初期在庫", 0))
                order_val = row.get("表示順", None)
                rec["表示順"] = to_float(order_val) if str(order_val).strip() not in ("", "None", "nan") else ""
                new_supplies.append(rec)
            if hasattr(sheets, "save_supplies"):
                sheets.save_supplies(new_supplies); done(f"{len(new_supplies)}件の資材マスタを保存しました。")
        card_end()

        if supplies:
            card_start()
            sec_title("🖼️ 資材の画像を更新")
            sup_by_name = {s.get("資材名"): s for s in sorted_supplies()}
            sel_sup_name = st.selectbox("画像を設定する資材", list(sup_by_name.keys()))
            up_img = st.file_uploader("📷 新しい画像", type=["jpg", "png", "jpeg"], key="sup_img_upl")
            if st.button("💾 画像を保存", key="save_sup_img"):
                if up_img and HAS_PIL:
                    img = Image.open(up_img).convert("RGB"); img.thumbnail((120, 120)); buffered = BytesIO(); img.save(buffered, format="JPEG", quality=70)
                    img_str = f"data:image/jpeg;base64,{base64.b64encode(buffered.getvalue()).decode('utf-8')}"
                    cur_sup = [dict(s) for s in supplies]
                    for s in cur_sup:
                        if s.get("資材名") == sel_sup_name: s["画像URL"] = img_str
                    if hasattr(sheets, "save_supplies"):
                        sheets.save_supplies(cur_sup); done("画像を更新しました。")
                else:
                    st.error("画像ファイルを選択してください。")
            card_end()

    with t5:
        card_start()
        sec_title("🏷️ こんにゃく粉 グレードマスタ")
        ed_grade = st.data_editor(pd.DataFrame({"グレード名": pd.array(parse_grade_list(order_points), dtype="string")}), num_rows="dynamic", use_container_width=True)
        if st.button("💾 グレードマスタ保存", type="primary"):
            save_grade_list(order_points, [str(x).strip() for x in ed_grade["グレード名"].tolist() if x is not None and str(x).strip() and str(x).strip().lower() != "nan"])
            done("保存しました。")
        card_end()
