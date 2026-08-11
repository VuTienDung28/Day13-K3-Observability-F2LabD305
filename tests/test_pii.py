from __future__ import annotations

import pytest

from app import pii


@pytest.mark.parametrize(
    ("raw_value", "marker"),
    [
        ("student@vinuni.edu.vn", "[REDACTED_EMAIL]"),
        ("001234567890", "[REDACTED_CCCD]"),
        ("4111111111111111", "[REDACTED_CREDIT_CARD]"),
        ("4111 1111 1111 1111", "[REDACTED_CREDIT_CARD]"),
        ("4111-1111-1111-1111", "[REDACTED_CREDIT_CARD]"),
        ("A1234567", "[REDACTED_PASSPORT]"),
        ("b12345678", "[REDACTED_PASSPORT]"),
    ],
)
def test_scrub_supported_identifier(raw_value: str, marker: str) -> None:
    output = pii.scrub_text(f"PII={raw_value}")

    assert raw_value not in output
    assert marker in output


@pytest.mark.parametrize(
    "phone_number",
    [
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    ],
)
def test_scrub_common_vietnamese_phone_formats(phone_number: str) -> None:
    output = pii.scrub_text(f"Contact: {phone_number}")

    assert phone_number not in output
    assert "[REDACTED_PHONE_VN]" in output


@pytest.mark.parametrize(
    "address_keyword",
    ["Số nhà", "Đường", "Phường", "Quận", "Huyện", "Tỉnh", "Thành phố"],
)
def test_scrub_vietnamese_address_keywords_case_insensitively(
    address_keyword: str,
) -> None:
    output = pii.scrub_text(f"{address_keyword}: 123")

    assert address_keyword not in output
    assert "[REDACTED_ADDRESS_VN]" in output


def test_scrub_value_recurses_through_nested_containers() -> None:
    source = {
        "email": "student@vinuni.edu.vn",
        "nested": {
            "items": [
                "Call 090 123 4567",
                ("Passport A1234567", None, 42, True),
            ]
        },
    }

    output = pii.scrub_value(source)

    assert output == {
        "email": "[REDACTED_EMAIL]",
        "nested": {
            "items": [
                "Call [REDACTED_PHONE_VN]",
                ("Passport [REDACTED_PASSPORT]", None, 42, True),
            ]
        },
    }
    assert isinstance(output["nested"]["items"], list)
    assert isinstance(output["nested"]["items"][1], tuple)


def test_scrub_value_is_idempotent() -> None:
    source = {
        "message": "student@vinuni.edu.vn used 4111 1111 1111 1111",
        "count": 3,
    }

    once = pii.scrub_value(source)
    twice = pii.scrub_value(once)

    assert twice == once
    assert twice["count"] == 3
