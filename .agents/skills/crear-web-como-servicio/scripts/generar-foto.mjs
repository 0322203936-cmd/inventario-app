#!/usr/bin/env node
// Generador de fotos de producto con OpenAI gpt-image-2 (julio 2026).
// Multiplataforma (Windows/Mac). Requiere Node 18+ (fetch/FormData nativos).
//
// Uso:
//   node generar-foto.mjs --clave clave-openai.txt --prompt "..." --salida foto.jpg
//        [--ref original1.jpg] [--ref original2.jpg] ...   (hasta 16 referencias)
//        [--calidad low|medium|high|auto] [--tamano 2048x1152] [--formato jpeg|png|webp]
//        [--n 1..10] [--mascara zona.png]
//
// - Con --ref usa /v1/images/edits (fiel al producto real); sin --ref, /v1/images/generations.
// - --tamano acepta cualquier ANCHOxALTO valido para gpt-image-2 (lados multiplos de 16,
//   lado mayor <= 3840, ratio <= 3:1, pixeles totales entre 655360 y 8294400).
// - --n genera variaciones del MISMO prompt en una llamada; con n>1 los archivos salen
//   numerados: foto-1.jpg, foto-2.jpg...
// - --mascara adjunta un PNG con canal alfa (mismas dimensiones que la PRIMERA --ref);
//   las zonas transparentes marcan que se repinta. Requiere al menos una --ref.
// Imprime "OK <ruta>" por cada imagen o "ERROR <detalle>". Codigo de salida 0/1.

import fs from "node:fs";
import path from "node:path";

function arg(name, def = null) {
  const i = process.argv.indexOf("--" + name);
  return i > -1 && process.argv[i + 1] ? process.argv[i + 1] : def;
}
function args(name) {
  const out = [];
  for (let i = 0; i < process.argv.length; i++) {
    if (process.argv[i] === "--" + name && process.argv[i + 1]) out.push(process.argv[i + 1]);
  }
  return out;
}

const claveArchivo = arg("clave");
const prompt = arg("prompt");
const salida = arg("salida");
const refs = args("ref");
const calidad = arg("calidad", "medium");
const tamano = arg("tamano", "1024x1024");
const formato = arg("formato", "jpeg");
const n = parseInt(arg("n", "1"), 10);
const mascara = arg("mascara");
const moderacion = arg("moderacion"); // "low" relaja el filtro ante falsos positivos

function fallo(msg) {
  console.error("ERROR " + msg);
  process.exit(1);
}

if (!claveArchivo || !prompt || !salida) {
  fallo("faltan argumentos obligatorios: --clave, --prompt, --salida");
}
if (!fs.existsSync(claveArchivo)) fallo("no existe el archivo de clave: " + claveArchivo);
const apiKey = fs.readFileSync(claveArchivo, "utf8").trim();
if (!apiKey.startsWith("sk-")) fallo("la clave del archivo no parece valida (debe empezar por sk-)");
for (const r of refs) if (!fs.existsSync(r)) fallo("no existe la imagen de referencia: " + r);
if (refs.length > 16) fallo("maximo 16 imagenes de referencia por llamada (hay " + refs.length + ")");
if (!Number.isInteger(n) || n < 1 || n > 10) fallo("--n debe ser un entero entre 1 y 10");
if (mascara) {
  if (refs.length === 0) fallo("--mascara requiere al menos una --ref (la foto a retocar va primero)");
  if (!fs.existsSync(mascara)) fallo("no existe la mascara: " + mascara);
  if (path.extname(mascara).toLowerCase() !== ".png") fallo("la mascara debe ser un PNG con canal alfa");
}

const MIME = { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp" };

// Ruta de salida para la imagen i (0-based) cuando n > 1: foto.jpg -> foto-1.jpg
function rutaSalida(i) {
  if (n === 1) return salida;
  const ext = path.extname(salida);
  const base = salida.slice(0, salida.length - ext.length);
  return base + "-" + (i + 1) + ext;
}

async function main() {
  let res;
  if (refs.length > 0) {
    // Edicion a partir de referencias (multipart)
    const form = new FormData();
    form.append("model", "gpt-image-2");
    form.append("prompt", prompt);
    form.append("quality", calidad);
    form.append("size", tamano);
    form.append("output_format", formato);
    form.append("n", String(n));
    if (moderacion) form.append("moderation", moderacion);
    for (const r of refs) {
      const mime = MIME[path.extname(r).toLowerCase()] || "image/jpeg";
      form.append("image[]", new Blob([fs.readFileSync(r)], { type: mime }), path.basename(r));
    }
    if (mascara) {
      form.append("mask", new Blob([fs.readFileSync(mascara)], { type: "image/png" }), path.basename(mascara));
    }
    res = await fetch("https://api.openai.com/v1/images/edits", {
      method: "POST",
      headers: { Authorization: "Bearer " + apiKey },
      body: form,
    });
  } else {
    // Generacion desde cero (JSON)
    res = await fetch("https://api.openai.com/v1/images/generations", {
      method: "POST",
      headers: {
        Authorization: "Bearer " + apiKey,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "gpt-image-2",
        prompt,
        quality: calidad,
        size: tamano,
        output_format: formato,
        n,
        ...(moderacion ? { moderation: moderacion } : {}),
      }),
    });
  }

  let data;
  try {
    data = await res.json();
  } catch {
    fallo("respuesta no valida del servidor (HTTP " + res.status + ")");
  }

  if (!res.ok || data.error) {
    const e = data.error || {};
    const code = e.code || res.status;
    let pista = "";
    if (res.status === 401) pista = " — clave incorrecta o caducada: pedir al usuario que la vuelva a pegar";
    else if (res.status === 429 && String(code).includes("insufficient_quota")) pista = " — sin creditos: el usuario debe recargar saldo en platform.openai.com (Billing)";
    else if (res.status === 429) pista = " — limite de ritmo: esperar 30-60 s y reintentar";
    else if (res.status === 400) pista = " — revisar parametros (size: lados multiplos de 16, ratio <= 3:1, pixeles 655360-8294400) o reformular el prompt";
    fallo((e.message || "HTTP " + res.status) + " [" + code + "]" + pista);
  }

  const imagenes = data?.data || [];
  if (!imagenes.length || !imagenes[0].b64_json) fallo("la respuesta no contiene imagen");
  fs.mkdirSync(path.dirname(path.resolve(salida)), { recursive: true });
  imagenes.forEach((img, i) => {
    if (!img.b64_json) return;
    const ruta = rutaSalida(i);
    fs.writeFileSync(ruta, Buffer.from(img.b64_json, "base64"));
    console.log("OK " + ruta);
  });
}

main().catch((e) => fallo(e.message || String(e)));
