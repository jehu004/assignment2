from abc import ABC, abstractmethod


MIN_USABLE_OBSERVATIONS = 4
RECOVERY_HR_DROP = 15
RECOVERY_ACTIVITY_DROP = 0.2

SUMMARY_FIELDS = ["heart_rate", "skin_response", "temperature", "activity_level"]


def calculate_summary(values):
    if len(values) == 0:
        return {"average": None, "minimum": None, "maximum": None}
    return {
        "average": round(sum(values) / len(values), 2),
        "minimum": min(values),
        "maximum": max(values),
    }


def detect_recovery(heart_rates, activity_levels):
    if len(heart_rates) < 6:
        return {"detected": False, "heart_rate_drop": 0, "activity_drop": 0}

    third = len(heart_rates) // 3
    start_hr = sum(heart_rates[:third]) / third
    end_hr = sum(heart_rates[-third:]) / third
    start_activity = sum(activity_levels[:third]) / third
    end_activity = sum(activity_levels[-third:]) / third

    hr_drop = round(start_hr - end_hr, 1)
    activity_drop = round(start_activity - end_activity, 2)
    detected = hr_drop >= RECOVERY_HR_DROP and activity_drop >= RECOVERY_ACTIVITY_DROP

    return {"detected": detected, "heart_rate_drop": hr_drop, "activity_drop": activity_drop}


class IntensityRule(ABC):

    label = "unknown"

    @abstractmethod
    def matches(self, hr_difference, average_activity):
        pass

    def explain(self, hr_difference, average_activity):
        return (f"Average heart rate was {hr_difference} bpm from baseline "
                f"and average activity was {average_activity}.")


class HighActivityRule(IntensityRule):
    label = "high activity"

    def matches(self, hr_difference, average_activity):
        return hr_difference >= 40 and average_activity >= 0.6

    def explain(self, hr_difference, average_activity):
        return (f"Heart rate was {hr_difference} bpm above baseline (40 or more) "
                f"and average activity was {average_activity} (0.6 or more).")


class ModerateActivityRule(IntensityRule):
    label = "moderate activity"

    def matches(self, hr_difference, average_activity):
        return hr_difference >= 15 and average_activity >= 0.3

    def explain(self, hr_difference, average_activity):
        return (f"Heart rate was {hr_difference} bpm above baseline (15 or more) "
                f"and average activity was {average_activity} (0.3 or more), "
                f"but not high enough for high activity.")


class RestingRule(IntensityRule):
    label = "resting"

    def matches(self, hr_difference, average_activity):
        return hr_difference < 15 and average_activity < 0.3

    def explain(self, hr_difference, average_activity):
        return (f"Heart rate stayed close to baseline ({hr_difference} bpm, under 15) "
                f"and average activity was low ({average_activity}, under 0.3).")


INTENSITY_RULES = [HighActivityRule(), ModerateActivityRule(), RestingRule()]


def classify_session(hr_difference, average_activity, recovery):
    if recovery["detected"]:
        return ("recovering",
                f"Heart rate dropped {recovery['heart_rate_drop']} bpm and activity dropped "
                f"{recovery['activity_drop']} between the start and the end of the session.")

    for rule in INTENSITY_RULES:
        if rule.matches(hr_difference, average_activity):
            return rule.label, rule.explain(hr_difference, average_activity)

    if hr_difference >= 40:
        label = "high activity"
    elif hr_difference >= 15:
        label = "moderate activity"
    else:
        label = "resting"
    return (label, f"Heart rate and activity disagreed, so heart rate alone was used "
                   f"({hr_difference} bpm from baseline).")


def analyze_session(session):
    participant = session.participant
    usable = session.observations

    result = {
        "session_id": session.session_id,
        "participant": participant,
        "participant_id": participant.participant_id,
        "total_rows": len(session),
        "usable_rows": len(usable),
        "rejected_rows": len(session.rejections),
        "rejections": session.rejections,
        "summaries": {},
        "comparison": None,
        "recovery": None,
        "classification": None,
        "explanation": None,
    }

    for field in SUMMARY_FIELDS:
        result["summaries"][field] = calculate_summary(session.values(field))

    if len(usable) < MIN_USABLE_OBSERVATIONS:
        result["classification"] = "insufficient data"
        result["explanation"] = (f"Only {len(usable)} of {len(session)} rows were usable "
                                 f"(at least {MIN_USABLE_OBSERVATIONS} are needed).")
        return result

    averages = {field: result["summaries"][field]["average"] for field in SUMMARY_FIELDS}
    result["comparison"] = {
        "heart_rate_difference": round(averages["heart_rate"] - participant.baseline_heart_rate, 1),
        "skin_response_difference": round(averages["skin_response"] - participant.baseline_skin_response, 2),
        "temperature_difference": round(averages["temperature"] - participant.baseline_temperature, 2),
    }

    recovery = detect_recovery(session.values("heart_rate"), session.values("activity_level"))
    result["recovery"] = recovery

    label, explanation = classify_session(result["comparison"]["heart_rate_difference"],
                                          averages["activity_level"], recovery)
    result["classification"] = label
    result["explanation"] = explanation
    return result
