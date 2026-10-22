// Capa de CONTENIDO SUNAT sobre los XML de specs/ref/ (la capa de ESTRUCTURA la valida ValidarXsd.java).
//  1. Códigos del XML existen en los catálogos de specs/catalogos/ (filas T-nn de la matriz).
//  2. Reglas peruanas: CustomizationID 2.0, serie F/B, RUC módulo 11, factura → cliente con RUC.
//  3. Aritmética interna del XML (líneas, impuestos, totales).
//  4. Si existe el JSON equivalente, el XML coincide con él campo por campo.
import { readFileSync, readdirSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { DOMParser } from '@xmldom/xmldom';
import xpath from 'xpath';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const refDir = join(root, 'specs', 'ref');
const select = xpath.useNamespaces({
  inv: 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2',
  cac: 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
  cbc: 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
});
// Equivalencia XML → JSON (los demás XML de specs/ref/ son de referencia, sin JSON).
const equivalentes = { '20123456786-01-F001-123.xml': 'schemas/examples/factura-response.json' };
// Ejemplos de terceros: se reportan sus hallazgos, pero no hacen fallar la validación.
const terceros = new Set(['sunat-factura-minima-ejemplo.xml']);

const catalogos = {};
for (const f of readdirSync(join(root, 'specs', 'catalogos'))) {
  const c = JSON.parse(readFileSync(join(root, 'specs', 'catalogos', f), 'utf8'));
  catalogos[c.numero] = new Map(c.codigos.map((x) => [x.codigo, x]));
}

const rucValido = (ruc) => {
  if (!/^(10|15|16|17|20)\d{9}$/.test(ruc)) return false;
  const suma = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2].reduce((s, w, i) => s + w * Number(ruc[i]), 0);
  const dv = (11 - (suma % 11)) % 10;
  return dv === Number(ruc[10]);
};
const num = (n) => Number(n?.textContent ?? n?.value ?? NaN);
const txt = (n) => (n?.textContent ?? n?.value ?? '').trim();
const r2 = (x) => Math.round((x + Number.EPSILON) * 100) / 100;
const igual = (a, b) => Math.abs(a - b) < 0.005;

let totalErrores = 0;
for (const file of readdirSync(refDir).filter((f) => f.endsWith('.xml')).sort()) {
  const doc = new DOMParser().parseFromString(readFileSync(join(refDir, file), 'utf8'), 'text/xml');
  const one = (xp, ctx = doc) => select(xp, ctx, true);
  const all = (xp, ctx = doc) => select(xp, ctx);
  const errores = [];
  const avisos = [];
  let checks = 0;
  const ok = (cond, msg) => { checks++; if (!cond) errores.push(msg); };
  const enCatalogo = (cat, codigo, fila) => ok(catalogos[cat]?.has(codigo), `${fila}: "${codigo}" no existe en el catálogo ${cat}`);

  // ---------- 1 y 2. Códigos y reglas SUNAT ----------
  ok(txt(one('/inv:Invoice/cbc:UBLVersionID')) === '2.1', 'T-01: UBLVersionID debe ser 2.1');
  ok(txt(one('/inv:Invoice/cbc:CustomizationID')) === '2.0', 'T-02: CustomizationID debe ser 2.0 (SUNAT)');
  const numero = txt(one('/inv:Invoice/cbc:ID'));
  ok(/^[FB][A-Z0-9]{3}-\d{1,8}$/.test(numero), `T-05: "${numero}" no tiene formato serie-correlativo SUNAT`);
  const tipo = txt(one('/inv:Invoice/cbc:InvoiceTypeCode'));
  enCatalogo('01', tipo, 'T-08');
  enCatalogo('51', txt(one('/inv:Invoice/cbc:InvoiceTypeCode/@listID')), 'T-09');
  ok(numero[0] === catalogos['01'].get(tipo)?.prefijoSerie, `T-05/T-08: la serie de ${numero} no corresponde al tipo ${tipo}`);
  const moneda = txt(one('/inv:Invoice/cbc:DocumentCurrencyCode'));
  enCatalogo('02', moneda, 'T-11');
  for (const n of all('//@currencyID')) ok(n.value === moneda, `T-11: currencyID "${n.value}" distinto de la moneda del documento`);

  const emisor = one('/inv:Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID');
  ok(txt(one('@schemeID', emisor)) === '6', 'T-12: el emisor debe identificarse con RUC (schemeID 6)');
  ok(rucValido(txt(emisor)), `T-12: RUC emisor ${txt(emisor)} no pasa módulo 11`);
  ok(txt(one('/inv:Invoice/cac:Signature/cac:SignatoryParty/cac:PartyIdentification/cbc:ID')) === txt(emisor), 'T-04: el firmante debe ser el RUC emisor');
  const cliente = one('/inv:Invoice/cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID');
  const tipoDocCliente = txt(one('@schemeID', cliente));
  enCatalogo('06', tipoDocCliente, 'T-16');
  const patron = catalogos['06'].get(tipoDocCliente)?.patron;
  if (patron) ok(new RegExp(patron).test(txt(cliente)), `T-17: documento del cliente "${txt(cliente)}" no cumple el patrón del catálogo 06`);
  if (tipoDocCliente === '6') ok(rucValido(txt(cliente)), `T-17: RUC cliente ${txt(cliente)} no pasa módulo 11`);
  if (tipo === '01') ok(tipoDocCliente === '6', 'SPEC-001 R-01: una factura exige cliente con RUC');

  for (const ts of all('//cac:TaxScheme')) {
    const id = txt(one('cbc:ID', ts));
    enCatalogo('05', id, 'T-24…T-29');
    const c = catalogos['05'].get(id);
    if (c) {
      ok(txt(one('cbc:Name', ts)) === c.nombre, `T-24…T-29: TaxScheme ${id} debe llamarse ${c.nombre}`);
      ok(txt(one('cbc:TaxTypeCode', ts)) === c.codigoInternacional, `T-24…T-29: TaxScheme ${id} debe tener TaxTypeCode ${c.codigoInternacional}`);
    }
  }
  for (const n of all('//cbc:TaxExemptionReasonCode')) enCatalogo('07', txt(n), 'T-49');
  for (const n of all('//cbc:TierRange')) enCatalogo('08', txt(n), 'T-51');
  for (const n of all('//cbc:PriceTypeCode')) enCatalogo('16', txt(n), 'T-43');
  for (const n of all('//cbc:InvoicedQuantity/@unitCode')) enCatalogo('03', n.value, 'T-41');
  // ISC presente ⇒ debe declarar su sistema de cálculo (catálogo 08). Solo en líneas.
  for (const sub of all('//cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal[cac:TaxCategory/cac:TaxScheme/cbc:ID="2000"]')) {
    ok(one('cac:TaxCategory/cbc:TierRange', sub), 'T-51 / SPEC-003 R-05: línea con ISC sin TierRange (catálogo 08)');
  }
  if (!one('/inv:Invoice/cac:PaymentTerms[cbc:ID="FormaPago"]')) {
    avisos.push('T-20: no informa la forma de pago (cac:PaymentTerms "FormaPago"), exigida por SUNAT desde 2021');
  }

  // ---------- 3. Aritmética interna ----------
  const lineas = all('/inv:Invoice/cac:InvoiceLine');
  let sumaValor = 0;
  const porTributo = {};
  for (const l of lineas) {
    const id = txt(one('cbc:ID', l));
    const valor = num(one('cbc:LineExtensionAmount', l));
    sumaValor += valor;
    ok(igual(valor, r2(num(one('cbc:InvoicedQuantity', l)) * num(one('cac:Price/cbc:PriceAmount', l)))), `Línea ${id}: LineExtensionAmount ≠ cantidad × valor unitario (SPEC-003 R-01)`);
    const subs = all('cac:TaxTotal/cac:TaxSubtotal', l);
    ok(igual(num(one('cac:TaxTotal/cbc:TaxAmount', l)), subs.reduce((s, x) => s + num(one('cbc:TaxAmount', x)), 0)), `Línea ${id}: TaxTotal ≠ Σ TaxSubtotal (T-55)`);
    const isc = subs.filter((x) => txt(one('cac:TaxCategory/cac:TaxScheme/cbc:ID', x)) === '2000').reduce((s, x) => s + num(one('cbc:TaxAmount', x)), 0);
    for (const s of subs) {
      const trib = txt(one('cac:TaxCategory/cac:TaxScheme/cbc:ID', s));
      porTributo[trib] = (porTributo[trib] ?? 0) + num(one('cbc:TaxAmount', s));
      if (trib === '1000') {
        ok(igual(num(one('cbc:TaxableAmount', s)), r2(valor + isc)), `Línea ${id}: base IGV ≠ valor venta + ISC (SPEC-003 R-03)`);
        ok(igual(num(one('cbc:TaxAmount', s)), r2(num(one('cbc:TaxableAmount', s)) * num(one('cac:TaxCategory/cbc:Percent', s)) / 100)), `Línea ${id}: IGV ≠ base × tasa (SPEC-003 R-04)`);
      }
      if (trib === '7152') {
        ok(igual(num(one('cbc:TaxAmount', s)), r2(num(one('cbc:BaseUnitMeasure', s)) * num(one('cac:TaxCategory/cbc:PerUnitAmount', s)))), `Línea ${id}: ICBPER ≠ bolsas × monto unitario (SPEC-003 R-06)`);
      }
    }
  }
  const cab = (xp) => num(one(`/inv:Invoice/${xp}`));
  ok(igual(cab('cac:LegalMonetaryTotal/cbc:LineExtensionAmount'), r2(sumaValor)), 'T-30: LineExtensionAmount ≠ Σ valor venta de las líneas');
  const subsCab = all('/inv:Invoice/cac:TaxTotal/cac:TaxSubtotal');
  ok(igual(cab('cac:TaxTotal/cbc:TaxAmount'), subsCab.reduce((s, x) => s + num(one('cbc:TaxAmount', x)), 0)), 'T-23: TaxTotal ≠ Σ TaxSubtotal de cabecera');
  for (const s of subsCab) {
    const trib = txt(one('cac:TaxCategory/cac:TaxScheme/cbc:ID', s));
    const tolerancia = trib === '1000' ? 1 : 0.005; // SPEC-003 R-09: ±1.00 entre IGV global y Σ líneas
    ok(Math.abs(num(one('cbc:TaxAmount', s)) - (porTributo[trib] ?? 0)) <= tolerancia, `T-24…T-29: total del tributo ${trib} no cuadra con Σ líneas`);
  }
  ok(igual(cab('cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount'), r2(cab('cac:LegalMonetaryTotal/cbc:LineExtensionAmount') + cab('cac:TaxTotal/cbc:TaxAmount'))), 'T-31: TaxInclusiveAmount ≠ valor venta + impuestos');
  ok(igual(cab('cac:LegalMonetaryTotal/cbc:PayableAmount'), cab('cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount')), 'T-34: PayableAmount ≠ TaxInclusiveAmount (sin descuentos ni anticipos)');

  // ---------- 4. Cruce con el JSON equivalente ----------
  if (equivalentes[file]) {
    const j = JSON.parse(readFileSync(join(root, 'specs', equivalentes[file]), 'utf8'));
    const t = j.totales;
    ok(numero === `${j.serie}-${j.correlativo}`, `T-05: ${numero} ≠ ${j.numero} del JSON`);
    ok(txt(one('/inv:Invoice/cbc:IssueDate')) === j.fechaEmision, 'T-06: fecha distinta del JSON');
    ok(tipo === j.tipoComprobante && moneda === j.moneda, 'T-08/T-11: tipo o moneda distintos del JSON');
    ok(txt(emisor) === j.emisor.ruc && txt(cliente) === j.cliente.numeroDocumento, 'T-12/T-17: RUC distinto del JSON');
    ok(txt(one('/inv:Invoice/cbc:Note[@languageLocaleID="1000"]')) === t.importeEnLetras, 'T-10: importe en letras distinto del JSON');
    ok(lineas.length === j.items.length, 'T-40: cantidad de líneas distinta del JSON');
    const pares = [
      ['cac:TaxTotal/cbc:TaxAmount', t.totalImpuestos, 'T-23'],
      ['cac:LegalMonetaryTotal/cbc:LineExtensionAmount', t.totalValorVenta, 'T-30'],
      ['cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount', t.totalPrecioVenta, 'T-31'],
      ['cac:LegalMonetaryTotal/cbc:PayableAmount', t.importeTotal, 'T-34'],
    ];
    for (const [xp, valor, fila] of pares) ok(igual(cab(xp), Number(valor)), `${fila}: ${xp} distinto del JSON (${valor})`);
    for (const [trib, campo] of [['1000', 'totalIgv'], ['2000', 'totalIsc'], ['7152', 'totalIcbper']]) {
      const n = one(`/inv:Invoice/cac:TaxTotal/cac:TaxSubtotal[cac:TaxCategory/cac:TaxScheme/cbc:ID="${trib}"]/cbc:TaxAmount`);
      ok(igual(num(n), Number(t[campo])), `T-24…T-29: tributo ${trib} distinto de ${campo} del JSON`);
    }
    j.items.forEach((it, i) => {
      const l = lineas[i];
      if (!l) return;
      const fila = `Línea ${it.numeroLinea}`;
      ok(txt(one('cac:Item/cac:SellersItemIdentification/cbc:ID', l)) === it.codigoProducto, `${fila}: código de producto distinto del JSON (T-47)`);
      ok(igual(num(one('cbc:InvoicedQuantity', l)), Number(it.cantidad)) && txt(one('cbc:InvoicedQuantity/@unitCode', l)) === it.unidadMedida, `${fila}: cantidad o unidad distinta del JSON (T-41)`);
      ok(igual(num(one('cbc:LineExtensionAmount', l)), Number(it.valorVenta)), `${fila}: valor venta distinto del JSON (T-42)`);
      ok(Math.abs(num(one('cac:PricingReference/cac:AlternativeConditionPrice/cbc:PriceAmount', l)) - Number(it.precioUnitario)) < 0.0001, `${fila}: precio unitario distinto del JSON (T-43)`);
      ok(txt(one('.//cbc:TaxExemptionReasonCode', l)) === it.afectacionIgv, `${fila}: afectación IGV distinta del JSON (T-49)`);
      ok(txt(one('.//cbc:TierRange', l)) === (it.isc?.sistema ?? ''), `${fila}: sistema ISC distinto del JSON (T-51)`);
      ok(igual(num(one('cac:TaxTotal/cbc:TaxAmount', l)), Number(it.totalImpuestos)), `${fila}: total impuestos distinto del JSON (T-55)`);
    });
  }

  const tercero = terceros.has(file);
  const estado = errores.length ? (tercero ? '⚠' : '✗') : '✓';
  const nota = equivalentes[file] ? ' (incluye cruce con JSON)' : tercero ? ' (ejemplo de terceros, solo informativo)' : '';
  console.log(`${estado} ${file}: ${checks - errores.length}/${checks} verificaciones SUNAT${nota}`);
  for (const e of errores) console.log(`   ${tercero ? '⚠' : '✗'} ${e}`);
  for (const a of avisos) console.log(`   ⚠ ${a}`);
  if (!tercero) totalErrores += errores.length;
}
process.exit(totalErrores ? 1 : 0);
