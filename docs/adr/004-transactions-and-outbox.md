# ADR-004: Two transactions and an outbox for issuing documents

- **Status:** Proposed
- **Date:** 2026-11-04

## Context

SPEC-005 locks the series row to assign the sequence number. If the same transaction also waited for the OSE or
SUNAT, the series would stay locked during a network call: one slow response would block every sale on that
series, and a failed transaction would lose the XML. The lock must not depend on an external system.

## Decision

Issuing is split into two transactions, and the connection between them is an **outbox** table:

1. **Numbering transaction (milliseconds, no external I/O).** Assigns the number with an atomic update of the
   series row, builds and signs the XML with a certificate already in memory, stores the document as `SIGNED` and
   writes the submission to the outbox. Validation and tax calculation run **before** it starts.
2. **Submission (outside any database transaction).** A worker reads the outbox with `FOR UPDATE SKIP LOCKED`,
   calls `SunatSubmissionPort` and, in a short transaction, stores the CDR, updates the status and writes
   the `InvoiceAccepted` event to the outbox.

The API waits a few seconds for the CDR without holding a transaction: it answers 201 with the result, or 202 if
the CDR has not arrived. Delivery is at-least-once, so the worker checks the status (`getStatus`) before resubmitting.

## Consequences

- (+) The series lock lasts milliseconds, regardless of the OSE.
- (+) A signed document is never lost if the OSE is down: the outbox retries it.
- (+) The outbox is already the event mechanism that phase 3 (microservices) needs.
- (−) Requires a worker and a table to monitor (pending rows, age of the oldest row).
- (−) A client may receive 202 and have to look up the final result.

## Alternatives considered

- **One transaction including the OSE call**: simple, but it blocks the series during the network call.
- **Assigning the number in its own transaction**: frees the lock even earlier, but a failure before signing would leave gaps in the numbering.
