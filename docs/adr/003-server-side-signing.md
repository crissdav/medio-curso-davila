# ADR-003: Digital signing and SUNAT/OSE submission on the server only

- **Status:** Proposed
- **Date:** 2026-10-22

## Context

The document XML is signed with the issuer's **digital certificate** (`.pfx` file with the private
key). The apps run on point-of-sale PCs and on the Android phones of route salespeople.

## Decision

- XML generation, signing and submission to SUNAT/OSE happen **only in the monolith**
  (`sunatintegration`), behind `DigitalSignaturePort` and `SunatSubmissionPort`.
- The certificate is kept in a server-side secrets store, never on the devices.
- The channel (SUNAT directly or an OSE) is a **swappable adapter** (`SunatAdapter` / `OseAdapter`)
  selected by configuration.
- Offline Android (UC-19) stores the **sale** in a local queue; the document is issued on
  synchronization. If something must be handed over on the spot, an internal sales note is given
  (it is not a tax document).

## Consequences

- (+) Losing a phone or having it stolen does not compromise the company's private key.
- (+) A single point controls sequence numbers, avoiding duplicates across devices.
- (−) Issuing requires a connection to the server; mitigated by the offline queue and the
  `PENDING_SUBMISSION` status.

## Alternatives considered

- **Signing on each device**: allows offline issuing, but distributes the private key and
  complicates numbering.
