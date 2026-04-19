from app.models import (
    CodeSubmissionOutcome,
    SubmissionResult,
    SubmissionStatus,
)
from app.services.code_store import CodeStateStore


def test_persist_after_scrape_adds_only_new_codes(tmp_path):
    store = CodeStateStore(
        tmp_path / "unsubmitted_codes.json",
        tmp_path / "submitted_codes.json",
    )

    first = store.persist_after_scrape(
        ["ABCDE-FGHIJ-KLMNO-PQRST-UVWXY"],
        ["https://example.com"],
    )
    second = store.persist_after_scrape(
        ["ABCDE-FGHIJ-KLMNO-PQRST-UVWXY", "ZZZZZ-11111-YYYYY-22222-XXXXX"],
        ["https://example.com"],
    )

    unsubmitted = store.load_unsubmitted()

    assert first.new_codes == ["ABCDE-FGHIJ-KLMNO-PQRST-UVWXY"]
    assert second.new_codes == ["ZZZZZ-11111-YYYYY-22222-XXXXX"]
    assert unsubmitted.codes == [
        "ABCDE-FGHIJ-KLMNO-PQRST-UVWXY",
        "ZZZZZ-11111-YYYYY-22222-XXXXX",
    ]


def test_persist_submission_results_moves_codes_to_bucket(tmp_path):
    store = CodeStateStore(
        tmp_path / "unsubmitted_codes.json",
        tmp_path / "submitted_codes.json",
    )
    store.persist_after_scrape(
        ["AAAAA-BBBBB-CCCCC-DDDDD-EEEEE", "FFFFF-GGGGG-HHHHH-IIIII-JJJJJ"],
        ["https://example.com"],
    )

    result = SubmissionResult(
        attempted_codes=2,
        processed_codes=[
            CodeSubmissionOutcome(
                code="AAAAA-BBBBB-CCCCC-DDDDD-EEEEE",
                status=SubmissionStatus.SUCCESSFUL,
            ),
            CodeSubmissionOutcome(
                code="FFFFF-GGGGG-HHHHH-IIIII-JJJJJ",
                status=SubmissionStatus.ALREADY_REDEEMED,
            ),
        ],
        remaining_unsubmitted_codes=0,
        login_attempts=1,
        target_game="Borderlands 4",
        target_platform="Redeem for PSN",
    )

    persisted = store.persist_submission_results(result)
    unsubmitted = store.load_unsubmitted()
    submitted = store.load_submitted()

    assert persisted.remaining_unsubmitted_codes == 0
    assert unsubmitted.codes == []
    assert submitted.successful_codes == ["AAAAA-BBBBB-CCCCC-DDDDD-EEEEE"]
    assert submitted.already_redeemed_codes == ["FFFFF-GGGGG-HHHHH-IIIII-JJJJJ"]
