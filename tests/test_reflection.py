"""
Unit tests for Self-Reflection & Hallucination Defense Engine in AutoVend Agent.
"""

from src.agent.reflection import (
    check_sales_compliance,
    reflect_and_guard,
    verify_numeric_hallucinations,
)


def test_sales_compliance_risk_interception():
    """Test拦截未经授权的极速价格或违规承诺."""
    raw_response = "这款车只要今天下单，我保证全网最低价，而且承诺包过户避税！"
    sanitized, warnings = check_sales_compliance(raw_response)

    assert len(warnings) == 2
    assert "保证全网最低价" not in sanitized
    assert "承诺包过户避税" not in sanitized
    assert "合同为准" in sanitized or "税法规定" in sanitized


def test_verify_numeric_hallucinations_detection():
    """Test 检测与真实匹配车辆超范围的参数幻觉."""
    raw_response = "为您推荐这款纯电SUV，续航达到 950 km，完全不用担心长途问题。"
    matched_cars = [
        {"model": "Model A", "electric_range": "450km"},
        {"model": "Model B", "electric_range": "500km"},
    ]

    warnings = verify_numeric_hallucinations(raw_response, matched_cars)
    assert len(warnings) == 1
    assert "可能存在续航参数幻觉" in warnings[0]


def test_reflect_and_guard_clean():
    """Test standard response without warnings."""
    raw_response = "为您推荐 Model A，纯电续航 450km，非常适合城市通勤使用。"
    matched_cars = [{"model": "Model A", "electric_range": "450km"}]

    sanitized, warnings = reflect_and_guard(raw_response, matched_cars)
    assert sanitized == raw_response
    assert len(warnings) == 0
