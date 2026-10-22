# SPEC-007: Submission to the OSE / SUNAT and CDR handling

- **Status:** Draft
- **Date:** 2026-10-22
- **Related:** UC-06, UC-09 · ADR-003 · [cdr-response.schema.json](../schemas/cdr-response.schema.json)

## Summary
Submit the signed document to the OSE or SUNAT, interpret the CDR and handle retries.

## Rules
| ID | Rule |
|---|---|
| R-01 | Channel configurable per company: `SUNAT` (SEE Del Contribuyente) or `OSE`. Both behind `SunatSubmissionPort`. |
| R-02 | Invoices and their notes: synchronous individual submission (`sendBill`). |
| R-03 | Response code interpretation: `0` → ACCEPTED; ≥ `4000` → OBSERVED (accepted with observations); `2000`–`3999` → REJECTED; `0100`–`1999` → EXCEPTION (retryable, status `PENDING_SUBMISSION`). |
| R-04 | A document cannot have two simultaneous submissions (`SUBMISSION_IN_PROGRESS`). |
| R-05 | Automatic retries with exponential backoff (1, 5, 15, 60 min…) within the current maximum submission deadline; the accountant is alerted as the deadline approaches. |
| R-06 | Before resubmitting after a timeout, the status is checked (`getStatus`) to avoid duplicate submissions. |
| R-07 | The CDR is stored as is (ZIP) next to the signed XML. |
| R-08 | A REJECTED document is neither corrected nor resubmitted: a new one is issued with another sequence number. |

## Acceptance criteria
- **AC-1:** Given a CDR with code 0, then status `ACCEPTED` and event `InvoiceAccepted`.
- **AC-2:** Given a CDR with code 2800, then status `REJECTED` and error `SUNAT-2800`.
- **AC-3:** Given an OSE timeout, then status `PENDING_SUBMISSION` and HTTP response 202.
- **AC-4:** Given a `PENDING_SUBMISSION` document, when the scheduler retries and SUNAT answers 0, then it becomes `ACCEPTED`.

## Open questions
- Choice of OSE (provider) and its specific SOAP contract.
