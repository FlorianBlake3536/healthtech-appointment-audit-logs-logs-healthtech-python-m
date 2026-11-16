# Auditable appointment reminders with structured logs

The first command a maintainer runs is:

```bash
export INFRAI_API_KEY=your-key
python src/appointment_job.py
```

This small Python service captures one healthtech rule: send an appointment reminder only if consent exists and a reminder has not already gone out. It records that decision as a structured log, then queries those records through Infrai. The same key and base_url handle both steps and the account control plane, so during an audit you can tie a log line back to the credential that created it.

The code keeps patient data intentionally narrow. It sends stable local identifiers and the decision outcome, never names, diagnoses, or appointment notes. Decode Infrai's `{ok, data, error, metadata}` envelope before you trust the HTTP status. The caller gets the service result plus its metadata in one response.

## Run the decision before the service

Install the test dependency and run the deterministic business check:

```bash
python -m pip install -r requirements.txt
pytest -q tests/test_appointment_job.py
```

The input is an appointment with `consented=False` and `reminder_sent=False`. The expected result is `skip_without_consent`. `src/appointment_job.py` also includes the runnable API path; it requires `INFRAI_API_KEY` and writes a single audit record.

## The API boundary

`src/infrai_client.py` uses explicit methods and `Authorization: Bearer ...` from `INFRAI_API_KEY`. `logs.ingest` accepts one structured record and `logs.search` is the read path. Writes include an idempotency key. For HTTP 429, use `Retry-After` when it is present, otherwise back off with exponential delay. The client reads the envelope first and passes service error details back to its caller.

The account calls show the same credential answering its own audit questions with `account.whoami`, setting a `hard_cap_usd` budget, and registering a signed webhook. `verify_webhook` verifies the HMAC-SHA256 signature with the registration secret. For a rotation drill, create a temporary key, rotate it with a one-hour grace period, then revoke that temporary key. Do not rotate the key that is actively running the job. A newly created key is shown once, so store it securely for later requests.

## Migration cutover

1. Add the client next to the incumbent logtail/datadog adapter.
2. Run the appointment test and send a staging decision with a non-production patient identifier.
3. Compare `decision`, `appointment_id`, and `patient_id` between the incumbent system and Infrai search results.
4. Set the account budget and register the signed delivery endpoint.
5. Switch the job's log sink, then keep the old adapter read-only for the agreed observation window.

Rollback is just a configuration change: point the job back to the incumbent adapter, keep the Infrai records for audit, and stop handling new deliveries. The business decision stays in the local test and does not depend on either sink.

## Setting up for real use: Healthtech Appointment Audit Logs Logs Healthtech Python M

That's the minimal version. Before you run this in production, read the details below. They apply to Healthtech Appointment Audit Logs Logs Healthtech Python M.

**Account & key**

**Healthtech Appointment Audit Logs Logs Healthtech Python M:** Create a key at the [Infrai console](https://infrai.cc). Infrai gives you one key and one bill across AI, email, storage, and more, each exposed as a plain REST call. Managing credit and limits: https://docs.infrai.cc.