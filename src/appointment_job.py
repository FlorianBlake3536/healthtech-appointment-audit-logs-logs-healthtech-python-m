"""Appointment notification workflow with a privacy-preserving audit record."""
from dataclasses import dataclass
from typing import Any

from infrai_client import InfraiClient


@dataclass(frozen=True)
class Appointment:
    appointment_id: str
    patient_id: str
    starts_at: str
    reminder_sent: bool
    consented: bool


def notification_decision(appointment: Appointment) -> str:
    if appointment.reminder_sent:
        return "skip_already_sent"
    if not appointment.consented:
        return "skip_without_consent"
    return "send_reminder"


def ship_audit_log(client: InfraiClient, appointment: Appointment) -> dict[str, Any]:
    decision = notification_decision(appointment)
    record = {
        "message": "appointment notification decision",
        "level": "info",
        "context": {
            "appointment_id": appointment.appointment_id,
            "patient_id": appointment.patient_id,
            "decision": decision,
        },
    }
    return client.ingest_log(record, f"appointment:{appointment.appointment_id}:{decision}")


def main() -> None:
    client = InfraiClient()
    appointment = Appointment("apt-100", "patient-100", "2026-11-02T09:00:00Z", False, True)
    print(notification_decision(appointment))
    print(ship_audit_log(client, appointment))


if __name__ == "__main__":
    main()
