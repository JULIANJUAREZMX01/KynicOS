"""
KynicOS — Skill: HVAC Triage
Diagnóstico técnico de sistemas de aire acondicionado (Fan & Coil)
Basado en manuales Carrier/Trane/York. Diferenciador clave vs competencia.
"""

from typing import Dict, List, Tuple


# Base de conocimiento de síntomas → diagnóstico
HVAC_KNOWLEDGE_BASE: Dict[str, Dict] = {
    "no_enfria": {
        "descripcion": "El AC no enfría / aire caliente",
        "diagnostico": [
            "🔍 **Filtro saturado** (causa más común) — requiere limpieza, 30 min",
            "🔍 **Refrigerante bajo** — requiere técnico certificado",
            "🔍 **Compresor falla** — emergencia, suite sin servicio",
        ],
        "preguntas_diagnostico": [
            "¿Desde hace cuánto tiempo?",
            "¿El aire sale pero sin frío, o no sale nada de aire?",
            "¿Hay un sonido raro o el equipo simplemente no enfría?",
        ],
        "prioridad": "media",
        "eta_minutos": 30,
    },
    "ruido_raro": {
        "descripcion": "Sonido extraño en el AC",
        "diagnostico": [
            "🔧 **Paletas del fan golpeando** — ajuste menor, 15 min",
            "🔧 **Vibración del compresor** — puede indicar falla inminente",
            "🔧 **Bloque de hielo en evaporador** — filtro muy sucio",
        ],
        "preguntas_diagnostico": [
            "¿El sonido es: traqueteo, silbido, o zumbido eléctrico?",
            "¿Ocurre solo al encender o constantemente?",
        ],
        "prioridad": "baja",
        "eta_minutos": 45,
    },
    "gotea_agua": {
        "descripcion": "El AC gotea agua / derrame",
        "diagnostico": [
            "💧 **Drenaje tapado** — limpieza inmediata para evitar daños",
            "💧 **Bandeja de condensados llena** — vaciado rutinario",
            "💧 **Exceso de humedad** — normal en Cancún, ajustar temperatura",
        ],
        "preguntas_diagnostico": [
            "¿El agua sale por el frente del equipo o por la pared/techo?",
            "¿Es poca (goteo) o mucha agua?",
        ],
        "prioridad": "alta",
        "eta_minutos": 20,
    },
    "no_enciende": {
        "descripcion": "El AC no enciende / sin respuesta al control",
        "diagnostico": [
            "⚡ **Control remoto sin batería** — reemplazar pilas (auto-soluble)",
            "⚡ **Breaker disparado** — reset en tablero eléctrico del cuarto",
            "⚡ **Falla de tarjeta electrónica** — técnico especializado",
        ],
        "preguntas_diagnostico": [
            "¿El display del equipo enciende aunque sea?",
            "¿El control remoto tiene el indicador de batería activo?",
        ],
        "prioridad": "alta",
        "eta_minutos": 15,
    },
    "temperatura_no_baja": {
        "descripcion": "El AC funciona pero no llega a la temperatura deseada",
        "diagnostico": [
            "🌡️ **Filtro semisaturado** — limpieza mejora eficiencia 30-40%",
            "🌡️ **Carga de cuarto alta** — ventanas con sol directo, muchas personas",
            "🌡️ **Refrigerante parcialmente bajo** — carga menor de gas",
        ],
        "preguntas_diagnostico": [
            "¿A qué temperatura lo tienes configurado?",
            "¿El cuarto tiene ventanas y están cerradas?",
            "¿Cuántas personas hay en el cuarto?",
        ],
        "prioridad": "baja",
        "eta_minutos": 60,
    }
}

# Mapa de palabras clave → síntoma
KEYWORD_MAP = {
    "no enfría": "no_enfria",
    "no enfriar": "no_enfria",
    "aire caliente": "no_enfria",
    "calor": "no_enfria",
    "no funciona el aire": "no_enfria",
    "ruido": "ruido_raro",
    "sonido": "ruido_raro",
    "hace ruido": "ruido_raro",
    "gotea": "gotea_agua",
    "agua": "gotea_agua",
    "gotear": "gotea_agua",
    "derrame": "gotea_agua",
    "no enciende": "no_enciende",
    "no prende": "no_enciende",
    "no funciona": "no_enciende",
    "apagado": "no_enciende",
    "temperatura": "temperatura_no_baja",
    "no baja": "temperatura_no_baja",
    "no llega": "temperatura_no_baja",
}


def detect_hvac_issue(message: str) -> Tuple[str, Dict]:
    """
    Detecta si el mensaje describe un problema de HVAC.
    Retorna (symptom_key, knowledge_entry) o (None, None)
    """
    msg_lower = message.lower()
    
    # Verificar si el mensaje es sobre el AC
    hvac_keywords = ["aire", "ac", "a/c", "clima", "acondicionado", "frio", "frío", "cooling", "hvac"]
    is_hvac = any(kw in msg_lower for kw in hvac_keywords)
    
    if not is_hvac:
        return None, None
    
    # Buscar síntoma específico
    for keyword, symptom_key in KEYWORD_MAP.items():
        if keyword in msg_lower:
            return symptom_key, HVAC_KNOWLEDGE_BASE[symptom_key]
    
    # AC mencionado pero síntoma no claro
    return "unknown", {
        "descripcion": "Problema con el aire acondicionado",
        "diagnostico": ["Necesito más detalles para diagnosticar"],
        "preguntas_diagnostico": [
            "¿El AC no enfría, hace ruido, gotea agua, o no enciende?",
        ],
        "prioridad": "media",
        "eta_minutos": 30,
    }


def generate_hvac_response(symptom_key: str, issue_data: Dict, room: str = "su habitación") -> str:
    """Genera respuesta de Leo al reporte técnico de HVAC"""
    
    if symptom_key == "unknown":
        return (
            f"Recibí tu reporte del AC en {room}. 🔧\n\n"
            f"{issue_data['preguntas_diagnostico'][0]}\n\n"
            "Dame un poco más de detalle y aviso al técnico de inmediato."
        )
    
    diagnostico_principal = issue_data["diagnostico"][0]
    prioridad = issue_data["prioridad"]
    eta = issue_data["eta_minutos"]
    
    if prioridad == "alta":
        urgencia_txt = "🔴 *Prioridad alta* — Técnico en camino"
    elif prioridad == "media":
        urgencia_txt = "🟡 *Prioridad media* — Asignando técnico"
    else:
        urgencia_txt = "🟢 Registro creado — Revisión programada"
    
    return (
        f"Recibí tu reporte: _{issue_data['descripcion']}_ en {room}.\n\n"
        f"{urgencia_txt}\n"
        f"ETA estimado: **{eta} minutos**\n\n"
        f"Diagnóstico probable: {diagnostico_principal}\n\n"
        f"¿Mientras tanto, puedo ofrecerte cambio de habitación?"
    )


def get_ticket_priority(symptom_key: str) -> str:
    """Retorna prioridad para el ticket de mantenimiento"""
    if symptom_key not in HVAC_KNOWLEDGE_BASE:
        return "media"
    return HVAC_KNOWLEDGE_BASE[symptom_key].get("prioridad", "media")
