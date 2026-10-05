import argparse
import csv
import sys
from pathlib import Path

from fitness.analysis import analyze_session
from fitness.errors import InvalidRecordError
from fitness.loader import load_participants, load_sessions
from fitness.reports import write_reports


DEFAULT_PROFILES = Path("data/participants.csv")
DEFAULT_SESSIONS = [Path("data/fitness_sessions.csv"), Path("data/fitness_sessions_invalid.csv")]
DEFAULT_OUTPUT = Path("output")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Analyze wearable fitness sessions stored in CSV files.")
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES,
                        help="CSV file with the participant profiles")
    parser.add_argument("--sessions", type=Path, nargs="+", default=DEFAULT_SESSIONS,
                        help="one or more CSV files with session measurements")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="directory for the generated reports")
    return parser.parse_args()


def main():
    arguments = parse_arguments()

    try:
        participants, rejected_rows = load_participants(arguments.profiles)
    except FileNotFoundError:
        print(f"Could not find the profile file {arguments.profiles}.")
        return 1
    except PermissionError:
        print(f"Not allowed to read the profile file {arguments.profiles}.")
        return 1
    except (InvalidRecordError, csv.Error) as error:
        print(f"Could not use the profile file {arguments.profiles}: {error}")
        return 1

    sessions = {}
    for path in arguments.sessions:
        try:
            file_sessions, file_rejections = load_sessions(path, participants)
        except (FileNotFoundError, PermissionError, csv.Error) as error:
            print(f"Skipping the session file {path}: {error}")
            continue
        sessions.update(file_sessions)
        rejected_rows.extend(file_rejections)

    if not sessions:
        print("No sessions could be read, so no reports were written.")
        return 1

    results = [analyze_session(session) for session in sessions.values()]

    try:
        created_files = write_reports(results, rejected_rows, arguments.output)
    except OSError as error:
        print(f"Could not write the reports to {arguments.output}: {error}")
        return 1

    accepted = sum(result["usable_rows"] for result in results)
    print(f"Sessions analyzed: {len(results)}")
    print(f"Accepted rows:     {accepted}")
    print(f"Rejected rows:     {len(rejected_rows)}")
    print("Report files:")
    for path in created_files:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
