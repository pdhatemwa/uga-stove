import pytest

from api.normalization import normalize_identifier


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("B-00120", "B00120"),
        (" b 00120 ", "B00120"),
        ("Ps_ug_m1996", "PSUGM1996"),
        ("PS-UG-M1996", "PSUGM1996"),
    ],
)
def test_identifier_normalization(raw, expected):
    assert normalize_identifier(raw) == expected


def test_empty_identifier_rejected():
    with pytest.raises(ValueError):
        normalize_identifier(" -- ")
