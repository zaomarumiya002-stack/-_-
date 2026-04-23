# --- START OF FILE report_generator.py ---
"""帳票生成モジュール（Excel出力）"""
from pathlib import Path
from datetime import date, datetime
import openpyxl
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side, numbers
)
from openpyxl.utils import get_column_letter

OUTPUT_DIR = Path("data/reports")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── スタイル定義 ─────────────────────────────────────────────────
BLUE_DARK  = "1a237e"
BLUE_MID   = "1565c0"
BLUE_LIGHT = "e3f2fd"
HEADER_BG  = "1565c0"
HEADER_FG  = "ffffff"
ACCENT     = "e8f5e9"
BORDER_COLOR = "b0bec5"

def thin_border():
    s = Side(style="thin", color=BORDER_COLOR)
    return Border(left=s, right=s, top=s, bottom=s)

def header_style(ws, row, col, value, width=None):
    cell = ws.cell(row=row, column=col, value=value)
    cell.font = Font(name="メイリオ", bold=True, color=HEADER_FG, size=10)
    cell.fill = PatternFill("solid", fgColor=HEADER_BG)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = thin_border()
    if width:
        ws.column_dimensions[get_column_letter(col)].width = width
    return cell

def data_style(ws, row, col, value, align="left", num_format=None, bg=None):
    cell = ws.cell(row=row, column=col, value=value)
    cell.font = Font(name="メイリオ", size=9)
    cell.alignment = Alignment(horizontal=align, vertical="center", wrap_text=True)
    cell.border = thin_border()
    if bg:
        cell.fill = PatternFill("solid", fgColor=bg)
    if num_format:
        cell.number_format = num_format
    return cell

def title_block(ws, title, subtitle=""):
    ws.row_dimensions[1].height = 32
    ws.row_dimensions[2].height = 16
    t = ws.cell(row=1, column=1, value=title)
    t.font = Font(name="メイリオ", bold=True, size=14, color=BLUE_DARK)
    t.alignment = Alignment(horizontal="left", vertical="center")
    if subtitle:
        s = ws.cell(row=2, column=1, value=subtitle)
        s.font = Font(name="メイリオ", size=9, color="607d8b")
    d = ws.cell(row=2, column=8, value=f"出力日: {date.today().strftime('%Y年%m月%d日')}")
    d.font = Font(name="メイリオ", size=9, color="607d8b")
    d.alignment = Alignment(horizontal="right")

# ─── 入荷記録帳票 ────────────────────────────────────────────────
def generate_arrival_report(arrivals: list) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "入荷記録"
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 3

    title_block(ws, "📦 原料入荷記録帳票", f"対象件数: {len(arrivals)}件")

    headers = [
        ("入荷No", 12), ("入荷日", 12), ("メーカー", 14), ("ロットNo", 14),
        ("原料種別", 18), ("袋数", 7), ("総量(kg)", 10),
        ("搬入温度", 10), ("外観", 10), ("臭い", 10), ("包装", 10),
        ("色調", 10), ("異物", 10), ("水分", 10), ("賞味期限", 10),
        ("異常内容", 18), ("担当者", 10), ("備考", 16)
    ]

    HR = 4
    ws.row_dimensions[HR].height = 28
    for ci, (h, w) in enumerate(headers, start=2):
        header_style(ws, HR, ci, h, w)

    def check_val(v):
        if v and "OK" in v: return "✓ OK"
        if v and "NG" in v: return "✗ NG"
        if v and "なし" in v: return "✓ なし"
        if v and "あり" in v: return "✗ あり"
        return v or "-"

    for ri, a in enumerate(reversed(arrivals), start=HR+1):
        bg = BLUE_LIGHT if ri % 2 == 0 else None
        ws.row_dimensions[ri].height = 20
        row_data = [
            (a.get("arrival_no",""), "center"),
            (a.get("arrival_date",""), "center"),
            (a.get("maker",""), "left"),
            (a.get("lot_no",""), "center"),
            (a.get("material_type",""), "left"),
            (a.get("bags",0), "right"),
            (a.get("total_kg",0), "right"),
            (check_val(a.get("transport_temp","")), "center"),
            (check_val(a.get("appearance","")), "center"),
            (check_val(a.get("odor","")), "center"),
            (check_val(a.get("packaging","")), "center"),
            (check_val(a.get("color_check","")), "center"),
            (check_val(a.get("contamination","")), "center"),
            (check_val(a.get("moisture","")), "center"),
            (check_val(a.get("expiry_check","")), "center"),
            (a.get("abnormal_detail","") or "-", "left"),
            (a.get("inspector",""), "center"),
            (a.get("remarks","") or "-", "left"),
        ]
        for ci, (val, align) in enumerate(row_data, start=2):
            data_style(ws, ri, ci, val, align, bg=bg)

    ws.freeze_panes = f"B{HR+1}"
    ws.auto_filter.ref = f"B{HR}:{get_column_letter(len(headers)+1)}{HR}"

    path = OUTPUT_DIR / f"入荷記録_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    wb.save(path)
    return path


# ─── 仕込み記録帳票 ──────────────────────────────────────────────
def generate_brewing_report(brewing: list) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "仕込み記録"
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 3

    title_block(ws, "🧪 仕込み記録帳票", f"対象件数: {len(brewing)}件")

    headers = [
        ("No", 6), ("仕込日", 12), ("品名", 20), ("メーカー", 12),
        ("主ロットNo", 12), ("海藻ロット", 12), ("デンプンロット", 14),
        ("仕込量(kg)", 10), ("精粉(kg)", 9), ("海藻粉(kg)", 9),
        ("加工デンプン(kg)", 14), ("デンプン種別", 10),
        ("石灰(kg)", 9), ("石灰水(ℓ)", 9), ("備考", 18)
    ]

    HR = 4
    ws.row_dimensions[HR].height = 28
    for ci, (h, w) in enumerate(headers, start=2):
        header_style(ws, HR, ci, h, w)

    total_brew = total_mat = total_sea = total_starch = total_lime = 0.0

    for ri, b in enumerate(reversed(brewing), start=HR+1):
        bg = BLUE_LIGHT if ri % 2 == 0 else None
        ws.row_dimensions[ri].height = 20
        bv = b.get("brew_amount", 0) or 0
        mv = b.get("material_kg", 0) or 0
        sv = b.get("seaweed_kg", 0) or 0
        stv = b.get("starch_kg", 0) or 0
        lv = b.get("lime_kg", 0) or 0
        total_brew += bv; total_mat += mv; total_sea += sv; total_starch += stv; total_lime += lv

        row_data = [
            (b.get("no",""), "center"),
            (b.get("brew_date",""), "center"),
            (b.get("product_name",""), "left"),
            (b.get("maker",""), "left"),
            (b.get("lot_no",""), "center"),
            (b.get("seaweed_lot","") or "-", "center"),
            (b.get("starch_lot","") or "-", "center"),
            (bv, "right"),
            (mv, "right"),
            (sv, "right"),
            (stv, "right"),
            (b.get("starch_type","") or "-", "center"),
            (lv, "right"),
            (b.get("lime_water_l",0) or 0, "right"),
            (b.get("notes","") or "-", "left"),
        ]
        for ci, (val, align) in enumerate(row_data, start=2):
            nf = "#,##0.00" if isinstance(val, float) else None
            data_style(ws, ri, ci, val, align, num_format=nf, bg=bg)

    # 合計行
    total_row = HR + len(brewing) + 1
    ws.row_dimensions[total_row].height = 22
    for ci in range(2, len(headers)+2):
        cell = ws.cell(row=total_row, column=ci)
        cell.font = Font(name="メイリオ", bold=True, size=9)
        cell.fill = PatternFill("solid", fgColor="fff9c4")
        cell.border = thin_border()
        cell.alignment = Alignment(horizontal="right", vertical="center")
    ws.cell(row=total_row, column=2, value="合計").alignment = Alignment(horizontal="center", vertical="center")
    
    # 9:仕込量, 10:精粉, 11:海藻粉, 12:加工デンプン, 14:石灰
    for col, val in [(9, total_brew), (10, total_mat), (11, total_sea), (12, total_starch), (14, total_lime)]:
        c = ws.cell(row=total_row, column=col, value=val)
        c.font = Font(name="メイリオ", bold=True, size=9)
        c.number_format = "#,##0.00"

    ws.freeze_panes = f"B{HR+1}"
    ws.auto_filter.ref = f"B{HR}:{get_column_letter(len(headers)+1)}{HR}"

    path = OUTPUT_DIR / f"仕込み記録_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    wb.save(path)
    return path


# ─── トレース帳票 ────────────────────────────────────────────────
def generate_trace_report(results: list, search_type: str, keyword: str) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "原料トレース"
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 3

    title_block(ws, "🔍 原料トレース帳票", f"検索条件: {search_type} = {keyword}　件数: {len(results)}件")

    headers_list = list(results[0].keys()) if results else []
    widths = {"入荷No":12,"メーカー":14,"入荷日":12,"主ロットNo":12,
              "海藻ロット":12,"デンプンロット":14,"袋数":8,"外観":10,
              "使用日":12,"品名":20,"精粉(kg)":10,"海藻(kg)":10,"デンプン(kg)":10,"仕込量(kg)":10,"仕込みNo":10}

    HR = 4
    ws.row_dimensions[HR].height = 28
    for ci, h in enumerate(headers_list, start=2):
        header_style(ws, HR, ci, h, widths.get(h, 12))

    for ri, row in enumerate(results, start=HR+1):
        bg = BLUE_LIGHT if ri % 2 == 0 else None
        ws.row_dimensions[ri].height = 20
        for ci, key in enumerate(headers_list, start=2):
            val = row.get(key, "")
            align = "right" if isinstance(val, (int, float)) else "left" if ci > 8 else "center"
            nf = "#,##0.00" if isinstance(val, float) else None
            data_style(ws, ri, ci, val, align, num_format=nf, bg=bg)

    path = OUTPUT_DIR / f"原料トレース_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    wb.save(path)
    return path


# ─── 集計帳票（日別・月別・年間） ──────────────────────────────────
def generate_summary_report(summary: list, brewing_all: list, period_type: str) -> Path:
    wb = openpyxl.Workbook()

    # シート1: 集計表
    ws = wb.active
    ws.title = f"{period_type}集計"
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 3

    title_block(ws, f"📊 {period_type} 原料使用量集計帳票")

    headers_list = list(summary[0].keys()) if summary else []
    HR = 4
    ws.row_dimensions[HR].height = 28
    for ci, h in enumerate(headers_list, start=2):
        w = 12 if "平均" in h or "計" in h else 14
        header_style(ws, HR, ci, h, w)

    for ri, row in enumerate(summary, start=HR+1):
        bg = BLUE_LIGHT if ri % 2 == 0 else None
        ws.row_dimensions[ri].height = 20
        for ci, key in enumerate(headers_list, start=2):
            val = row.get(key, "")
            align = "center" if ci == 2 else "right"
            nf = "#,##0.00" if isinstance(val, float) else None
            data_style(ws, ri, ci, val, align, num_format=nf, bg=bg)

    # シート2: 全仕込み明細
    ws2 = wb.create_sheet("仕込み明細")
    ws2.sheet_view.showGridLines = False
    ws2.column_dimensions["A"].width = 3
    title_block(ws2, "仕込み記録 全明細")
    generate_brewing_detail(ws2, brewing_all)

    path = OUTPUT_DIR / f"{period_type}集計_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    wb.save(path)
    return path

def generate_brewing_detail(ws, brewing):
    headers = [("No",6),("仕込日",12),("品名",20),("メーカー",12),("主ロットNo",12),
               ("海藻ロット",12),("デンプンロット",14),
               ("仕込量(kg)",10),("精粉(kg)",9),("海藻粉(kg)",9),("デンプン(kg)",12),("石灰(kg)",9)]
    HR = 4
    ws.row_dimensions[HR].height = 28
    for ci, (h, w) in enumerate(headers, start=2):
        header_style(ws, HR, ci, h, w)
    for ri, b in enumerate(reversed(brewing), start=HR+1):
        bg = BLUE_LIGHT if ri % 2 == 0 else None
        ws.row_dimensions[ri].height = 18
        vals = [b.get("no",""), b.get("brew_date",""), b.get("product_name",""),
                b.get("maker",""), b.get("lot_no",""), b.get("seaweed_lot",""), b.get("starch_lot",""),
                b.get("brew_amount",0), b.get("material_kg",0), b.get("seaweed_kg",0), 
                b.get("starch_kg",0), b.get("lime_kg",0)]
        for ci, val in enumerate(vals, start=2):
            align = "right" if isinstance(val, (int, float)) else "center" if ci <= 8 else "left"
            nf = "#,##0.00" if isinstance(val, float) else None
            data_style(ws, ri, ci, val, align, num_format=nf, bg=bg)
# --- END OF FILE report_generator.py ---
