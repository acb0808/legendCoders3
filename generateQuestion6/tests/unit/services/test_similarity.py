from math_variant.services.similarity import (
    longest_common_substring,
    ngram_similarity,
    normalize_text,
    similarity_report,
)


def test_normalize_strips_punctuation_and_space() -> None:
    assert normalize_text("직선 y=-x+3 위의 점 P, O(0,0)") == "직선yx3위의점PO00"


def test_lcs_long_reuse_detected() -> None:
    a = normalize_text("직선 위의 점 P에서 x축에 내린 수선의 발을 H라 한다")
    b = normalize_text("직선 위의 점 P에서 x축에 내린 수선의 발을 H라 하고 넓이를 구하라")
    lcs_len, _a_start, _b_start = longest_common_substring(a, b)
    assert lcs_len >= 20


def test_ngram_similarity_high_for_copied_sentence() -> None:
    a = normalize_text("삼각형 OPH의 넓이가 9가 되도록 하는 점 P의 좌표를 구하시오")
    b = normalize_text("삼각형 OPH의 넓이가 9가 되도록 하는 점 P의 좌표를 구하시오")
    assert ngram_similarity(a, b) > 0.8


def test_ngram_low_for_different_problem() -> None:
    a = normalize_text("직선 위 점에서 축에 수선을 내려 삼각형 넓이를 구한다")
    b = normalize_text("포물선과 직선의 교점 사이의 거리를 구한다")
    assert ngram_similarity(a, b) < 0.3


def test_report_flags_copy_with_snippet() -> None:
    source = "직선 위의 점 P에서 x축에 내린 수선의 발을 H라 하면 삼각형 OPH의 넓이가 9이다."
    candidate = (
        "직선 위의 점 P에서 x축에 내린 수선의 발을 H라 하면 "
        "삼각형 OPH의 넓이가 9가 되는 P를 구하시오."
    )
    report = similarity_report(source, candidate)
    assert report.too_similar is True
    assert report.lcs_len > 20
    assert "삼각형" in report.match_snippet or "OPH" in report.match_snippet


def test_report_pass_for_different_problem() -> None:
    source = "직선 위의 점에서 축에 내린 수선과 삼각형 넓이를 이용한다."
    candidate = "포물선 y=ax^2와 직선 y=x+3의 두 교점 사이의 거리를 구하시오."
    report = similarity_report(source, candidate)
    assert report.too_similar is False
