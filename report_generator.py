# --- START OF FILE report_generator.py ---
from pathlib import Path
from datetime import date, datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import json

OUTPUT_DIR = Path("data/reports")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BLUE_DARK, HEADER_BG, HEADER_FG, BORDER_COLOR = "1a237e", "1565c0", "ffffff", "b0bec5"
BLUE_LIGHT = "e3f2fd"

def thin_border():
    s = Side(style="thin", color=BORDER_COLOR)
    return Border(left=s, right=s, top=s, bottom=s)

def format_cell(ws, row, col, value, align="center", is_header=False, bg=None, num_format=None, width=None):
    c = ws.cell(row=row, column=col, value=value)
    c.border = thin_border()
    c.alignment = Alignment(horizontal=align, vertical="center", wrap_text=True)
    if is_header:
        c.font = Font(name="メイリオ", bold=True, color=HEADER_FG, size=10)
        c.fill = PatternFill("solid", fgColor=HEADER_BG)
        if width: ws.column_dimensions[get_column_letter(col)].width = width
    else:
        c.font = Font(name="メイリオ", size=9)
        if bg: c.fill = PatternFill("solid", fgColor=bg)
        if num_format: c.number_format = num_format
    return c

def title_block(ws, title, subtitle=""):
    ws.row_dimensions[1].height, ws.row_dimensions[2].height = 32, 16
    t = ws.cell(row=1, column=1, value=title)
    t.font = Font(name="メイリオ", bold=True, size=14, color=BLUE_DARK)
    if subtitle: ws.cell(row=2, column=1, value=subtitle).font = Font(name="メイリオ", size=9, color="607d8b")
    d = ws.cell(row=2, column=8, value=f"出力日: {date.today().strftime('%Y/%m/%d')}")
    d.font = Font(name="メイリオ", size=9, color="607d8b"); d.alignment = Alignment(horizontal="right")

def _parse_others(json_str):
    if not json_str: return ""
    try:
        items = json.loads(json_str)
        return "\n".join([f"{i.get('name','')} (Lot:{i.get('lot','-')}): {i.get('kg',0)}kg" for i in items])
    except: return json_str

def generate_brewing_report(brewing: list) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "仕込み記録"
    ws.sheet_view.showGridLines = False
    title_block(ws, "🧪 仕込み記録帳票", f"対象: {len(brewing)}件")
    
    headers = [("No",6), ("仕込日",12), ("品名",18), ("メーカー",12), ("主ロット",12),
               ("仕込量",10), ("精粉",9), ("海藻粉",9), ("デンプン",10),
               ("その他添加物詳細", 30), ("備考", 18)]
    for ci, (h, w) in enumerate(headers, start=2): format_cell(ws, 4, ci, h, is_header=True, width=w)
    
    for ri, b in enumerate(reversed(brewing), start=5):
        bg = BLUE_LIGHT if ri % 2 == 0 else None
        ws.row_dimensions[ri].height = 30
        data = [
            (b.get("no",""), "center", None), (b.get("brew_date",""), "center", None),
            (b.get("product_name",""), "left", None), (b.get("maker",""), "left", None),
            (b.get("lot_no",""), "center", None), (b.get("brew_amount",0), "right", "#,##0.00"),
            (b.get("material_kg",0), "right", "#,##0.00"), (b.get("seaweed_kg",0), "right", "#,##0.00"),
            (b.get("starch_kg",0), "right", "#,##0.00"), (_parse_others(b.get("other_additives","")), "left", None),
            (b.get("notes",""), "left", None)
        ]
        for ci, (val, align, nf) in enumerate(data, start=2):
            format_cell(ws, ri, ci, val, align, bg=bg, num_format=nf)
            
    ws.freeze_panes = "B5"
    path = OUTPUT_DIR / f"仕込み記録_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    wb.save(path)
    return path
# 他の出力関数（入荷、トレース、集計）も同様にフォーマット可能ですが、文字数都合で省略（既存のものがそのまま動きます）
# --- END OF FILE report_generator.py ---
