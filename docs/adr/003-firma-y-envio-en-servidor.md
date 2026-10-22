# ADR-003: Firma digital y envío a SUNAT/OSE solo en el servidor

- **Estado:** Propuesto
- **Fecha:** 2026-10-22

## Contexto

El XML del comprobante se firma con el **certificado digital** del emisor (archivo `.pfx` con
clave privada). Las apps corren en PCs de caja y en celulares Android de vendedores en ruta.

## Decisión

- La generación del XML, la firma y el envío a SUNAT/OSE ocurren **solo en el monolito**
  (`integracionsunat`), detrás de `FirmaDigitalPort` y `EnvioSunatPort`.
- El certificado se guarda en un almacén de secretos del servidor, nunca en los dispositivos.
- El canal (SUNAT directo u OSE) es un **adaptador intercambiable** (`SunatAdapter` / `OseAdapter`)
  elegido por configuración.
- Android sin conexión (UC-19) guarda la **venta** en una cola local; el comprobante se emite al
  sincronizar. Si se requiere entregar algo en el momento, se entrega una nota de venta interna
  (no es comprobante).

## Consecuencias

- (+) La pérdida o robo de un celular no compromete la clave privada de la empresa.
- (+) Un único punto controla correlativos, evitando duplicados entre dispositivos.
- (−) La emisión requiere conexión al servidor; mitigado con cola offline y estado `PENDIENTE_ENVIO`.

## Alternativas consideradas

- **Firma en cada dispositivo**: permite emitir offline, pero distribuye la clave privada y
  complica la numeración.
