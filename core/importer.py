"""
core/importer.py - 银行账单导入解析器

支持从 Excel（.xlsx）和 CSV（.csv）文件中解析银行账单。
采用列映射策略：用户指定源文件中各列对应的数据字段。
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import Optional

from core.category import list_categories, get_category
from core.transaction import create_transaction


class FileType(str, Enum):
    XLSX = "xlsx"
    CSV = "csv"


@dataclass
class ColumnMapping:
    """列映射配置：源文件列名 → 数据字段。"""
    date_col: str = ""       # 交易日期列
    amount_col: str = ""     # 金额列
    note_col: str = ""       # 备注/摘要列
    category_col: str = ""   # 分类列（可选，有值则自动匹配）
    type_col: str = ""       # 收支类型列（可选，正数收入/负数支出）
    amount_positive_is_income: bool = False  # 正数代表收入（否则默认正数为支出）
    skip_header: int = 1      # 跳过前 N 行（通常跳过表头）


@dataclass
class ImportError:
    """导入错误记录。"""
    row: int
    message: str


@dataclass
class ImportResult:
    """导入结果。"""
    total_rows: int = 0
    imported: int = 0
    skipped: int = 0
    errors: list[ImportError] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.errors and all("跳过" in e.message for e in self.errors) or self.imported > 0


def detect_file_type(file_path: str) -> FileType:
    """根据文件扩展名检测文件类型。"""
    ext = Path(file_path).suffix.lower()
    if ext == ".xlsx":
        return FileType.XLSX
    elif ext == ".csv":
        return FileType.CSV
    else:
        raise ValueError(f"不支持的文件格式：{ext}，仅支持 .xlsx 和 .csv")


def parse_file(file_path: str, mapping: ColumnMapping,
               default_type: str = "expense",
               default_category_id: Optional[int] = None) -> list[dict]:
    """
    解析账单文件，返回结构化记录列表。

    Returns:
        [{"date": "2026-06-27", "amount": 93.80, "type": "expense",
          "note": "超市购物", "category_id": 1}, ...]
    """
    ftype = detect_file_type(file_path)

    if ftype == FileType.XLSX:
        rows = _parse_xlsx(file_path, mapping)
    else:
        rows = _parse_csv(file_path, mapping)

    records = []
    for i, raw in enumerate(rows, start=mapping.skip_header + 1):
        try:
            record = _raw_to_record(raw, mapping, default_type, default_category_id)
            if record:
                records.append(record)
        except Exception:
            continue

    return records


def import_records(records: list[dict]) -> ImportResult:
    """
    批量导入交易记录。

    Args:
        records: parse_file 返回的记录列表

    Returns:
        ImportResult 包含导入统计
    """
    result = ImportResult(total_rows=len(records))

    for i, rec in enumerate(records):
        try:
            # 检查必填字段
            if not rec.get("date") or not rec.get("amount"):
                result.skipped += 1
                result.errors.append(ImportError(row=i + 1, message="跳过：缺少日期或金额"))
                continue

            # 金额校验
            if rec["amount"] <= 0:
                result.skipped += 1
                result.errors.append(ImportError(row=i + 1, message=f"跳过：金额无效 {rec['amount']}"))
                continue

            # 日期格式校验
            date.fromisoformat(rec["date"])

            create_transaction(
                type=rec.get("type", "expense"),
                amount=rec["amount"],
                category_id=rec.get("category_id", 1),
                date=rec["date"],
                note=rec.get("note", "") or "",
                source="import",
            )
            result.imported += 1

        except Exception as e:
            result.errors.append(ImportError(row=i + 1, message=str(e)))

    return result


def match_category_by_keyword(keyword: str, cat_type: str = "expense") -> Optional[int]:
    """
    根据关键词模糊匹配分类名称，返回分类 ID。

    Args:
        keyword: 账单中的分类/商户关键词
        cat_type: 收支类型

    Returns:
        匹配到的分类 ID，未匹配返回 None
    """
    if not keyword:
        return None

    cats = list_categories(type=cat_type)
    keyword_lower = keyword.strip().lower()

    for cat in cats:
        name_lower = cat["name"].lower()
        if keyword_lower in name_lower or name_lower in keyword_lower:
            return cat["id"]

    return None


# ─── 内部函数 ──────────────────────────────────────────────────────────────

def _parse_xlsx(file_path: str, mapping: ColumnMapping) -> list[dict]:
    """解析 Excel 文件。"""
    import openpyxl
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    ws = wb.active

    rows = []
    for row in ws.iter_rows(values_only=True):
        rows.append(row)

    wb.close()
    return rows


def _parse_csv(file_path: str, mapping: ColumnMapping) -> list[dict]:
    """解析 CSV 文件。"""
    rows = []
    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:
            rows.append(row)
    return rows


def _raw_to_record(raw: tuple, mapping: ColumnMapping,
                    default_type: str, default_category_id: Optional[int]) -> Optional[dict]:
    """将原始行数据转为记录字典。"""
    # 跳过空行
    if not raw or all(c is None or str(c).strip() == "" for c in raw):
        return None

    # 将行转为以列索引为 key 的字典（同时支持按列名匹配）
    row_dict = {}
    for i, val in enumerate(raw):
        row_dict[i] = val

    # 获取值
    def get_col(col_name: str):
        """按列名或索引获取值。"""
        if not col_name:
            return None
        # 先尝试按列名匹配
        for key, val in row_dict.items():
            if str(val).strip() == col_name and key > 0:
                # 值本身等于列名，说明当前行就是表头
                continue
            if isinstance(key, str) and key.strip().lower() == col_name.lower():
                return val
        # 尝试按列名在第一行（表头）中查找索引
        try:
            idx = int(col_name)
            return row_dict.get(idx)
        except (ValueError, TypeError):
            pass
        # 在表头行中查找列名匹配
        return None

    # 日期
    date_val = _parse_date(get_col(mapping.date_col))
    if not date_val:
        return None

    # 金额
    amount_val = _parse_amount(get_col(mapping.amount_col))
    if amount_val is None:
        return None

    # 收支类型
    tx_type = default_type
    if mapping.type_col:
        type_val = get_col(mapping.type_col)
        if type_val:
            type_str = str(type_val).strip().lower()
            if type_str in ("收入", "income", "转入", "存入", "工资", "奖金", "津贴"):
                tx_type = "income"

    # 正负号判断
    if mapping.amount_positive_is_income and amount_val > 0:
        tx_type = "income"
    elif not mapping.amount_positive_is_income and amount_val > 0:
        tx_type = "expense"

    # 备注
    note_val = ""
    if mapping.note_col:
        note_raw = get_col(mapping.note_col)
        if note_raw:
            note_val = str(note_raw).strip()

    # 分类匹配
    category_id = default_category_id or 1
    if mapping.category_col:
        cat_raw = get_col(mapping.category_col)
        if cat_raw:
            matched = match_category_by_keyword(str(cat_raw).strip(), tx_type)
            if matched:
                category_id = matched

    return {
        "date": date_val,
        "amount": abs(amount_val),
        "type": tx_type,
        "note": note_val,
        "category_id": category_id,
    }


def _parse_date(value) -> Optional[str]:
    """解析日期值为 YYYY-MM-DD 字符串。"""
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()

    val_str = str(value).strip()
    if not val_str:
        return None

    # 尝试多种日期格式
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y年%m月%d日",
        "%m-%d",
        "%m/%d",
        "%Y%m%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(val_str, fmt)
            # 补全年份
            if dt.year == 1900 and fmt in ("%m-%d", "%m/%d"):
                dt = dt.replace(year=date.today().year)
            return dt.date().isoformat()
        except ValueError:
            continue

    return None


def _parse_amount(value) -> Optional[float]:
    """解析金额值为正浮点数。"""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return abs(float(value))

    val_str = str(value).strip()
    if not val_str:
        return None

    # 去掉货币符号和逗号
    for ch in ["￥", "¥", "$", ",", " "]:
        val_str = val_str.replace(ch, "")

    try:
        return abs(float(val_str))
    except ValueError:
        return None
