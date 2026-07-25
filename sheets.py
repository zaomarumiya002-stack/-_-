# sheets.py
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import collections
from datetime import datetime

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

COLS_ARR = ["入荷No", "入荷日", "メーカー", "ロットNo", "原料種別", "袋数", "1袋重量(kg)", "総量(kg)", "搬入温度", "外観", "臭い", "包装", "色調", "異物", "水分", "賞味期限", "異常内容", "担当者", "備考", "登録日時", "品名・規格確認"]
COLS_BRW = ["仕込No", "仕込日", "品名", "メーカー", "主原料ロット", "仕込量(kg)", "こんにゃく精粉(kg)", "海藻粉(kg)", "海藻粉ロット", "デンプン(kg)", "デンプンロット", "デンプン種別", "石灰(kg)", "石灰水(L)", "その他添加物", "備考", "登録日時"]
COLS_ADJ = ["調整ID", "入荷No", "調整日", "調整袋数", "理由", "担当者", "登録日時"]
COLS_SUP = ["資材ID", "資材名", "カテゴリ", "画像URL", "初期在庫", "発注点", "登録日"]
COLS_LOG = ["ログID", "登録日", "資材ID", "処理", "数量", "作業者", "備考", "登録日時"]
COLS_REC_LOG = ["ログID", "変更日時", "品名", "処理", "変更内容", "作業者"]

# 🌟 配合マスタは横持ち形式(品名ごとに1行)で保存する。下記は移行判定にのみ使う旧形式の列定義。
COLS_REC = ["品名", "大カテゴリ", "中カテゴリ", "原料名", "配合比率(%)"]

@st.cache_resource(ttl=3600)
def _client():
    if "gcp_service_account" not in st.secrets:
        raise ValueError("Secretsに 'gcp_service_account' がありません。")
    info = dict(st.secrets["gcp_service_account"])
    if "private_key" in info:
        pk = info["private_key"].replace("\\n", "\n")
        pk = pk.replace("-----BEGIN PRIVATE KEY-----", "-----BEGIN PRIVATE KEY-----\n")
        pk = pk.replace("-----END PRIVATE KEY-----", "\n-----END PRIVATE KEY-----\n")
        info["private_key"] = pk.replace("\n\n\n", "\n").replace("\n\n", "\n")
    return gspread.authorize(Credentials.from_service_account_info(info, scopes=SCOPES))

@st.cache_resource(ttl=600)
def _get_spreadsheet():
    client = _client()
    return client.open_by_key(st.secrets["spreadsheet"]["sheet_id"])

@st.cache_resource(ttl=600)
def _get_worksheets_dict():
    sh = _get_spreadsheet()
    return {ws.title: ws for ws in sh.worksheets()}

def _ws(name, cols):
    w_dict = _get_worksheets_dict()
    if name in w_dict:
        return w_dict[name]
    else:
        sh = _get_spreadsheet()
        w = sh.add_worksheet(title=name, rows=2000, cols=max(10, len(cols)))
        w.update(range_name="A1", values=[cols])
        st.cache_resource.clear()
        return w

def _read(name, cols):
    w = _ws(name, cols)
    all_vals = w.get_all_values()
    if not all_vals:
        w.update(range_name="A1", values=[cols])
        return []
    data_rows = all_vals[1:]
    records = []
    for row in data_rows:
        row_data = row + [""] * (len(cols) - len(row))
        records.append({cols[i]: row_data[i] for i in range(len(cols))})
    return records

def _append(name, cols, rec): 
    _ws(name, cols).append_row([str(rec.get(c, "")) for c in cols])
    st.cache_data.clear() 

def _update(name, cols, kcol, kval, rec):
    w = _ws(name, cols)
    cvals = w.col_values(cols.index(kcol)+1)
    if str(kval) in cvals: 
        w.update(range_name=f"A{cvals.index(str(kval))+1}", values=[[str(rec.get(c, "")) for c in cols]])
    else: 
        _append(name, cols, rec)
    st.cache_data.clear()

def _over(name, cols, recs):
    w = _ws(name, cols)
    w.clear()
    w.update(range_name="A1", values=[cols] + [[str(r.get(c, "")) for c in cols] for r in recs])
    st.cache_data.clear()

def _f(v, d=0.0):
    try: return float(str(v).replace(",","")) if str(v).strip() else d
    except: return d

def _i(v, d=0):
    try: return int(float(str(v).replace(",",""))) if str(v).strip() else d
    except: return d

def _lcol(n, d):
    try: 
        vals = _ws(n, ["name"]).col_values(1)[1:]
        return [v for v in vals if v] or d
    except: 
        return d

def _scol(n, vs):
    w = _ws(n, ["name"])
    w.clear()
    w.update(range_name="A1", values=[["name"]] + [[v] for v in vs])
    st.cache_data.clear()

# ★【変更】配合マスタのスプレッドシート表示を「縦持ち(原料ごとに行)」から
#   「横持ち(製品ごとに1行、原料名がそのまま列見出しになる)」に変更。
#   例: 品名 | 大カテゴリ | 中カテゴリ | こんにゃく粉（国産） | 海藻粉 | 石灰 | 水 ...
#   スプレッドシート上で製品ごとの配合比率を一覧で見比べやすくなる。
RECIPE_FIXED_COLS = ["品名", "大カテゴリ", "中カテゴリ"]

# 原料の列並び順(見やすさのため、よく使う原料カテゴリを優先し、それ以外は50音順)
_ING_PRIORITY_KEYWORDS = ["こんにゃく", "海藻", "でんぷん", "デンプン", "石灰", "カルシウム", "食塩", "水"]

def _ing_sort_key(name):
    for idx, kw in enumerate(_ING_PRIORITY_KEYWORDS):
        if kw in name:
            return (idx, name)
    return (len(_ING_PRIORITY_KEYWORDS), name)

def _read_recipe_sheet_raw():
    """配合マスタシートを、実際に書き込まれているヘッダー行に基づいて読み込む
    (原料列が製品ごとに動的に増減するため、固定カラムリストでは読めない)。"""
    w = _ws("配合マスタ", RECIPE_FIXED_COLS)
    all_vals = w.get_all_values()
    if not all_vals or not all_vals[0]:
        return [], []
    header = all_vals[0]
    data_rows = all_vals[1:]
    records = []
    for row in data_rows:
        row_data = row + [""] * (len(header) - len(row))
        records.append({header[i]: row_data[i] for i in range(len(header))})
    return records, header

def _write_recipe_sheet_wide(header, rows):
    w = _ws("配合マスタ", RECIPE_FIXED_COLS)
    w.clear()
    w.update(range_name="A1", values=[header] + [[str(r.get(c, "")) for c in header] for r in rows])
    st.cache_data.clear()

def _build_wide_recipe_rows(recipe_list):
    """[{"品名":..,"大カテゴリ":..,"中カテゴリ":..,"配合JSON": [{"原料名":..,"比率":..}, ...] または JSON文字列}]
    という内部形式から、横持ち形式の (ヘッダー, 行データ) を構築する。"""
    ing_names = set()
    wide_rows = []
    for r in recipe_list:
        p_name = str(r.get("品名", "")).strip()
        if not p_name: continue
        ing_list = r.get("配合JSON", [])
        if isinstance(ing_list, str):
            try: ing_list = json.loads(ing_list)
            except Exception: ing_list = []
        row = {"品名": p_name, "大カテゴリ": r.get("大カテゴリ", "その他"), "中カテゴリ": r.get("中カテゴリ", "その他")}
        for ing in ing_list:
            name = str(ing.get("原料名", "")).strip()
            if not name: continue
            row[name] = str(ing.get("比率", ""))
            ing_names.add(name)
        wide_rows.append(row)
    ing_cols = sorted(ing_names, key=_ing_sort_key)
    return RECIPE_FIXED_COLS + ing_cols, wide_rows

# ーーー 配合マスタ読込（横持ちシートをプログラム用の構造に自動変換） ーーー
@st.cache_data(ttl=20)
def load_recipes():
    raw_rows, header = _read_recipe_sheet_raw()

    if not raw_rows:
        # 初期サンプル(横持ち形式で作成)
        default_recipe = [{
            "品名": "標準こんにゃく（黒）", "大カテゴリ": "プラント", "中カテゴリ": "黒",
            "配合JSON": [
                {"原料名": "こんにゃく粉（国産）", "比率": 2.50},
                {"原料名": "海藻粉", "比率": 0.20},
                {"原料名": "石灰", "比率": 0.14},
                {"原料名": "水", "比率": 97.16},
            ]
        }]
        header, raw_rows = _build_wide_recipe_rows(default_recipe)
        _write_recipe_sheet_wide(header, raw_rows)

    # ★互換性維持: 旧・縦持ち形式(品名/大カテゴリ/中カテゴリ/原料名/配合比率(%))の
    #   シートが残っている場合は、データを失わずに自動で横持ち形式へ移行する。
    if set(header) == {"品名", "大カテゴリ", "中カテゴリ", "原料名", "配合比率(%)"}:
        grouped = collections.defaultdict(list)
        meta = {}
        for r in raw_rows:
            p_name = str(r.get("品名", "")).strip()
            if not p_name: continue
            meta[p_name] = {"大カテゴリ": r.get("大カテゴリ", "その他"), "中カテゴリ": r.get("中カテゴリ", "その他")}
            grouped[p_name].append({"原料名": r.get("原料名", ""), "比率": _f(r.get("配合比率(%)", 0.0))})
        migrated = [
            {"品名": p, "大カテゴリ": meta[p]["大カテゴリ"], "中カテゴリ": meta[p]["中カテゴリ"], "配合JSON": ing_list}
            for p, ing_list in grouped.items()
        ]
        header, raw_rows = _build_wide_recipe_rows(migrated)
        _write_recipe_sheet_wide(header, raw_rows)

    ing_cols = [c for c in header if c not in RECIPE_FIXED_COLS]
    res = []
    for r in raw_rows:
        p_name = str(r.get("品名", "")).strip()
        if not p_name: continue
        ing_list = []
        for col in ing_cols:
            val = str(r.get(col, "")).strip()
            if val:
                ing_list.append({"原料名": col, "比率": _f(val)})
        res.append({
            "品名": p_name,
            "大カテゴリ": r.get("大カテゴリ", "その他"),
            "中カテゴリ": r.get("中カテゴリ", "その他"),
            "配合JSON": json.dumps(ing_list, ensure_ascii=False)  # 互換性の維持
        })
    return res

# ーーー 配合マスタ書込（保存時は自動で横持ち形式に組み立ててスプレッドシートに書き込む） ーーー
def save_recipes(recs):
    header, wide_rows = _build_wide_recipe_rows(recs)
    _write_recipe_sheet_wide(header, wide_rows)

# ーーー 既存関数 ーーー
@st.cache_data(ttl=20)
def load_recipe_logs(): return _read("レシピ変更履歴", COLS_REC_LOG)
def append_recipe_log(r): _append("レシピ変更履歴", COLS_REC_LOG, r)

@st.cache_data(ttl=20)
def load_arrivals():
    rows = _read("入荷記録", COLS_ARR)
    for r in rows: 
        r["袋数"] = _f(r.get("袋数"))
        r["1袋重量(kg)"] = _f(r.get("1袋重量(kg)", 20.0))
        r["総量(kg)"] = _f(r.get("総量(kg)"))
    return rows

def append_arrival(r): _append("入荷記録", COLS_ARR, r)
def update_arrival(no, r): _update("入荷記録", COLS_ARR, "入荷No", no, r)
def next_arrival_no(arr): 
    nums = [int(a.get('入荷No','A-0').split('-')[1]) for a in arr if '入荷No' in a and '-' in str(a.get('入荷No',''))]
    return f"A-{(max(nums + [0]) + 1):04d}"

@st.cache_data(ttl=20)
def load_brewing():
    rows = _read("仕込み記録", COLS_BRW)
    for r in rows:
        r["仕込量(kg)"] = _f(r.get("仕込量(kg)"))
        r["こんにゃく精粉(kg)"] = _f(r.get("こんにゃく精粉(kg)"))
        r["海藻粉(kg)"] = _f(r.get("海藻粉(kg)"))
        r["デンプン(kg)"] = _f(r.get("デンプン(kg)"))
        r["石灰(kg)"] = _f(r.get("石灰(kg)"))
        r["石灰水(L)"] = _f(r.get("石灰水(L)"))
        r["仕込No"] = _i(r.get("仕込No"))
    return rows

def append_brewing(r): _append("仕込み記録", COLS_BRW, r)
def update_brewing(no, r): _update("仕込み記録", COLS_BRW, "仕込No", str(no), r)

def save_brewing(recs):
    """仕込み記録を全件洗い替えで保存する。
    履歴・帳票タブの「対象記録のインライン操作(編集・削除)」機能が
    app.py側で sheets.save_brewing(list) を呼び出す設計になっていたが、
    本関数が未実装だったため、その場では常にエラーメッセージが表示される
    だけで実際には保存できない状態だった。save_supplies/save_recipesと
    同じ洗い替え方式(_over)で実装し、正しく動作するように修正。"""
    _over("仕込み記録", COLS_BRW, recs)

def delete_brewing(no):
    w = _ws("仕込み記録", COLS_BRW)
    cvals = w.col_values(COLS_BRW.index("仕込No") + 1)
    if str(no) in cvals:
        w.delete_rows(cvals.index(str(no)) + 1)
    st.cache_data.clear()

def next_brewing_no(brw): 
    nums = [_i(b.get("仕込No")) for b in brw]
    return max(nums + [0]) + 1

@st.cache_data(ttl=20)
def load_adjustments():
    rows = _read("在庫調整", COLS_ADJ)
    for r in rows: r["調整袋数"] = _f(r.get("調整袋数"))
    return rows
def append_adjustment(r): _append("在庫調整", COLS_ADJ, r)

@st.cache_data(ttl=20)
def load_supplies():
    rows = _read("資材マスター", COLS_SUP)
    for r in rows: r["初期在庫"] = _f(r.get("初期在庫")); r["発注点"] = _f(r.get("発注点"))
    return rows
def save_supplies(rs): _over("資材マスター", COLS_SUP, rs)

@st.cache_data(ttl=20)
def load_supply_logs():
    rows = _read("資材入出庫", COLS_LOG)
    for r in rows: r["数量"] = _f(r.get("数量"))
    return rows
def append_supply_log(r): _append("資材入出庫", COLS_LOG, r)
def delete_supply_log(log_id):
    w = _ws("資材入出庫", COLS_LOG)
    cvals = w.col_values(COLS_LOG.index("ログID") + 1)
    if str(log_id) in cvals: w.delete_rows(cvals.index(str(log_id)) + 1)
    st.cache_data.clear()

@st.cache_data(ttl=30)
def load_materials(): return _lcol("原料マスター", ["こんにゃく粉（国産）","こんにゃく粉（輸入）","海藻粉","加工デンプン","石灰","食塩"])
def save_materials(v): _scol("原料マスター", v)
@st.cache_data(ttl=30)
def load_makers(): return _lcol("メーカーマスター", ["滝田商店","荻野","オリヒロ","その他"])
def save_makers(v): _scol("メーカーマスター", v)
@st.cache_data(ttl=30)
def load_inspectors(): return _lcol("担当者マスター", ["若槻","志村","斎藤"])
def save_inspectors(v): _scol("担当者マスター", v)
@st.cache_data(ttl=30)
def load_order_points():
    try: 
        rows = _ws("発注点マスター", ["material", "order_point"]).get_all_values()[1:]
        return {r[0]: _f(r[1]) for r in rows if r and r[0]}
    except: return {}
def save_order_points(d):
    w = _ws("発注点マスター", ["material","order_point"])
    w.clear()
    w.update(range_name="A1", values=[["material","order_point"]] + [[k,str(v)] for k,v in d.items()])
    st.cache_data.clear()
