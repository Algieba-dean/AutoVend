"""
Chinese PII recognizers for Presidio.

Presidio ships US/EU-centric recognizers. Against a Chinese sales transcript
they miss essentially everything that matters:

    "我叫张伟，手机13888888888，身份证310101199001011234"
    -> built-ins detect: nothing (plus a false-positive URL on any email domain)

So the entity types this system actually leaks are defined here. All are
pattern-based rather than model-based: a regex either matches a mainland phone
number or it does not, which is auditable in a way an NER model's confidence
score is not — and this layer decides what leaves the machine.

Validation matters as much as matching. An 18-digit run is not an ID card; the
GB 11643-1999 checksum is what separates a real one from a date-like number, and
Luhn does the same for bank cards. Without those checks the interceptor would
mask arbitrary long digit strings, which is its own kind of failure.
"""

import re
from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer

# ── Entity types ──────────────────────────────────────────────────────
CN_PHONE = "CN_PHONE_NUMBER"
CN_ID_CARD = "CN_ID_CARD"
CN_BANK_CARD = "CN_BANK_CARD"
CN_PLATE = "CN_LICENSE_PLATE"
CN_NAME = "CN_PERSON"
CN_ADDRESS = "CN_ADDRESS"
EMAIL = "EMAIL_ADDRESS"

#: Every entity this module can detect. Used as the analyzer's entity list so a
#: newly added recognizer cannot be silently left out of the scan.
CN_ENTITIES = [CN_PHONE, CN_ID_CARD, CN_BANK_CARD, CN_PLATE, CN_NAME, CN_ADDRESS, EMAIL]


class ChinesePhoneRecognizer(PatternRecognizer):
    """
    Mainland mobile numbers: 11 digits starting 1[3-9].

    The negative lookarounds stop an 11-digit window from being carved out of a
    longer digit run — an 18-digit ID card contains a substring that matches the
    phone pattern, and masking half an ID card is worse than masking neither.
    """

    PATTERNS = [
        Pattern(
            name="cn_mobile",
            regex=r"(?<!\d)1[3-9]\d{9}(?!\d)",
            score=0.9,
        ),
        Pattern(
            name="cn_mobile_separated",
            regex=r"(?<!\d)1[3-9]\d[\s-]\d{4}[\s-]\d{4}(?!\d)",
            score=0.85,
        ),
        Pattern(
            name="cn_landline",
            regex=r"(?<!\d)0\d{2,3}[-\s]?\d{7,8}(?!\d)",
            score=0.6,
        ),
    ]

    CONTEXT = ["手机", "电话", "号码", "联系方式", "phone", "mobile", "tel"]

    def __init__(self, supported_language: str = "zh"):
        super().__init__(
            supported_entity=CN_PHONE,
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )


class ChineseIDCardRecognizer(PatternRecognizer):
    """Resident identity card (居民身份证), 18 digits with a GB 11643 checksum."""

    PATTERNS = [
        Pattern(
            name="cn_id_18",
            # Region (6) + birth date (8) + sequence (3) + check digit.
            regex=r"(?<![0-9A-Za-z])[1-9]\d{5}(?:19|20)\d{2}"
            r"(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?![0-9A-Za-z])",
            score=0.6,
        ),
    ]

    CONTEXT = ["身份证", "证件", "identity", "id card"]

    #: GB 11643-1999 weights and check-digit alphabet.
    _WEIGHTS = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
    _CHECK_CHARS = "10X98765432"

    def __init__(self, supported_language: str = "zh"):
        super().__init__(
            supported_entity=CN_ID_CARD,
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )

    def validate_result(self, pattern_text: str) -> Optional[bool]:
        """
        Verify the check digit.

        Returns True/False rather than None so Presidio promotes a verified
        match to full confidence and drops a failed one — an 18-digit number
        that fails the checksum is far more likely to be an order number than a
        redacted-worthy identity card.
        """
        if len(pattern_text) != 18:
            return False
        try:
            total = sum(int(ch) * w for ch, w in zip(pattern_text[:17], self._WEIGHTS))
        except ValueError:
            return False
        return pattern_text[17].upper() == self._CHECK_CHARS[total % 11]


class ChineseBankCardRecognizer(PatternRecognizer):
    """Bank card numbers, 16-19 digits, validated with the Luhn checksum."""

    PATTERNS = [
        Pattern(name="cn_bank_card", regex=r"(?<!\d)\d{16,19}(?!\d)", score=0.4),
    ]

    CONTEXT = ["银行卡", "卡号", "储蓄卡", "信用卡", "bank", "card"]

    def __init__(self, supported_language: str = "zh"):
        super().__init__(
            supported_entity=CN_BANK_CARD,
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )

    def validate_result(self, pattern_text: str) -> Optional[bool]:
        digits = [int(ch) for ch in pattern_text]
        checksum = 0
        for index, digit in enumerate(reversed(digits)):
            if index % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit
        return checksum % 10 == 0


class ChineseLicensePlateRecognizer(PatternRecognizer):
    """Vehicle plates — both the 7-character conventional and 8-character NEV forms."""

    PATTERNS = [
        Pattern(
            name="cn_plate_nev",
            regex=r"[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领]"
            r"[A-HJ-NP-Z][DF][A-HJ-NP-Z0-9]\d{5}",
            score=0.9,
        ),
        Pattern(
            name="cn_plate_standard",
            regex=r"[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领]"
            r"[A-HJ-NP-Z][A-HJ-NP-Z0-9]{4}[A-HJ-NP-Z0-9挂学警港澳]",
            score=0.85,
        ),
    ]

    CONTEXT = ["车牌", "牌照", "号牌", "plate"]

    def __init__(self, supported_language: str = "zh"):
        super().__init__(
            supported_entity=CN_PLATE,
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )


class ChineseNameRecognizer(PatternRecognizer):
    """
    Personal names, detected via the phrase that introduces them.

    Deliberately *not* a general Chinese-name detector. Free-standing name
    detection over CJK needs an NER model, and a wrong guess here is expensive
    in both directions: masking "宝马" as a name would corrupt the vehicle
    query, while missing a name leaks it. Anchoring on introduction phrases
    ("我叫X", "我是X", "称呼我X") keeps precision high and confines misses to
    names the user never actually introduced.

    The trailing lookahead stops the capture from swallowing the rest of the
    clause — "我叫张伟，今年35岁" must yield 张伟, not 张伟，今年35岁.
    """

    _INTRO = r"(?:我叫|我是|我姓|称呼我|叫我|本人|姓名是|姓名：|名字是|名字叫)"
    _SURNAME_GIVEN = r"[一-龥]{2,4}"

    PATTERNS = [
        Pattern(
            name="cn_name_introduced",
            regex=rf"(?<={_INTRO}){_SURNAME_GIVEN}(?=[，,。！!？?\s]|$)",
            score=0.75,
        ),
        Pattern(
            name="cn_name_honorific",
            regex=r"(?<![一-龥])[一-龥]{1,2}(?=(?:先生|女士|小姐|太太)(?![一-龥]))",
            score=0.55,
        ),
    ]

    CONTEXT = ["姓名", "名字", "称呼", "我叫", "name"]

    def __init__(self, supported_language: str = "zh"):
        super().__init__(
            supported_entity=CN_NAME,
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )

    def validate_result(self, pattern_text: str) -> Optional[bool]:
        # Common words that follow an introduction phrase but are not names.
        if pattern_text in _NON_NAME_TOKENS:
            return False
        return None  # fall back to the pattern's own score


class ChineseAddressRecognizer(PatternRecognizer):
    """
    Street-level addresses.

    Only fires when a street-level unit (号/室/栋/单元/楼) is present. A bare
    city name is not PII and is load-bearing for the sales conversation —
    parking conditions and dealer selection both depend on knowing the user is
    in 上海.

    The unit group repeats because addresses stack them: "世纪大道100号2室"
    ends in 室, not 号. Matching only the first unit would leave a dangling
    "室" outside the placeholder — visible leakage of the address's shape, and
    ugly in the masked text.
    """

    PATTERNS = [
        Pattern(
            name="cn_address_street",
            regex=r"[一-龥]{2,10}(?:省|市|区|县)"
            r"[一-龥\dA-Za-z]{2,30}?(?:路|街|道|巷|里)"
            r"(?:[\dA-Za-z一-龥]{0,20}?(?:号|室|栋|幢|单元|楼|层))+"
            r"[\dA-Za-z]{0,10}",
            score=0.7,
        ),
    ]

    CONTEXT = ["地址", "住址", "住在", "家住", "address"]

    def __init__(self, supported_language: str = "zh"):
        super().__init__(
            supported_entity=CN_ADDRESS,
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )


class AsciiEmailRecognizer(PatternRecognizer):
    """
    Email addresses with an ASCII-only local part.

    Presidio's built-in email pattern anchors on `\\b` with a `\\w` local part.
    Under Unicode, CJK characters are word characters and there is no boundary
    between 箱 and z, so "邮箱zhang@example.com" is captured whole — the mask
    then eats the word "邮箱" and the sentence loses its meaning. Restricting
    the local part to ASCII fixes the span without weakening detection.
    """

    PATTERNS = [
        Pattern(
            name="ascii_email",
            regex=r"(?<![A-Za-z0-9._%+\-])[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
            score=0.9,
        ),
    ]

    CONTEXT = ["邮箱", "邮件", "email", "mail"]

    def __init__(self, supported_language: str = "zh"):
        super().__init__(
            supported_entity=EMAIL,
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )


#: Words that follow "我叫/我是" without being names. Kept small and literal —
#: an over-broad list would start suppressing real surnames.
_NON_NAME_TOKENS = frozenset(
    {
        "什么",
        "谁",
        "来的",
        "来看",
        "想买",
        "想要",
        "过来",
        "这样",
        "这么",
        "客户",
        "用户",
        "他们",
        "我们",
    }
)

_WHITESPACE = re.compile(r"\s+")


def build_recognizers(language: str = "zh") -> List[PatternRecognizer]:
    """All Chinese recognizers, ready to register with an AnalyzerEngine."""
    return [
        ChinesePhoneRecognizer(language),
        ChineseIDCardRecognizer(language),
        ChineseBankCardRecognizer(language),
        ChineseLicensePlateRecognizer(language),
        ChineseNameRecognizer(language),
        ChineseAddressRecognizer(language),
        AsciiEmailRecognizer(language),
    ]
