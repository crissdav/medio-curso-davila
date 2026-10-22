# 06 — Legacy system migration

> Supports the "Legacy and Data Migration" constraint. Formal rules in
> [SPEC-009](../specs/features/009-legacy-migration.md).

## 1. Legacy assessment

The legacy system is a **warehouse control**, not a sales system. Its records contain no price,
customer or taxes, so they **cannot be turned into electronic documents**, and that must not be
attempted: retroactive issuance does not exist. What is migrated with full traceability is the
**movement history** and the **product master**.

## 2. Field-by-field mapping

```mermaid
flowchart LR
    subgraph L["Legacy (record)"]
        f[fecha]
        i[ingreso]
        s[salida]
        p[producto]
        n[nro_documento]
    end
    subgraph N["New model"]
        MI["InventoryMovement<br/>date · type · quantity"]
        PR["Product<br/>code · description<br/>requiresReview=true"]
        DR["DocumentReference<br/>type=LEGACY_INTERNAL"]
        OR["DataOrigin<br/>LEGACY · batch · row · hash"]
    end
    f -->|"normalize to ISO-8601 (M-02)"| MI
    i -->|"type=INBOUND (M-03)"| MI
    s -->|"type=OUTBOUND (M-03)"| MI
    p -->|"normalize + group (M-04)"| PR
    n -->|"kept as is (M-05)"| DR
    L -.->|"SHA-256 of the row (M-01)"| OR
    MI --- OR
    MI --- DR
    MI --> PR
```

| Legacy field | Target | Transformation | On failure |
|---|---|---|---|
| `fecha` | `InventoryMovement.date` | Multi-format parsing → `yyyy-mm-dd` | Quarantine (M-02) |
| `ingreso` | `InventoryMovement` type `INBOUND`, `quantity` | Number > 0 | Quarantine (M-03) |
| `salida` | `InventoryMovement` type `OUTBOUND`, `quantity` | Number > 0 | Quarantine (M-03) |
| `producto` | `Product.description` + generated `code`; `InventoryMovement.productCode` | Trim, uppercase, no accents, deduplicate | Quarantine if empty |
| `nro_documento` | `DocumentReference{type: LEGACY_INTERNAL, number}` | None | Empty allowed |
| (whole row) | `DataOrigin{system: LEGACY, migrationBatch, sourceRow, sourceHash}` | SHA-256 | — |

## 3. Process (ETL with audit trail)

```mermaid
flowchart TB
    A["1 · Extract<br/>CSV / dump (read-only)"] --> B["2 · Profile<br/>date formats, nulls,<br/>distinct product names"]
    B --> C["3 · Dry run<br/>applies M-01..M-05, nothing persisted"]
    C --> D{"Acceptable<br/>issues?"}
    D -- No --> E["Fix at source<br/>or synonym dictionary"] --> C
    D -- Yes --> F["4 · Load<br/>idempotent by sourceHash (M-06)"]
    F --> G["5 · Reconcile (M-08)<br/>Σ source = Σ target"]
    G --> H["6 · Tax review<br/>admin confirms IGV / ISC affectation<br/>of requiresReview products"]
    H --> I["Batch COMPLETED"]
```

## 4. Traceability guarantees (RS 234-2006)

1. **Bidirectional:** from any migrated movement you reach the source row (`sourceRow` +
   `sourceHash`), and from any source row you find its movement(s).
2. **No loss:** every row ends up migrated **or** quarantined with its reason; nothing is silently discarded.
3. **Reconciliation:** control totals per product and overall, stored with the batch.
4. **Immutability:** migrated movements are never edited; they are corrected with an `ADJUSTMENT`.
5. **Untouched source:** the legacy system is not modified and is archived read-only.

## 5. Special cases

| Case | Handling |
|---|---|
| Same product spelled differently ("Cerveza 620ml", "CERVEZA 620 ML") | Normalization + synonym dictionary reviewed by the administrator. |
| Inbound and outbound in the same row | Two movements with the same `sourceHash`. |
| `nro_documento` formatted like `F001-123` | Kept as `LEGACY_INTERNAL`; **not** linked to SUNAT sequence numbers (SPEC-005 R-07). |
| Resulting negative stock | Migrated anyway (it reflects the real history) and reported as a reconciliation issue. |
