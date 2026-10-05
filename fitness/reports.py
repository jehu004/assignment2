import csv
from pathlib import Path

from .analysis import SUMMARY_FIELDS


SUMMARY_COLUMNS = [
    "session_id", "participant_id", "name", "total_rows", "usable_rows", "rejected_rows",
    "average_heart_rate", "average_skin_response", "average_temperature",
    "average_activity_level", "heart_rate_difference", "classification",
]

UNITS = {"heart_rate": " bpm", "skin_response": "", "temperature": " C", "activity_level": ""}


def format_value(value, unit=""):
    if value is None:
        return "n/a"
    return f"{value}{unit}"


def write_summary_csv(results, path):
    with open(path, "w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(SUMMARY_COLUMNS)
        for result in results:
            averages = {field: result["summaries"][field]["average"] for field in SUMMARY_FIELDS}
            comparison = result["comparison"]
            writer.writerow([
                result["session_id"],
                result["participant_id"],
                result["participant"].name,
                result["total_rows"],
                result["usable_rows"],
                result["rejected_rows"],
                "" if averages["heart_rate"] is None else averages["heart_rate"],
                "" if averages["skin_response"] is None else averages["skin_response"],
                "" if averages["temperature"] is None else averages["temperature"],
                "" if averages["activity_level"] is None else averages["activity_level"],
                "" if comparison is None else comparison["heart_rate_difference"],
                result["classification"],
            ])


def write_report_text(results, path):
    with open(path, "w", encoding="utf-8") as report_file:
        report_file.write("Smart Fitness Session Analyzer - session reports\n")

        for result in results:
            report_file.write("\n" + "=" * 64 + "\n")
            report_file.write(f" Session {result['session_id']}\n")
            report_file.write("=" * 64 + "\n")
            report_file.write(f"{result['participant']}\n")
            report_file.write(f"Rows: {result['total_rows']} total, "
                              f"{result['usable_rows']} usable, "
                              f"{result['rejected_rows']} rejected\n")

            for rejection in result["rejections"]:
                report_file.write(f"  - {rejection}\n")

            report_file.write("\nSummary of usable rows:\n")
            for field in SUMMARY_FIELDS:
                summary = result["summaries"][field]
                unit = UNITS[field]
                report_file.write(f"  {field:<15} avg {format_value(summary['average'], unit):<11}"
                                  f" min {format_value(summary['minimum'], unit):<11}"
                                  f" max {format_value(summary['maximum'], unit)}\n")

            if result["comparison"] is not None:
                comparison = result["comparison"]
                recovery = result["recovery"]
                report_file.write("\nCompared with personal baseline:\n")
                report_file.write(f"  heart rate     {comparison['heart_rate_difference']:+} bpm\n")
                report_file.write(f"  skin response  {comparison['skin_response_difference']:+}\n")
                report_file.write(f"  temperature    {comparison['temperature_difference']:+} C\n")
                report_file.write(f"  recovery check: HR drop {recovery['heart_rate_drop']} bpm, "
                                  f"activity drop {recovery['activity_drop']}\n")

            report_file.write(f"\nCLASSIFICATION: {result['classification'].upper()}\n")
            report_file.write(f"Reason: {result['explanation']}\n")

        report_file.write("\n" + "=" * 64 + "\n")
        report_file.write(" Overview\n")
        report_file.write("=" * 64 + "\n")
        for result in results:
            report_file.write(f"  {result['session_id']:<16} -> {result['classification']}\n")


def write_rejected_rows(rejected_rows, path):
    with open(path, "w", encoding="utf-8") as rejected_file:
        rejected_file.write("Rejected rows (source file, row number, field, reason)\n")
        rejected_file.write("=" * 64 + "\n")
        if not rejected_rows:
            rejected_file.write("No rows were rejected.\n")
        for rejected in rejected_rows:
            rejected_file.write(f"{rejected}\n")
        rejected_file.write(f"\n{len(rejected_rows)} rows rejected in total.\n")


def write_reports(results, rejected_rows, output_directory):
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    summary_path = output_directory / "analysis_summary.csv"
    report_path = output_directory / "analysis_report.txt"
    rejected_path = output_directory / "rejected_records.txt"

    write_summary_csv(results, summary_path)
    write_report_text(results, report_path)
    write_rejected_rows(rejected_rows, rejected_path)

    return [summary_path, report_path, rejected_path]
