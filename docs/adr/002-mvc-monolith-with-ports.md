# ADR-002: Modular MVC monolith with ports and adapters

- **Status:** Proposed
- **Date:** 2026-10-22

## Context

Management requires starting with a **clean MVC monolith** and being able to migrate later to
**Hexagonal / Clean Architecture** and **microservices**. A classic MVC (controller → service →
JPA entity) couples the model to the database and the framework, and makes the migration expensive.

## Decision

1. **MVC only in the delivery layer**: REST controllers and views (Compose apps).
2. **The "Model" is a hexagonal core**: `domain` (pure entities and rules) + `application`
   (use cases as **input ports** and external dependencies as **output ports**).
3. **Modular monolith**: one package or module per bounded context (invoicing, taxation,
   identity, SUNAT integration, inventory, migration, catalogs). Each module has its own
   database schema.
4. Communication between modules: through public ports or **domain events**.
5. Dependency rules verified in CI with ArchUnit.

## Consequences

- (+) Migrating to Hexagonal means **renaming and moving**, not rewriting.
- (+) Each module can become a microservice by swapping the adapter (local call → HTTP / broker event).
- (+) The domain is tested with unit tests without a database or network.
- (−) More interfaces and mappings (DTO ↔ domain ↔ JPA entity) than a plain MVC.

## Alternatives considered

- **Classic MVC with JPA entities as the model**: faster at first, but blocks the migration.
- **Microservices from day 1**: operational overhead for a mid-sized company; management explicitly
  asked for a monolith.
