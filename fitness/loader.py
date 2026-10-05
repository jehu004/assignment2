import csv
import re
from pathlib import Path

from .errors import InvalidIdentifierError, InvalidRecordError
from .models import Observation, Participant, RejectedRow, Session


PARTICIPANT_ID_PATTERN = re.compile(r"^P\d{3}$")
SESSION_ID_PATTERN = re.compile(r"^FIT-\d{4}-\d{3}$")

MIN_SIGNAL_QUALITY = 0.6

FIELD_RULES = {
    "heart_rate": (int, 35, 205),
    "skin_response": (float, 0, 20),
    "temperature": (float, 25, 42),
    "activity_level": (float, 0, 1),
    "signal_quality": (float, 0, 1),
}

SESSION_COLUMNS = ["session_id", "participant_id", "timestamp"] + list(FIELD_RULES)


def read_field(row, field):
    try:
        value = row[field]
    except KeyError:
        raise InvalidRecordError(f"the column '{field}' is missing from the file", field=field)
    if value is None or value.strip() == "":
        raise InvalidRecordError(f"{field} is missing", field=field)
    return value.strip()


def to_number(value, convert, field):
    try:
        return convert(value)
    except ValueError:
        wanted = "whole number" if convert is int else "number"
        raise InvalidRecordError(f"{field} '{value}' is not a {wanted}", field=field)


def check_identifier(value, pattern, field, description):
    if pattern.fullmatch(value) is None:
        raise InvalidIdentifierError(f"{field} '{value}' is not {description}", field=field)
    return value


def check_row_length(row):
    if None in row:
        raise InvalidRecordError("the row has more columns than the header", field="row")
    for column in SESSION_COLUMNS:
        if column in row and row[column] is None:
            raise InvalidRecordError("the row has fewer columns than the header", field="row")


def build_observation(row):
    timestamp = to_number(read_field(row, "timestamp"), int, "timestamp")
    if timestamp < 0:
        raise InvalidRecordError(f"timestamp {timestamp} is negative", field="timestamp")

    measurements = {}
    for field, (convert, low, high) in FIELD_RULES.items():
        value = to_number(read_field(row, field), convert, field)
        if not low <= value <= high:
            raise InvalidRecordError(f"{field} {value} is outside the possible range {low}-{high}",
                                     field=field)
        measurements[field] = value

    quality = measurements["signal_quality"]
    if quality < MIN_SIGNAL_QUALITY:
        raise InvalidRecordError(f"signal quality {quality} is below the limit {MIN_SIGNAL_QUALITY}",
                                 field="signal_quality")

    return Observation(timestamp, **measurements)


def load_participants(path):
    path = Path(path)
    participants = {}
    rejections = []

    with open(path, encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            try:
                participant_id = check_identifier(read_field(row, "participant_id"),
                                                  PARTICIPANT_ID_PATTERN, "participant_id",
                                                  "P followed by three digits")
                profile = {
                    "participant_id": participant_id,
                    "name": read_field(row, "name"),
                    "baseline_heart_rate": to_number(read_field(row, "baseline_heart_rate"),
                                                     int, "baseline_heart_rate"),
                    "baseline_skin_response": to_number(read_field(row, "baseline_skin_response"),
                                                        float, "baseline_skin_response"),
                    "baseline_temperature": to_number(read_field(row, "baseline_temperature"),
                                                      float, "baseline_temperature"),
                }
                participants[participant_id] = Participant.from_profile(profile)
            except (InvalidIdentifierError, InvalidRecordError) as error:
                rejections.append(RejectedRow(path.name, reader.line_num, error.field, str(error)))
            except ValueError as error:
                rejections.append(RejectedRow(path.name, reader.line_num,
                                              "baseline_heart_rate", str(error)))

    if not participants:
        raise InvalidRecordError(f"no usable participant profiles in {path}", field="file")
    return participants, rejections


def load_sessions(path, participants):
    path = Path(path)
    sessions = {}
    rejections = []

    with open(path, encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            try:
                check_row_length(row)
                session_id = check_identifier(read_field(row, "session_id"),
                                              SESSION_ID_PATTERN, "session_id",
                                              "written as FIT-YYYY-NNN")
                participant_id = check_identifier(read_field(row, "participant_id"),
                                                  PARTICIPANT_ID_PATTERN, "participant_id",
                                                  "P followed by three digits")
                if participant_id not in participants:
                    raise InvalidRecordError(f"participant {participant_id} is not in the "
                                             f"profile file", field="participant_id")
                if session_id not in sessions:
                    sessions[session_id] = Session(session_id, participants[participant_id])
                session = sessions[session_id]
            except (InvalidIdentifierError, InvalidRecordError) as error:
                rejections.append(RejectedRow(path.name, reader.line_num, error.field, str(error)))
                continue

            try:
                session.add_observation(build_observation(row))
            except (InvalidIdentifierError, InvalidRecordError) as error:
                rejected = RejectedRow(path.name, reader.line_num, error.field, str(error))
                session.add_rejection(rejected)
                rejections.append(rejected)

    return sessions, rejections
