import io
import json
from datetime import datetime
from decimal import Decimal
from urllib.parse import quote

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.agent.llm import llm_zhipu
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt
from app.services.query_service import QueryService


class ReportService:
    def __init__(self, query_service: QueryService):
        self.query_service = query_service

    async def generate_report(self, query: str) -> tuple[bytes, str]:
        collected = await self.query_service.collect_query(query)
        error = collected.get("error")
        data = collected.get("data") or []
        sql = collected.get("sql") or ""

        analysis = ""
        if not error and data:
            analysis = await self._generate_analysis(query, sql, data)

        wb = self._build_workbook(
            query=query,
            sql=sql,
            data=data,
            analysis=analysis,
            error=error,
        )

        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)
        content = bio.getvalue()

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        ascii_name = f"report_{ts}.xlsx"
        utf8_name = quote(f"数据报表_{ts}.xlsx")
        disposition = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{utf8_name}"
        return content, disposition

    async def _generate_analysis(self, query: str, sql: str, data: list[dict]) -> str:
        limit = 20
        preview = data[:limit]
        try:
            prompt = PromptTemplate(
                template=load_prompt("generate_report_analysis"),
                input_variables=["query", "sql", "data_preview", "limit", "total"],
            )
            chain = prompt | llm_zhipu | StrOutputParser()
            result = await chain.ainvoke(
                {
                    "query": query,
                    "sql": sql or "（未生成）",
                    "data_preview": json.dumps(preview, ensure_ascii=False, default=str, indent=2),
                    "limit": limit,
                    "total": len(data),
                }
            )
            return result.strip()
        except Exception as e:
            logger.warning(f"生成报表分析失败: {e}")
            return "（自动分析生成失败，请查看数据明细）"

    def _build_workbook(self, query: str, sql: str, data: list[dict], analysis: str, error):
        wb = Workbook()

        title_font = Font(name="微软雅黑", size=16, bold=True, color="1F4E79")
        label_font = Font(name="微软雅黑", size=11, bold=True, color="333333")
        value_font = Font(name="微软雅黑", size=11, color="333333")
        header_font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill("solid", fgColor="4472C4")
        thin = Side(style="thin", color="BFBFBF")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        wrap_top = Alignment(horizontal="left", vertical="top", wrap_text=True)
        wrap_center = Alignment(horizontal="left", vertical="center", wrap_text=True)

        ws = wb.active
        ws.title = "报表概览"
        ws.column_dimensions["A"].width = 14
        ws.column_dimensions["B"].width = 90

        ws.merge_cells("A1:B1")
        c = ws["A1"]
        c.value = "数据报表"
        c.font = title_font
        c.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 32

        rows = [
            ("查询问题", query),
            ("生成时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("数据行数", len(data) if not error else "查询失败"),
        ]
        if error:
            rows.append(("错误信息", str(error)))
        rows.append(("执行SQL", sql or "（未生成）"))
        rows.append(("分析结论", analysis or "（无）"))

        row_idx = 3
        for label, value in rows:
            a = ws.cell(row=row_idx, column=1, value=label)
            a.font = label_font
            a.alignment = wrap_center
            a.border = border
            b = ws.cell(row=row_idx, column=2, value=value)
            b.font = value_font
            b.alignment = wrap_top
            b.border = border
            if label in ("执行SQL", "分析结论", "错误信息"):
                ws.row_dimensions[row_idx].height = 90
            row_idx += 1

        ws2 = wb.create_sheet("数据明细")
        if data:
            columns = list(data[0].keys())
            ws2.append(columns)
            for col_idx, col_name in enumerate(columns, start=1):
                cell = ws2.cell(row=1, column=col_idx)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = border
            for row in data:
                ws2.append([self._normalize(row.get(col)) for col in columns])
            max_row = ws2.max_row
            for r in range(2, max_row + 1):
                for col_idx in range(1, len(columns) + 1):
                    cell = ws2.cell(row=r, column=col_idx)
                    cell.border = border
                    cell.alignment = Alignment(vertical="center")
            for col_idx, col_name in enumerate(columns, start=1):
                max_len = len(str(col_name))
                for row in data:
                    val = row.get(col_name)
                    length = len(str(val)) if val is not None else 0
                    if length > max_len:
                        max_len = length
                ws2.column_dimensions[get_column_letter(col_idx)].width = min(max(max_len + 2, 10), 50)
            ws2.freeze_panes = "A2"
            ws2.auto_filter.ref = f"A1:{get_column_letter(len(columns))}{max_row}"
        else:
            ws2.merge_cells("A1:B1")
            c = ws2["A1"]
            c.value = "未查询到有效数据" if not error else "查询执行失败，请查看报表概览中的错误信息"
            c.font = label_font
            c.alignment = Alignment(horizontal="center", vertical="center")
            ws2.row_dimensions[1].height = 30

        return wb

    @staticmethod
    def _normalize(value):
        if isinstance(value, Decimal):
            return float(value)
        return value