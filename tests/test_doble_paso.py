#!/usr/bin/env python3
"""Pruebas del flujo de doble paso. Sin red, sin Telegram: pura lógica.

Ejecuta:  python3 tests/test_doble_paso.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.security import doble_paso as dp  # noqa: E402

CHAT = 8247886073
OTRO_CHAT = 111111

correctas = 0
fallidas = 0


def comprobar(nombre: str, condicion: bool, extra: str = "") -> None:
    global correctas, fallidas
    if condicion:
        correctas += 1
        print(f"  OK     {nombre}")
    else:
        fallidas += 1
        print(f"  FALLA  {nombre} {extra}")


def reinicio() -> None:
    dp.reiniciar_para_pruebas()
    os.environ["KYNIKOS_PALABRA_1"] = "kalpixk-abre"
    os.environ.pop("KYNIKOS_PALABRA_2", None)


print("\n1. Falla cerrado sin configuración")
dp.reiniciar_para_pruebas()
os.environ.pop("KYNIKOS_PALABRA_1", None)
comprobar("sin palabra configurada, configurado() es False", dp.configurado() is False)
try:
    dp.solicitar(CHAT)
    comprobar("solicitar() debe negarse", False)
except dp.ErrorDoblePaso:
    comprobar("solicitar() se niega sin configuración", True)

print("\n2. Detección de la palabra clave")
reinicio()
comprobar("reconoce la palabra", dp.detectar_primer_paso("kalpixk-abre"))
comprobar("reconoce con mayúsculas y espacios", dp.detectar_primer_paso("  KALPIXK-ABRE  "))
comprobar("rechaza otra palabra", dp.detectar_primer_paso("kalpixk-otra") is False)
comprobar("rechaza texto vacío", dp.detectar_primer_paso("") is False)

print("\n3. Una sola notificación por chat")
reinicio()
sol1, nueva1 = dp.solicitar(CHAT)
sol2, nueva2 = dp.solicitar(CHAT)
comprobar("la primera es nueva", nueva1 is True)
comprobar("la segunda se reutiliza", nueva2 is False)
comprobar("es la misma solicitud", sol1.id == sol2.id)

print("\n4. Emisión de la palabra y formato")
palabra, expira = dp.autorizar(sol1.id, CHAT)
import re
comprobar("formato KALPIXK-XXXX-XXXX", bool(re.fullmatch(r"KALPIXK-[0-9A-F]{4}-[0-9A-F]{4}", palabra)), palabra)
comprobar("longitud de 17 caracteres", len(palabra) == 17, str(len(palabra)))
comprobar("caduca en 5 minutos", abs((expira - time.time()) - dp.VIDA_PALABRA) < 3)
comprobar("se guarda solo el hash", dp._estado.solicitudes[sol1.id].hash_palabra != palabra)

print("\n5. Verificación y un solo uso")
comprobar("acepta la palabra correcta", dp.verificar(palabra) is True)
comprobar("rechaza la reutilización", dp.verificar(palabra) is False)
comprobar("estado final consumida", dp._estado.solicitudes[sol1.id].estado == "consumida")

print("\n6. Solicitud ajena no autoriza")
reinicio()
sol, _ = dp.solicitar(CHAT)
try:
    dp.autorizar(sol.id, OTRO_CHAT)
    comprobar("otro chat no debe autorizar", False)
except dp.ErrorDoblePaso:
    comprobar("otro chat no puede autorizar", True)

print("\n7. Rechazo explícito")
reinicio()
sol, _ = dp.solicitar(CHAT)
dp.rechazar(sol.id, CHAT)
try:
    dp.autorizar(sol.id, CHAT)
    comprobar("rechazada no debe emitir palabra", False)
except dp.ErrorDoblePaso:
    comprobar("rechazada no emite palabra", True)

print("\n8. Caducidad de la solicitud (2 minutos)")
reinicio()
sol, _ = dp.solicitar(CHAT)
dp._estado.solicitudes[sol.id].creada = time.time() - (dp.TTL_SOLICITUD + 5)
try:
    dp.autorizar(sol.id, CHAT)
    comprobar("expirada no debe autorizar", False)
except dp.ErrorDoblePaso:
    comprobar("la ventana vencida no autoriza", True)

print("\n9. Caducidad de la palabra emitida (5 minutos)")
reinicio()
sol, _ = dp.solicitar(CHAT)
palabra, _ = dp.autorizar(sol.id, CHAT)
dp._estado.solicitudes[sol.id].emitida = time.time() - (dp.VIDA_PALABRA + 5)
comprobar("palabra vencida no verifica", dp.verificar(palabra) is False)

print("\n10. Freno anti fuerza bruta")
reinicio()
for _ in range(dp.MAX_INTENTOS):
    dp.verificar("KALPIXK-0000-0000")
comprobar("se activa el bloqueo", dp.estado_publico()["bloqueado"] is True)
sol, _ = dp.solicitar(CHAT) if False else (None, None)
try:
    dp.solicitar(CHAT)
    comprobar("bloqueado no debe permitir solicitar", False)
except dp.ErrorDoblePaso:
    comprobar("bloqueado impide nuevas solicitudes", True)

print("\n11. La auditoría no filtra la palabra")
reinicio()
sol, _ = dp.solicitar(CHAT)
palabra, _ = dp.autorizar(sol.id, CHAT)
dp.verificar(palabra)
volcado = str(dp.estado_publico()["auditoria"])
comprobar("la palabra no aparece en la auditoría", palabra not in volcado)
comprobar("la auditoría registra el ciclo", "verificada" in volcado and "autorizada" in volcado)

print("\n12. Palabra sin configurar el segundo paso por entorno no rompe")
reinicio()
comprobar("el flujo no depende de KYNIKOS_PALABRA_2", dp.configurado() is True)

print(f"\n{'=' * 46}")
print(f"correctas: {correctas} | fallidas: {fallidas}")
sys.exit(0 if fallidas == 0 else 1)
