Assignment 02 Option A
Smart Fitness Session Analyzer

Jens Berger Husem 4950

The program reads participant profiles and wearable session measurements from CSV files, checks every row before it is used, and classifies each session as resting, moderate activity, high activity, recovering or insufficient data. Rows with broken identifiers, wrong types, impossible values or poor signal quality are rejected and explained instead of silently dropped. The analysis itself is the one from Assignment 1.

Structure and class design

The solution is split into a package, so the structure is explained here. main.py is the command line program; fitness/loader.py reads and validates the CSV files; fitness/models.py holds the classes; fitness/analysis.py summarises and classifies; fitness/reports.py writes the output files; tests.py holds the tests.

Participant holds a participant's identifier, name and personal baselines. Observation is one accepted measurement window. Session groups a participant with that session's accepted and rejected rows. RejectedRow records the file, row number, field and reason for a row that was not used. IntensityRule is an abstract base class, and HighActivityRule, ModerateActivityRule and RestingRule each define their own thresholds. InvalidIdentifierError and InvalidRecordError are the two custom exceptions.

Composition, encapsulation, inheritance and overriding

Composition: Session stores a Participant object and lists of Observation and RejectedRow objects. Encapsulation: Participant._baseline_heart_rate is reached through a property whose setter rejects values outside 30–120 bpm, and Observation and Session return copies of their protected collections. Inheritance and overriding: the three rule classes inherit from IntensityRule and override matches() and explain(); both custom exceptions inherit from ValueError.

Assumptions and rules

A row is rejected whole if any single value fails, since the values come from one sensor reading. Identifiers must match ^P\d{3}$ and ^FIT-\d{4}-\d{3}$, the participant must exist in the profile file, heart rate must be 35–205 bpm, skin response 0–20, temperature 25–42 °C, activity level 0–1, and signal quality 0–1 and not below 0.6. Classification uses the first rule that fits: fewer than four usable rows is insufficient data; a drop of 15 bpm and 0.2 activity between the first and last third is recovering; 40 bpm above baseline with activity 0.6+ is high activity; 15 bpm above baseline with activity 0.3+ is moderate activity; otherwise resting.

The project uses only Python standard library.

    git clone https://github.com/jehu004/assignment2.git
    cd assignment2
    python3 main.py

Example Output

Sessions analyzed: 7
Accepted rows:     25
Rejected rows:     15
Report files:
  output/analysis_summary.csv
  output/analysis_report.txt
  output/rejected_records.txt

-Skin response and temperature are summarised but do not affect the classification
-A row is rejected as a whole even when only one value is faulty. 
-Recovery is measured between the first and last third of a session, so a six-row session that peaks in the middle, such as FIT-2026-004, is reported as moderate activity rather than recovering.
-A row with a broken identifier is listed in the rejection file but cannot be counted on any session.