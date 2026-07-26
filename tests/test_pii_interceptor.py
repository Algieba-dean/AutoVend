"""
Tests for the PII interceptor.

Two things have to hold at once and they pull against each other: nothing
sensitive may reach a model, and the product still has to greet the customer by
name and book a test drive against a real phone number. So most of these assert
the *round trip*, not just the masking.

Marked slow: Presidio loads a spaCy pipeline, which costs seconds.
"""

import re

import pytest

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def pii():
    from src.privacy import PIIInterceptor

    interceptor = PIIInterceptor()
    try:
        interceptor.detect("warmup")
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"Presidio unavailable: {exc}")
    return interceptor


class TestChineseDetection:
    """Presidio's built-ins find none of these, which is why they exist."""

    @pytest.mark.parametrize(
        "text,entity,value",
        [
            ("我的手机是13888888888", "CN_PHONE_NUMBER", "13888888888"),
            ("身份证310101199001011234", "CN_ID_CARD", "310101199001011234"),
            ("车牌沪A12345", "CN_LICENSE_PLATE", "沪A12345"),
            ("我叫张伟", "CN_PERSON", "张伟"),
            ("银行卡6222021234567890128", "CN_BANK_CARD", "6222021234567890128"),
        ],
    )
    def test_detects_chinese_pii(self, pii, text, entity, value):
        matches = pii.detect(text)

        assert any(m.entity_type == entity and m.text == value for m in matches), (
            f"expected {entity}={value}, got {[(m.entity_type, m.text) for m in matches]}"
        )

    def test_email_span_stops_at_the_ascii_boundary(self, pii):
        """
        Presidio's built-in email pattern uses `\\w`, which includes CJK, so
        "邮箱zhang@example.com" matched whole and the mask ate the word 邮箱.
        """
        matches = pii.detect("邮箱zhang@example.com")

        emails = [m for m in matches if m.entity_type == "EMAIL_ADDRESS"]
        assert emails and emails[0].text == "zhang@example.com"

    def test_id_card_checksum_is_enforced(self, pii):
        """An 18-digit run is not an ID card; GB 11643 says which ones are."""
        valid = pii.detect("身份证310101199001011234")
        invalid = pii.detect("订单号310101199001011235")

        assert any(m.entity_type == "CN_ID_CARD" for m in valid)
        assert not any(m.entity_type == "CN_ID_CARD" for m in invalid)

    def test_bank_card_luhn_is_enforced(self, pii):
        assert any(m.entity_type == "CN_BANK_CARD" for m in pii.detect("卡号6222021234567890128"))
        assert not any(
            m.entity_type == "CN_BANK_CARD" for m in pii.detect("卡号6222021234567890123")
        )

    def test_phone_pattern_does_not_carve_up_an_id_card(self, pii):
        """
        An ID card contains an 11-digit window matching the mobile pattern.
        Masking half an ID card would be worse than masking neither.
        """
        matches = pii.detect("身份证310101199001011234")

        assert not any(m.entity_type == "CN_PHONE_NUMBER" for m in matches)


class TestNoFalsePositives:
    """A false positive corrupts the question the customer actually asked."""

    @pytest.mark.parametrize(
        "text",
        [
            "我想要一台中型纯电SUV，预算40万",
            "宝马和奔驰哪个好",
            "续航600公里够用吗",
            "我住在上海",  # a city alone is not PII and the sales flow needs it
            "预算20到30万之间",
        ],
    )
    def test_vehicle_talk_is_left_alone(self, pii, text):
        masked, matches = pii.mask(text, "clean")

        assert masked == text, f"unexpectedly masked: {[(m.entity_type, m.text) for m in matches]}"


class TestRoundTrip:
    def test_mask_then_unmask_restores_the_original(self, pii):
        text = "我叫李明，手机13912345678"

        masked, _ = pii.mask(text, "rt1")

        assert "李明" not in masked
        assert "13912345678" not in masked
        assert pii.unmask(masked, "rt1") == text

    def test_placeholders_are_stable_within_a_session(self, pii):
        """Turn 3 must refer to the same token as turn 1 for the same value."""
        first, _ = pii.mask("我的手机是13912345678", "stable")
        second, _ = pii.mask("还是打13912345678吧", "stable")

        placeholder = first.replace("我的手机是", "")
        assert placeholder in second

    def test_one_session_cannot_decode_another(self, pii):
        """
        Without a per-session tag every vault numbers from 1, so session A
        would resolve session B's `<CN_PERSON_1>` to A's customer — quietly
        putting the wrong person's name in the reply.
        """
        pii.mask("我叫赵六", "session_a")
        masked_b, _ = pii.mask("我叫钱七", "session_b")

        assert pii.unmask(masked_b, "session_a") == masked_b
        assert pii.unmask(masked_b, "session_b") == "我叫钱七"


class TestNameDetectionLimits:
    """
    Name detection is intentionally introduction-anchored, not general.

    Free-standing Chinese name detection needs an NER model, and a wrong guess
    is costly both ways: masking "宝马" as a person corrupts the vehicle query,
    while a miss leaks a name. Anchoring on "我叫X"/"我是X" keeps precision high
    and confines misses to names the customer never introduced. These tests
    pin that trade-off so a future change to it is a deliberate one.
    """

    def test_introduced_names_are_caught(self, pii):
        assert any(m.entity_type == "CN_PERSON" for m in pii.detect("我叫王芳"))

    def test_bare_names_are_not_caught(self, pii):
        assert not any(m.entity_type == "CN_PERSON" for m in pii.detect("王芳的预算是30万"))

    def test_brand_names_are_never_treated_as_people(self, pii):
        assert not any(m.entity_type == "CN_PERSON" for m in pii.detect("我是宝马的粉丝"))


class TestNestedRestoration:
    def test_unmask_restores_values_inside_extracted_fields(self, pii):
        """
        The failure this prevents: storing the placeholder as the customer's
        name and printing it on the test-drive booking.

        Placeholders are read back from the masked text rather than written
        literally — they carry a per-session tag, so hardcoding one here would
        pin the test to an implementation detail it should not know.
        """
        masked, _ = pii.mask("我叫孙八，手机13700001111", "nested")
        placeholders = re.findall(r"<[A-Z_]+_[0-9a-f]*_?\d+>", masked)
        name_ph = next(p for p in placeholders if "CN_PERSON" in p)
        phone_ph = next(p for p in placeholders if "CN_PHONE_NUMBER" in p)

        restored = pii.unmask_mapping(
            {"profile": {"name": name_ph, "phone": phone_ph}, "cars": ["BMW-X3"]},
            "nested",
        )

        assert restored["profile"]["name"] == "孙八"
        assert restored["profile"]["phone"] == "13700001111"
        assert restored["cars"] == ["BMW-X3"]

    def test_unknown_placeholders_pass_through(self, pii):
        """A model that invents a placeholder must not crash the turn."""
        pii.mask("我叫周九", "unknown")

        assert "<CN_PERSON_99>" in pii.unmask("你好 <CN_PERSON_99>", "unknown")


class TestVaultLifecycle:
    def test_summary_reports_counts_not_values(self, pii):
        pii.mask("我叫吴十，手机13600002222", "vault")

        summary = pii.vault_summary("vault")

        assert summary["CN_PERSON"] == 1
        assert "吴十" not in str(summary)

    def test_clear_session_drops_the_mapping(self, pii):
        masked, _ = pii.mask("我叫郑十一", "clearme")
        pii.clear_session("clearme")

        assert pii.unmask(masked, "clearme") == masked
        assert pii.vault_summary("clearme") == {}

    def test_empty_input_is_a_no_op(self, pii):
        assert pii.mask("", "empty") == ("", [])
        assert pii.detect("   ") == []


class TestOverlapResolution:
    def test_overlapping_entities_do_not_nest(self, pii):
        """An ID card also matches the bank-card pattern; only one may win."""
        masked, matches = pii.mask("身份证310101199001011234", "overlap")

        assert masked.count("<") == 1
        assert len(matches) == 1
