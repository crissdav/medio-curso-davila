// Validación del entregable Spec-First:
//  1. JSON Schemas compilan y los ejemplos los cumplen.
//  2. Los catálogos cumplen su esquema y coinciden con los enums de common.schema.json.
//  3. El ejemplo de factura cuadra con las reglas de cálculo de SPEC-003.
//  4. La matriz de trazabilidad solo usa rutas DTO y códigos de catálogo existentes.
//  5. Las reglas citadas (SPEC-nnn R-nn / M-nn) existen y los enlaces relativos resuelven.
import { readFileSync, readdirSync, existsSync, statSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const p = (...s) => join(root, ...s);
const readJson = (f) => JSON.parse(readFileSync(f, 'utf8'));

const errors = [];
const warnings = [];
let checks = 0;
const ok = (cond, msg) => { checks++; if (!cond) errors.push(msg); };

// ---------- 1. Schemas y ejemplos ----------
const ajv = new Ajv2020({ allErrors: true, strict: true, strictRequired: false, strictTypes: false });
addFormats(ajv);
const schemaDir = p('specs', 'schemas');
const schemas = {};
for (const f of readdirSync(schemaDir).filter((f) => f.endsWith('.schema.json'))) {
  schemas[f] = readJson(join(schemaDir, f));
  ajv.addSchema(schemas[f]);
}
const base = 'https://abc-software.pe/specs/schemas/';
for (const f of Object.keys(schemas)) {
  try { ajv.getSchema(base + f); checks++; } catch (e) { errors.push(`Schema ${f} no compila: ${e.message}`); }
}

const examples = [
  ['factura-request.json', 'comprobante.schema.json#/$defs/EmitirComprobanteRequest'],
  ['factura-response.json', 'comprobante.schema.json#/$defs/Comprobante'],
  ['nota-credito-request.json', 'nota.schema.json'],
  ['legacy-movimiento.json', 'legacy-movimiento.schema.json'],
  ['movimiento-inventario.json', 'movimiento-inventario.schema.json'],
];
for (const [file, ref] of examples) {
  const validate = ajv.getSchema(base + ref);
  const valid = validate(readJson(join(schemaDir, 'examples', file)));
  ok(valid, `Ejemplo ${file} no cumple ${ref}: ${ajv.errorsText(validate.errors)}`);
}

// Casos negativos: el esquema DEBE rechazarlos.
const req = readJson(join(schemaDir, 'examples', 'factura-request.json'));
const emitir = ajv.getSchema(base + 'comprobante.schema.json#/$defs/EmitirComprobanteRequest');
const negativos = [
  ['factura con cliente DNI', { ...req, cliente: { tipoDocumento: '1', numeroDocumento: '12345678', razonSocial: 'X' } }],
  ['factura con serie B', { ...req, serie: 'B001' }],
  ['USD sin tipo de cambio', { ...req, moneda: 'USD' }],
  ['crédito sin cuotas', { ...req, formaPago: { tipo: 'Credito' } }],
  ['ISC sistema 02 sin monto fijo', { ...req, items: [{ ...req.items[1], isc: { sistema: '02' } }] }],
  ['afectación inexistente 99', { ...req, items: [{ ...req.items[0], afectacionIgv: '99' }] }],
  ['monto como number', { ...req, items: [{ ...req.items[0], valorUnitario: 20 }] }],
];
for (const [nombre, dato] of negativos) ok(!emitir(dato), `El esquema debió rechazar: ${nombre}`);
const notaSchema = ajv.getSchema(base + 'nota.schema.json');
const nc = readJson(join(schemaDir, 'examples', 'nota-credito-request.json'));
ok(!notaSchema({ ...nc, tipoComprobante: '08', tipoNota: '05' }), 'El esquema debió rechazar ND con tipoNota 05 (no existe en catálogo 10)');

// ---------- 2. Catálogos ----------
const catDir = p('specs', 'catalogos');
const catalogos = {};
const catValidate = ajv.getSchema(base + 'catalogo.schema.json');
for (const f of readdirSync(catDir).filter((f) => f.endsWith('.json'))) {
  const c = readJson(join(catDir, f));
  ok(catValidate(c), `Catálogo ${f} inválido: ${ajv.errorsText(catValidate.errors)}`);
  catalogos[c.numero] = new Set(c.codigos.map((x) => x.codigo));
}
const defs = schemas['common.schema.json'].$defs;
const sameSet = (enumArr, set) => enumArr.length === set.size && enumArr.every((x) => set.has(x));
for (const [def, cat] of [['AfectacionIgv', '07'], ['SistemaIsc', '08'], ['TipoDocumentoIdentidad', '06'], ['Moneda', '02'], ['UnidadMedida', '03'], ['TipoOperacion', '51']]) {
  ok(sameSet(defs[def].enum, catalogos[cat]), `Enum ${def} no coincide con catálogo ${cat}`);
}
const notaThen = schemas['nota.schema.json'].allOf.map((a) => a.then.properties.tipoNota.enum);
ok(sameSet(notaThen[0], catalogos['09']), 'Enum tipoNota (07) no coincide con catálogo 09');
ok(sameSet(notaThen[1], catalogos['10']), 'Enum tipoNota (08) no coincide con catálogo 10');
const afectacion = readJson(join(catDir, 'cat-07-afectacion-igv.json'));
for (const c of afectacion.codigos) ok(catalogos['05'].has(c.tributo), `Catálogo 07 código ${c.codigo} apunta a tributo inexistente ${c.tributo}`);

// ---------- 3. Aritmética de SPEC-003 sobre el ejemplo ----------
const TASA_IGV = 0.18, ICBPER = 0.5;
const r2 = (x) => Math.round((x + Number.EPSILON) * 100) / 100;
const f2 = (x) => r2(x).toFixed(2);
const resp = readJson(join(schemaDir, 'examples', 'factura-response.json'));
let sumValor = 0, sumIsc = 0, sumBaseIgv = 0, sumIgvLineas = 0, sumIcbper = 0, sumImpuestos = 0;
for (const l of resp.items) {
  const cant = Number(l.cantidad), vu = Number(l.valorUnitario);
  const valorVenta = r2(cant * vu - Number(l.descuento ?? 0));
  let isc = 0;
  if (l.isc?.sistema === '01') isc = r2(valorVenta * Number(l.isc.tasa));
  if (l.isc?.sistema === '02') isc = r2(cant * Number(l.isc.montoFijo));
  if (l.isc?.sistema === '03') isc = r2(cant * (Number(l.isc.precioVentaPublico) / (1 + TASA_IGV)) * Number(l.isc.tasa));
  const baseIgv = r2(valorVenta + isc);
  const igv = ['10', '17'].includes(l.afectacionIgv) ? r2(baseIgv * TASA_IGV) : 0;
  const icbper = r2((l.cantidadBolsasIcbper ?? 0) * ICBPER);
  const linea = `línea ${l.numeroLinea}`;
  ok(l.valorVenta === f2(valorVenta), `${linea}: valorVenta ${l.valorVenta} ≠ ${f2(valorVenta)} (SPEC-003 R-01)`);
  ok(l.montoIsc === f2(isc), `${linea}: montoIsc ${l.montoIsc} ≠ ${f2(isc)} (SPEC-003 R-02)`);
  ok(l.baseIgv === f2(baseIgv), `${linea}: baseIgv ${l.baseIgv} ≠ ${f2(baseIgv)} (SPEC-003 R-03)`);
  ok(l.igv === f2(igv), `${linea}: igv ${l.igv} ≠ ${f2(igv)} (SPEC-003 R-04)`);
  ok(l.icbper === f2(icbper), `${linea}: icbper ${l.icbper} ≠ ${f2(icbper)} (SPEC-003 R-06)`);
  ok(l.totalImpuestos === f2(isc + igv + icbper), `${linea}: totalImpuestos ${l.totalImpuestos} ≠ ${f2(isc + igv + icbper)}`);
  const pu = (valorVenta + isc + igv) / cant;
  ok(Math.abs(Number(l.precioUnitario) - pu) < 0.0001, `${linea}: precioUnitario ${l.precioUnitario} ≠ ${pu} (SPEC-003 R-08)`);
  sumValor += valorVenta; sumIsc += isc; sumBaseIgv += baseIgv; sumIgvLineas += igv; sumIcbper += icbper; sumImpuestos += isc + igv + icbper;
}
const t = resp.totales;
const igvGlobal = r2(sumBaseIgv * TASA_IGV);
ok(t.totalGravadas === f2(sumValor), `totalGravadas ${t.totalGravadas} ≠ ${f2(sumValor)}`);
ok(t.totalIsc === f2(sumIsc), `totalIsc ${t.totalIsc} ≠ ${f2(sumIsc)}`);
ok(t.totalIgv === f2(igvGlobal), `totalIgv ${t.totalIgv} ≠ ${f2(igvGlobal)} (SPEC-003 R-09)`);
ok(Math.abs(igvGlobal - sumIgvLineas) <= 1, 'Σ IGV de líneas difiere del IGV global en más de 1.00 (SPEC-003 R-09)');
ok(t.totalIcbper === f2(sumIcbper), `totalIcbper ${t.totalIcbper} ≠ ${f2(sumIcbper)}`);
ok(t.totalImpuestos === f2(sumIsc + igvGlobal + sumIcbper), `totalImpuestos ${t.totalImpuestos} incorrecto`);
ok(t.importeTotal === f2(sumValor + sumIsc + igvGlobal + sumIcbper), `importeTotal ${t.importeTotal} ≠ ${f2(sumValor + sumIsc + igvGlobal + sumIcbper)} (INV-04)`);
ok(t.totalPrecioVenta === t.importeTotal, 'totalPrecioVenta debe igualar importeTotal sin descuentos ni cargos');

// RUC módulo 11 (SPEC-004 R-01) sobre los RUC de los ejemplos.
const rucValido = (ruc) => {
  if (!/^(10|15|16|17|20)\d{9}$/.test(ruc)) return false;
  const pesos = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2];
  const suma = pesos.reduce((s, w, i) => s + w * Number(ruc[i]), 0);
  let dv = 11 - (suma % 11);
  if (dv === 10) dv = 0;
  if (dv === 11) dv = 1;
  return dv === Number(ruc[10]);
};
ok(rucValido(resp.emisor.ruc), `RUC emisor ${resp.emisor.ruc} no pasa módulo 11`);
ok(rucValido(resp.cliente.numeroDocumento), `RUC cliente ${resp.cliente.numeroDocumento} no pasa módulo 11`);
ok(rucValido('20123456786') && !rucValido('20123456787') && !rucValido('30123456786'), 'Casos de SPEC-004 AC-1/AC-2 no se cumplen');

// ---------- 4. Matriz de trazabilidad ----------
const roots = {
  Comprobante: { file: 'comprobante.schema.json', ptr: '#/$defs/Comprobante' },
  Nota: { file: 'nota.schema.json', ptr: '#' },
  Producto: { file: 'producto.schema.json', ptr: '#' },
  Cdr: { file: 'respuesta-cdr.schema.json', ptr: '#' },
  MovimientoInventario: { file: 'movimiento-inventario.schema.json', ptr: '#' },
};
const deref = (file, ptr) => {
  let node = schemas[file];
  for (const seg of ptr.replace(/^#\/?/, '').split('/').filter(Boolean)) node = node[seg];
  return { file, node };
};
const follow = ({ file, node }) => {
  if (node?.$ref) {
    const [f, ptr = ''] = node.$ref.split('#');
    return follow(deref(f || file, '#' + ptr));
  }
  return { file, node };
};
// Devuelve las propiedades visibles de un nodo (sigue $ref y allOf).
const propsOf = (ctx) => {
  const { file, node } = follow(ctx);
  const out = {};
  for (const [k, v] of Object.entries(node.properties ?? {})) out[k] = { file, node: v };
  for (const sub of node.allOf ?? []) Object.assign(out, propsOf({ file, node: sub }));
  return out;
};
const resolvePath = (path) => {
  const [rootName, ...segs] = path.split('.');
  if (!roots[rootName]) return false;
  let ctx = deref(roots[rootName].file, roots[rootName].ptr);
  for (const raw of segs) {
    const isArray = raw.endsWith('[]');
    const name = raw.replace('[]', '');
    const props = propsOf(ctx);
    if (!props[name]) return false;
    ctx = props[name];
    if (isArray) ctx = { file: follow(ctx).file, node: follow(ctx).node.items };
  }
  return true;
};
const matriz = readFileSync(p('docs', '05-matriz-trazabilidad.md'), 'utf8');
const filas = matriz.split('\n').filter((l) => /^\| \**T-\d{2}/.test(l));
ok(filas.length >= 50, `La matriz tiene solo ${filas.length} filas T-nn`);
const ids = new Set();
for (const fila of filas) {
  const cols = fila.split(' | ');
  const id = cols[0].replace(/[|* ]/g, '');
  ok(!ids.has(id), `Fila duplicada en la matriz: ${id}`);
  ids.add(id);
  for (const m of cols[2].matchAll(/`cat-(\d{2}):([^`]+)`/g)) {
    ok(catalogos[m[1]]?.has(m[2]), `${id}: código cat-${m[1]}:${m[2]} no existe en specs/catalogos`);
  }
  for (const m of cols[5].matchAll(/`([A-Za-z]+\.[A-Za-z.\[\]]+)`/g)) {
    ok(resolvePath(m[1]), `${id}: ruta DTO ${m[1]} no existe en los JSON Schemas`);
  }
  ok(/^\d{3}$/.test(cols[6].replace(/[| ]/g, '')), `${id}: spec inválida "${cols[6]}"`);
}
// Cobertura (advertencias): hojas del Comprobante sin fila en la matriz.
// Campos justificados en la sección 10 de la matriz; `cdr.*` se cubre con las filas Cdr (T-70…T-72).
const sinUbl = new Set(['id', 'estado', 'correlativo', 'serie', 'ubigeo', 'correo', 'montoFijo', 'precioVentaPublico', 'totalExportacion']);
const subarbolesSinUbl = ['cdr.', 'enlaces.'];
const usados = new Set([...matriz.matchAll(/`Comprobante\.([A-Za-z.\[\]]+)`/g)].map((m) => m[1].split('.').pop().replace('[]', '')));
const hojas = (ctx, prefix, depth = 0) => {
  if (depth > 4) return [];
  return Object.entries(propsOf(ctx)).flatMap(([k, v]) => {
    const n = follow(v).node;
    if (n.type === 'array' && n.items) return hojas({ file: follow(v).file, node: n.items }, `${prefix}${k}[].`, depth + 1);
    if (n.properties || n.allOf) return hojas(v, `${prefix}${k}.`, depth + 1);
    return [`${prefix}${k}`];
  });
};
for (const h of hojas(deref('comprobante.schema.json', '#/$defs/Comprobante'), '')) {
  const leaf = h.split('.').pop().replace('[]', '');
  if (subarbolesSinUbl.some((s) => h.startsWith(s))) continue;
  if (!usados.has(leaf) && !sinUbl.has(leaf)) warnings.push(`Campo Comprobante.${h} sin fila en la matriz`);
}

// ---------- 5. Referencias a reglas y enlaces ----------
const mdFiles = [];
const walk = (dir) => {
  for (const f of readdirSync(dir)) {
    if (f === 'node_modules' || f.startsWith('.')) continue;
    const full = join(dir, f);
    if (statSync(full).isDirectory()) walk(full);
    else if (f.endsWith('.md')) mdFiles.push(full);
  }
};
walk(root);
const specFiles = Object.fromEntries(readdirSync(p('specs', 'features')).map((f) => [f.slice(0, 3), readFileSync(p('specs', 'features', f), 'utf8')]));
for (const file of mdFiles) {
  const text = readFileSync(file, 'utf8');
  for (const m of text.matchAll(/SPEC-(\d{3})(?:\/| )([RM]-\d{2})/g)) {
    ok(specFiles[m[1]]?.includes(`| ${m[2]} |`), `${file.replace(root, '')}: referencia a SPEC-${m[1]} ${m[2]} inexistente`);
  }
  for (const m of text.matchAll(/\]\(([^)#\s]+)(#[^)]*)?\)/g)) {
    if (/^(https?:|mailto:)/.test(m[1])) continue;
    ok(existsSync(resolve(dirname(file), m[1])), `${file.replace(root, '')}: enlace roto → ${m[1]}`);
  }
}
for (const [num, text] of Object.entries(specFiles)) {
  ok(/\*\*AC-1:\*\*/.test(text), `SPEC-${num} sin criterios de aceptación`);
}
// Las referencias a reglas desde los esquemas y openapi también deben existir.
for (const f of [...Object.keys(schemas).map((s) => join(schemaDir, s)), p('specs', 'api', 'openapi.yaml')]) {
  for (const m of readFileSync(f, 'utf8').matchAll(/SPEC-(\d{3})\/([RM]-\d{2})/g)) {
    ok(specFiles[m[1]]?.includes(`| ${m[2]} |`), `${f.replace(root, '')}: referencia a SPEC-${m[1]}/${m[2]} inexistente`);
  }
}

// ---------- Resultado ----------
for (const w of warnings) console.warn(`⚠  ${w}`);
if (errors.length) {
  for (const e of errors) console.error(`✗ ${e}`);
  console.error(`\n${errors.length} error(es) en ${checks} verificaciones.`);
  process.exit(1);
}
console.log(`✓ ${checks} verificaciones correctas (${filas.length} filas de matriz, ${mdFiles.length} documentos, ${Object.keys(schemas).length} esquemas, ${Object.keys(catalogos).length} catálogos).`);
