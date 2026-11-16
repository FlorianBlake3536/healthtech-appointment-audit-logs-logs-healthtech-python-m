import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from appointment_job import Appointment, notification_decision


def test_unconsented_patient_never_receives_a_reminder():
    appointment = Appointment("apt-1", "patient-1", "2026-11-02T09:00:00Z", False, False)
    assert notification_decision(appointment) == "skip_without_consent"
