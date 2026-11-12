import streamlit as st
import pandas as pd
import json
import time
import base64
import re
import html as _html
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
.rsheet-wrap { overflow-x: auto; margin: 6px 0 8px 0; }
table.rsheet { border-collapse: collapse; width: 100%; font-size: 0.92rem; background: #ffffff; }
table.rsheet th, table.rsheet td { border: 1px solid #cbd5e1; padding: 6px 12px; text-align: center; white-space: nowrap; color: var(--c-secondary); }
table.rsheet th { background: var(--c-primary-soft); font-weight: 800; }
table.rsheet td.rl { background: #f1f5f9; font-weight: 800; text-align: left; }
table.rsheet td.water { background: #f8fafc; color: #64748b; }
table.rsheet td.kg { font-weight: 900; font-size: 1.02rem; }
.corr-badge { display: inline-block; background: var(--c-warn-bg); border: 1px solid #f59e0b; color: #78350f; border-radius: 999px; padding: 1px 10px; font-size: 0.8rem; font-weight: 800; }
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

_WRITE_GUARD = {"save_recipes": "recipes", "save_brewing": "brewing", "save_arrivals": "arrivals", "save_materials": "materials",
                "save_supplies": "supplies", "save_inspectors": "inspectors", "save_order_points": "order_points", "save_vendors": "vendors"}

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
            if name == "save_recipes" and a:
                try:
                    a = (recipes_to_sheet_format(a[0]),) + tuple(a[1:])
                    _new_ing = sum(len(_recipe_items(r.get("配合JSON"))) for r in a[0])
                    _cur_ing = sum(len(_recipe_items(r.get("配合JSON"))) for r in ((globals().get("dataset") or {}).get("recipes") or []))
                except Exception:
                    _new_ing = _cur_ing = 0
                if _cur_ing and not _new_ing and not st.session_state.get("_allow_shrink_write"):
                    st.error("🛑 保存を中止しました：すべての配合の原料・比率が空になる内容です。誤操作・データ消失を防ぐため止めています。")
                    st.stop()
            if is_write and name in _WRITE_GUARD and a:
                try:
                    _cur = (globals().get("dataset") or {}).get(_WRITE_GUARD[name]) or []
                    _n_cur, _n_new = len(_cur), len(a[0])
                except Exception:
                    _n_cur = _n_new = 0
                if _n_cur and (_n_new == 0 or (_n_cur >= 4 and _n_new < _n_cur * 0.5)) and not st.session_state.get("_allow_shrink_write"):
                    st.error(f"🛑 保存を中止しました（{name}）：現在 {_n_cur} 件あるデータが {_n_new} 件になる内容です。誤操作・データ消失を防ぐため止めています。"
                             "意図した操作の場合は「🛟 バックアップ・復旧」→「詳細設定」で許可してから、もう一度保存してください。")
                    st.stop()
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

def parse_any_date(s):
    """「2026-11-06」「2026/4/14」「2026年4月14日」など → date（読めなければ None）"""
    m = re.match(r"^\s*(\d{4})\s*[/\-.年]\s*(\d{1,2})\s*[/\-.月]\s*(\d{1,2})", str(s or ""))
    if not m: return None
    try: return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
    except Exception: return None

def norm_date_str(s):
    d = parse_any_date(s)
    return d.isoformat() if d else str(s or "").strip()

arrivals = dataset.get("arrivals") or []
brewing = [{**_b, "仕込日": norm_date_str(_b.get("仕込日"))} for _b in (dataset.get("brewing") or [])]
try: vendors = list(sheets.load_vendors() or []) if hasattr(sheets, "load_vendors") else []
except Exception: vendors = []
dataset["vendors"] = vendors
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
        try: return [{**it, "希釈倍率": it.get("希釈倍率", it.get("比率", 0))} for it in json.loads(r_val)]
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

_ING_LOOSE = re.compile(r"(?:^|[,、，/／\n])\s*([^,、，/／:：()\n]+?)\s*[:：]\s*([\d\.]+)\s*kg\s*(?:\(((?:[^()]|\([^()]*\))*)\))?")

def _parse_ingredients_loose(r_val):
    out = []
    for m in _ING_LOOSE.finditer(str(r_val)):
        try: out.append({"原料名": m.group(1).strip(), "kg": float(m.group(2)), "lot": (m.group(3) or "").strip() or "─"})
        except Exception: pass
    return out

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
        loose = _parse_ingredients_loose(r_val)
        if len(loose) > len(items): items = loose
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

def negative_stock_lots(include_ignored=False):
    """記録上マイナス(入荷より使用が多い)のロット = 入荷登録漏れ・ロット誤入力の疑い（「表示しない」にしたロットは除く）"""
    ig = set() if include_ignored else _neg_ignored_set()
    return [v for v in inventory_data.values() if v["理論残(袋)"] < -EPS_BAGS and f"{v['原料種別']}|{v['ロットNo']}" not in ig]

def _lot_remaining(mat, lot):
    """(原料, ロット) の計算上の残（袋）。同じロットの複数入荷を合算した値（マイナスもそのまま）"""
    return sum(v["理論残(袋)"] for v in inventory_data.values() if v["原料種別"] == mat and v["ロットNo"] == lot)

def _get_active_lots(mat):
    """在庫が0・マイナスのロットは候補から除外する"""
    o = []
    for v in inventory_data.values():
        if v["原料種別"] == mat and v["現在庫(袋)"] > 0 and v["ロットNo"] not in o and round(_lot_remaining(mat, v["ロットNo"]), 2) > 0:
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
    l = [v for v in inventory_data.values() if v["原料種別"] == mat and v["現在庫(袋)"] > 0 and round(_lot_remaining(mat, v["ロットNo"]), 2) > 0]
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
        bags = max(_lot_remaining(mat_name, l), 0.0)
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


def render_excel_history_editor(full_records, filtered_df, id_col, editable_cols, numeric_cols, save_func, key_prefix, reload_func=None, audit=None):
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

            audit_reason, audit_op = "", None
            if audit is not None and (n_c or n_d):
                audit_reason = st.text_input("📝 修正理由（必須・修正記録に残ります）", key=f"{key_prefix}_audit_reason")
                audit_op = render_operator_selector(f"{key_prefix}_audit_op")
            if (n_c or n_d) and st.button("✅ この内容で確定保存する", type="primary", key=f"{key_prefix}_confirm_btn", use_container_width=True, disabled=(not del_ok) or (audit is not None and not audit_reason.strip())):
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
                if audit is not None:
                    audit({str(r.get(id_col)): dict(r) for r in base_records}, id_to_record, audit_reason.strip(), audit_op)   # 先に修正記録を残す
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
    d["修正"] = d["仕込No"].map(lambda n: corr_badge_text(n))
    for _c in ("仕込量(kg)", "石灰水(L)"):
        if _c in d.columns: d[_c] = d[_c].apply(lambda x: int(round(to_float(x))))
    d = d.rename(columns={"メーカー": "担当者"})
    return d

# ════════════════════════════════════════════════════════════════
#  製造記録：配合比のセル別表示 ／ 修正記録（監査ログ） ／ 粉の突合 ／ 粉の消費分析
#   * 修正記録は sheets.append_brewing_correction / load_brewing_corrections があればそれを使用し、
#     無ければ配合履歴シート(recipe_logs)に「【製造修正】{JSON}」として追記（マスタ系シートには書き込まない）
# ════════════════════════════════════════════════════════════════

def _is_water_name(n):
    n = str(n)
    return ("水" in n) or ("お湯" in n)

def _is_lime_name(n):
    n = str(n)
    return ("石灰" in n) or ("カルシウム" in n)

def _lot_blend_pct(lot):
    """ロット表記末尾の「(50%)」からブレンド比率を取り出す（無ければNone）"""
    m = re.search(r"\(\s*([\d\.]+)\s*%\s*\)?\s*$", str(lot or ""))
    return float(m.group(1)) if m else None

def _items_of(b):
    """製造記録の原料リスト。内訳が読めない古い記録は、旧来の列（精粉・海藻粉・デンプン・石灰）から復元する"""
    items = parse_brewing_ingredients(b.get("その他添加物", ""))
    if items: return items
    out = []
    for kgc, lotc, nm in [("こんにゃく精粉(kg)", "主原料ロット", "こんにゃく精粉"), ("海藻粉(kg)", "海藻粉ロット", "海藻粉"),
                          ("デンプン(kg)", "デンプンロット", "デンプン"), ("石灰(kg)", None, "石灰")]:
        kg = to_float(b.get(kgc))
        if kg > 0: out.append({"原料名": nm, "kg": kg, "lot": (str(b.get(lotc, "") or "─") if lotc else "─")})
    return out

def brew_ingredient_ratio_rows(b):
    """1件の製造記録 → 原料ごとの {原料名, kg, ratio(配合比%), basis, blend(ブレンド比%), lot, 水}"""
    total = to_float(b.get("仕込量(kg)"))
    lime_l = to_float(b.get("石灰水(L)"))
    rows = []
    for it in _items_of(b):
        name = str(it.get("原料名", "")).strip()
        if not name: continue
        kg = to_float(it.get("kg"))
        lot_raw = str(it.get("lot", "")).strip()
        water = _is_water_name(name)
        if _is_lime_name(name) and not water:
            ratio = (kg / lime_l * 10.0) if lime_l > 0 else None   # 石灰は「石灰水量」に対する比率
            basis = "石灰水"
        else:
            ratio = (kg / total * 100.0) if total > 0 else None
            basis = "仕込量"
        rows.append({"原料名": name, "kg": kg, "ratio": ratio, "basis": basis,
                     "blend": _lot_blend_pct(lot_raw), "lot": " / ".join(split_lots(lot_raw)) or "─", "lot_raw": lot_raw, "水": water})
    return rows

def recipe_sheet_html(b):
    """配合比を『原料ごとに1列(セル)』で並べた帳票表（投入量／配合比／ブレンド比／ロット）"""
    rows = brew_ingredient_ratio_rows(b)
    if not rows:
        return ""
    e = _html.escape
    head = "<tr><th></th>" + "".join(f"<th>{e(r['原料名'])}</th>" for r in rows) + "<th>合計</th></tr>"
    def cells(fn, extra=""):
        return "".join(f'<td class="{extra}{" water" if r["水"] else ""}">{fn(r)}</td>' for r in rows)
    tot_kg = sum(r["kg"] for r in rows)
    tot_ratio = sum(r["ratio"] for r in rows if r["ratio"] is not None and r["basis"] == "仕込量")
    has_lime = any(r["basis"] == "石灰水" for r in rows)
    r_kg = '<tr><td class="rl">投入量 (kg)</td>' + cells(lambda r: fmt_kg(round(r["kg"], 3)), "kg ") + f'<td class="kg">{fmt_kg(round(tot_kg, 2))}</td></tr>'
    r_ratio = ('<tr><td class="rl">配合比 (%)</td>'
               + cells(lambda r: "—" if r["ratio"] is None else f"{r['ratio']:.2f}" + ("※" if r["basis"] == "石灰水" else ""))
               + f'<td>{tot_ratio:.2f}</td></tr>')
    r_blend = '<tr><td class="rl">ブレンド比 (%)</td>' + cells(lambda r: "—" if r["blend"] is None else f"{fmt_kg(r['blend'])}") + "<td></td></tr>"
    r_lot = '<tr><td class="rl">ロットNo</td>' + cells(lambda r: e(r["lot"])) + "<td></td></tr>"
    note = '<div style="font-size:0.8rem;color:#64748b;">※ 石灰の配合比は石灰水量に対する比率です。それ以外は仕込量に対する比率です。</div>' if has_lime else ""
    return f'<div class="rsheet-wrap"><table class="rsheet">{head}{r_kg}{r_ratio}{r_blend}{r_lot}</table></div>{note}'

def brew_ratio_wide_df(records):
    """製造記録 → 1行1仕込・原料ごとに「投入kg／配合比%／ロット」の列を持つ表（Excel用）"""
    recs = list(records)
    order, per = [], []
    for b in recs:
        rows = brew_ingredient_ratio_rows(b)
        per.append(rows)
        for r in rows:
            if r["原料名"] not in order: order.append(r["原料名"])
    out = []
    for b, rows in zip(recs, per):
        d = {"仕込日": b.get("仕込日", ""), "仕込No": b.get("仕込No", ""), "品名": b.get("品名", ""),
             "担当者": b.get("メーカー", ""), "仕込量(kg)": to_float(b.get("仕込量(kg)"))}
        merged = {}
        for r in rows:
            if r["原料名"] in merged:
                m = merged[r["原料名"]]
                m["kg"] += r["kg"]
                if m["ratio"] is not None and r["ratio"] is not None: m["ratio"] += r["ratio"]
                m["lot"] = f"{m['lot']} / {r['lot']}"
            else:
                merged[r["原料名"]] = dict(r)
        for n in order:
            m = merged.get(n)
            d[f"{n}｜投入kg"] = round(m["kg"], 3) if m else None
            d[f"{n}｜配合比%"] = (round(m["ratio"], 3) if (m and m["ratio"] is not None) else None)
            d[f"{n}｜ロット"] = m["lot"] if m else ""
        out.append(d)
    return pd.DataFrame(out)

# ── 修正記録（監査ログ） ────────────────────────────────────────
CORR_KINDS = ("製造修正", "製造取消")

def _log_text(l):
    return str(l.get("変更内容") or l.get("内容") or "")

def load_brew_corrections(logs=None):
    if hasattr(sheets, "load_brewing_corrections"):
        try: return list(sheets.load_brewing_corrections() or [])
        except Exception: pass
    out = []
    for l in (recipe_logs if logs is None else logs):
        if str(l.get("処理", "")) in CORR_KINDS:
            try: out.append(json.loads(_log_text(l)))
            except Exception: pass
    out.sort(key=lambda x: str(x.get("修正日時", "")), reverse=True)
    return out

def _append_log_rows(rows):
    """配合履歴シート（レシピ変更履歴）に1行ずつ追記する。既存データは書き換えない。"""
    if not hasattr(sheets, "append_recipe_log"):
        st.error("sheets.append_recipe_log が見つからないため、履歴を保存できません。"); st.stop()
    for r in rows: sheets.append_recipe_log(r)

def append_recipe_changes(changes, operator):
    """配合マスタ画面の変更内容（【新規追加】【変更】【削除】）を配合履歴に追記"""
    rows = []
    for i, c in enumerate(changes):
        m = re.match(r"【(.+?)】(.*)$", str(c))
        kind, rest = (m.group(1), m.group(2)) if m else ("変更", str(c))
        rows.append({"ログID": f"RLOG-{now_jst().strftime('%Y%m%d%H%M%S%f')}-{i}", "変更日時": now_jst().isoformat(timespec="seconds"),
                     "品名": rest.split(" (")[0].strip(), "処理": kind, "変更内容": str(c), "作業者": operator or ""})
    _append_log_rows(rows)

def append_brew_corrections(entries):
    """製造記録の修正記録を追記（他のマスタには一切書き込まない）"""
    if not entries: return
    if hasattr(sheets, "append_brewing_correction"):
        for en in entries: sheets.append_brewing_correction(en)
        return
    _append_log_rows([{"ログID": f"CLOG-{now_jst().strftime('%Y%m%d%H%M%S%f')}-{i}", "変更日時": en["修正日時"], "品名": f"仕込No.{en['仕込No']}",
                       "処理": "製造" + en["種別"], "変更内容": json.dumps(en, ensure_ascii=False), "作業者": en.get("修正者", "")} for i, en in enumerate(entries)])

brew_corrections = load_brew_corrections()
corr_by_no = {}
for _c in brew_corrections:
    corr_by_no.setdefault(str(_c.get("仕込No", "")), []).append(_c)
corr_count_by_no = {k: len([c for c in v if c.get("種別") == "修正"]) for k, v in corr_by_no.items()}

def corr_badge_text(no):
    n = corr_count_by_no.get(str(no), 0)
    return f"✏️ 修正{n}回" if n else "─"

BREW_DIFF_FIELDS = [("仕込日", "仕込日", False), ("品名", "品名", False), ("仕込量(kg)", "仕込量(kg)", True),
                    ("石灰水(L)", "石灰水(L)", True), ("メーカー", "担当者", False), ("主原料ロット", "主原料ロット", False), ("備考", "備考", False)]
BREW_EDIT_KEYS = ["仕込日", "品名", "仕込量(kg)", "石灰水(L)", "備考", "その他添加物", "主原料ロット", "こんにゃく精粉(kg)",
                  "海藻粉(kg)", "海藻粉ロット", "デンプン(kg)", "デンプンロット", "石灰(kg)"]

def _ing_str(it):
    return f"{it.get('原料名', '')} {fmt_kg(to_float(it.get('kg')))}kg [{it.get('lot', '─') or '─'}]"

def brew_diff_lines(old, new):
    lines = []
    for f, label, isnum in BREW_DIFF_FIELDS:
        a, b = old.get(f, ""), new.get(f, "")
        if isnum:
            if abs(to_float(a) - to_float(b)) > 1e-9:
                lines.append(f"{label}: {fmt_kg(to_float(a))} → {fmt_kg(to_float(b))}")
        elif str(a if a is not None else "").strip() != str(b if b is not None else "").strip():
            lines.append(f"{label}: {str(a).strip() or '(空)'} → {str(b).strip() or '(空)'}")
    def _keyed(items):
        d, c = {}, {}
        for it in items:
            n = str(it.get("原料名", "")).strip(); c[n] = c.get(n, 0) + 1; d[(n, c[n])] = it
        return d
    oi, ni = _keyed(_items_of(old)), _keyed(_items_of(new))
    for k, b in ni.items():
        if k not in oi: lines.append(f"原料追加: {_ing_str(b)}")
    for k, a in oi.items():
        if k not in ni: lines.append(f"原料削除: {_ing_str(a)}")
        elif _ing_str(a) != _ing_str(ni[k]): lines.append(f"{k[0]}: {_ing_str(a)} → {_ing_str(ni[k])}")
    return lines

def brew_edit_fields(items, b_date, prod, size, lime_l, remarks):
    """編集後の原料リスト等 → 製造記録に書き戻す項目一式（派生項目も再計算）"""
    k_kg = s_kg = st_kg = lime_kg = 0.0
    k_lot = s_lot = st_lot = "─"
    for ing in items:
        n, amt, lot = ing["原料名"], ing["kg"], ing["lot"]
        if "こんにゃく" in n: k_kg += amt; k_lot = lot if k_lot == "─" else (k_lot if lot in k_lot else f"{k_lot} / {lot}")
        elif "海藻" in n: s_kg += amt; s_lot = lot if s_lot == "─" else (s_lot if lot in s_lot else f"{s_lot} / {lot}")
        elif "デンプン" in n or "でんぷん" in n: st_kg += amt; st_lot = lot if st_lot == "─" else (st_lot if lot in st_lot else f"{st_lot} / {lot}")
        elif "石灰" in n or "カルシウム" in n: lime_kg += amt
    return {"仕込日": str(b_date), "品名": prod, "仕込量(kg)": int(round(size)), "石灰水(L)": int(round(lime_l)), "備考": remarks,
            "その他添加物": ", ".join(f"{i['原料名']}:{round(i['kg'], 3)}kg({i['lot']})" for i in items),
            "主原料ロット": k_lot, "こんにゃく精粉(kg)": round(k_kg, 2), "海藻粉(kg)": round(s_kg, 2), "海藻粉ロット": s_lot,
            "デンプン(kg)": round(st_kg, 2), "デンプンロット": st_lot, "石灰(kg)": round(lime_kg, 2)}

def normalize_lot_edit(s):
    """ロット入力の安全化（ブレンド比率の末尾「(50%)」は保持し、それ以外のカンマ・括弧は置換）"""
    s = "" if (s is None or (isinstance(s, float) and s != s)) else str(s).strip()
    if not s or s == "─": return "─"
    m = re.match(r"^(.*?)(\(\s*[\d\.]+\s*%\s*\))?$", s)
    base, tail = sanitize_lot(m.group(1)), (m.group(2) or "").replace(" ", "")
    return (base + tail) if base else "─"

def make_corr_entry(kind, no, operator, reason, lines, snapshot=None, idx=0):
    ts = now_jst()
    en = {"修正ID": f"COR-{ts.strftime('%Y%m%d%H%M%S%f')}-{idx}", "修正日時": ts.isoformat(timespec="seconds"), "仕込No": str(no),
          "種別": kind, "修正者": operator or "", "理由": reason or "", "変更内容": lines}
    if snapshot: en["取消前の記録"] = snapshot
    return en

def brew_audit_save(old_map, new_map, reason, operator):
    """一括編集用：変更・削除された仕込Noごとに修正記録を残す"""
    entries, i = [], 0
    for no, new in new_map.items():
        old = old_map.get(no)
        if old is None: continue
        lines = brew_diff_lines(old, new)
        if lines: entries.append(make_corr_entry("修正", no, operator, reason, lines, idx=i)); i += 1
    for no, old in old_map.items():
        if no not in new_map:
            snap = {k: old.get(k, "") for k in ("仕込日", "品名", "仕込量(kg)", "メーカー", "石灰水(L)", "その他添加物", "備考")}
            entries.append(make_corr_entry("取消", no, operator, reason, ["記録を取消（削除）"], snapshot=snap, idx=i)); i += 1
    append_brew_corrections(entries)

def corr_log_df(entries):
    rows = [{"修正日時": str(c.get("修正日時", "")).replace("T", " "), "仕込No": c.get("仕込No", ""), "種別": c.get("種別", ""),
             "変更内容": " ／ ".join(c.get("変更内容", []) or []), "理由": c.get("理由", ""), "修正者": c.get("修正者", "")} for c in entries]
    return pd.DataFrame(rows, columns=["修正日時", "仕込No", "種別", "変更内容", "理由", "修正者"])

def render_correction_log(entries, key, limit=10, title="📝 修正記録（いつ・誰が・何を・なぜ）"):
    st.markdown(f"**{title}**")
    if not entries:
        st.caption("修正記録はまだありません。")
        return
    df = corr_log_df(entries[:limit])
    st.dataframe(df, use_container_width=True, hide_index=True)
    if len(entries) > limit: st.caption(f"直近{limit}件を表示（全{len(entries)}件は「📋 履歴・帳票」→「📝 修正履歴」）")

def render_brew_correction_editor(records, key_prefix):
    """製造記録を1件選び、仕込日・製品・仕込量・石灰水・備考・各原料の量とロットを修正する。
    確定すると必ず修正記録（理由・修正者・変更内容）が残り、在庫・トレースは自動で再計算される。"""
    recs = [dict(r) for r in records]
    if not recs:
        st.info("修正できる製造記録がありません。"); return
    labels = {f"{r.get('仕込日', '')} ／ No.{r.get('仕込No', '')} ／ {r.get('品名', '')} ／ {fmt_kg(to_float(r.get('仕込量(kg)')))}kg ／ {r.get('メーカー', '')}": str(r.get("仕込No", "")) for r in recs}
    sel = st.selectbox("✏️ 修正する製造記録", list(labels.keys()), key=f"{key_prefix}_sel")
    no = labels[sel]
    rec = next(r for r in recs if str(r.get("仕込No", "")) == no)
    wk = f"{key_prefix}_{no}"
    try: cur_date = datetime.strptime(str(rec.get("仕込日", "")).strip()[:10], "%Y-%m-%d").date()
    except Exception: cur_date = today_jst()
    cur_prod = str(rec.get("品名", ""))
    prod_opts = sorted({str(r.get("品名", "")) for r in recipes_raw if r.get("品名")} | ({cur_prod} if cur_prod else set()))

    c1, c2 = st.columns(2)
    n_date = c1.date_input("📅 仕込日", value=cur_date, key=f"{wk}_date")
    n_prod = c2.selectbox("🍥 製品", prod_opts or [cur_prod], index=(prod_opts.index(cur_prod) if cur_prod in prod_opts else 0), key=f"{wk}_prod")
    c3, c4, c5 = st.columns(3)
    n_size = c3.number_input("🏭 仕込量 (kg)", min_value=0.0, value=float(to_float(rec.get("仕込量(kg)"))), step=1.0, format="%.2f", key=f"{wk}_size")
    n_lime = c4.number_input("💧 石灰水 (L)", min_value=0.0, value=float(to_float(rec.get("石灰水(L)"))), step=0.5, format="%.2f", key=f"{wk}_lime")
    n_rem = c5.text_input("📝 備考", value=str(rec.get("備考", "") or ""), key=f"{wk}_rem")

    items = parse_brewing_ingredients(rec.get("その他添加物", ""))
    df_i = pd.DataFrame([{"原料名": str(it.get("原料名", "")), "投入量(kg)": to_float(it.get("kg")), "ロット": str(it.get("lot", "─") or "─")} for it in items]
                        or [{"原料名": "", "投入量(kg)": 0.0, "ロット": "─"}])
    name_opts = sorted(set(sorted_materials()) | {str(it.get("原料名", "")) for it in items} | {str(i.get("原料名", "")).strip() for r in recipes_raw for i in (safe_parse_recipe(r.get("配合JSON")) if r.get("大カテゴリ") != "調味料" else safe_parse_seasoning_recipe(r.get("配合JSON"))) if str(i.get("原料名", "")).strip()})
    st.caption("原料ごとの投入量とロットを直接修正できます（行の追加・削除も可）。ブレンド時は「L100(50%)」の形のまま編集してください。ロットが無い場合は「─」。")
    edited = st.data_editor(df_i, num_rows="dynamic", use_container_width=True, hide_index=True, key=f"{wk}_ing",
                            column_config={"原料名": st.column_config.SelectboxColumn("原料名", options=name_opts, required=True),
                                           "投入量(kg)": st.column_config.NumberColumn("投入量(kg)", min_value=0.0, format="%.3f"),
                                           "ロット": st.column_config.TextColumn("ロットNo")})

    reason = st.text_input("📝 修正理由（必須・修正記録に残ります）", key=f"{wk}_reason", placeholder="例：石灰の投入量を入力ミス → 実測値に訂正")
    operator = render_operator_selector(f"{wk}_op")

    def _s(x): return "" if (x is None or (isinstance(x, float) and x != x)) else str(x).strip()
    new_items = []
    for _, row in edited.iterrows():
        n = _s(row.get("原料名"))
        if not n: continue
        lot = "─" if _is_water_name(n) else normalize_lot_edit(row.get("ロット"))
        new_items.append({"原料名": n, "kg": to_float(row.get("投入量(kg)")), "lot": lot})
    fields = brew_edit_fields(new_items, n_date, n_prod, n_size, n_lime, n_rem.strip())
    sig = json.dumps(fields, ensure_ascii=False, sort_keys=True)
    pend_key = f"{wk}_pending"

    if st.button("🔍 修正内容を確認する", key=f"{wk}_check", use_container_width=True):
        if not reason.strip():
            st.session_state.pop(pend_key, None); st.error("修正理由を入力してください。")
        else:
            st.session_state[pend_key] = {"sig": sig, "reason": reason.strip(), "op": operator}
    pend = st.session_state.get(pend_key)
    if pend and pend.get("sig") != sig:
        st.session_state.pop(pend_key, None); pend = None
        st.info("入力が変更されたため、もう一度「修正内容を確認する」を押してください。")
    if pend:
        lines = brew_diff_lines(rec, {**rec, **fields})
        if not lines:
            st.info("変更はありません。")
        else:
            st.markdown('<div style="background:#fffbeb;border:2px solid #f59e0b;border-radius:10px;padding:12px;margin:8px 0;"><b>この内容で修正します</b><br>' + "<br>".join("・" + _html.escape(l) for l in lines) + "</div>", unsafe_allow_html=True)
            st.caption("※ 在庫・トレース・分析は修正後の内容で自動的に再計算されます。")
            if st.button("✅ 修正を確定して保存（修正記録に残す）", type="primary", key=f"{wk}_confirm", use_container_width=True):
                try: base = list(sheets.load_brewing() or [])
                except Exception: base = list(brewing)
                idx = next((i for i, r in enumerate(base) if str(r.get("仕込No", "")) == no), None)
                if idx is None:
                    st.error("対象の記録が見つかりません（他の端末で削除された可能性）。「🔄 最新データに更新」を押してください。"); st.stop()
                old_fresh = dict(base[idx]); new_full = {**old_fresh, **fields}
                lines_f = brew_diff_lines(old_fresh, new_full)
                append_brew_corrections([make_corr_entry("修正", no, pend["op"], pend["reason"], lines_f)])   # ① 先に修正記録
                base[idx] = new_full
                sheets.save_brewing(base)                                                                    # ② 記録本体を更新
                for k in [k for k in st.session_state.keys() if str(k).startswith(wk)]: del st.session_state[k]
                done(f"仕込No.{no} を修正しました（修正記録に保存）。")

    st.markdown("---")
    with st.expander("🗑️ この記録を取消（誤登録・二重登録の場合）"):
        st.warning("取消すと製造記録から削除され、在庫・トレース・分析からも除かれます。取消した記録の内容は修正記録に残ります。")
        del_reason = st.text_input("取消理由（必須）", key=f"{wk}_del_reason")
        del_ok = st.checkbox("取消内容を確認しました", key=f"{wk}_del_ok")
        if st.button("🗑️ 取消を確定する", key=f"{wk}_del_btn", disabled=not (del_ok and del_reason.strip()), use_container_width=True):
            try: base = list(sheets.load_brewing() or [])
            except Exception: base = list(brewing)
            target = next((r for r in base if str(r.get("仕込No", "")) == no), None)
            if target is None:
                st.error("対象の記録が見つかりません。「🔄 最新データに更新」を押してください。"); st.stop()
            snap = {k: target.get(k, "") for k in ("仕込日", "品名", "仕込量(kg)", "メーカー", "石灰水(L)", "その他添加物", "備考")}
            append_brew_corrections([make_corr_entry("取消", no, operator, del_reason.strip(), ["記録を取消（削除）"], snapshot=snap)])
            sheets.save_brewing([r for r in base if str(r.get("仕込No", "")) != no])
            for k in [k for k in st.session_state.keys() if str(k).startswith(wk)]: del st.session_state[k]
            done(f"仕込No.{no} を取消しました（修正記録に保存）。")

def _norm_cell(v):
    if v is None or (isinstance(v, float) and v != v): return ""
    if isinstance(v, (int, float)): return round(float(v), 4)
    return str(v).strip()

def _ing_prio(n):
    for i, kw in enumerate(["こんにゃく", "海藻", "デンプン", "でんぷん", "でん粉", "石灰", "カルシウム", "食塩"]):
        if kw in n: return (i, n)
    return (9 if _is_water_name(n) else 8, n)

def render_brew_grid(records, kp, readonly=False):
    """製造記録を「1行=1仕込、原料ごとに kg／配合比%／ロット の列」で表示し、そのままExcelのように編集できる。
    確定時は必ず修正記録（理由・修正者・変更内容）を残す。行を削除すると「取消」として記録される。"""
    recs = [dict(r) for r in records]
    if not recs:
        st.caption("製造記録はまだありません。"); return
    per = []
    for b in recs:
        cnt, rows = {}, []
        for r in brew_ingredient_ratio_rows(b):
            n = r["原料名"]; cnt[n] = cnt.get(n, 0) + 1
            rows.append((n if cnt[n] == 1 else f"{n}#{cnt[n]}", r))
        per.append(dict(rows))
    order = []
    for m in per:
        for cn in m:
            if cn not in order: order.append(cn)
    freq = {cn: sum(1 for m in per if cn in m and m[cn]["kg"] > 0) for cn in order}
    order = sorted(order, key=lambda cn: (-freq[cn], order.index(cn)))
    layout = "col"
    if readonly:
        extra = []
        c_r1, c_r2 = st.columns([1, 2])
        show_ratio = c_r1.checkbox("配合比(%)を表示", value=True, key=f"{kp}_ratio")
        layout = "pack" if c_r2.radio("列の並び", ["🧪 原料ごとの列", "⬅️ 左詰め（記録ごとに原料を左から順に）"], horizontal=True, key=f"{kp}_layout").startswith("⬅️") else "col"
    else:
        c_a, c_b = st.columns([3, 1])
        extra = c_a.multiselect("➕ 記録に無い原料を入力したいときは、ここで列を追加", [x for x in sorted_materials() if x not in order], key=f"{kp}_extra")
        show_ratio = c_b.checkbox("配合比(%)を表示", value=True, key=f"{kp}_ratio")
    order += extra

    rows = []
    for b, m in zip(recs, per):
        no = str(b.get("仕込No", ""))
        d = {"仕込No": no, "修正": corr_badge_text(no), "仕込日": str(b.get("仕込日", "")).strip()[:10], "品名": str(b.get("品名", "")),
             "担当者": str(b.get("メーカー", "")), "仕込量(kg)": int(round(to_float(b.get("仕込量(kg)")))), "石灰水(L)": int(round(to_float(b.get("石灰水(L)")))), "備考": str(b.get("備考", "") or "")}
        for cn in order:
            r = m.get(cn)
            d[f"{cn} kg"] = round(r["kg"], 3) if r else None
            if show_ratio: d[f"{cn} %"] = (round(r["ratio"], 2) if (r and r["ratio"] is not None) else None)
            d[f"{cn} ロット"] = ("" if (not r or r["lot_raw"] in ("─", "")) else r["lot_raw"])
        rows.append(d)
    df = pd.DataFrame(rows)
    prods = sorted({str(r.get("品名", "")) for r in recipes_raw if r.get("品名")} | {d["品名"] for d in rows if d["品名"]})
    ops = sorted(set(inspectors) | {d["担当者"] for d in rows if d["担当者"]})
    cfg = {"仕込No": st.column_config.TextColumn("仕込No", disabled=True), "修正": st.column_config.TextColumn("修正", disabled=True),
           "仕込日": st.column_config.TextColumn("仕込日", help="例 2026-11-06"),
           "品名": st.column_config.TextColumn("品名") if readonly else st.column_config.SelectboxColumn("品名", options=prods),
           "担当者": st.column_config.TextColumn("担当者") if readonly else st.column_config.SelectboxColumn("担当者", options=ops),
           "仕込量(kg)": st.column_config.NumberColumn("仕込量(kg)", format="%d", min_value=0, step=1),
           "石灰水(L)": st.column_config.NumberColumn("石灰水(L)", format="%d", min_value=0, step=1)}
    for cn in order:
        cfg[f"{cn} kg"] = st.column_config.NumberColumn(f"{cn} kg", format="%.2f", min_value=0.0)
        if show_ratio: cfg[f"{cn} %"] = st.column_config.NumberColumn(f"{cn} %", format="%.2f", disabled=True)
        cfg[f"{cn} ロット"] = st.column_config.TextColumn(f"{cn} ロット")
    if readonly and layout == "pack":
        maxn = max((len(m) for m in per), default=0)
        prow = []
        for b, m in zip(recs, per):
            d = {k: rows[len(prow)][k] for k in ("仕込No", "修正", "仕込日", "品名", "担当者", "仕込量(kg)", "石灰水(L)", "備考")}
            its = sorted(m.items(), key=lambda kv: _ing_prio(kv[0].split("#")[0]))
            for i in range(maxn):
                if i < len(its):
                    cn, r = its[i]
                    d[f"原料{i + 1}"] = cn.split("#")[0]; d[f"原料{i + 1} kg"] = round(r["kg"], 3)
                    if show_ratio: d[f"原料{i + 1} %"] = round(r["ratio"], 2) if r["ratio"] is not None else None
                    d[f"原料{i + 1} ロット"] = "" if r["lot_raw"] in ("─", "") else r["lot_raw"]
                else:
                    d[f"原料{i + 1}"] = ""; d[f"原料{i + 1} kg"] = None
                    if show_ratio: d[f"原料{i + 1} %"] = None
                    d[f"原料{i + 1} ロット"] = ""
            prow.append(d)
        pcfg = {k: v for k, v in cfg.items() if k in ("仕込No", "修正", "仕込日", "品名", "担当者", "仕込量(kg)", "石灰水(L)")}
        for i in range(maxn):
            pcfg[f"原料{i + 1} kg"] = st.column_config.NumberColumn(f"原料{i + 1} kg", format="%.2f")
            if show_ratio: pcfg[f"原料{i + 1} %"] = st.column_config.NumberColumn(f"原料{i + 1} %", format="%.2f")
        st.caption("配合のある原料を、記録ごとに左から順（こんにゃく粉 → 海藻粉 → デンプン → 石灰 → その他 → 水）に詰めて表示しています。")
        st.dataframe(pd.DataFrame(prow), use_container_width=True, hide_index=True, column_config=pcfg)
        return
    if readonly:
        st.caption("原料ごとに「kg／配合比％／ロット」を列に分けて表示しています（使われている原料だけ、よく使う順）。修正は「🧾 配合帳票・修正」で行えます。")
        st.dataframe(df, use_container_width=True, hide_index=True, column_config=cfg)
        return
    st.caption("💡 セルをダブルタップして直接直せます（％は自動計算）。直したら下で理由を書いて「確認」→「確定」。行を選んで🗑で取消。修正は必ず記録に残ります。")
    sig0 = hashlib.md5(df.to_json().encode()).hexdigest()[:10]
    edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=True, column_config=cfg, key=f"{kp}_ed_{sig0}")

    reason = st.text_input("📝 修正理由（修正するとき必須・修正記録に残ります）", key=f"{kp}_reason", placeholder="例：石灰の投入量を入力ミス → 実測値に訂正")
    operator = render_operator_selector(f"{kp}_op")
    pend_key = f"{kp}_pending"
    esig = hashlib.md5(edited.to_json().encode()).hexdigest()

    if st.button("🔍 変更内容を確認する", key=f"{kp}_check", use_container_width=True):
        orig = df.set_index("仕込No")
        ed = edited.copy()
        ed["仕込No"] = ed["仕込No"].fillna("").astype(str).str.strip()
        valid = ed[ed["仕込No"] != ""]
        by_no = {str(r.get("仕込No", "")): r for r in recs}
        deleted = sorted(set(orig.index) - set(valid["仕込No"]))
        edit_cols = [c for c in df.columns if c not in ("仕込No", "修正") and not c.endswith(" %")]
        changes, errors = {}, []
        for _, row in valid.iterrows():
            no = row["仕込No"]
            if no not in orig.index: continue
            o = orig.loc[no]
            if all(_norm_cell(row[c]) == _norm_cell(o[c]) for c in edit_cols): continue
            d = parse_any_date(row["仕込日"])
            if d is None: errors.append(f"{no}：仕込日の形式が正しくありません（例 2026-11-06）"); continue
            items = []
            for cn in order:
                kg = to_float(row[f"{cn} kg"])
                if kg <= 0: continue
                nm = cn.split("#")[0]
                lot = "─" if _is_water_name(nm) else normalize_lot_edit(row[f"{cn} ロット"])
                items.append({"原料名": nm, "kg": kg, "lot": lot})
            f = brew_edit_fields(items, d, str(row["品名"]), to_float(row["仕込量(kg)"]), to_float(row["石灰水(L)"]), _norm_cell(row["備考"]) if _norm_cell(row["備考"]) != "" else "")
            f["メーカー"] = str(row["担当者"]) if _norm_cell(row["担当者"]) != "" else by_no[no].get("メーカー", "")
            changes[no] = f
        if not reason.strip() and (changes or deleted): errors.append("修正理由を入力してください。")
        st.session_state[pend_key] = {"sig": esig, "changes": changes, "deleted": deleted, "errors": errors, "reason": reason.strip(), "op": operator}
        st.rerun()

    pend = st.session_state.get(pend_key)
    if pend and pend["sig"] != esig:
        st.session_state.pop(pend_key, None); pend = None
    if pend:
        for e in pend["errors"]: st.error(e)
        if not pend["changes"] and not pend["deleted"] and not pend["errors"]:
            st.info("変更はありませんでした。")
        elif not pend["errors"]:
            by_no = {str(r.get("仕込No", "")): r for r in recs}
            ls = []
            for no, f in pend["changes"].items():
                ls.append(f"<b>No.{_html.escape(no)}</b>：" + " ／ ".join(_html.escape(x) for x in brew_diff_lines(by_no[no], {**by_no[no], **f})))
            for no in pend["deleted"]:
                ls.append(f"<b>No.{_html.escape(no)}</b>：🗑️ 記録を取消（削除）")
            st.markdown('<div style="background:#fffbeb;border:2px solid #f59e0b;border-radius:10px;padding:12px;margin:8px 0;">' + "<br>".join(ls) + "</div>", unsafe_allow_html=True)
            del_ok = True
            if pend["deleted"]:
                st.warning("取消した記録は在庫・トレース・分析から除かれます（内容は修正記録に残ります）。")
                del_ok = st.checkbox("取消内容を確認しました", key=f"{kp}_del_ok")
            if st.button("✅ 確定して保存（修正記録に残す）", type="primary", key=f"{kp}_confirm", use_container_width=True, disabled=not del_ok):
                try: base = list(sheets.load_brewing() or [])
                except Exception: base = list(brewing)
                fresh = {str(r.get("仕込No", "")): dict(r) for r in base}
                entries, i = [], 0
                for no, f in pend["changes"].items():
                    if no not in fresh: continue
                    new_full = {**fresh[no], **f}
                    lines = brew_diff_lines(fresh[no], new_full)
                    if lines: entries.append(make_corr_entry("修正", no, pend["op"], pend["reason"], lines, idx=i)); i += 1
                    fresh[no] = new_full
                for no in pend["deleted"]:
                    if no not in fresh: continue
                    old = fresh.pop(no)
                    snap = {k: old.get(k, "") for k in ("仕込日", "品名", "仕込量(kg)", "メーカー", "石灰水(L)", "その他添加物", "備考")}
                    entries.append(make_corr_entry("取消", no, pend["op"], pend["reason"], ["記録を取消（削除）"], snapshot=snap, idx=i)); i += 1
                _n_after = len(fresh)
                if len(base) and (_n_after == 0 or (len(base) >= 4 and _n_after < len(base) * 0.5)) and not st.session_state.get("_allow_shrink_write"):
                    st.error(f"🛑 保存を中止しました：{len(base)}件の製造記録が{_n_after}件になる内容です。誤操作・データ消失を防ぐため止めています。"
                             "意図した操作の場合は「🛟 バックアップ・復旧」→「詳細設定」で許可してから、もう一度行ってください。")
                    st.stop()
                append_brew_corrections(entries)                                   # ① 先に修正記録
                sheets.save_brewing([fresh[str(r.get("仕込No", ""))] for r in base if str(r.get("仕込No", "")) in fresh])   # ② 本体を更新
                for k in [k for k in st.session_state.keys() if str(k).startswith(kp)]: del st.session_state[k]
                done(f"{len(entries)}件を保存しました（修正記録に残しました）。")


# ── 発注先マスタ（発注品目・メーカー(発注先)・担当者名・連絡先） ───────────────
def _vendor_img(item):
    """品目の画像（原料はマスタの画像、資材は資材マスタの画像）"""
    try:
        img = get_material_image(order_points, item)
        if img: return img
    except Exception: pass
    for s_ in supplies:
        if str(s_.get("資材名", "")).strip() == str(item).strip() and str(s_.get("画像URL", "")).startswith(("data:", "http")):
            return s_.get("画像URL")
    return ""

def vendors_for_item(item):
    return [v for v in vendors if str(v.get("発注品目", "")).strip() == str(item).strip()]

def render_vendor_cards(rows, compact=False):
    """発注先カード（品目画像・発注先・担当者・連絡先）。電話・メールはタップで発信/送信できる"""
    if not rows:
        if not compact: st.info("該当する発注先が登録されていません。「⚙️ マスタ設定 → 📇 発注先」で登録できます。")
        return
    e = _html.escape
    cards = []
    for v in rows:
        tel = str(v.get("連絡先", "")).strip(); mail = str(v.get("メール", "")).strip()
        tel_h = f'<a href="tel:{e(re.sub(r"[^0-9+]", "", tel))}" style="color:#0f766e;font-weight:800;text-decoration:none;">📞 {e(tel)}</a>' if tel else '<span style="color:#94a3b8;">📞 （未登録）</span>'
        mail_h = f'<a href="mailto:{e(mail)}" style="color:#0f766e;text-decoration:none;">✉️ {e(mail)}</a>' if mail else ""
        img = _vendor_img(v.get("発注品目", "")) if not compact else ""
        img_h = f'<img src="{e(img)}" style="width:56px;height:56px;object-fit:cover;border-radius:8px;border:1px solid #cbd5e1;margin-right:12px;">' if img else ""
        note = f'<div style="font-size:0.8rem;color:#64748b;margin-top:4px;">📝 {e(str(v.get("備考", "")))}</div>' if str(v.get("備考", "")).strip() else ""
        pr = to_float(v.get("単価(円)"))
        price_h = f'　💴 <b>{pr:,.0f}円</b>/{e(str(v.get("単位", "")).strip() or "袋")}' if pr > 0 else ""
        cards.append(
            f'<div style="display:flex;align-items:center;border:1px solid #cbd5e1;border-radius:12px;padding:10px 14px;background:#fff;margin:6px 0;">{img_h}'
            f'<div style="flex:1;min-width:0;"><div style="font-weight:900;font-size:1.02rem;">{e(str(v.get("発注品目", "")))}</div>'
            f'<div style="margin-top:2px;">🏢 <b>{e(str(v.get("メーカー(発注先)", "")))}</b>　👤 {e(str(v.get("担当者名", "")) or "（担当者未登録）")}{price_h}</div>'
            f'<div style="margin-top:2px;">{tel_h}　{mail_h}</div>{note}</div></div>')
    st.markdown("".join(cards), unsafe_allow_html=True)

def render_vendor_directory():
    """発注先一覧（いつでも確認できる見やすい一覧）"""
    if not hasattr(sheets, "load_vendors"):
        st.warning("発注先マスタを使うには、新しい sheets.py に差し替えてください。"); return
    c1, c2 = st.columns([2, 1])
    kw = c1.text_input("🔎 検索（品目・発注先・担当者・連絡先）", key="vnd_kw")
    view = c2.radio("表示", ["カード", "一覧表"], horizontal=True, key="vnd_view")
    rows = [v for v in vendors if not kw.strip() or kw.strip().lower() in " ".join(str(x) for x in v.values()).lower()]
    rows = sorted(rows, key=lambda v: (str(v.get("発注品目", "")), str(v.get("メーカー(発注先)", ""))))
    if not vendors:
        st.info("発注先がまだ登録されていません。「⚙️ マスタ設定 → 📇 発注先」で登録できます。"); return
    if view == "一覧表":
        st.dataframe(pd.DataFrame(rows, columns=["発注品目", "メーカー(発注先)", "担当者名", "連絡先", "メール", "単価(円)", "単位", "備考"]), use_container_width=True, hide_index=True)
    else:
        render_vendor_cards(rows)
    st.caption(f"{len(rows)}件")

def render_vendor_master_editor():
    """マスタ設定：発注先の登録・修正（品目ごとに発注先・担当者・連絡先）"""
    if not hasattr(sheets, "save_vendors"):
        st.warning("発注先マスタを使うには、新しい sheets.py に差し替えてください。"); return
    st.caption("発注品目ごとに、発注先（メーカー）・担当者名・連絡先・単価を登録します。発注管理の画面でいつでも確認でき、発注登録時にも自動で表示されます。単価は、粉・原料は「1袋あたり」、資材は「使用数量1あたり」の金額です（分析の金額計算に使います）。品目の画像は「⚗️ 原料マスタ・詳細」「📦 資材」で登録したものが表示されます。")
    items = sorted(set(sorted_materials()) | {str(s_.get("資材名", "")).strip() for s_ in supplies if s_.get("資材名")} | {str(v.get("発注品目", "")).strip() for v in vendors if v.get("発注品目")})
    mk_opts = sorted(set(makers) | {str(v.get("メーカー(発注先)", "")).strip() for v in vendors if v.get("メーカー(発注先)")})
    df = pd.DataFrame(vendors, columns=COLS_VND_UI) if vendors else pd.DataFrame(columns=COLS_VND_UI)
    df["単価(円)"] = df["単価(円)"].apply(to_float)
    sig = hashlib.md5(df.to_json().encode()).hexdigest()[:8]
    edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=True, key=f"vnd_ed_{sig}",
                            column_config={"発注品目": st.column_config.SelectboxColumn("発注品目", options=items, required=True),
                                           "メーカー(発注先)": st.column_config.SelectboxColumn("メーカー(発注先)", options=mk_opts),
                                           "担当者名": st.column_config.TextColumn("担当者名"), "連絡先": st.column_config.TextColumn("連絡先（電話）"),
                                           "メール": st.column_config.TextColumn("メール"), "備考": st.column_config.TextColumn("備考"),
                                           "単価(円)": st.column_config.NumberColumn("💴 単価（円）", min_value=0.0, format="%.2f", help="粉・原料は1袋あたり、資材は使用数量1あたりの金額"),
                                           "単位": st.column_config.SelectboxColumn("単位", options=PRICE_UNITS)})
    rows = []
    for _, r in edited.iterrows():
        d = {c: ("" if pd.isna(r[c]) else str(r[c]).strip()) for c in COLS_VND_UI}
        _pr = to_float(r["単価(円)"])
        d["単価(円)"] = "" if _pr <= 0 else (int(_pr) if _pr == int(_pr) else _pr)
        if d["発注品目"]: rows.append(d)
    n_del = max(0, len(vendors) - len(rows))
    ok = True
    if n_del >= 1:
        st.warning(f"{n_del}件が削除されます。")
        ok = st.checkbox("削除を確認しました", key="vnd_del_ok")
    if st.button("💾 発注先マスタを保存", type="primary", key="vnd_save", disabled=not ok, use_container_width=True):
        if not rows and vendors:
            st.error("全件削除になるため保存を中止しました。"); st.stop()
        sheets.save_vendors(rows)
        done(f"発注先マスタを保存しました（{len(rows)}件）。")

COLS_VND_UI = ["発注品目", "メーカー(発注先)", "担当者名", "連絡先", "メール", "単価(円)", "単位", "備考"]

# ── 入荷に紐づく書類（スキャンPDF・写真）の保管 ───────────────────────
ATT_MAX_MB = 4
ATT_TYPES = ["pdf", "jpg", "jpeg", "png"]

def load_attachments_safe():
    if not hasattr(sheets, "load_attachments"): return None
    try: return list(sheets.load_attachments() or [])
    except Exception: return []

def save_arrival_files(arrival_no, files, operator):
    """アップロードされた書類を入荷Noに紐づけて保管（スプレッドシート内。1ファイル4MBまで）"""
    if not files: return 0
    if not hasattr(sheets, "append_attachment"):
        st.error("書類の保管には、新しい sheets.py への差し替えが必要です。"); st.stop()
    n = 0
    for f in files:
        data = f.getvalue()
        if len(data) > ATT_MAX_MB * 1024 * 1024:
            st.error(f"「{f.name}」は {ATT_MAX_MB}MB を超えているため保管できません。圧縮・縮小してからもう一度お試しください。"); continue
        sheets.append_attachment({"添付ID": f"ATT-{now_jst().strftime('%Y%m%d%H%M%S%f')}-{n}", "入荷No": str(arrival_no), "ファイル名": f.name,
                                  "種別": f.type or "", "サイズ(KB)": round(len(data) / 1024, 1), "登録日時": now_jst().isoformat(timespec="seconds"),
                                  "担当者": operator or ""}, base64.b64encode(data).decode("ascii"))
        n += 1
    return n

def render_arrival_files(arrival_no, atts, key):
    """入荷Noに紐づく書類の一覧（取り出し・削除）"""
    mine = [a for a in (atts or []) if str(a.get("入荷No", "")) == str(arrival_no)]
    if not mine:
        st.caption("この入荷に紐づく書類はまだありません。"); return
    for a in sorted(mine, key=lambda x: str(x.get("登録日時", "")), reverse=True):
        aid = a.get("添付ID")
        c1, c2, c3 = st.columns([4, 1.4, 1])
        c1.markdown(f"📎 **{a.get('ファイル名')}**　<span style='color:#64748b;font-size:0.85rem;'>{a.get('サイズ(KB)')}KB ／ {str(a.get('登録日時', '')).replace('T', ' ')} ／ {a.get('担当者', '')}</span>", unsafe_allow_html=True)
        dk = f"{key}_data_{aid}"
        if dk not in st.session_state:
            if c2.button("📥 開く", key=f"{key}_open_{aid}", use_container_width=True):
                try: st.session_state[dk] = sheets.get_attachment_data(aid)
                except Exception as ex: st.error(f"取り出せませんでした: {ex}")
                st.rerun()
        else:
            raw = base64.b64decode(st.session_state[dk] or "")
            c2.download_button("⬇️ 保存", raw, file_name=str(a.get("ファイル名", "file")), mime=str(a.get("種別") or "application/octet-stream"), key=f"{key}_dl_{aid}", use_container_width=True)
        with c3.popover("🗑️", use_container_width=True):
            st.warning("この書類を削除します。")
            if st.button("削除する", key=f"{key}_del_{aid}", type="primary", use_container_width=True):
                sheets.delete_attachment(aid); st.session_state.pop(dk, None); done("書類を削除しました。", "warn")
        if dk in st.session_state and str(a.get("種別", "")).startswith("image/"):
            st.image(base64.b64decode(st.session_state[dk] or ""), width=360)


# ── 金額（単価）の紐づけ：資材・粉・原料 ───────────────────────────────
PRICE_UNITS = ["袋", "個", "箱", "kg", "L", "本", "枚", "巻"]

def _bag_weight(mat):
    _, wt = parse_op_data(order_points.get(mat, 0.0))
    return wt if wt > 0 else 20.0

def master_price(item):
    """発注先・単価マスタの単価 → (単価, 単位)"""
    for v in vendors_for_item(item):
        p = to_float(v.get("単価(円)"))
        if p > 0: return p, (str(v.get("単位", "")).strip() or "袋")
    return 0.0, ""

def order_price_points(item):
    """発注（単価入力あり）の単価履歴 [(発注日, 単価, 単位, 根拠)] 古い順"""
    pts = []
    for o in parse_purchase_orders(order_points):
        if str(o.get("原料名", "")).strip() == str(item).strip() and o.get("ステータス") != "取消":
            p = to_float(o.get("単価"))
            if p > 0:
                d = norm_date_str(o.get("発注日"))
                pts.append((d, p, str(o.get("単位", "")).strip() or "袋", f"発注 {d}"))
    pts.sort()
    return pts

def default_price_for(item, maker=None):
    """発注登録の初期値：同じ発注先のマスタ単価 → 直近の発注単価 → マスタ単価"""
    for v in vendors_for_item(item):
        if (maker is None or v.get("メーカー(発注先)") == maker) and to_float(v.get("単価(円)")) > 0:
            return to_float(v.get("単価(円)")), (str(v.get("単位", "")).strip() or "袋")
    pts = order_price_points(item)
    if pts: return pts[-1][1], pts[-1][2]
    p, u = master_price(item)
    return p, (u or "袋")

class _PriceBook:
    """使用日ごとの単価を引く（使用日以前で最新の発注単価 → マスタ単価 → それ以降の発注単価）"""
    def __init__(self): self.cache = {}
    def get(self, item, date_s, is_supply):
        pts = self.cache.get(item)
        if pts is None: pts = self.cache[item] = order_price_points(item)
        chosen = None
        for d, p, u, src in pts:
            if d <= date_s: chosen = (p, u, src)
        if chosen is None:
            mp, mu = master_price(item)
            if mp > 0: chosen = (mp, mu or "袋", "マスタ単価")
            elif pts: chosen = (pts[0][1], pts[0][2], pts[0][3] + "（以降の発注）")
        if chosen is None: return None, "未設定"
        p, u, src = chosen
        if is_supply: return p, src                                  # 資材：使用数量1あたりの単価
        return (p if u == "kg" else p / _bag_weight(item)), src      # 粉・原料：kgあたりに換算（袋単価 ÷ 1袋重量）

def render_order_price_editor(orders, update_fn, key):
    """発注の単価・金額を入力／修正する（請求書どおりに後から直せる）"""
    cand = sorted([o for o in orders if o.get("ステータス") != "取消"], key=lambda o: str(o.get("発注日", "")), reverse=True)[:80]
    if not cand:
        st.caption("対象の発注がありません。"); return
    lab = {f"{o.get('発注日', '')} ／ {o.get('原料名', '')} ／ {o.get('メーカー', '')} ／ {fmt_kg(o.get('個数'))}個 ／ "
           + (f"{fmt_kg(to_float(o.get('金額')))}円" if to_float(o.get("金額")) > 0 else "金額未入力"): o for o in cand}
    pick = st.selectbox("発注を選ぶ", list(lab.keys()), key=f"{key}_sel")
    o = lab[pick]; oid = o.get("発注ID")
    d_p, d_u = (to_float(o.get("単価")), str(o.get("単位", "")).strip()) if to_float(o.get("単価")) > 0 else default_price_for(o.get("原料名"), o.get("メーカー"))
    c1, c2 = st.columns(2)
    price = c1.number_input("💴 単価（円）", min_value=0.0, value=float(d_p), step=1.0, format="%.2f", key=f"{key}_p_{oid}")
    unit = c2.selectbox("単位", PRICE_UNITS, index=PRICE_UNITS.index(d_u) if d_u in PRICE_UNITS else 0, key=f"{key}_u_{oid}")
    qty = to_float(o.get("個数"))
    st.caption(f"金額 ＝ {fmt_kg(qty)} × {fmt_kg(price)}円 ＝ **{price * qty:,.0f}円**")
    if st.button("💾 単価・金額を保存", key=f"{key}_save_{oid}", type="primary", use_container_width=True):
        update_fn(oid, **{"単価": price, "単位": unit, "金額": round(price * qty)})
        done(f"単価・金額を保存しました（{o.get('原料名')}：{price * qty:,.0f}円）")

# ── 使用量と金額（日・週・月）の分析 ────────────────────────────────
def build_cost_df():
    """日別の使用量（資材・粉・原料）に単価を当てて金額を出す"""
    pb = _PriceBook()
    rows = []
    u = build_usage_df(brewing)
    if not u.empty:
        u = u[~u["原料名"].astype(str).map(_is_water_name)].copy()
        u["日"] = u["仕込日"].map(norm_date_str)
        for (d, n), kg in u.groupby(["日", "原料名"])["投入量(kg)"].apply(lambda s_: pd.to_numeric(s_, errors="coerce").fillna(0).sum()).items():
            if kg <= 0: continue
            price, src = pb.get(n, d, False)
            rows.append({"日付": d, "区分": "こんにゃく粉" if is_konjac_material(n) else "原料", "品目": n, "数量": float(kg), "単位": "kg",
                         "単価(円/単位)": price, "金額": (kg * price) if price is not None else None, "単価の根拠": src})
    sup = {s_.get("資材ID"): s_.get("資材名") for s_ in supplies}
    for l in supply_logs:
        if l.get("処理") != "使用": continue
        n, q = sup.get(l.get("資材ID")), to_float(l.get("数量"))
        if not n or q <= 0: continue
        d = norm_date_str(l.get("登録日"))
        price, src = pb.get(n, d, True)
        rows.append({"日付": d, "区分": "資材", "品目": n, "数量": q, "単位": "個", "単価(円/単位)": price, "金額": (q * price) if price is not None else None, "単価の根拠": src})
    df = pd.DataFrame(rows, columns=["日付", "区分", "品目", "数量", "単位", "単価(円/単位)", "金額", "単価の根拠"])
    df["日付_dt"] = pd.to_datetime(df["日付"], errors="coerce")
    df = df[df["日付_dt"].notna()].copy()
    for c in ("単価(円/単位)", "金額"): df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def _period_labels(dt, gran):
    if gran == "日": return dt.dt.strftime("%Y-%m-%d")
    if gran == "週": return (dt - pd.to_timedelta(dt.dt.weekday, unit="D")).dt.strftime("%Y-%m-%d") + "週"
    return dt.dt.strftime("%Y-%m")

def _period_index(d_from, d_to, gran):
    idx = pd.date_range(pd.Timestamp(d_from), pd.Timestamp(d_to), freq="D")
    return list(dict.fromkeys(_period_labels(pd.Series(idx), gran)))

def _yen(x):
    return "－" if x is None or (isinstance(x, float) and x != x) else f"{x:,.0f}"

def render_cost_analysis():
    df0 = build_cost_df()
    if df0.empty:
        st.info("使用実績（製造記録・資材の使用ログ）がまだありません。"); return

    card_start()
    c1, c2, c3 = st.columns([1.2, 2.2, 1.2])
    with c1: s_d, e_d = period_select("cost", default="今月")
    with c2: kind = st.radio("📦 対象", ["すべて", "🧻 資材", "🌾 こんにゃく粉", "📦 その他の原料"], horizontal=True, key="cost_kind")
    base0 = df0
    if "資材" in kind: base0 = df0[df0["区分"] == "資材"]
    elif "こんにゃく粉" in kind: base0 = df0[df0["区分"] == "こんにゃく粉"]
    elif "その他" in kind: base0 = df0[df0["区分"] == "原料"]
    with st.expander("🔎 品目を絞り込む（必要なときだけ）"):
        sel_items = st.multiselect("品目", sorted(base0["品目"].unique()), key="cost_items")
    if sel_items: base0 = base0[base0["品目"].isin(sel_items)]
    d_min, d_max = df0["日付_dt"].min().date(), df0["日付_dt"].max().date()
    d_from, d_to = (s_d or d_min), (e_d or d_max)
    days = max(1, (d_to - d_from).days + 1)
    with c3: gran = st.radio("📅 集計", ["日", "週", "月"], horizontal=True, index=2 if days > 90 else (1 if days > 31 else 0), key="cost_gran")
    card_end()

    cur = base0[(base0["日付_dt"].dt.date >= d_from) & (base0["日付_dt"].dt.date <= d_to)].copy()
    if cur.empty:
        st.info("対象期間内の使用実績がありません。"); return
    cur["期間"] = _period_labels(cur["日付_dt"], gran)
    tot = cur["金額"].sum()
    missing = sorted(cur[cur["金額"].isna()]["品目"].unique())
    delta = None
    prev = None
    if s_d is not None:
        p_to = d_from - timedelta(days=1); p_from = p_to - timedelta(days=days - 1)
        prev = base0[(base0["日付_dt"].dt.date >= p_from) & (base0["日付_dt"].dt.date <= p_to)].copy()
        if not prev.empty and prev["金額"].sum() > 0: delta = f"{(tot - prev['金額'].sum()) / prev['金額'].sum() * 100:+.1f}%（前の{days}日比）"
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💴 総金額", f"{tot:,.0f} 円", delta=delta, delta_color="inverse")
    k2.metric("1日あたり", f"{tot / days:,.0f} 円")
    k3.metric("使用した品目", f"{cur['品目'].nunique()} 品目")
    k4.metric("単価未設定", f"{len(missing)} 品目")
    if missing:
        st.warning("単価が未設定の品目は、金額に含まれていません：" + "、".join(missing[:12]) + ("…" if len(missing) > 12 else "")
                   + "　→「⚙️ マスタ設定 → 📇 発注先」または「📝 発注管理」で単価を入れると反映されます。")

    t_tr, t_cmp, t_rec = st.tabs(["📅 推移（日・週・月）", "🆚 比較・統計", "🧾 記録（日別の数量と金額）"])

    with t_tr:
        card_start()
        a1, a2 = st.columns(2)
        metric = a1.radio("見る項目", ["💴 金額", "📦 数量"], horizontal=True, key="cost_metric")
        stack = a2.radio("内訳", ["品目別", "区分別", "合計のみ"], horizontal=True, key="cost_stack")
        use_amt = metric.startswith("💴")
        ycol = "金額" if use_amt else "数量"
        if not use_amt and cur["単位"].nunique() > 1:
            st.info("数量は「資材（個）」と「粉・原料（kg）」で単位が違います。上の「対象」を選ぶと数量で見られます。")
        else:
            work = cur.copy()
            if stack == "品目別":
                top = work.groupby("品目")[ycol].sum().sort_values(ascending=False).head(12).index
                work["内訳"] = work["品目"].where(work["品目"].isin(top), "その他")
            elif stack == "区分別": work["内訳"] = work["区分"]
            else: work["内訳"] = "合計"
            g = work.groupby(["期間", "内訳"])[ycol].sum().reset_index().sort_values("期間")
            fig = px.bar(g, x="期間", y=ycol, color="内訳" if stack != "合計のみ" else None, barmode="stack", title=f"{gran}別 {'金額(円)' if use_amt else '数量'}")
            fig.update_xaxes(type="category"); fig.update_layout(plot_bgcolor="#ffffff", yaxis_title="円" if use_amt else (cur["単位"].iloc[0]))
            if stack == "合計のみ": fig.update_traces(marker_color="#0f766e")
            st.plotly_chart(fig, use_container_width=True)
            pv = work.pivot_table(index="期間", columns="品目", values=ycol, aggfunc="sum", fill_value=0)
            pv["合計"] = pv.sum(axis=1)
            pv = pv.sort_index().reset_index()
            fmt = (lambda x: f"{x:,.0f}") if use_amt else (lambda x: fmt_kg(round(x, 2)))
            st.dataframe(pv.assign(**{c: pv[c].map(fmt) for c in pv.columns if c != "期間"}), use_container_width=True, hide_index=True)
            download_buttons({f"{gran}別_{'金額' if use_amt else '数量'}": pv}, f"使用量と金額_{gran}別_{today_jst()}", "cost_tr_dl")
        card_end()

    with t_cmp:
        card_start()
        mode = st.radio("比較のしかた", ["前の同じ長さの期間と比べる", "月ごとに並べる（直近6か月）"], horizontal=True, key="cost_cmp")
        if mode.startswith("前"):
            if prev is None:
                st.info("「全期間」では比較できません。期間を選んでください。")
            else:
                gc = cur.groupby("品目").agg(今期_数量=("数量", "sum"), 今期_金額=("金額", "sum"), 単位=("単位", "first")).reset_index()
                gp = prev.groupby("品目").agg(前期_数量=("数量", "sum"), 前期_金額=("金額", "sum")).reset_index()
                m = gc.merge(gp, on="品目", how="outer").fillna({"今期_数量": 0, "今期_金額": 0, "前期_数量": 0, "前期_金額": 0, "単位": ""})
                m["数量増減%"] = [round((a - b) / b * 100, 1) if b else None for a, b in zip(m["今期_数量"], m["前期_数量"])]
                m["金額増減"] = m["今期_金額"] - m["前期_金額"]
                m["金額増減%"] = [round((a - b) / b * 100, 1) if b else None for a, b in zip(m["今期_金額"], m["前期_金額"])]
                m = m.sort_values("今期_金額", ascending=False)
                st.caption(f"今期：{d_from}〜{d_to} ／ 前期：{d_from - timedelta(days=days)}〜{d_from - timedelta(days=1)}")
                top = m.head(15)
                figc = px.bar(top.melt(id_vars="品目", value_vars=["今期_金額", "前期_金額"], var_name="期間", value_name="金額"), x="品目", y="金額", color="期間", barmode="group", title="品目別 金額（今期 vs 前期）")
                figc.update_layout(plot_bgcolor="#ffffff"); st.plotly_chart(figc, use_container_width=True)
                shown = m[["品目", "単位", "今期_数量", "前期_数量", "数量増減%", "今期_金額", "前期_金額", "金額増減", "金額増減%"]]
                st.dataframe(fmt_df_numeric(shown, ["今期_数量", "前期_数量", "今期_金額", "前期_金額", "金額増減"]), use_container_width=True, hide_index=True)
                download_buttons({"前期比較": shown}, f"前期比較_{today_jst()}", "cost_cmp_dl")
        else:
            mm = base0.copy(); mm["月"] = mm["日付_dt"].dt.strftime("%Y-%m")
            months = sorted(mm["月"].unique())[-6:]
            mm = mm[mm["月"].isin(months)]
            pvm = mm.pivot_table(index="品目", columns="月", values="金額", aggfunc="sum", fill_value=0)
            pvm["合計"] = pvm.sum(axis=1); pvm = pvm.sort_values("合計", ascending=False).reset_index()
            figm = px.bar(mm.groupby(["月", "区分"])["金額"].sum().reset_index(), x="月", y="金額", color="区分", barmode="stack", title="月別 金額（区分別）")
            figm.update_xaxes(type="category"); figm.update_layout(plot_bgcolor="#ffffff"); st.plotly_chart(figm, use_container_width=True)
            st.dataframe(pvm.assign(**{c: pvm[c].map(lambda x: f"{x:,.0f}") for c in pvm.columns if c != "品目"}), use_container_width=True, hide_index=True)
            download_buttons({"月別比較": pvm}, f"月別比較_{today_jst()}", "cost_cmp2_dl")

        st.markdown("---")
        sec_title(f"📈 統計（{gran}ごとの使用量のばらつき）")
        idx = _period_index(d_from, d_to, gran)
        srows = []
        for item, g in cur.groupby("品目"):
            sq = g.groupby("期間")["数量"].sum().reindex(idx, fill_value=0)
            sm = g.groupby("期間")["金額"].sum().reindex(idx, fill_value=0)
            srows.append({"品目": item, "区分": g["区分"].iloc[0], "単位": g["単位"].iloc[0], f"{gran}の数": len(idx), "使用した期間": int((sq > 0).sum()),
                          "平均数量": round(sq.mean(), 2), "最大": round(sq.max(), 2), "最小": round(sq.min(), 2), "標準偏差": round(sq.std(ddof=0), 2),
                          "平均金額": round(sm.mean()), "最大金額": round(sm.max()), "合計金額": round(sm.sum())})
        sdf = pd.DataFrame(srows).sort_values("合計金額", ascending=False)
        st.dataframe(fmt_df_numeric(sdf, ["平均数量", "最大", "最小", "標準偏差", "平均金額", "最大金額", "合計金額"]), use_container_width=True, hide_index=True)
        download_buttons({"統計": sdf}, f"使用量統計_{gran}_{today_jst()}", "cost_stat_dl")

        st.markdown("---")
        sec_title("🔍 検証：発注金額と使用金額（月別）")
        st.caption("発注した金額と、使った分の金額を月ごとに並べます。大きく食い違う月は、入荷・使用の記録や単価の入力を確認してください。")
        po = []
        names_in_scope = set(base0["品目"].unique())
        for o in parse_purchase_orders(order_points):
            if o.get("ステータス") == "取消" or o.get("原料名") not in names_in_scope: continue
            d = parse_any_date(o.get("発注日"))
            amt = to_float(o.get("金額")) or (to_float(o.get("単価")) * to_float(o.get("個数")))
            if d and amt > 0 and d_from <= d <= d_to: po.append({"月": d.strftime("%Y-%m"), "発注金額": amt})
        used = cur.assign(月=cur["日付_dt"].dt.strftime("%Y-%m")).groupby("月")["金額"].sum().rename("使用金額")
        ordd = pd.DataFrame(po, columns=["月", "発注金額"]).groupby("月")["発注金額"].sum() if po else pd.Series(dtype=float, name="発注金額")
        vf = pd.concat([ordd, used], axis=1).fillna(0).reset_index().rename(columns={"index": "月"})
        if vf.empty: st.caption("対象期間に発注金額の入力がありません。")
        else:
            vf["差（発注−使用）"] = vf["発注金額"] - vf["使用金額"]
            st.dataframe(fmt_df_numeric(vf, ["発注金額", "使用金額", "差（発注−使用）"]), use_container_width=True, hide_index=True)
        card_end()

    with t_rec:
        card_start()
        only_missing = st.checkbox("単価が未設定の記録だけ表示", key="cost_only_missing")
        rec = cur[["日付", "区分", "品目", "数量", "単位", "単価(円/単位)", "金額", "単価の根拠"]].copy()
        if only_missing: rec = rec[rec["金額"].isna()]
        rec = rec.sort_values(["日付", "区分", "品目"], ascending=[False, True, True])
        rec["数量"] = rec["数量"].round(3); rec["単価(円/単位)"] = rec["単価(円/単位)"].round(2); rec["金額"] = rec["金額"].round(0)
        st.caption(f"{len(rec)}件 ／ 金額合計 {rec['金額'].sum():,.0f} 円")
        st.dataframe(fmt_df_numeric(rec.head(500), ["数量", "単価(円/単位)", "金額"]), use_container_width=True, hide_index=True)
        if len(rec) > 500: st.caption("画面には新しい順に500件を表示。ダウンロードには全件が入ります。")
        download_buttons({"使用量と金額（日別）": rec}, f"使用量と金額_日別_{today_jst()}", "cost_rec_dl")
        card_end()


# ── 粉の突合・リセット（理論在庫と現場の実在庫のズレを直す） ───────────────
RECON_REASONS = ["計量誤差・端数", "こぼれ・ロス", "入荷登録漏れ", "ロット誤入力・取り違え", "その他"]

def _lot_groups():
    """(原料, ロット) 単位に集約した理論在庫"""
    g = {}
    for v in inventory_data.values():
        key = (v["原料種別"], v["ロットNo"])
        x = g.setdefault(key, {"原料": v["原料種別"], "ロットNo": v["ロットNo"], "メーカー": v["メーカー"], "グレード": v["グレード"], "入荷日": v["入荷日"],
                               "入荷袋数": 0.0, "使用袋数": 0.0, "調整袋数": 0.0, "理論残": 0.0, "現在庫": 0.0, "1袋重量": v["1袋重量"], "arrivals": []})
        x["入荷袋数"] += v["入荷袋数"]; x["使用袋数"] += v["使用袋数"]; x["調整袋数"] += v["調整袋数"]
        x["理論残"] += v["理論残(袋)"]; x["現在庫"] += v["現在庫(袋)"]
        x["arrivals"].append((_lot_date_sort_key(v["入荷日"]), v["入荷No"]))
    for x in g.values():
        x["arrivals"].sort()
        x["最新入荷No"] = x["arrivals"][-1][1]
    return g

def _save_recon(changes, cat, note, op):
    if not hasattr(sheets, "append_adjustment"):
        st.error("sheets.append_adjustment が見つかりません。"); st.stop()
    for i, c in enumerate(changes):
        sheets.append_adjustment({
            "調整ID": f"ADJ-{now_jst().strftime('%Y%m%d%H%M%S%f')}-{i}", "入荷No": c["入荷No"], "調整日": str(today_jst()),
            "調整袋数": c["差分"], "理由": f"【突合】{cat} 計算{fmt_kg(round(c['計算'], 3))}→実{fmt_kg(round(c['実'], 3))}袋 {note}".strip(),
            "担当者": op, "登録日時": now_jst().isoformat()})

def render_flour_reconcile():
    st.markdown("**現場の実在庫に合わせて、計算上の在庫をリセットします。** 「現場にあるのに計算上は無い」「計算上あるのに現場には無い」どちらにも対応します。"
                "調整は差分として履歴に残り、元の入荷・製造記録は変わりません。")
    groups = _lot_groups()
    mats = sorted({k[0] for k in groups})
    c1, c2, c3 = st.columns([2, 2, 2])
    f_mat = c1.selectbox("🔎 原料", ["🌾 こんにゃく粉すべて", "すべての原料"] + mats, key="recon_mat")
    show_zero = c2.checkbox("在庫0のロットも表示", value=False, key="recon_zero", help="現場で見つかった在庫を計算上に戻したいときにチェック")
    kw = c3.text_input("🔎 ロットNo検索", key="recon_kw")

    def _hit(x):
        if f_mat.startswith("🌾"): ok = is_konjac_material(x["原料"])
        elif f_mat == "すべての原料": ok = True
        else: ok = (x["原料"] == f_mat)
        if not ok: return False
        if kw.strip() and kw.strip().lower() not in x["ロットNo"].lower(): return False
        return show_zero or x["現在庫"] > 0 or abs(x["理論残"]) >= EPS_BAGS
    rows = sorted([x for x in groups.values() if _hit(x)], key=lambda x: (x["原料"], x["入荷日"], x["ロットNo"]))
    if not rows:
        st.info("条件に合うロットがありません。（入荷登録そのものが無い粉は「📥 入荷登録」から先に登録してください）"); return

    def _state(x):
        if x["理論残"] < -EPS_BAGS: return "❓ 計算上マイナス（現場には有るはず）"
        if x["現在庫"] <= 0: return "⚪ 計算上0"
        return "✅ 在庫あり"
    default_actual = {i: round(max(snap_zero(x["理論残"], EPS_BAGS), 0.0), 3) for i, x in enumerate(rows)}
    df = pd.DataFrame([{"原料": x["原料"], "ロットNo": x["ロットNo"], "メーカー": x["メーカー"], "グレード": x["グレード"], "入荷日": x["入荷日"],
                        "入荷(袋)": round(x["入荷袋数"], 3), "使用(袋)": round(x["使用袋数"], 3), "調整累計(袋)": round(x["調整袋数"], 3),
                        "計算上の残(袋)": round(x["理論残"], 3), "状態": _state(x),
                        "現場の実在庫(袋)": default_actual[i], "🔄 計算値を0にリセット": False} for i, x in enumerate(rows)])
    cfg = {c: st.column_config.TextColumn(c, disabled=True) for c in ["原料", "ロットNo", "メーカー", "グレード", "入荷日", "状態"]}
    for c in ["入荷(袋)", "使用(袋)", "調整累計(袋)", "計算上の残(袋)"]:
        cfg[c] = st.column_config.NumberColumn(c, format="%.3f", disabled=True)
    cfg["現場の実在庫(袋)"] = st.column_config.NumberColumn("現場の実在庫(袋)【入力】", format="%.3f", min_value=0.0, step=0.1)
    cfg["🔄 計算値を0にリセット"] = st.column_config.CheckboxColumn("🔄 現場も0（リセット）", help="計算上マイナスで現場も無い場合などにチェック")
    st.caption("💡 「現場の実在庫(袋)」に実際の袋数（端数は小数）を入力。計算上マイナスのロットを0に戻すときは右端にチェック。")
    edited = st.data_editor(df, use_container_width=True, hide_index=True, num_rows="fixed", column_config=cfg, key=f"recon_ed_{f_mat}_{kw}_{show_zero}")

    dk = "recon_pending"
    cA, cB = st.columns([2, 1])
    if cA.button("🔍 変更内容を確認する", key="recon_check", use_container_width=True):
        changes = []
        for i, (_, r) in enumerate(edited.iterrows()):
            x = rows[i]
            actual = max(0.0, to_float(r["現場の実在庫(袋)"]))
            if actual < EPS_BAGS: actual = 0.0
            flag = bool(r["🔄 計算値を0にリセット"])
            if flag: actual = 0.0
            if flag or abs(actual - default_actual[i]) > 0.0005:
                diff = round(actual - x["理論残"], 4)
                if abs(diff) < 0.0005: continue
                changes.append({"原料": x["原料"], "ロットNo": x["ロットNo"], "入荷No": x["最新入荷No"], "計算": x["理論残"], "実": actual, "差分": diff, "1袋重量": x["1袋重量"]})
        st.session_state[dk] = changes; st.rerun()
    if cB.button("❌ 取消", key="recon_cancel", use_container_width=True):
        st.session_state.pop(dk, None); st.rerun()

    changes = st.session_state.get(dk)
    if changes is not None:
        if not changes:
            st.info("変更はありませんでした。")
        else:
            lines = [f"{'➕ 現場の方が多い' if c['差分'] > 0 else '➖ 現場の方が少ない'}　{c['原料']} ／ {c['ロットNo']}：計算 {fmt_kg(round(c['計算'], 2))}袋 → 実 {fmt_kg(round(c['実'], 2))}袋"
                     f"（{c['差分']:+.2f}袋 ≒ {c['差分'] * c['1袋重量']:+.1f}kg）" for c in changes]
            st.markdown('<div style="background:#fffbeb;border:2px solid #f59e0b;border-radius:10px;padding:14px;margin:10px 0;">' + "<br>".join(_html.escape(l) for l in lines) + "</div>", unsafe_allow_html=True)
            cat = st.selectbox("差異の原因", RECON_REASONS, key="recon_cat")
            note = st.text_input("補足メモ（任意）", key="recon_note")
            op = render_operator_selector("recon_op")
            if st.button("✅ 確定してリセット（履歴に記録）", type="primary", key="recon_confirm", use_container_width=True):
                _save_recon(changes, cat, note, op)
                st.session_state.pop(dk, None)
                done(f"{len(changes)}件のロットを現場の実在庫に合わせました。")

    neg = negative_stock_lots()
    if neg:
        with st.expander(f"❓ 計算上マイナスのロットを一括で0に戻す（{len(neg)}件）"):
            st.caption("入荷登録漏れ・ロット誤入力などで、使用量が入荷量を上回っているロットです。現場にも無い（使い切った）場合に使います。")
            for v in neg:
                st.write(f"・{v['原料種別']} ／ {v['ロットNo']}：計算 {fmt_kg(round(v['理論残(袋)'], 2))}袋 → 0袋")
            nop = render_operator_selector("recon_neg_op")
            if st.button("🧹 マイナスをすべて0にリセット", key="recon_neg_btn", use_container_width=True):
                ch = [{"入荷No": v["入荷No"], "計算": v["理論残(袋)"], "実": 0.0, "差分": round(-v["理論残(袋)"], 4)} for v in neg]
                _save_recon(ch, "ロット誤入力・取り違え", "マイナス在庫の一括リセット", nop)
                done(f"{len(ch)}件のマイナス在庫を0にリセットしました。")

# ── マイナス在庫（使用量＞入荷量）の警告：リセット／表示しない ───────────────
def _neg_ignored_set():
    best = None
    for l in recipe_logs:
        if str(l.get("処理", "")) == "設定" and str(l.get("品名", "")) == "マイナス警告非表示":
            k = (str(l.get("変更日時", "")), str(l.get("ログID", "")))
            if best is None or k > best[0]: best = (k, _log_text(l))
    if not best: return set()
    try: return set(json.loads(best[1]))
    except Exception: return set()

def save_neg_ignored(keys):
    _append_log_rows([{"ログID": f"SLOG-{now_jst().strftime('%Y%m%d%H%M%S%f')}", "変更日時": now_jst().isoformat(timespec="seconds"), "品名": "マイナス警告非表示",
                       "処理": "設定", "変更内容": json.dumps(sorted(set(keys)), ensure_ascii=False), "作業者": ""}])

def render_negative_panel():
    neg = negative_stock_lots()
    ig = _neg_ignored_set()
    if neg:
        alert_box("❓ 入荷量より使用量が多いロットがあります（入荷登録漏れ・ロット誤入力・テスト運用データの疑い）：<br>" +
                  "<br>".join(f"・{v['原料種別']} / {v['ロットNo']}（入荷{fmt_kg(v['入荷袋数'])}袋 ＜ 使用{fmt_kg(round(v['使用袋数'], 2))}袋）" for v in neg), "warn")
        st.caption("現場の実数と合わないときは、0にリセット（履歴に残ります）するか、警告を表示しないようにできます。")
        op = render_operator_selector("neg_panel_op")
        c1, c2 = st.columns(2)
        if c1.button("🧹 すべて0にリセット（調整として記録）", key="neg_panel_reset", use_container_width=True):
            _save_recon([{"入荷No": v["入荷No"], "計算": v["理論残(袋)"], "実": 0.0, "差分": round(-v["理論残(袋)"], 4)} for v in neg],
                        "ロット誤入力・取り違え", "マイナス在庫の一括リセット", op)
            done(f"{len(neg)}件のマイナス在庫を0にリセットしました。")
        if c2.button("🙈 これらの警告を表示しない", key="neg_panel_hide", use_container_width=True):
            save_neg_ignored(ig | {f"{v['原料種別']}|{v['ロットNo']}" for v in neg})
            done(f"{len(neg)}件の警告を非表示にしました（在庫の計算は変わりません）。")
    if ig:
        with st.expander(f"🙈 警告を非表示にしているロット（{len(ig)}件）"):
            for k in sorted(ig): st.write("・" + k.replace("|", " ／ "))
            if st.button("👁️ 非表示をすべて解除", key="neg_panel_unhide"):
                save_neg_ignored(set()); done("非表示を解除しました。")


# ── バックアップ・復旧 ──────────────────────────────────────────
def _full_backup_dict():
    return {"_作成日時": now_jst().isoformat(timespec="seconds"), "recipes": recipes_raw, "recipe_logs": recipe_logs, "brewing": brewing, "arrivals": arrivals,
            "adjustments": adjustments, "materials": materials, "makers": makers, "inspectors": inspectors, "supplies": supplies,
            "supply_logs": supply_logs, "order_points": order_points}

def _backup_excel_bytes():
    import io
    d = _full_backup_dict(); bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as xw:
        for k, nm in [("recipes", "配合マスタ"), ("recipe_logs", "配合履歴"), ("brewing", "製造記録"), ("arrivals", "入荷"), ("adjustments", "棚卸調整"),
                      ("supplies", "資材マスタ"), ("supply_logs", "資材ログ")]:
            pd.DataFrame(d[k]).to_excel(xw, sheet_name=nm, index=False)
        pd.DataFrame({"原料名": list(materials)}).to_excel(xw, sheet_name="原料マスタ", index=False)
        pd.DataFrame({"担当者名": list(inspectors)}).to_excel(xw, sheet_name="担当者", index=False)
        pd.DataFrame([{"キー": k, "値": (str(v)[:30000] + "…(省略)") if len(str(v)) > 30000 else v} for k, v in order_points.items()]).to_excel(xw, sheet_name="発注点・設定", index=False)
    return bio.getvalue()

def _recipe_items(v):
    """配合の値（JSON文字列／リスト／「原料:5.0%, 水:95.0%」の文字列）→ [(原料名, 数値)]"""
    if isinstance(v, str) and v.strip().startswith("["):
        try: v = json.loads(v)
        except Exception: v = []
    if isinstance(v, list):
        out = []
        for it in v:
            if isinstance(it, dict) and str(it.get("原料名", "")).strip():
                try: out.append((str(it["原料名"]).strip(), float(it.get("比率", it.get("希釈倍率", 0)) or 0)))
                except Exception: pass
        return out
    out = []
    for p in str(v or "").split(","):
        if ":" in p:
            n, r = p.split(":", 1)
            try: out.append((n.strip(), float(r.replace("%", "").replace("倍", "").strip())))
            except Exception: pass
    return out

def _recipe_text(v, unit="%"):
    return ", ".join(f"{n}:{x}{unit}" for n, x in _recipe_items(v))

def recipes_to_sheet_format(recs):
    """配合マスタに保存する形（配合JSON＝[{原料名, 比率}]のJSON）へ統一。文字列形式のままだと原料が空で保存されてしまうため"""
    out = []
    for r in recs:
        d = dict(r)
        d["配合JSON"] = json.dumps([{"原料名": n, "比率": x} for n, x in _recipe_items(r.get("配合JSON"))], ensure_ascii=False)
        out.append(d)
    return out

def recipes_from_logs(logs):
    """配合履歴（【新規追加】【変更】【削除】）を時系列に再生して、最新の配合マスタを再構成する"""
    cur = {}
    for l in sorted(logs, key=lambda x: (str(x.get("変更日時", "")), str(x.get("ログID", "")))):
        c = _log_text(l).strip()
        try:
            if c.startswith("【新規追加】") and c.endswith(")"):
                name, js = c[len("【新規追加】"):-1].rsplit(" (", 1)
            elif c.startswith("【変更】") and c.endswith(")"):
                name, inner = c[len("【変更】"):-1].rsplit(" (", 1); js = inner.split(" → ")[-1]
            elif c.startswith("【削除】"):
                cur.pop(c[len("【削除】"):].strip(), None); continue
            else:
                continue
        except Exception:
            continue
        name, js = name.strip(), js.strip()
        old = cur.get(name, {})
        seasoning = ("倍" in js) and ("%" not in js)
        cur[name] = {"品名": name, "大カテゴリ": old.get("大カテゴリ") or ("調味料" if seasoning else "プラント"),
                     "中カテゴリ": old.get("中カテゴリ") or ("希釈" if seasoning else "黒"), "配合JSON": js}
    return [r for r in cur.values() if _recipe_items(r["配合JSON"])]

def recipes_from_brewing(records, recipes, n_recent=5):
    """製造記録（直近n回）の「原料投入量÷仕込量」から配合比を推定する（石灰は石灰水量に対する比率）。中央値で季節増量・微調整の影響を抑える"""
    import statistics
    cat = {str(r.get("品名", "")).strip(): (r.get("大カテゴリ") or "プラント", r.get("中カテゴリ") or "黒") for r in recipes}
    by = {}
    for b in sorted(records, key=lambda x: (str(x.get("仕込日", "")), str(x.get("登録日時", ""))), reverse=True):
        nm = str(b.get("品名", "")).strip()
        if nm: by.setdefault(nm, []).append(b)
    def _prio(n):
        for i, kw in enumerate(["こんにゃく", "海藻", "デンプン", "でんぷん", "石灰", "カルシウム", "食塩"]):
            if kw in n: return (i, n)
        return (9 if _is_water_name(n) else 8, n)
    out = []
    for nm, recs in by.items():
        samples, used = {}, 0
        for b in recs[:n_recent]:
            size, lime_l = to_float(b.get("仕込量(kg)")), to_float(b.get("石灰水(L)"))
            if size <= 0: continue
            agg = {}
            for it in _items_of(b):
                n = str(it.get("原料名", "")).strip()
                if n: agg[n] = agg.get(n, 0.0) + to_float(it.get("kg"))
            if not agg: continue
            used += 1
            for n, kg in agg.items():
                ratio = (kg / lime_l * 10.0) if (_is_lime_name(n) and not _is_water_name(n) and lime_l > 0) else (kg / size * 100.0)
                samples.setdefault(n, []).append(ratio)
        items = [(n, round(statistics.median(v), 2)) for n, v in samples.items() if len(v) * 2 >= used and statistics.median(v) > 0]
        if not items: continue
        items.sort(key=lambda x: _prio(x[0]))
        c1, c2 = cat.get(nm, ("プラント", "黒"))
        out.append({"品名": nm, "大カテゴリ": c1, "中カテゴリ": c2, "配合JSON": ", ".join(f"{n}:{x}%" for n, x in items), "推定元": f"直近{used}回の製造記録"})
    return out

def render_backup_restore():
    st.markdown("### 📥 1. バックアップ（定期的に保存しておくと安心です）")
    st.caption("配合マスタ・製造記録・入荷・在庫調整・各種マスタをまとめて保存します。JSONは「復旧」に使えます。Excelは中身の確認用です。")
    b1, b2 = st.columns(2)
    stamp = now_jst().strftime("%Y%m%d_%H%M")
    b1.download_button("💾 全データ（JSON・復旧用）", json.dumps(_full_backup_dict(), ensure_ascii=False, default=str).encode("utf-8"),
                       file_name=f"ERPバックアップ_{stamp}.json", mime="application/json", use_container_width=True)
    try: b2.download_button("📊 全データ（Excel・確認用）", _backup_excel_bytes(), file_name=f"ERPバックアップ_{stamp}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    except Exception as e: b2.warning(f"Excel作成に失敗しました: {e}")

    st.markdown("---")
    st.markdown("### 🔁 2. 配合マスタの復旧")
    n_empty = len([r for r in recipes_raw if not _recipe_items(r.get("配合JSON"))])
    if not recipes_raw:
        st.error("配合マスタが空です。下のいずれかから復旧できます。")
    elif n_empty:
        st.warning(f"配合マスタ {len(recipes_raw)}件のうち、**原料・配合比が空の配合が {n_empty}件**あります。下の方法で補えます。")
    else:
        st.success(f"配合マスタ {len(recipes_raw)}件（すべて配合あり）")
    st.caption("まず「3. Googleの版の履歴」で元に戻せるか確認するのが最も正確です。難しい場合に、下の方法を使ってください。")
    src = st.radio("復旧元", ["🧾 製造記録から推定（おすすめ）", "📤 バックアップファイル（JSON / Excel）", "🕒 配合履歴から再構成"], key="rst_src")
    cand = []
    if src.startswith("🧾"):
        cand = recipes_from_brewing(brewing, recipes_raw)
        if cand: st.caption("直近5回の製造記録から、各原料の「投入量÷仕込量」の中央値で配合比を推定しました。夏場の石灰増量や微調整が混ざるため、**必ず内容を確認して直してください**（石灰は石灰水量に対する比率。水は不要なら行から削除）。")
        else: st.warning("推定できる製造記録がありません。")
    elif src.startswith("📤"):
        up = st.file_uploader("バックアップファイル", type=["json", "xlsx"], key="rst_file")
        if up is not None:
            try:
                if up.name.lower().endswith(".json"):
                    cand = [dict(r) for r in (json.loads(up.getvalue().decode("utf-8")).get("recipes") or [])]
                else:
                    cand = pd.read_excel(up, sheet_name="配合マスタ").fillna("").to_dict("records")
                for r in cand: r["配合JSON"] = ", ".join(f"{n}:{x}%" for n, x in _recipe_items(r.get("配合JSON")))
                st.caption(f"{len(cand)}件の配合を読み込みました。")
            except Exception as e:
                st.error(f"ファイルを読み込めませんでした: {e}")
    else:
        logs = [l for l in recipe_logs if _log_text(l).startswith(("【新規追加】", "【変更】", "【削除】"))]
        if not logs: st.warning("復元に使える配合履歴がありません。")
        else:
            cand = recipes_from_logs(logs)
            st.caption(f"配合履歴 {len(logs)}件から {len(cand)}件を再構成しました。大カテゴリ・中カテゴリは履歴に無いため、必要に応じて直してください。")
    if cand:
        df = pd.DataFrame(cand)
        for c in ["品名", "大カテゴリ", "中カテゴリ", "配合JSON"]:
            if c not in df.columns: df[c] = ""
        show_cols = ["品名", "大カテゴリ", "中カテゴリ", "配合JSON"] + (["推定元"] if "推定元" in df.columns else [])
        df = df[show_cols]
        edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=True, key=f"rst_ed_{hashlib.md5(df.to_json().encode()).hexdigest()[:8]}",
                                column_config={"大カテゴリ": st.column_config.SelectboxColumn("大カテゴリ", options=["プラント", "OKM", "手詰め", "調味料"]),
                                               "中カテゴリ": st.column_config.SelectboxColumn("中カテゴリ", options=["白", "黒", "耐冷", "ショクカイ", "めん", "その他", "希釈"]),
                                               "配合JSON": st.column_config.TextColumn("配合（原料:比率%, …）", width="large"),
                                               **({"推定元": st.column_config.TextColumn("推定元", disabled=True)} if "推定元" in df.columns else {})})
        mode = st.radio("復旧のしかた", ["🩹 空の配合・足りない配合だけ補う（今の配合は残す）", "♻️ すべてこの内容に置き換える"], key="rst_mode")
        ok = st.checkbox("内容を確認しました", key="rst_ok")
        if st.button("✅ 配合マスタを復旧する", type="primary", disabled=not ok, key="rst_go", use_container_width=True):
            rows = [{"品名": str(r["品名"]).strip(), "大カテゴリ": r["大カテゴリ"] or "プラント", "中カテゴリ": r["中カテゴリ"] or "黒", "配合JSON": r["配合JSON"]}
                    for _, r in edited.iterrows() if str(r["品名"]).strip() and str(r["品名"]).strip().lower() != "nan" and _recipe_items(r["配合JSON"])]
            if not rows:
                st.error("復旧する配合（原料と比率）がありません。"); st.stop()
            if not hasattr(sheets, "save_recipes"):
                st.error("sheets.save_recipes が見つかりません。"); st.stop()
            if mode.startswith("🩹"):
                new_by = {r["品名"]: r for r in rows}
                final, seen = [], set()
                for r in recipes_raw:
                    nm = str(r.get("品名", "")).strip(); seen.add(nm)
                    if nm in new_by and not _recipe_items(r.get("配合JSON")): final.append({**r, "配合JSON": new_by[nm]["配合JSON"]})
                    else: final.append(r)
                final += [r for r in rows if r["品名"] not in seen]
            else:
                final = rows
            sheets.save_recipes(final)
            _append_log_rows([{"ログID": f"RLOG-{now_jst().strftime('%Y%m%d%H%M%S%f')}", "変更日時": now_jst().isoformat(timespec="seconds"), "品名": "（配合マスタ全体）",
                               "処理": "復元", "変更内容": f"【復元】{src} から {len(rows)}件の配合を復旧（{mode[:2]}）", "作業者": ""}])
            done(f"配合マスタを復旧しました（{len(final)}件）。")

    st.markdown("---")
    with st.expander("🗂️ 3. スプレッドシートそのものを元に戻す（Googleの版の履歴）← 最も正確", expanded=True):
        st.markdown(
            "Googleスプレッドシートには、過去の編集内容が自動で残っています。\n\n"
            "1. 対象のスプレッドシートを開く\n"
            "2. メニュー **ファイル → 版の履歴 → 版の履歴を表示**\n"
            "3. 右側の一覧から、**消える前の日時**を選んで内容を確認\n"
            "4. スプレッドシート全体を戻すなら **「この版を復元」**\n"
            "5. 一部のシートだけ戻したいときは、その版で該当シート（配合マスタなど）を全選択してコピーし、現在のシートに貼り付け\n\n"
            "※ 復元する前に、現在の状態を「コピーを作成」で控えておくと安全です。")
    with st.expander("⚙️ 詳細設定"):
        st.caption("通常はオフのままにしてください。保存でデータが半分未満になる（または全件消える）操作は、誤操作防止のため自動で止めています。意図した操作のときだけ一時的にオンにします。")
        st.checkbox("大量削除・全件削除の保存を許可する", key="_allow_shrink_write")


# ── 粉の消費量分析 ──────────────────────────────────────────────
CONS_DIMS = {"原料別": ["原料名"], "メーカー別": ["メーカー"], "グレード別": ["グレード"], "メーカー×グレード": ["メーカー", "グレード"],
             "原料×メーカー": ["原料名", "メーカー"], "原料×グレード": ["原料名", "グレード"], "原料×メーカー×グレード": ["原料名", "メーカー", "グレード"],
             "製品別": ["品名"], "ライン別": ["ライン"], "ロット別": ["原料名", "ロットNo"], "担当者別": ["担当者"]}
CONS_AXES = ["原料名", "メーカー", "グレード", "品名", "ライン", "担当者", "ロットNo"]

def period_select(key, default="直近30日"):
    """期間をプルダウン1つで選ぶ（「期間を指定」のときだけ日付入力）→ (開始日, 終了日)。全期間は (None, None)"""
    sel = st.selectbox("📅 期間", PERIOD_CHOICES, index=PERIOD_CHOICES.index(default), key=f"{key}_psel")
    t = today_jst()
    if sel == "今日": return t, t
    if sel == "昨日": y = t - timedelta(days=1); return y, y
    if sel == "今週": return t - timedelta(days=t.weekday()), t
    if sel == "今月": return t.replace(day=1), t
    if sel == "先月":
        le = t.replace(day=1) - timedelta(days=1); return le.replace(day=1), le
    if sel == "直近30日": return t - timedelta(days=29), t
    if sel == "全期間": return None, None
    a, b = st.columns(2)
    s0 = a.date_input("開始", value=t.replace(day=1), key=f"{key}_ps2"); e0 = b.date_input("終了", value=t, key=f"{key}_pe2")
    return (e0, s0) if s0 > e0 else (s0, e0)

def build_consumption_df():
    u = build_usage_df(brewing)
    if u.empty: return u
    u = u[~u["原料名"].astype(str).map(_is_water_name)].copy()
    if u.empty: return u
    cat = {r.get("品名"): (r.get("大カテゴリ") or "その他", r.get("中カテゴリ") or "その他") for r in recipes_raw}
    bag_w = {}
    for m in sorted_materials():
        _, wt = parse_op_data(order_points.get(m, 0.0)); bag_w[m] = wt if wt > 0 else 20
    u["ライン"] = u["品名"].map(lambda p: cat.get(p, ("不明", ""))[0])
    unreg = u["入荷No"].astype(str).str.strip() == ""
    u["メーカー"] = [("（入荷未登録）" if r else (str(m).strip() or "（メーカー未設定）")) for r, m in zip(unreg, u["入荷メーカー"])]
    u["グレード"] = [("（入荷未登録）" if r else (str(g).strip() or "（グレード未設定）")) for r, g in zip(unreg, u["グレード"])]
    u["ロットNo"] = u["ロットNo"].map(lambda l: "（ロット未指定）" if str(l).strip() in ("", "─") else l)
    u["日付_dt"] = pd.to_datetime(u["仕込日"], errors="coerce")
    u = u[u["日付_dt"].notna()].copy()
    u["投入量(kg)"] = pd.to_numeric(u["投入量(kg)"], errors="coerce").fillna(0.0)
    u["袋換算"] = [kg / bag_w.get(n, 20) for kg, n in zip(u["投入量(kg)"], u["原料名"])]
    return u

def render_flour_analysis():
    u0 = build_consumption_df()
    if u0.empty:
        st.info("製造記録がまだありません。"); return

    card_start()
    c_p, c_f = st.columns([1, 2])
    with c_p: s_d, e_d = period_select("cons", default="直近30日")
    with c_f: focus = st.radio("📦 対象", ["🌾 こんにゃく粉のみ", "すべての原料（水を除く）"], horizontal=True, key="cons_focus")
    base = u0[u0["原料名"].map(is_konjac_material)] if "こんにゃく粉" in focus else u0
    base = base[in_period(base["仕込日"], s_d, e_d)]
    if base.empty:
        st.info("対象期間内の消費実績がありません。"); card_end(); return
    with st.expander("🔎 絞り込み（原料・メーカー・グレード・製品・ライン）※ 必要なときだけ"):
        f1, f2, f3, f4, f5 = st.columns(5)
        sel = {"原料名": f1.multiselect("原料", sorted(base["原料名"].unique()), key="cons_f_mat"),
               "メーカー": f2.multiselect("メーカー", sorted(base["メーカー"].unique()), key="cons_f_mk"),
               "グレード": f3.multiselect("グレード", sorted(base["グレード"].unique()), key="cons_f_gr"),
               "品名": f4.multiselect("製品", sorted(base["品名"].astype(str).unique()), key="cons_f_prod"),
               "ライン": f5.multiselect("ライン", sorted(base["ライン"].astype(str).unique()), key="cons_f_line")}
    u = base
    for col, vals in sel.items():
        if vals: u = u[u[col].isin(vals)]
    if any(sel.values()): st.caption("🔎 絞り込み中：" + " ／ ".join(f"{k}={'・'.join(v)}" for k, v in sel.items() if v))
    card_end()
    if u.empty:
        st.info("絞り込み条件に合う消費実績がありません。"); return

    d_from = s_d or u["日付_dt"].min().date()
    d_to = e_d or u["日付_dt"].max().date()
    days = max(1, (d_to - d_from).days + 1)
    tot = u["投入量(kg)"].sum()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("総消費量", f"{fmt_kg(round(tot, 1))} kg")
    k2.metric("袋換算", f"{fmt_kg(round(u['袋換算'].sum(), 1))} 袋")
    k3.metric("仕込回数", f"{u['仕込No'].nunique()} 回")
    k4.metric("1日あたり平均", f"{fmt_kg(round(tot / days, 2))} kg")

    t_trend, t_dim, t_lot, t_diff, t_unit, t_det = st.tabs(
        ["📅 推移", "🔀 切り口別", "🧾 ロット別", "⚖️ 現場との差異", "🍥 原単位", "🕒 明細・出力"])

    with t_trend:
        card_start()
        c_a, c_b = st.columns(2)
        gran = c_a.radio("集計単位", ["日", "週", "月"], horizontal=True, index=2 if days > 90 else (1 if days > 31 else 0), key="cons_gran")
        axis = c_b.selectbox("積み上げの切り口", ["（総量のみ）"] + CONS_AXES, key="cons_axis")
        tmp = u.copy()
        if gran == "日": tmp["期間"] = tmp["日付_dt"].dt.strftime("%Y-%m-%d")
        elif gran == "週": tmp["期間"] = (tmp["日付_dt"] - pd.to_timedelta(tmp["日付_dt"].dt.weekday, unit="D")).dt.strftime("%Y-%m-%d") + "週"
        else: tmp["期間"] = tmp["日付_dt"].dt.strftime("%Y-%m")
        gcols = ["期間"] + ([] if axis == "（総量のみ）" else [axis])
        grp = tmp.groupby(gcols)["投入量(kg)"].sum().reset_index().sort_values("期間")
        fig = px.bar(grp, x="期間", y="投入量(kg)", color=None if axis == "（総量のみ）" else axis, barmode="stack", title=f"{gran}別 消費量 (kg)")
        fig.update_xaxes(type="category"); fig.update_layout(plot_bgcolor="#ffffff", yaxis_title="消費量(kg)")
        if axis == "（総量のみ）": fig.update_traces(marker_color="#0f766e")
        st.plotly_chart(fig, use_container_width=True)
        if axis == "（総量のみ）":
            show = grp.rename(columns={"投入量(kg)": "消費量(kg)"})
        else:
            show = grp.pivot_table(index="期間", columns=axis, values="投入量(kg)", aggfunc="sum", fill_value=0)
            show["合計"] = show.sum(axis=1); show = show.reset_index()
        st.dataframe(fmt_df_numeric(show, [c for c in show.columns if c != "期間"]), use_container_width=True, hide_index=True)
        card_end()

    with t_dim:
        card_start()
        dim_label = st.selectbox("切り口", list(CONS_DIMS.keys()), key="cons_dim")
        cols = CONS_DIMS[dim_label]
        g = u.groupby(cols).agg(消費量kg=("投入量(kg)", "sum"), 袋換算=("袋換算", "sum"), 仕込回数=("仕込No", "nunique"), 直近使用日=("仕込日", "max")).reset_index()
        g["構成比%"] = (g["消費量kg"] / g["消費量kg"].sum() * 100).round(1)
        g["1日平均kg"] = (g["消費量kg"] / days).round(2)
        g = g.sort_values("消費量kg", ascending=False).reset_index(drop=True)
        g["袋換算"] = g["袋換算"].round(2); g["消費量kg"] = g["消費量kg"].round(2)
        g["区分"] = g[cols].astype(str).agg(" / ".join, axis=1)
        top = g.head(25).sort_values("消費量kg")
        figd = px.bar(top, x="消費量kg", y="区分", orientation="h", text="消費量kg", title=f"{dim_label} 消費量 (kg)" + ("（上位25）" if len(g) > 25 else ""))
        figd.update_traces(texttemplate="%{text:,.1f} kg", textposition="outside", marker_color="#0f766e")
        figd.update_layout(plot_bgcolor="#ffffff", height=max(300, 32 * len(top) + 80), yaxis_title="")
        st.plotly_chart(figd, use_container_width=True)
        shown = g[cols + ["消費量kg", "袋換算", "構成比%", "仕込回数", "1日平均kg", "直近使用日"]]
        st.dataframe(fmt_df_numeric(shown, ["消費量kg", "袋換算", "構成比%", "1日平均kg"]), use_container_width=True, hide_index=True)
        download_buttons({f"消費量_{dim_label}": shown}, f"粉消費量_{dim_label}_{today_jst()}", "cons_dim_dl")
        card_end()

    with t_lot:
        card_start()
        st.caption("※ 消費は選択期間内、入荷・現在庫は全期間の値です。")
        gl = u.groupby(["原料名", "ロットNo", "メーカー", "グレード"]).agg(期間内消費kg=("投入量(kg)", "sum"), 期間内消費袋=("袋換算", "sum"), 仕込回数=("仕込No", "nunique"),
                                                                    初回使用=("仕込日", "min"), 最終使用=("仕込日", "max")).reset_index()
        lots_info = _lot_groups()
        gl["入荷日"] = [lots_info.get((m, l), {}).get("入荷日", "（入荷未登録）") for m, l in zip(gl["原料名"], gl["ロットNo"])]
        gl["入荷(袋)"] = [round(lots_info.get((m, l), {}).get("入荷袋数", 0.0), 2) for m, l in zip(gl["原料名"], gl["ロットNo"])]
        gl["計算上の残(袋)"] = [round(lots_info.get((m, l), {}).get("理論残", 0.0), 2) for m, l in zip(gl["原料名"], gl["ロットNo"])]
        gl["期間内消費kg"] = gl["期間内消費kg"].round(2); gl["期間内消費袋"] = gl["期間内消費袋"].round(2)
        gl = gl.sort_values("期間内消費kg", ascending=False)
        gl = gl[["原料名", "ロットNo", "メーカー", "グレード", "入荷日", "入荷(袋)", "期間内消費kg", "期間内消費袋", "計算上の残(袋)", "仕込回数", "初回使用", "最終使用"]]
        st.dataframe(fmt_df_numeric(gl, ["入荷(袋)", "期間内消費kg", "期間内消費袋", "計算上の残(袋)"]), use_container_width=True, hide_index=True)
        download_buttons({"ロット別消費": gl}, f"ロット別消費_{today_jst()}", "cons_lot_dl")
        card_end()

    with t_diff:
        card_start()
        st.caption("棚卸・突合で入力した調整（＝計算上の在庫と現場の差）です。＋は「現場の方が多かった」、−は「現場の方が少なかった（ロス等）」。")
        rows_a = []
        for a in adjustments:
            v = inventory_data.get(str(a.get("入荷No", "")).strip())
            if not v: continue
            if "こんにゃく粉" in focus and not is_konjac_material(v["原料種別"]): continue
            bags = to_float(a.get("調整袋数"))
            reason = str(a.get("理由", ""))
            rows_a.append({"調整日": str(a.get("調整日", "")), "原料": v["原料種別"], "メーカー": v["メーカー"] or "（メーカー未設定）", "グレード": v["グレード"] or "（グレード未設定）",
                           "ロットNo": v["ロットNo"], "調整(袋)": round(bags, 3), "調整(kg)": round(bags * v["1袋重量"], 2),
                           "区分": "突合" if "【突合】" in reason else ("棚卸" if "【棚卸】" in reason else "その他"), "理由": reason, "担当者": a.get("担当者", "")})
        dfa = pd.DataFrame(rows_a, columns=["調整日", "原料", "メーカー", "グレード", "ロットNo", "調整(袋)", "調整(kg)", "区分", "理由", "担当者"])
        if not dfa.empty: dfa = dfa[in_period(dfa["調整日"], s_d, e_d)]
        if sel["原料名"] and not dfa.empty: dfa = dfa[dfa["原料"].isin(sel["原料名"])]
        if dfa.empty:
            st.info("対象期間内の棚卸・突合の調整はありません。")
        else:
            net = dfa["調整(kg)"].sum()
            d1, d2, d3, d4 = st.columns(4)
            d1.metric("調整の純増減", f"{net:+.1f} kg")
            d2.metric("現場が多かった分", f"{dfa[dfa['調整(kg)'] > 0]['調整(kg)'].sum():+.1f} kg")
            d3.metric("現場が少なかった分", f"{dfa[dfa['調整(kg)'] < 0]['調整(kg)'].sum():+.1f} kg")
            d4.metric("消費量に対する純差異率", f"{(net / tot * 100) if tot else 0:+.2f} %")
            by_m = dfa.groupby("原料").agg(調整kg=("調整(kg)", "sum"), 調整回数=("調整(kg)", "count")).reset_index()
            cons_m = u.groupby("原料名")["投入量(kg)"].sum().rename("消費量kg")
            by_m = by_m.merge(cons_m, left_on="原料", right_index=True, how="left").fillna({"消費量kg": 0.0})
            by_m["差異率%"] = [round(a / c * 100, 2) if c else None for a, c in zip(by_m["調整kg"], by_m["消費量kg"])]
            by_m = by_m.round({"調整kg": 2, "消費量kg": 2}).sort_values("調整kg")
            st.markdown("**原料別：消費量に対する差異**（−が大きい原料ほど、計算より現場が減っている＝ロス・計量誤差が大きい）")
            st.dataframe(fmt_df_numeric(by_m, ["調整kg", "消費量kg"]), use_container_width=True, hide_index=True)
            dfa["月"] = pd.to_datetime(dfa["調整日"], errors="coerce").dt.strftime("%Y-%m")
            figa = px.bar(dfa.groupby(["月", "原料"])["調整(kg)"].sum().reset_index(), x="月", y="調整(kg)", color="原料", barmode="relative", title="月別 調整量 (kg)")
            figa.update_xaxes(type="category"); figa.update_layout(plot_bgcolor="#ffffff")
            st.plotly_chart(figa, use_container_width=True)
            st.dataframe(fmt_df_numeric(dfa.drop(columns=["月"]).sort_values("調整日", ascending=False), ["調整(袋)", "調整(kg)"]), use_container_width=True, hide_index=True)
            download_buttons({"理論と現場の差異": dfa.drop(columns=["月"])}, f"差異調整_{today_jst()}", "cons_diff_dl")
        card_end()

    with t_unit:
        card_start()
        st.caption("仕込100kgあたり、何kgの粉を使ったか（原単位）。製品ごとの使いすぎ・ばらつきの確認に使えます。")
        bt = ensure_cols(pd.DataFrame(brewing), ["仕込日", "仕込No", "品名", "仕込量(kg)"])
        bt = bt[in_period(bt["仕込日"], s_d, e_d)].copy()
        if sel["品名"]: bt = bt[bt["品名"].isin(sel["品名"])]
        if sel["ライン"]: bt = bt[bt["品名"].map(lambda p: next((r.get("大カテゴリ") for r in recipes_raw if r.get("品名") == p), "")).isin(sel["ライン"])]
        bt["仕込量"] = bt["仕込量(kg)"].apply(to_float)
        use_b = u.groupby("仕込No")["投入量(kg)"].sum()
        bt["粉kg"] = bt["仕込No"].map(use_b).fillna(0.0)
        bt = bt[bt["仕込量"] > 0]
        if bt.empty:
            st.info("対象の製造記録がありません。")
        else:
            gp = bt.groupby("品名").agg(仕込回数=("仕込No", "count"), 仕込量kg=("仕込量", "sum"), 粉消費kg=("粉kg", "sum")).reset_index()
            gp["粉kg/仕込100kg"] = (gp["粉消費kg"] / gp["仕込量kg"] * 100).round(2)
            gp = gp.sort_values("粉消費kg", ascending=False)
            figu = px.bar(gp.sort_values("粉kg/仕込100kg"), x="粉kg/仕込100kg", y="品名", orientation="h", text="粉kg/仕込100kg", title="製品別 原単位（粉kg／仕込100kg）")
            figu.update_traces(texttemplate="%{text:.2f}", textposition="outside", marker_color="#0f766e")
            figu.update_layout(plot_bgcolor="#ffffff", height=max(300, 34 * len(gp) + 80), yaxis_title="")
            st.plotly_chart(figu, use_container_width=True)
            st.dataframe(fmt_df_numeric(gp.round(2), ["仕込量kg", "粉消費kg", "粉kg/仕込100kg"]), use_container_width=True, hide_index=True)
            p_pick = st.selectbox("🔎 製品を選んで仕込ごとのばらつきを見る", list(gp["品名"]), key="cons_unit_prod")
            one = bt[bt["品名"] == p_pick].sort_values("仕込日").copy()
            one["原単位"] = (one["粉kg"] / one["仕込量"] * 100).round(2)
            figl = px.line(one, x="仕込日", y="原単位", markers=True, hover_data=["仕込No", "仕込量", "粉kg"], title=f"{p_pick}：仕込ごとの原単位（粉kg／100kg）")
            figl.update_xaxes(type="category"); figl.update_layout(plot_bgcolor="#ffffff")
            st.plotly_chart(figl, use_container_width=True)
        card_end()

    with t_det:
        card_start()
        det = u[["仕込日", "仕込No", "品名", "ライン", "担当者", "原料名", "メーカー", "グレード", "ロットNo", "投入量(kg)", "袋換算"]].copy()
        det["袋換算"] = det["袋換算"].round(3); det["投入量(kg)"] = det["投入量(kg)"].round(3)
        det = det.sort_values(["仕込日", "仕込No"], ascending=False)
        mon = u.assign(月=u["日付_dt"].dt.strftime("%Y-%m")).groupby(["月", "原料名"])["投入量(kg)"].sum().reset_index()
        xl = {"消費明細": det,
              "原料別": u.groupby("原料名")["投入量(kg)"].sum().reset_index().sort_values("投入量(kg)", ascending=False),
              "メーカー別": u.groupby("メーカー")["投入量(kg)"].sum().reset_index().sort_values("投入量(kg)", ascending=False),
              "グレード別": u.groupby("グレード")["投入量(kg)"].sum().reset_index().sort_values("投入量(kg)", ascending=False),
              "メーカー×グレード": u.groupby(["メーカー", "グレード"])["投入量(kg)"].sum().reset_index().sort_values("投入量(kg)", ascending=False),
              "月別×原料": mon}
        download_buttons(xl, f"粉消費量_{d_from}_{d_to}", "cons_det_dl")
        st.dataframe(fmt_df_numeric(det.head(300), ["投入量(kg)", "袋換算"]), use_container_width=True, hide_index=True)
        if len(det) > 300: st.caption("画面には直近300行を表示。Excel/CSVには全件が入ります。")
        card_end()


# ════════════════════════════════════════════════════════════════
#  サイドバー
# ════════════════════════════════════════════════════════════════
PAGES = ["🏭 製造仕込み", "📊 ダッシュボード", "📝 発注管理", "📥 入荷登録", "📦 在庫・棚卸",
         "🧹 資材管理", "🔍 トレース", "📋 履歴・帳票", "📈 分析", "⚙️ マスタ設定", "🛟 バックアップ・復旧"]

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

    # ── 直近5件の製造履歴（配合帳票・直接修正） ──────────────
    card_start()
    sec_title("🧾 直近5件の製造履歴（配合帳票）")
    _mode = st.radio("表示", ["🍥 製品ごとの最新5件", "🕒 新しい順に5件"], horizontal=True, key="recent_mode")
    _sorted_b = sorted(brewing, key=lambda b: (str(b.get("仕込日", "")), str(b.get("登録日時", "")), to_float(b.get("仕込No"))), reverse=True)
    if "製品ごと" in _mode:
        _seen, recent5 = set(), []
        for _b in _sorted_b:
            _p = str(_b.get("品名", ""))
            if _p in _seen: continue
            _seen.add(_p); recent5.append(_b)
            if len(recent5) >= 5: break
    else:
        recent5 = _sorted_b[:5]
    render_brew_grid(recent5, "recent_grid")
    render_correction_log(brew_corrections, "recent_corr_log", limit=10)
    card_end()

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

    t_new, t_list, t_vnd = st.tabs(["➕ 新規発注登録", f"📋 発注一覧・入荷処理（未入荷 {len(pending_orders)}件）", "📇 発注先一覧（連絡先）"])
    with t_new:
        card_start()
        order_category = st.radio("🏷️ 発注区分", ["🥦 原材料", "🧻 衛生資材・消耗品"], horizontal=True)
        is_raw_mat = "原材料" in order_category
        item_opts = sorted_materials() if is_raw_mat else [s.get("資材名") for s in sorted_supplies() if s.get("資材名")]
        o_mat = st.selectbox("発注品目", item_opts if item_opts else ["未登録"], key="new_order_item")
        _vs = vendors_for_item(o_mat)
        if _vs: render_vendor_cards(_vs, compact=True)
        _mk_opts = list(makers) + [v.get("メーカー(発注先)") for v in _vs if v.get("メーカー(発注先)") and v.get("メーカー(発注先)") not in makers]
        _mk_opts = _mk_opts or ["未登録"]
        _def_mk = next((v.get("メーカー(発注先)") for v in _vs if v.get("メーカー(発注先)") in _mk_opts), None)
        with st.form("new_order_form"):
            o_maker = st.selectbox("メーカー/発注先", _mk_opts, index=_mk_opts.index(_def_mk) if _def_mk else 0, key=f"new_order_maker_{o_mat}")
            c_a, c_b = st.columns(2)
            o_date = c_a.date_input("発注日", value=today_jst())
            o_due = c_b.date_input("納品予定日", value=today_jst() + timedelta(days=7))
            o_qty = st.number_input("発注個数 (袋/箱など)", min_value=1, value=10, step=1)
            _pp, _pu = default_price_for(o_mat, _def_mk)
            c_p1, c_p2 = st.columns(2)
            o_price = c_p1.number_input("💴 単価（円）", min_value=0.0, value=float(_pp), step=1.0, format="%.2f", key=f"new_order_price_{o_mat}", help="分からなければ0のままでOK。あとから「単価・金額の入力・修正」で入れられます。")
            o_unit = c_p2.selectbox("単位", PRICE_UNITS, index=PRICE_UNITS.index(_pu) if _pu in PRICE_UNITS else (0 if is_raw_mat else 1), key=f"new_order_unit_{o_mat}")
            st.caption("金額 ＝ 発注個数 × 単価（自動計算）。" + ("" if is_raw_mat else "※ 資材は、発注の単位と使用記録の単位が同じ前提で金額を計算します。"))
            o_note = st.text_input("備考（任意）")
            if st.form_submit_button("💾 発注を登録する", type="primary", use_container_width=True):
                if not item_opts: st.error("発注品目が登録されていません。マスタ設定で登録してください。")
                elif o_due < o_date: st.error("納品予定日が発注日より前になっています。")
                else:
                    orders = fresh_purchase_orders()
                    orders.append({
                        "発注ID": f"PO-{now_jst().strftime('%Y%m%d%H%M%S%f')}", "発注区分": "原材料" if is_raw_mat else "衛生資材",
                        "発注日": str(o_date), "原料名": o_mat, "メーカー": o_maker, "個数": o_qty, "納品予定日": str(o_due), "ステータス": "未入荷",
                        "紐づく入荷No": "", "備考": o_note, "登録日時": now_jst().isoformat(), "単価": o_price, "単位": o_unit, "金額": round(o_price * o_qty)
                    })
                    save_purchase_orders(order_points, orders)
                    done(f"発注を登録しました（{o_mat} × {o_qty}" + (f"　{o_price * o_qty:,.0f}円" if o_price > 0 else "") + "）")
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
                    _amt = to_float(o.get("金額")) or (to_float(o.get("単価")) * to_float(o.get("個数")))
                    st.caption(f"💴 単価 {to_float(o.get('単価')):,.0f}円/{o.get('単位') or '袋'} ／ 金額 {_amt:,.0f}円" if _amt > 0 else "💴 金額 未入力（下の「単価・金額の入力・修正」で入れられます）")
                    _pv = [v for v in vendors_for_item(o.get("原料名")) if v.get("メーカー(発注先)") == o.get("メーカー")] or vendors_for_item(o.get("原料名"))
                    if _pv: render_vendor_cards(_pv[:1], compact=True)
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

        with st.expander("💴 単価・金額の入力・修正（未入荷・入荷済みどちらも）"):
            render_order_price_editor(all_orders, _update_order, "po_price")

        if done_orders:
            sec_title("✅ 入荷済みの発注（履歴）")
            df_done = pd.DataFrame(sorted(done_orders, key=lambda x: str(x.get("入荷処理日", "")), reverse=True))
            st.dataframe(fmt_df_numeric(df_done[[c for c in ["発注区分", "発注日", "原料名", "メーカー", "個数", "単価", "単位", "金額", "入荷処理日", "紐づく入荷No"] if c in df_done.columns]].head(50), ["個数"]), use_container_width=True, hide_index=True)
        if cancelled_orders:
            with st.expander(f"🗑️ 取消した発注（{len(cancelled_orders)}件）"):
                df_c = pd.DataFrame(cancelled_orders)
                st.dataframe(df_c[[c for c in ["発注区分", "発注日", "原料名", "メーカー", "個数", "入荷処理日"] if c in df_c.columns]], use_container_width=True, hide_index=True)


    with t_vnd:
        card_start()
        sec_title("📇 発注先一覧（品目・発注先・担当者・連絡先）")
        render_vendor_directory()
        card_end()


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

        _att_n = st.session_state.get("arr_files_n", 0)
        arr_files = st.file_uploader(f"📎 書類を添付（スキャンPDF・写真／任意・1ファイル{ATT_MAX_MB}MBまで）", type=ATT_TYPES, accept_multiple_files=True, key=f"arr_files_{_att_n}") if hasattr(sheets, "append_attachment") else []
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
                _n_att = save_arrival_files(new_no, arr_files, operator)
                st.session_state["arr_files_n"] = _att_n + 1
                for k in ["arr_lot_val", "arr_note", "arr_dup_ok"] + [f"chk_{k_n}" for k_n, _ in CHK_ITEMS]:
                    st.session_state.pop(k, None)
                done(f"入荷記録を保存しました（入荷No. {new_no} ／ {m_type} ／ ロット {lot_clean} ／ {bags_qty}袋）" + (f"　📎 書類{_n_att}件を保管" if _n_att else ""))
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
            _atts = load_attachments_safe()
            _att_cnt = {}
            for _a in (_atts or []): _att_cnt[str(_a.get("入荷No", ""))] = _att_cnt.get(str(_a.get("入荷No", "")), 0) + 1
            df_arr["📎書類"] = df_arr["入荷No"].astype(str).map(lambda n: f"📎 {_att_cnt[n]}件" if n in _att_cnt else "─")
            c_k1, c_k2, c_k3 = st.columns(3)
            c_k1.metric("入荷件数", f"{len(df_arr)} 件")
            c_k2.metric("入荷総量", f"{fmt_kg(round(df_arr['総量(kg)'].apply(to_float).sum(), 1))} kg")
            c_k3.metric("検査 異常あり", f"{int((df_arr['検査判定'] == '⚠️ 異常あり').sum())} 件")
            show_cols = ["入荷日", "入荷No", "原料種別", "グレード", "メーカー", "ロットNo", "袋数", "1袋重量(kg)", "総量(kg)", "検査判定", "外観", "品名・規格確認", "賞味期限", "異物", "担当者", "📎書類", "備考"]
            st.dataframe(fmt_df_numeric(df_arr[show_cols], ["袋数", "1袋重量(kg)", "総量(kg)"]), use_container_width=True, hide_index=True)
            if not df_arr.empty: download_buttons({"入荷記録": df_arr[show_cols]}, f"入荷記録_{today_jst()}", "arr_dl")
            card_end()

            card_start()
            sec_title("📎 書類の保管・紐づけ（スキャンPDF・写真）")
            if _atts is None:
                st.warning("書類の保管には、新しい sheets.py への差し替えが必要です。")
            elif df_arr.empty:
                st.caption("対象の入荷がありません。")
            else:
                _lab = {f"{r['入荷日']} ／ {r['入荷No']} ／ {r['原料種別']} ／ ロット {r['ロットNo']}": str(r["入荷No"]) for _, r in df_arr.head(200).iterrows()}
                _sel_a = st.selectbox("書類を紐づける入荷", list(_lab.keys()), key="arr_att_sel")
                _ano = _lab[_sel_a]
                render_arrival_files(_ano, _atts, f"arr_att_{_ano}")
                _up = st.file_uploader(f"📎 書類を追加（PDF・写真／1ファイル{ATT_MAX_MB}MBまで）", type=ATT_TYPES, accept_multiple_files=True, key=f"arr_att_up_{_ano}_{st.session_state.get('arr_att_n', 0)}")
                _op_a = render_operator_selector("arr_att_op")
                if _up and st.button("💾 この入荷に紐づけて保管", type="primary", key="arr_att_save", use_container_width=True):
                    _n = save_arrival_files(_ano, _up, _op_a)
                    st.session_state["arr_att_n"] = st.session_state.get("arr_att_n", 0) + 1
                    done(f"書類を{_n}件保管しました（入荷No. {_ano}）。")
            card_end()

            with st.expander("✏️ 入荷記録の修正・削除（管理者向け）"):
                arr_editable_cols = [c for c in ["入荷日", "原料種別", "メーカー", "ロットNo", "袋数", "1袋重量(kg)", "備考"] if c in df_arr.columns]
                if "グレード" in df_arr.columns: arr_editable_cols.insert(2, "グレード")
                render_excel_history_editor(full_records=arrivals, filtered_df=df_arr.head(200), id_col="入荷No", editable_cols=arr_editable_cols, numeric_cols=["袋数", "1袋重量(kg)"], save_func=_save_arrivals_recalc, key_prefix="arr_hist", reload_func=sheets.load_arrivals)


# ═══════════════════════════════════════════════════════════════
#  📦 在庫・棚卸
# ═══════════════════════════════════════════════════════════════
elif page == "📦 在庫・棚卸":
    page_header("📦 在庫・棚卸管理", "ロット別の現在庫を確認し、実数に合わせて調整できます。調整はすべて履歴に残ります。")
    render_negative_panel()
    t_inv, t_rec, t_sum, t_hist = st.tabs(["📋 在庫一覧・棚卸し", "⚖️ 粉の突合・リセット", "🧮 原料別サマリー", "🕒 変更履歴"])

    with t_inv:
        card_start()
        active_inv = [v for v in inventory_data.values() if v["現在庫(袋)"] > 0]
        if active_inv: render_lot_inventory_manager(active_inv)
        else: st.info("在庫データがありません。")
        card_end()

    with t_rec:
        card_start()
        render_flour_reconcile()
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

        _hv = st.radio("表示", ['📄 一覧・帳票出力', '🧾 配合帳票・修正', '🔬 1件ずつ詳細確認', '📆 日別・製品別集計', '📝 修正履歴'], horizontal=True, key="brw_hist_view", label_visibility="collapsed")

        if _hv == "📄 一覧・帳票出力":
            card_start()
            list_cols = ["仕込日", "仕込No", "品名", "担当者", "仕込量(kg)", "石灰水(L)", "原料内訳（全原料の投入量）", "修正", "備考"]
            if view.empty:
                st.info("条件に合う製造記録がありません。")
            else:
                usage_df = build_usage_df(df_f.to_dict("records"))
                daily = view.groupby("仕込日", as_index=False).agg(件数=("仕込No", "count"), 製造量kg=("仕込量(kg)", "sum")).sort_values("仕込日")
                xl_sheets = {"製造記録": view[list_cols], "配合比(セル別)": brew_ratio_wide_df(df_f.to_dict("records")), "原料使用明細": usage_df, "日別集計": daily}
                _nos = set(df_f["仕込No"].astype(str))
                _cl = [c for c in brew_corrections if str(c.get("仕込No", "")) in _nos]
                if _cl: xl_sheets["修正履歴"] = corr_log_df(_cl)
                download_buttons(xl_sheets, f"製造記録_{s_date or '全期間'}_{e_date or ''}".rstrip("_"), "brw_dl")
                render_brew_grid(df_f.to_dict("records"), "brw_hist_list", readonly=True)
                st.caption("※ Excelには「製造記録」「配合比(セル別)」「原料使用明細（ロット・入荷日・メーカー付き）」「日別集計」（修正があれば「修正履歴」）が入ります。")
            card_end()

        if _hv == "🧾 配合帳票・修正":
            card_start()
            if view.empty:
                st.info("条件に合う製造記録がありません。")
            else:
                st.caption("※ 絞り込み条件に合う新しい順200件が対象です。")
                render_brew_grid(df_f.head(200).to_dict("records"), "brw_hist_grid")
            card_end()

        if _hv == "🔬 1件ずつ詳細確認":
            card_start()
            if view.empty:
                st.info("条件に合う製造記録がありません。")
            else:
                opts = {f"{r['仕込日']} ／ No.{r['仕込No']} ／ {r['品名']} ／ {fmt_kg(r['仕込量(kg)'])}kg ／ {r['担当者']}": i for i, r in view.iterrows()}
                sel = st.selectbox("確認する製造記録", list(opts.keys()), key="brw_detail_sel")
                r = view.loc[opts[sel]]
                d1, d2, d3, d4 = st.columns(4)
                d1.metric("仕込日", str(r["仕込日"])); d2.metric("製品", str(r["品名"])); d3.metric("仕込量", f"{fmt_kg(r['仕込量(kg)'])} kg"); d4.metric("担当者", str(r["担当者"]))
                for _c in corr_by_no.get(str(r["仕込No"]), []):
                    st.caption(f"✏️ {str(_c.get('修正日時', '')).replace('T', ' ')} ／ {_c.get('種別', '')} ／ {_c.get('修正者', '')} ／ 理由: {_c.get('理由', '')} ／ " + " ・ ".join(_c.get("変更内容", []) or []))
                u = build_usage_df([df_f.loc[opts[sel]].to_dict()])
                if u.empty: pass
                else: st.dataframe(fmt_df_numeric(u[["原料名", "投入量(kg)", "ロットNo", "入荷日", "入荷メーカー", "グレード"]], ["投入量(kg)"]), use_container_width=True, hide_index=True)
                if str(r.get("備考", "")).strip(): st.info(f"📝 備考: {r['備考']}")
                st.caption(f"登録日時: {r.get('登録日時', '')}")
            card_end()

        if _hv == "📆 日別・製品別集計":
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

        if _hv == "📝 修正履歴":
            card_start()
            kw_c = st.text_input("🔎 キーワード（仕込No・理由・修正者・内容）", key="brw_corr_kw")
            cdf = corr_log_df(brew_corrections)
            if not cdf.empty and kw_c.strip(): cdf = cdf[keyword_mask(cdf, list(cdf.columns), kw_c)]
            if cdf.empty: st.info("修正記録はありません。")
            else:
                st.dataframe(cdf, use_container_width=True, hide_index=True)
                download_buttons({"製造記録の修正履歴": cdf}, f"製造修正履歴_{today_jst()}", "brw_corr_dl")
            card_end()

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

    _av = st.radio("表示", ["🏭 生産分析", "💴 使用量と金額", "🌾 粉の消費量分析", "🧻 資材 消費分析"], horizontal=True, key="ana_view", label_visibility="collapsed")

    # ---------------------------------------------------------------
    # 🏭 生産分析（従来の製造量分析）
    # ---------------------------------------------------------------
    if _av == "🏭 生産分析":
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

            pie_data = df_brw_global.groupby("品名")["仕込量(kg)"].sum().reset_index().sort_values("仕込量(kg)", ascending=False)
            with st.container():
                card_start()
                topN = pie_data.sort_values("仕込量(kg)", ascending=True).tail(15)
                fig_bar = px.bar(topN, x="仕込量(kg)", y="品名", orientation='h', title="製造量 上位15品目", text="仕込量(kg)")
                fig_bar.update_traces(texttemplate="%{text:,.0f} kg", textposition="outside", marker_color="#0f766e"); fig_bar.update_layout(height=max(380, 34 * len(topN)), plot_bgcolor="#ffffff", yaxis_title="")
                st.plotly_chart(fig_bar, use_container_width=True)
                card_end()

    # ---------------------------------------------------------------
    # 🌾 粉の消費分析（総量／原料／メーカー／グレード／製品／ロット など多角的）
    # ---------------------------------------------------------------
    if _av == "🌾 粉の消費量分析":
        render_flour_analysis()

    # ---------------------------------------------------------------
    # 🧻 資材 消費分析
    # ---------------------------------------------------------------
    if _av == "💴 使用量と金額":
        render_cost_analysis()

    if _av == "🧻 資材 消費分析":
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
    t1, t2, t3, t4, t5, t6 = st.tabs(["⚗️ 原料マスタ・詳細", "🏢 担当者", "🧪 レシピ・石灰", "📦 資材", "🏷️ グレード", "📇 発注先"])
    
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
                df_rlog = pd.DataFrame([l for l in recipe_logs if str(l.get("処理", "")) not in ("製造修正", "製造取消", "設定")] or [{"変更内容": "（変更履歴はありません）"}])
                if "変更日時" in df_rlog.columns: df_rlog = df_rlog.sort_values("変更日時", ascending=False)
                st.dataframe(df_rlog, use_container_width=True, hide_index=True)
            else:
                st.info("変更履歴はありません。")

        recipe_kind = st.radio("レシピ種別を選択", ["🍽️ 通常レシピ（仕込み配合）", "🌶️ 調味料レシピ（希釈）"], horizontal=True)
        op_recipe = render_operator_selector("recipe_op")
        
        if "通常" in recipe_kind:
            card_start()
            sec_title("🍽️ 通常レシピの編集")
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
                    elif sorted(_recipe_items(orig_dict[pname])) != sorted(_recipe_items(new_json)): changes.append(f"【変更】{pname} ({_recipe_text(orig_dict[pname])} → {new_json})")
                
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
                    append_recipe_changes(changes, op_recipe)
                    
                    done(f"{len(changes)}件の変更を保存しました。")
            card_end()
            
        else:
            card_start()
            sec_title("🌶️ 調味料レシピ（希釈）の編集")
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
                    elif sorted(_recipe_items(orig_s_dict[pname])) != sorted(_recipe_items(new_json)): changes_s.append(f"【変更】{pname} ({_recipe_text(orig_s_dict[pname], '倍')} → {new_json})")
                
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
                    append_recipe_changes(changes_s, op_recipe)
                    
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


    with t6:
        card_start()
        sec_title("📇 発注先マスタ（発注品目・メーカー・担当者名・連絡先）")
        render_vendor_master_editor()
        card_end()


# ═══════════════════════════════════════════════════════════════
#  🛟 バックアップ・復旧
# ═══════════════════════════════════════════════════════════════
elif page == "🛟 バックアップ・復旧":
    page_header("🛟 バックアップ・復旧", "データのバックアップと、配合マスタの復旧ができます。")
    render_backup_restore()
