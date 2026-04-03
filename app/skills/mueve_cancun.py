"""
KynicOS — Skill: MueveCancún Integration
Cuando el huésped pregunta sobre transporte público, este skill
proporciona información de rutas y enlaza con la PWA.
"""

from typing import Optional, Dict


APP_URL = "https://querutamellevacancun.onrender.com/es/home"

# Rutas más consultadas por turistas
POPULAR_ROUTES = {
    "aeropuerto_centro": {
        "nombre": "Aeropuerto → Centro Cancún",
        "opciones": [
            {"tipo": "ADO", "precio": "$150 MXN", "tiempo": "10 min", "ruta": "R-ADO Aeropuerto"},
            {"tipo": "Autobús urbano", "precio": "$15 MXN", "tiempo": "20 min", "ruta": "R10 Las Américas-Aeropuerto"},
        ]
    },
    "centro_zona_hotelera": {
        "nombre": "Centro → Zona Hotelera",
        "opciones": [
            {"tipo": "Autobús", "precio": "$15 MXN", "tiempo": "30-45 min", "ruta": "R1 / R2"},
        ]
    },
    "aeropuerto_zona_hotelera": {
        "nombre": "Aeropuerto → Zona Hotelera",
        "opciones": [
            {"tipo": "ADO", "precio": "$150 MXN", "tiempo": "15 min", "ruta": "ADO Aeropuerto"},
            {"tipo": "Taxi oficial", "precio": "$250-350 MXN", "tiempo": "10 min", "ruta": "Taxi Aeropuerto"},
        ]
    },
    "zona_hotelera_playa_del_carmen": {
        "nombre": "Zona Hotelera → Playa del Carmen",
        "opciones": [
            {"tipo": "ADO", "precio": "$90-120 MXN", "tiempo": "1h15min", "ruta": "ADO desde Terminal Centro"},
        ]
    },
    "cancun_tulum": {
        "nombre": "Cancún → Tulum",
        "opciones": [
            {"tipo": "ADO", "precio": "$140-200 MXN", "tiempo": "2h", "ruta": "ADO desde Terminal Centro"},
            {"tipo": "Colectivo", "precio": "$60-80 MXN", "tiempo": "2h30min", "ruta": "Colectivo desde Av. Tulum"},
        ]
    },
    "cancun_chichen": {
        "nombre": "Cancún → Chichén Itzá",
        "opciones": [
            {"tipo": "ADO", "precio": "$300-400 MXN", "tiempo": "2h45min", "ruta": "ADO primera clase"},
            {"tipo": "Tour organizado", "precio": "$600-1200 MXN", "tiempo": "día completo", "ruta": "Varias agencias"},
        ]
    }
}

# Keywords para detectar consultas de transporte
TRANSPORT_KEYWORDS = [
    "autobús", "autobus", "bus", "ruta", "transporte", "cómo llego", "como llego",
    "cómo ir", "como ir", "llegar a", "ir a", "taxi", "combi", "ado", "colectivo",
    "moverse", "moverte", "r1", "r2", "r10", "zona hotelera", "aeropuerto",
    "playa del carmen", "tulum", "chichen", "centro cancun"
]


def is_transport_query(message: str) -> bool:
    """Detecta si el mensaje es una consulta de transporte"""
    msg_lower = message.lower()
    return any(kw in msg_lower for kw in TRANSPORT_KEYWORDS)


def get_route_info(message: str) -> Optional[Dict]:
    """Intenta encontrar la ruta más relevante para el mensaje"""
    msg_lower = message.lower()
    
    if "aeropuerto" in msg_lower and ("zona hotelera" in msg_lower or "hotel" in msg_lower):
        return POPULAR_ROUTES["aeropuerto_zona_hotelera"]
    elif "aeropuerto" in msg_lower and "centro" in msg_lower:
        return POPULAR_ROUTES["aeropuerto_centro"]
    elif "tulum" in msg_lower:
        return POPULAR_ROUTES["cancun_tulum"]
    elif "playa del carmen" in msg_lower or "pdp" in msg_lower:
        return POPULAR_ROUTES["zona_hotelera_playa_del_carmen"]
    elif "chichen" in msg_lower or "chichén" in msg_lower:
        return POPULAR_ROUTES["cancun_chichen"]
    elif ("zona hotelera" in msg_lower or "hotel" in msg_lower) and "centro" in msg_lower:
        return POPULAR_ROUTES["centro_zona_hotelera"]
    
    return None


def format_route_response(route_info: Dict, language: str = "es") -> str:
    """Formatea la información de ruta como respuesta de Leo"""
    nombre = route_info["nombre"]
    opciones = route_info["opciones"]
    
    lines = [f"🚌 *{nombre}*\n"]
    
    for op in opciones:
        lines.append(
            f"• *{op['tipo']}* — {op['precio']} | ⏱ {op['tiempo']}\n"
            f"  Ruta: {op['ruta']}"
        )
    
    lines.append(f"\n📱 Para buscar tu ruta exacta:\n{APP_URL}")
    
    return "\n".join(lines)


def get_generic_transport_response() -> str:
    """Respuesta genérica cuando no se detecta ruta específica"""
    return (
        "Para moverte en Cancún sin taxi, el transporte público es muy bueno 🚌\n\n"
        "Las rutas principales cuestan **$13-15 MXN** (menos de $1 USD).\n\n"
        "Dime: ¿de dónde a dónde necesitas ir? También puedes consultar todas las "
        f"rutas en nuestra app gratuita:\n{APP_URL}"
    )
