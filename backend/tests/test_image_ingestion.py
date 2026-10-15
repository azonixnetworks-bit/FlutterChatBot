from io import BytesIO
import pytest
from PIL import Image
from app.services.image_ingestion import ImageExtractor, ImageIngestionError

def test_image_creates_ocr_and_private_vision_chunks():
    out=BytesIO(); Image.new("RGB",(20,20),"white").save(out,"PNG")
    chunks=ImageExtractor(ocr=lambda _: "Demand zone").extract(out.getvalue(),source_id="s",asset_path="u/s/chart.png")
    assert [c.content_type for c in chunks] == ["image_ocr","image_vision"]
    assert chunks[1].metadata["asset_path"] == "u/s/chart.png"
def test_invalid_image_fails():
    with pytest.raises(ImageIngestionError): ImageExtractor().extract(b"bad",source_id="s",asset_path="x")
