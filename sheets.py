# sheets.py
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import collections
from datetime import datetime

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

COLS_ARR = ["入荷No", "入荷日", "メーカー", "ロットNo", "原料種別", "袋数", "1袋重量(kg)", "総量(kg)", "搬入温度", "外観", "臭い", "包装", "色調", "異物", "水分", "賞味期限", "異常内容", "担当者", "備考", "登録日時", "品名・規格確認", "グレード"]
COLS_BRW = ["仕込No", "仕込日", "品名", "メーカー", "主原料ロット", "仕込量(kg)", "こんにゃく精粉(kg)", "海藻粉(kg)", "海藻粉ロット", "デンプン(kg)", "デンプンロット", "デンプン種別", "石灰(kg)", "石灰水(L)", "その他添加物", "備考", "登録日時"]
COLS_ADJ = ["調整ID", "入荷No", "調整日", "調整袋数", "理由", "担当者", "登録日時"]
COLS_SUP = ["資材ID", "資材名", "カテゴリ", "画像URL", "初期在庫", "発注点", "登録日", "表示順"]
COLS_LOG = ["ログID", "登録日", "資材ID", "処理", "数量", "作業者", "備考", "登録日時"]
COLS_REC_LOG = ["ログID", "変更日時", "品名", "処理", "変更内容", "作業者"]
COLS_VND = ["発注品目", "メーカー(発注先)", "担当者名", "連絡先", "メール", "備考", "単価(円)", "単位"]   # 発注先・単価マスタ（旧版の6列に単価・単位を末尾追加）
COLS_ATT = ["添付ID", "入荷No", "ファイル名", "種別", "サイズ(KB)", "登録日時", "担当者", "分割数"]   # 入荷に紐づく書類(スキャンPDF・写真など)の台帳
COLS_ATTDATA = ["添付ID", "連番", "データ"]   # 書類の中身（base64を分割して保存）
ATT_CHUNK = 40000   # 1セルの上限(5万字)に収まるサイズ
COLS_PO = ["発注ID", "発注日", "原料名", "メーカー", "個数", "納品予定日", "ステータス", "紐づく入荷No", "備考", "登録日時", "発注区分", "入荷処理日", "単価", "単位", "金額"] # 発注管理用（新規）

# 配合マスタは横持ち形式(品名ごとに1行)で保存する。
RECIPE_FIXED_COLS = ["品名", "大カテゴリ", "中カテゴリ"]
_ING_PRIORITY_KEYWORDS = ["こんにゃく", "海藻", "でんぷん", "デンプン", "石灰", "カルシウム", "食塩", "水"]

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
    hdr = all_vals[0]
    if len(hdr) < len(cols) and list(hdr) == list(cols[:len(hdr)]):
        w.update(range_name="A1", values=[cols])
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

# ーーー 配合マスタ（横持ち形式） ーーー
def _ing_sort_key(name):
    for idx, kw in enumerate(_ING_PRIORITY_KEYWORDS):
        if kw in name: return (idx, name)
    return (len(_ING_PRIORITY_KEYWORDS), name)

def _read_recipe_sheet_raw():
    w = _ws("配合マスタ", RECIPE_FIXED_COLS)
    all_vals = w.get_all_values()
    if not all_vals or not all_vals[0]: return [], []
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

def _parse_recipe_value(v):
    """配合の値を [{原料名, 比率}] に統一する。
    JSON文字列／リストのほか、アプリの編集画面が渡す「原料:5.0%, 水:95.0%」（調味料は「原料:10.0倍」）の文字列にも対応。
    （以前は文字列形式だと json.loads に失敗して空リストになり、保存すると全配合の原料・比率が消えていた）"""
    if isinstance(v, list): items = v
    else:
        v = str(v or "").strip()
        items = None
        if v.startswith("["):
            try: items = json.loads(v)
            except Exception: items = None
        if items is None:
            items = []
            for p in v.split(","):
                if ":" in p:
                    n, r = p.split(":", 1)
                    items.append({"原料名": n.strip(), "比率": r.replace("%", "").replace("倍", "").strip()})
    out = []
    for it in items:
        if isinstance(it, dict):
            val = it.get("比率", it.get("希釈倍率", ""))
            out.append({"原料名": str(it.get("原料名", "")).strip(), "比率": val})
    return out

def _build_wide_recipe_rows(recipe_list):
    ing_names = set()
    wide_rows = []
    for r in recipe_list:
        p_name = str(r.get("品名", "")).strip()
        if not p_name: continue
        ing_list = _parse_recipe_value(r.get("配合JSON", []))
        row = {"品名": p_name, "大カテゴリ": r.get("大カテゴリ", "その他"), "中カテゴリ": r.get("中カテゴリ", "その他")}
        for ing in ing_list:
            name = str(ing.get("原料名", "")).strip()
            if not name: continue
            row[name] = str(ing.get("比率", ""))
            ing_names.add(name)
        wide_rows.append(row)
    ing_cols = sorted(ing_names, key=_ing_sort_key)
    return RECIPE_FIXED_COLS + ing_cols, wide_rows

@st.cache_data(ttl=20)
def load_recipes():
    raw_rows, header = _read_recipe_sheet_raw()
    ing_cols = [c for c in header if c not in RECIPE_FIXED_COLS]
    res = []
    for r in raw_rows:
        p_name = str(r.get("品名", "")).strip()
        if not p_name: continue
        ing_list = []
        for col in ing_cols:
            val = str(r.get(col, "")).strip()
            if val: ing_list.append({"原料名": col, "比率": _f(val)}) # 配合比率は小数を許容
        res.append({
            "品名": p_name,
            "大カテゴリ": r.get("大カテゴリ", "その他"),
            "中カテゴリ": r.get("中カテゴリ", "その他"),
            "配合JSON": json.dumps(ing_list, ensure_ascii=False)
        })
    return res

def save_recipes(recs):
    header, wide_rows = _build_wide_recipe_rows(recs)
    # 安全装置：原料・比率が1つも無い内容で、今ある配合を上書きしない（全配合の消失防止）
    if wide_rows and len(header) <= len(RECIPE_FIXED_COLS):
        _, old_header = _read_recipe_sheet_raw()
        if len(old_header) > len(RECIPE_FIXED_COLS):
            raise ValueError("全ての配合の原料・比率が空になるため、配合マスタの保存を中止しました。")
    _write_recipe_sheet_wide(header, wide_rows)

@st.cache_data(ttl=20)
def load_recipe_logs(): return _read("レシピ変更履歴", COLS_REC_LOG)
def append_recipe_log(r): _append("レシピ変更履歴", COLS_REC_LOG, r)


# ーーー 入荷・在庫 ーーー
@st.cache_data(ttl=20)
def load_arrivals():
    rows = _read("入荷記録", COLS_ARR)
    for r in rows: 
        # UIに合わせて整数(int)として読み込むように統一
        r["袋数"] = _i(r.get("袋数"))
        r["1袋重量(kg)"] = _i(r.get("1袋重量(kg)", 20))
        r["総量(kg)"] = _i(r.get("総量(kg)"))
    return rows

def append_arrival(r): _append("入荷記録", COLS_ARR, r)
def update_arrival(no, r): _update("入荷記録", COLS_ARR, "入荷No", no, r)

# 【追加】入荷履歴のインライン編集・削除用
def save_arrivals(recs): 
    _over("入荷記録", COLS_ARR, recs)

def next_arrival_no(arr): 
    nums = [int(a.get('入荷No','A-0').split('-')[1]) for a in arr if '入荷No' in a and '-' in str(a.get('入荷No',''))]
    return f"A-{(max(nums + [0]) + 1):04d}"

@st.cache_data(ttl=20)
def load_brewing():
    rows = _read("仕込み記録", COLS_BRW)
    for r in rows:
        # UIに合わせて整数(int)として読み込むように統一
        r["仕込量(kg)"] = _i(r.get("仕込量(kg)"))
        r["こんにゃく精粉(kg)"] = _i(r.get("こんにゃく精粉(kg)"))
        r["海藻粉(kg)"] = _i(r.get("海藻粉(kg)"))
        r["デンプン(kg)"] = _i(r.get("デンプン(kg)"))
        r["石灰(kg)"] = _i(r.get("石灰(kg)"))
        r["石灰水(L)"] = _i(r.get("石灰水(L)"))
        r["仕込No"] = _i(r.get("仕込No"))
    return rows

def append_brewing(r): _append("仕込み記録", COLS_BRW, r)
def update_brewing(no, r): _update("仕込み記録", COLS_BRW, "仕込No", str(no), r)
def save_brewing(recs): _over("仕込み記録", COLS_BRW, recs)

def delete_brewing(no):
    w = _ws("仕込み記録", COLS_BRW)
    cvals = w.col_values(COLS_BRW.index("仕込No") + 1)
    if str(no) in cvals: w.delete_rows(cvals.index(str(no)) + 1)
    st.cache_data.clear()

def next_brewing_no(brw): 
    nums = [_i(b.get("仕込No")) for b in brw]
    return max(nums + [0]) + 1

@st.cache_data(ttl=20)
def load_adjustments():
    rows = _read("在庫調整", COLS_ADJ)
    for r in rows:
        # 【重要】以前はint変換(_i)していたため、棚卸で0にする際に書き込む
        # 小数の調整量(例: -37.6543袋)が -37 に切り捨てられ、在庫が永久に
        # ピッタリ0にならない不具合の原因になっていた。float(_f)に修正。
        r["調整袋数"] = _f(r.get("調整袋数"))
    return rows
def append_adjustment(r): _append("在庫調整", COLS_ADJ, r)


# ーーー 資材 ーーー
@st.cache_data(ttl=20)
def load_supplies():
    rows = _read("資材マスター", COLS_SUP)
    for r in rows: 
        r["初期在庫"] = _f(r.get("初期在庫"))
        r["発注点"] = _f(r.get("発注点"))
        # 表示順は未設定(空欄)と0を区別したいので、数値変換せず文字列のまま保持する
        r["表示順"] = str(r.get("表示順", "")).strip()
    return rows
def save_supplies(rs): _over("資材マスター", COLS_SUP, rs)

@st.cache_data(ttl=20)
def load_supply_logs():
    rows = _read("資材入出庫", COLS_LOG)
    for r in rows: r["数量"] = _f(r.get("数量"))  # 実地数量の小数入力を切り捨てないようfloatに変更
    return rows
def append_supply_log(r): _append("資材入出庫", COLS_LOG, r)
def delete_supply_log(log_id):
    w = _ws("資材入出庫", COLS_LOG)
    cvals = w.col_values(COLS_LOG.index("ログID") + 1)
    if str(log_id) in cvals: w.delete_rows(cvals.index(str(log_id)) + 1)
    st.cache_data.clear()


# ーーー マスタ系 ーーー
@st.cache_data(ttl=30)
def load_materials(): return _lcol("原料マスター", ["こんにゃく粉（国産）","こんにゃく粉（輸入）","海藻粉","加工デンプン","石灰","食塩"])
def save_materials(v): _scol("原料マスター", v)

@st.cache_data(ttl=30)
def load_makers(): return _lcol("メーカーマスター", ["滝田商店","荻野","オリヒロ","その他"])
def save_makers(v): _scol("メーカーマスター", v)

@st.cache_data(ttl=30)
def load_inspectors(): return _lcol("担当者マスター", ["若槻","志村","斎藤"])
def save_inspectors(v): _scol("担当者マスター", v)

# 【追加】粉グレードマスター（行と列の綺麗なリストとして管理）
@st.cache_data(ttl=30)
def load_grades(): return _lcol("グレードマスター", ["1級", "2級", "特等"])
def save_grades(v): _scol("グレードマスター", v)

@st.cache_data(ttl=30)
def load_order_points():
    try:
        rows = _ws("発注点マスター", ["material", "order_point"]).get_all_values()[1:]
    except Exception:
        return {}
    d = {}
    for r in rows:
        # 1行だけ列数が足りない/壊れていても、他の設定(グレード・除外ロット・
        # 石灰ルール・画像など)を丸ごと失わないよう、行単位でスキップする
        if not r or not r[0]: continue
        d[r[0]] = str(r[1]) if len(r) > 1 else ""
    return d
def save_order_points(d):
    w = _ws("発注点マスター", ["material","order_point"])
    w.clear()
    w.update(range_name="A1", values=[["material","order_point"]] + [[k,str(v)] for k,v in d.items()])
    st.cache_data.clear()


# ーーー 発注管理（新規シート独立管理） ーーー
@st.cache_data(ttl=20)
def load_purchase_orders():
    rows = _read("発注管理", COLS_PO)
    for r in rows: r["個数"] = _i(r.get("個数"))
    return rows

def save_purchase_orders(recs):
    _over("発注管理", COLS_PO, recs)


# ーーー 発注先マスタ（発注品目・メーカー(発注先)・担当者名・連絡先） ーーー
@st.cache_data(ttl=20)
def load_vendors(): return _read("発注先マスター", COLS_VND)
def save_vendors(recs): _over("発注先マスター", COLS_VND, recs)


# ーーー 入荷に紐づく書類（スキャンPDF・写真など）の保管 ーーー
# 台帳(入荷添付)と中身(入荷添付データ：base64を40,000字ずつ分割)の2シートで保管する。
@st.cache_data(ttl=20)
def load_attachments(): return _read("入荷添付", COLS_ATT)

def append_attachment(meta, b64):
    """meta: 台帳の1行(dict)、b64: ファイル内容のbase64文字列。中身→台帳の順に書き込む"""
    chunks = [b64[i:i + ATT_CHUNK] for i in range(0, len(b64), ATT_CHUNK)] or [""]
    w = _ws("入荷添付データ", COLS_ATTDATA)
    w.append_rows([[str(meta["添付ID"]), i, c] for i, c in enumerate(chunks)], value_input_option="RAW")
    meta = dict(meta); meta["分割数"] = len(chunks)
    _append("入荷添付", COLS_ATT, meta)

def get_attachment_data(att_id):
    """書類の中身(base64)を取り出す。必要なときだけ呼ぶ（キャッシュしない）"""
    w = _ws("入荷添付データ", COLS_ATTDATA)
    ids = w.col_values(1)
    idx = [i + 1 for i, v in enumerate(ids) if v == str(att_id)]
    if not idx: return ""
    rows = w.get(f"A{idx[0]}:C{idx[-1]}")
    rows = [r for r in rows if r and r[0] == str(att_id) and len(r) >= 3]
    rows.sort(key=lambda r: _i(r[1]))
    return "".join(r[2] for r in rows)

def delete_attachment(att_id):
    w = _ws("入荷添付データ", COLS_ATTDATA)
    ids = w.col_values(1)
    idx = [i + 1 for i, v in enumerate(ids) if v == str(att_id)]
    if idx: w.delete_rows(idx[0], idx[-1])
    m = _ws("入荷添付", COLS_ATT)
    cvals = m.col_values(1)
    if str(att_id) in cvals: m.delete_rows(cvals.index(str(att_id)) + 1)
    st.cache_data.clear()
