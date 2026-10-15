from app.services.spreadsheet_ingestion import SpreadsheetExtractor, SpreadsheetIngestionError
import pytest

def test_csv_rows_keep_header_and_row_context():
    chunks=SpreadsheetExtractor().extract(b"Pair,Bias\nEURUSD,Bullish\n", file_type="csv", source_id="s")
    assert chunks[0].content == "Pair: EURUSD; Bias: Bullish"
    assert chunks[0].metadata["row_number"] == 2

def test_bad_workbook_fails():
    with pytest.raises(SpreadsheetIngestionError): SpreadsheetExtractor().extract(b"bad", file_type="xlsx", source_id="s")
