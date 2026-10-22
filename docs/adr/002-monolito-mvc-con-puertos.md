# ADR-002: Monolito MVC modular con puertos y adaptadores

- **Estado:** Propuesto
- **Fecha:** 2026-10-22

## Contexto

La gerencia exige iniciar con un **monolito MVC limpio** y poder migrar luego a
**Hexagonal / Clean Architecture** y a **microservicios**. Un MVC clásico (controlador → servicio →
entidad JPA) acopla el modelo a la base de datos y al framework, y hace costosa la migración.

## Decisión

1. **MVC solo en la capa de entrega**: controladores REST y vistas (apps Compose).
2. **El "Modelo" es un núcleo hexagonal**: `domain` (entidades y reglas puras) + `application`
   (casos de uso como **puertos de entrada** y dependencias externas como **puertos de salida**).
3. **Monolito modular**: un paquete o módulo por contexto delimitado (facturación, tributación,
   identidad, integración SUNAT, inventario, migración, catálogos). Cada módulo tiene su propio
   esquema de base de datos.
4. Comunicación entre módulos: por puertos públicos o por **eventos de dominio**.
5. Reglas de dependencia verificadas en CI con ArchUnit.

## Consecuencias

- (+) La migración a Hexagonal es **renombrar y mover**, no reescribir.
- (+) Cada módulo puede convertirse en microservicio cambiando el adaptador (llamada local →
  HTTP / evento en un broker).
- (+) El dominio se prueba con tests unitarios sin base de datos ni red.
- (−) Más interfaces y mapeos (DTO ↔ dominio ↔ entidad JPA) que un MVC simple.

## Alternativas consideradas

- **MVC clásico con entidades JPA como modelo**: más rápido al inicio, pero bloquea la migración.
- **Microservicios desde el día 1**: sobrecosto operativo para una empresa mediana; la gerencia
  pidió explícitamente un monolito.
