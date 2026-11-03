//! Buscador local de KYNIKOS en WebAssembly.
//!
//! Vive en el navegador: indexa el histórico del propio bot y responde sin red.
//! Si el módulo no está compilado, la PWA usa el respaldo en JavaScript con la
//! misma firma, así que la interfaz nunca se rompe.

use wasm_bindgen::prelude::*;

/// Puntúa un documento contra los términos de la consulta.
/// Cuenta apariciones y premia coincidencias en el inicio del texto.
fn puntuar(documento: &str, terminos: &[&str]) -> u32 {
    let texto = documento.to_lowercase();
    let mut total: u32 = 0;
    for termino in terminos {
        let t = termino.trim();
        if t.is_empty() {
            continue;
        }
        let mut apariciones = 0u32;
        let mut desde = 0usize;
        while let Some(pos) = texto[desde..].find(t) {
            apariciones += 1;
            desde += pos + t.len();
            if apariciones >= 8 {
                break;
            }
        }
        if apariciones > 0 {
            total += apariciones * 3;
            if texto.starts_with(t) {
                total += 5;
            }
        }
    }
    total
}

/// Devuelve índices de los documentos relevantes, ordenados por puntuación.
/// `limite` acota cuántos resultados se devuelven.
#[wasm_bindgen]
pub fn buscar(consulta: &str, documentos: Vec<String>, limite: usize) -> Vec<usize> {
    let terminos: Vec<&str> = consulta.split_whitespace().collect();
    let mut puntuados: Vec<(usize, u32)> = documentos
        .iter()
        .enumerate()
        .map(|(i, d)| (i, puntuar(d, &terminos)))
        .filter(|(_, p)| *p > 0)
        .collect();
    puntuados.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(&b.0)));
    puntuados.into_iter().take(limite.max(1)).map(|(i, _)| i).collect()
}

/// Versión informativa, para que la PWA confirme que cargó el módulo real.
#[wasm_bindgen]
pub fn version() -> String {
    "wasm-busqueda 0.1.0".to_string()
}
