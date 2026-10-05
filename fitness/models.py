def is_in_range(value, low, high):
    if value is None:
        return False
    return low <= value <= high


class Participant:
    def __init__(self, participant_id, name, baseline_heart_rate,
                 baseline_skin_response, baseline_temperature):
        self.participant_id = participant_id
        self.name = name
        self.baseline_heart_rate = baseline_heart_rate
        self._baseline_skin_response = baseline_skin_response
        self._baseline_temperature = baseline_temperature

    @property
    def baseline_heart_rate(self):
        return self._baseline_heart_rate

    @baseline_heart_rate.setter
    def baseline_heart_rate(self, value):
        if not is_in_range(value, 30, 120):
            raise ValueError(f"Baseline heart rate must be between 30 and 120 bpm, got {value}.")
        self._baseline_heart_rate = value

    @property
    def baseline_skin_response(self):
        return self._baseline_skin_response

    @property
    def baseline_temperature(self):
        return self._baseline_temperature

    @classmethod
    def from_profile(cls, profile):
        return cls(
            participant_id=profile["participant_id"],
            name=profile["name"],
            baseline_heart_rate=profile["baseline_heart_rate"],
            baseline_skin_response=profile["baseline_skin_response"],
            baseline_temperature=profile["baseline_temperature"],
        )

    def __str__(self):
        return (f"Participant {self.participant_id} ({self.name}) "
                f"- baseline HR {self.baseline_heart_rate} bpm, "
                f"skin {self.baseline_skin_response}, "
                f"temp {self.baseline_temperature} C")


class Observation:
    def __init__(self, timestamp, heart_rate, skin_response, temperature,
                 activity_level, signal_quality):
        self.timestamp = timestamp
        self._measurements = {
            "heart_rate": heart_rate,
            "skin_response": skin_response,
            "temperature": temperature,
            "activity_level": activity_level,
            "signal_quality": signal_quality,
        }

    def get(self, field_name):
        return self._measurements.get(field_name)

    @property
    def measurements(self):
        return self._measurements.copy()

    def __str__(self):
        return (f"Window {self.timestamp}: "
                f"{self.get('heart_rate')} bpm, activity {self.get('activity_level')}")


class RejectedRow:
    def __init__(self, source_file, row_number, field, reason):
        self.source_file = source_file
        self.row_number = row_number
        self.field = field
        self.reason = reason

    def __str__(self):
        return f"{self.source_file} row {self.row_number} [{self.field}]: {self.reason}"


class Session:
    def __init__(self, session_id, participant):
        self.session_id = session_id
        self.participant = participant
        self._observations = []
        self._rejections = []

    def add_observation(self, observation):
        self._observations.append(observation)

    def add_rejection(self, rejected_row):
        self._rejections.append(rejected_row)

    @property
    def observations(self):
        return self._observations.copy()

    @property
    def rejections(self):
        return self._rejections.copy()

    def values(self, field_name):
        return [observation.get(field_name) for observation in self._observations]

    def __len__(self):
        return len(self._observations) + len(self._rejections)

    def __str__(self):
        return (f"Session {self.session_id} for {self.participant.participant_id} "
                f"({len(self._observations)} usable of {len(self)} rows)")
