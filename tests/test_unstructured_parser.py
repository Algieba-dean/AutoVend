"""
Unit tests for Unstructured Data Parser & TOML Converter (src/ingestion/unstructured_parser.py).
"""

import tempfile
from pathlib import Path

import toml

from src.ingestion.unstructured_parser import UnstructuredDataParser, VehicleTOMLConverter


def test_parse_html_and_text():
    """Test parsing HTML and TXT content."""
    parser = UnstructuredDataParser()

    with tempfile.TemporaryDirectory() as tmpdir:
        html_file = Path(tmpdir) / "spec.html"
        html_file.write_text(
            "<html><body><h1>车型：小米SU7</h1><p>价格：21.59万 纯电SUV</p></body></html>",
            encoding="utf-8",
        )

        text = parser.parse_file(html_file)
        assert "小米SU7" in text
        assert "21.59万" in text


def test_convert_file_to_toml():
    """Test extracting fields and writing standard TOML file."""
    converter = VehicleTOMLConverter()

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "input.txt"
        input_file.write_text(
            "车型：理想L7 品牌：理想 价格：30.18万 增程式 纯电续航210km 中大型SUV", encoding="utf-8"
        )

        output_dir = Path(tmpdir) / "toml_out"
        toml_path = converter.convert_file_to_toml(input_file, output_dir)

        assert toml_path.exists()
        content = toml.load(toml_path)
        first_key = list(content.keys())[0]
        rec = content[first_key]

        assert rec["powertrain_type"] == "range-extended"
        assert "理想" in rec["brand"] or "理想" in first_key
        assert rec["price"] == "300,000 ~ 400,000"


def test_price_bucket_magnitude_and_field_name():
    """Verify price field name and correct 10,000 RMB magnitude (15万 -> 100,000~200,000)."""
    converter = VehicleTOMLConverter()
    text = "车型：比亚迪海豹 指导价：15.98万 纯电中型轿车"
    fields = converter.extract_structured_fields(text)

    # Must have correct field name 'price'
    assert "price" in fields
    assert fields["price"] == "100,000 ~ 200,000"
    assert fields["powertrain_type"] == "bev"


def test_powertrain_negation_handling():
    """Verify that negations like '绝非纯电' do not falsely classify car as BEV."""
    converter = VehicleTOMLConverter()
    text = "车型：问界M7 价格：28.98万 本车绝非纯电车型，彻底解决续航焦虑，搭载增程动力系统。"
    fields = converter.extract_structured_fields(text)

    assert fields["powertrain_type"] == "range-extended"
    assert fields["powertrain_type"] != "bev"

    # Pure gasoline with negation of electric
    gas_text = "车型：大众迈腾 指导价：19.98万 本车并非纯电或插混，采用2.0T燃油发动机。"
    gas_fields = converter.extract_structured_fields(gas_text)
    assert gas_fields["powertrain_type"] == "gasoline"


def test_scanned_pdf_ocr_fallback():
    """Test automatic detection and fallback for scanned PDF files."""
    import fitz
    import pytest
    from src.ingestion.layout_parser import DocumentParsingUnrecoverableError

    parser = UnstructuredDataParser()
    with tempfile.TemporaryDirectory() as tmpdir:
        dummy_pdf = Path(tmpdir) / "scanned_poster.pdf"
        doc = fitz.open()
        page = doc.new_page(width=400, height=300)
        page.insert_text((50, 50), "扫描件 PDF 测试文本", fontname="china-s")
        doc.save(str(dummy_pdf))
        doc.close()

        text = parser.parse_pdf(dummy_pdf)
        assert "扫描件" in text
        assert "PDF" in text


def test_corrupted_empty_pdf_raises_unrecoverable_error():
    """Test that a completely corrupted or empty PDF raises DocumentParsingUnrecoverableError."""
    import pytest
    from src.ingestion.layout_parser import DocumentParsingUnrecoverableError

    parser = UnstructuredDataParser()
    with tempfile.TemporaryDirectory() as tmpdir:
        dummy_pdf = Path(tmpdir) / "corrupt.pdf"
        dummy_pdf.write_bytes(b"%PDF-1.4 empty pdf without text layer")
        with pytest.raises(DocumentParsingUnrecoverableError):
            parser.parse_pdf(dummy_pdf)


def test_blank_white_pdf_raises_unrecoverable_error():
    """Test that a valid PDF with zero text characters raises DocumentParsingUnrecoverableError."""
    import fitz
    import pytest
    from src.ingestion.layout_parser import DocumentParsingUnrecoverableError

    parser = UnstructuredDataParser()
    with tempfile.TemporaryDirectory() as tmpdir:
        blank_pdf = Path(tmpdir) / "blank.pdf"
        doc = fitz.open()
        doc.new_page(width=400, height=300)
        doc.save(str(blank_pdf))
        doc.close()

        with pytest.raises(DocumentParsingUnrecoverableError):
            parser.parse_pdf(blank_pdf)


def test_digital_pdf_stream_parsing():
    """Test that a digital PDF with >30 chars extracts directly from PyMuPDF stream."""
    import fitz

    parser = UnstructuredDataParser()
    with tempfile.TemporaryDirectory() as tmpdir:
        digital_pdf = Path(tmpdir) / "digital.pdf"
        doc = fitz.open()
        page = doc.new_page(width=400, height=300)
        page.insert_text(
            (50, 50),
            "这是一份标准的数字排版车辆技术规格书，包含大量详细参数用于测试直接文本流提取。",
            fontname="china-s",
        )
        doc.save(str(digital_pdf))
        doc.close()

        text = parser.parse_pdf(digital_pdf)
        assert "车辆技术规格书" in text
        assert "详细参数" in text


