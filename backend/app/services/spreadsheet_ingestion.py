from __future__ import annotations
import csv
from io import BytesIO, StringIO
import openpyxl
from app.services.chunking import ChunkDraft

class SpreadsheetIngestionError(ValueError): pass

class SpreadsheetExtractor:
    def extract(self, data: bytes, *, file_type: str, source_id: str) -> list[ChunkDraft]:
        if not data: raise SpreadsheetIngestionError("The spreadsheet is empty.")
        if file_type == "csv":
            rows = list(csv.reader(StringIO(data.decode("utf-8-sig", errors="replace"))))
            return self._rows(rows, "CSV", source_id)
        try:
            book = openpyxl.load_workbook(BytesIO(data), read_only=True, data_only=True)
        except Exception as exc:
            raise SpreadsheetIngestionError("The file is not a valid XLS/XLSX workbook.") from exc
        chunks=[]
        for sheet in book.worksheets:
            chunks.extend(self._rows([[str(c) if c is not None else "" for c in row] for row in sheet.iter_rows(values_only=True)], sheet.title, source_id))
        return chunks
    @staticmethod
    def _rows(rows, sheet, source):
        rows=[r for r in rows if any(str(v).strip() for v in r)]
        if len(rows)<2: return []
        headers=[str(v).strip() or f"Column {i+1}" for i,v in enumerate(rows[0])]
        return [ChunkDraft("; ".join(f"{headers[i]}: {value}" for i,value in enumerate(row) if value), "spreadsheet_table", metadata={"source_id":source,"extraction_method":"spreadsheet","sheet_name":sheet,"row_number":n}) for n,row in enumerate(rows[1:],2) if any(row)]
