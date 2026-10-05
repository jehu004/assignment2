"""Simple tests for the Smart Fitness Session Analyzer. Run with: python3 tests.py"""

import tempfile
from pathlib import Path

from fitness.analysis import analyze_session, calculate_summary, detect_recovery
from fitness.errors import InvalidIdentifierError, InvalidRecordError
from fitness.loader import (PARTICIPANT_ID_PATTERN, SESSION_ID_PATTERN, build_observation,
                            check_identifier, load_participants, load_sessions)
from fitness.models import Participant
from fitness.reports import write_reports


DATA = Path(__file__).resolve().parent / "data"
PROFILES = DATA / "participants.csv"
VALID_SESSIONS = DATA / "fitness_sessions.csv"
INVALID_SESSIONS = DATA / "fitness_sessions_invalid.csv"


def make_row(**changes):
    row = {
        "session_id": "FIT-2026-001",
        "participant_id": "P001",
        "timestamp": "0",
        "heart_rate": "72",
        "skin_response": "1.20",
        "temperature": "32.4",
        "activity_level": "0.10",
        "signal_quality": "0.95",
    }
    row.update(changes)
    return row


def expect_rejection(row, field):
    try:
        build_observation(row)
        assert False, f"the row should have been rejected because of {field}"
    except InvalidRecordError as error:
        assert error.field == field, f"expected field {field}, got {error.field}"


# --- valid data ---------------------------------------------------------

def test_valid_row_becomes_an_observation():
    observation = build_observation(make_row())
    assert observation.timestamp == 0
    assert observation.get("heart_rate") == 72
    assert observation.get("activity_level") == 0.10


def test_identifier_patterns_accept_the_official_format():
    assert check_identifier("P001", PARTICIPANT_ID_PATTERN, "participant_id", "P and 3 digits")
    assert check_identifier("FIT-2026-001", SESSION_ID_PATTERN, "session_id", "FIT-YYYY-NNN")


def test_participant_from_profile():
    profile = {"participant_id": "P007", "name": "Test Person", "baseline_heart_rate": 65,
               "baseline_skin_response": 1.2, "baseline_temperature": 32.1}
    participant = Participant.from_profile(profile)
    assert participant.participant_id == "P007"
    assert participant.baseline_heart_rate == 65


def test_official_files_are_loaded():
    participants, profile_rejections = load_participants(PROFILES)
    assert len(participants) == 3
    assert profile_rejections == []

    sessions, rejections = load_sessions(VALID_SESSIONS, participants)
    assert len(sessions) == 5
    assert len(sessions["FIT-2026-001"].observations) == 6
    # the five windows of FIT-2026-005 all have poor signal quality
    assert len(rejections) == 5


def test_classifications_of_the_official_valid_file():
    participants, _ = load_participants(PROFILES)
    sessions, _ = load_sessions(VALID_SESSIONS, participants)
    expected = {
        "FIT-2026-001": "resting",
        "FIT-2026-002": "moderate activity",
        "FIT-2026-003": "high activity",
        "FIT-2026-005": "insufficient data",
    }
    for session_id, label in expected.items():
        result = analyze_session(sessions[session_id])
        assert result["classification"] == label, (session_id, result["classification"])


# --- invalid data -------------------------------------------------------

def test_bad_identifiers_are_rejected():
    for value in ["001", "p001", "P01", "P0012", ""]:
        try:
            check_identifier(value, PARTICIPANT_ID_PATTERN, "participant_id", "P and 3 digits")
            assert False, f"'{value}' should not be accepted"
        except InvalidIdentifierError:
            pass
    for value in ["FIT-26-102", "FIT-2026-1021", "fit-2026-102"]:
        try:
            check_identifier(value, SESSION_ID_PATTERN, "session_id", "FIT-YYYY-NNN")
            assert False, f"'{value}' should not be accepted"
        except InvalidIdentifierError:
            pass


def test_wrong_type_is_rejected():
    expect_rejection(make_row(heart_rate="fast"), "heart_rate")
    expect_rejection(make_row(timestamp="two"), "timestamp")


def test_missing_value_is_rejected():
    expect_rejection(make_row(activity_level=""), "activity_level")


def test_missing_column_is_rejected():
    row = make_row()
    del row["signal_quality"]
    expect_rejection(row, "signal_quality")


def test_impossible_values_are_rejected():
    expect_rejection(make_row(heart_rate="-15"), "heart_rate")
    expect_rejection(make_row(temperature="55.0"), "temperature")
    expect_rejection(make_row(activity_level="1.30"), "activity_level")
    expect_rejection(make_row(skin_response="-0.50"), "skin_response")


def test_poor_signal_quality_is_rejected():
    expect_rejection(make_row(signal_quality="0.34"), "signal_quality")


def test_unknown_participant_is_rejected():
    participants, _ = load_participants(PROFILES)
    sessions, rejections = load_sessions(INVALID_SESSIONS, participants)
    reasons = [rejected.reason for rejected in rejections]
    assert any("P999" in reason for reason in reasons), reasons


def test_every_rejection_says_file_row_field_and_reason():
    participants, _ = load_participants(PROFILES)
    sessions, rejections = load_sessions(INVALID_SESSIONS, participants)
    assert len(rejections) == 10, len(rejections)
    for rejected in rejections:
        assert rejected.source_file == INVALID_SESSIONS.name
        assert rejected.row_number >= 2
        assert rejected.field != ""
        assert rejected.reason != ""


def test_invalid_file_still_gives_a_result():
    participants, _ = load_participants(PROFILES)
    sessions, _ = load_sessions(INVALID_SESSIONS, participants)
    result = analyze_session(sessions["FIT-2026-101"])
    assert result["usable_rows"] == 1
    assert result["classification"] == "insufficient data"


# --- missing file -------------------------------------------------------

def test_missing_profile_file_raises_file_not_found():
    try:
        load_participants(DATA / "not_a_real_file.csv")
        assert False, "a FileNotFoundError should have been raised"
    except FileNotFoundError:
        pass


def test_missing_session_file_raises_file_not_found():
    participants, _ = load_participants(PROFILES)
    try:
        load_sessions(DATA / "not_a_real_file.csv", participants)
        assert False, "a FileNotFoundError should have been raised"
    except FileNotFoundError:
        pass


# --- boundary cases -----------------------------------------------------

def test_heart_rate_boundaries():
    assert build_observation(make_row(heart_rate="35")).get("heart_rate") == 35
    assert build_observation(make_row(heart_rate="205")).get("heart_rate") == 205
    expect_rejection(make_row(heart_rate="34"), "heart_rate")
    expect_rejection(make_row(heart_rate="206"), "heart_rate")


def test_signal_quality_boundary():
    assert build_observation(make_row(signal_quality="0.6")).get("signal_quality") == 0.6
    expect_rejection(make_row(signal_quality="0.59"), "signal_quality")


def test_baseline_setter_rejects_bad_value():
    participant = Participant("P001", "Test Person", 70, 1.5, 32.0)
    try:
        participant.baseline_heart_rate = 300
        assert False, "a ValueError should have been raised"
    except ValueError:
        pass
    assert participant.baseline_heart_rate == 70


def test_calculate_summary():
    assert calculate_summary([10, 20, 30]) == {"average": 20.0, "minimum": 10, "maximum": 30}
    assert calculate_summary([])["average"] is None


def test_recovery_detection():
    assert detect_recovery([130, 125, 120, 100, 90, 80], [0.8, 0.8, 0.7, 0.4, 0.2, 0.1])["detected"]
    assert not detect_recovery([100, 101, 99, 100, 102, 100], [0.5] * 6)["detected"]
    assert not detect_recovery([130, 120, 90], [0.8, 0.5, 0.1])["detected"]


# --- output files -------------------------------------------------------

def test_reports_are_written():
    participants, rejected = load_participants(PROFILES)
    sessions, rejections = load_sessions(VALID_SESSIONS, participants)
    results = [analyze_session(session) for session in sessions.values()]

    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "output"
        created = write_reports(results, rejected + rejections, output)
        assert len(created) == 3
        for path in created:
            assert path.exists(), path
        lines = (output / "analysis_summary.csv").read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == len(results) + 1
        assert "rejected" in (output / "rejected_records.txt").read_text(encoding="utf-8").lower()


ALL_TESTS = [
    test_valid_row_becomes_an_observation,
    test_identifier_patterns_accept_the_official_format,
    test_participant_from_profile,
    test_official_files_are_loaded,
    test_classifications_of_the_official_valid_file,
    test_bad_identifiers_are_rejected,
    test_wrong_type_is_rejected,
    test_missing_value_is_rejected,
    test_missing_column_is_rejected,
    test_impossible_values_are_rejected,
    test_poor_signal_quality_is_rejected,
    test_unknown_participant_is_rejected,
    test_every_rejection_says_file_row_field_and_reason,
    test_invalid_file_still_gives_a_result,
    test_missing_profile_file_raises_file_not_found,
    test_missing_session_file_raises_file_not_found,
    test_heart_rate_boundaries,
    test_signal_quality_boundary,
    test_baseline_setter_rejects_bad_value,
    test_calculate_summary,
    test_recovery_detection,
    test_reports_are_written,
]


def run_all_tests():
    passed = 0
    for test in ALL_TESTS:
        try:
            test()
            print(f"PASS  {test.__name__}")
            passed += 1
        except AssertionError as error:
            print(f"FAIL  {test.__name__}: {error}")
    print(f"\n{passed} of {len(ALL_TESTS)} tests passed.")


if __name__ == "__main__":
    run_all_tests()
