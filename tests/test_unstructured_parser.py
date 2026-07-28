"""
Unit tests for Unstructured Data Parser & TOML Converter (src/ingestion/unstructured_parser.py).
"""

from pathlib import Path
import tempfile
import toml

from src.ingestion.unstructured_parser import UnstructuredDataParser, VehicleTOMLConverter


def test_parse_html_and_text():
    """Test parsing HTML and TXT content."""
    parser = UnstructuredDataParser()

    with tempfile.TemporaryDirectory() as tmpdir:
        html_file = Path(tmpdir) / "spec.html"
        html_file.write_text("<html><body><h1>车型：小米SU7</h1><p>价格：21.59万 纯电SUV</p></body></html>", encoding="utf-8")

        text = parser.parse_file(html_file)
        assert "小米SU7" in text
        assert "21.59万" in text


def test_convert_file_to_toml():
    """Test extracting fields and writing standard TOML file."""
    converter = VehicleTOMLConverter()

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "input.txt"
        input_file.write_text("车型：理想L7 品牌：理想 价格：30.18万 增程式 纯电续航210km 中大型SUV", encoding="utf-8")

        output_dir = Path(tmpdir) / "toml_out"
        toml_path = converter.convert_file_to_toml(input_file, output_dir)

        assert toml_path.exists()
        content = toml.load(toml_path)
        first_key = list(content.keys())[0]
        rec = content[first_key]

        assert rec["powertrain_type"] == "range-extended"
        assert "理想" in rec["brand"] or "理想" in first_key


def test_scanned_pdf_ocr_fallback():
    """Test automatic detection and fallback for scanned PDF files."""
    parser = UnstructuredDataParser()
    with tempfile.TemporaryDirectory() as tmpdir:
        dummy_pdf = Path(tmpdir) / "scanned_poster.pdf"
        dummy_pdf.write_bytes(b"%PDF-1.4 empty pdf without text layer")

        text = parser.parse_pdf(dummy_pdf)
        assert "扫描件" in text or "PDF" in text
