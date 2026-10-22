# SPEC-009: Legacy data migration

- **Status:** Draft
- **Date:** 2026-10-22
- **Related:** UC-13 · INV-09 · RS 234-2006/SUNAT · [06-legacy-migration.md](../../docs/06-legacy-migration.md)

## Summary
Migrate the warehouse records (`fecha, ingreso, salida, producto, nro_documento`) to the `Product`
and `InventoryMovement` entities **without losing traceability**.

## Transformation rules (M-n)
| ID | Rule |
|---|---|
| M-01 | Each source row gets a `sourceHash` = SHA-256 of the normalized raw row + row number; stored in `DataOrigin`. |
| M-02 | `fecha`: accepts `dd/mm/yyyy`, `yyyy-mm-dd`, `dd-mm-yy`; converted to ISO-8601. Null, invalid or future date → quarantine. |
| M-03 | `ingreso` > 0 and empty `salida` → `INBOUND` movement; `salida` > 0 and empty `ingreso` → `OUTBOUND`; both > 0 → **two** movements with the same `sourceHash`; both empty or 0 → quarantine. Negative or non-numeric values → quarantine. |
| M-04 | `producto`: normalized (trim, uppercase, single spaces, no accents) and grouped; each distinct normalized name creates a `Product` with a generated code, **provisional** `igvAffectation = 10` and `unit = NIU`, and flag `requiresReview = true` (the administrator confirms the tax configuration before selling). |
| M-05 | `nro_documento` → `documentReference` with type `LEGACY_INTERNAL`. It **never** becomes a SUNAT series/sequence number and no retroactive electronic documents are generated. |
| M-06 | Re-running the same batch is **idempotent**: rows whose `sourceHash` was already migrated are skipped. |
| M-07 | Dry-run mode by default: reports results without persisting. |
| M-08 | Mandatory reconciliation when closing the batch: Σ inbound and Σ outbound source = target (per product and overall); final stock per product = Σ inbound − Σ outbound. If it does not match → `COMPLETED_WITH_ISSUES`. |
| M-09 | The source is read-only: the migration never modifies the legacy system. |

## Acceptance criteria
- **AC-1:** Given [legacy-movement.json](../schemas/examples/legacy-movement.json), when I migrate it, then I get [inventory-movement.json](../schemas/examples/inventory-movement.json) (OUTBOUND of 12 `CER-620`, reference `N-0458`, origin LEGACY).
- **AC-2:** Given a row with empty `ingreso` and `salida`, then it is quarantined with rule `SPEC-009/M-03`.
- **AC-3:** Given the same file loaded twice, then the second load migrates 0 rows.
- **AC-4:** Given a completed batch, then the reconciliation shows source sums = target sums.
- **AC-5:** Given a migrated movement, when I look up its `sourceHash`, then I can locate the exact row of the legacy file.

## Contracts
- `POST /migrations`, `GET /migrations/{batch}`, `GET /migrations/{batch}/issues`
- [legacy-movement.schema.json](../schemas/legacy-movement.schema.json) → [inventory-movement.schema.json](../schemas/inventory-movement.schema.json)
