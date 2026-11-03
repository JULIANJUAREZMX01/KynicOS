# kynikos · instalación por comandos

Un ejecutable, sin dependencias, para dejar cualquier computadora como nodo del bot.
Detecta el hardware real y elige el modelo que **cabe y se puede usar**, no el más grande.

```bash
python3 cli/kynikos.py doctor      # qué tiene esta máquina y qué modelo le toca
python3 cli/kynikos.py plan        # .env sugerido, sin tocar nada
python3 cli/kynikos.py init        # escribe .env (token enmascarado, permisos 600)
python3 cli/kynikos.py telegram    # estado del bot y del webhook
python3 cli/kynikos.py install     # Ollama + dependencias (--si para ejecutar sin preguntar)
python3 cli/kynikos.py run         # arranca el nodo
python3 cli/kynikos.py status      # salud local
python3 cli/kynikos.py models      # modelos instalados y recomendación
python3 cli/kynikos.py config      # ver o cambiar .env (clave=valor)
python3 cli/kynikos.py service     # unidad systemd o tarea de Windows
```

## Criterio de selección

Elige el modelo más grande que quepa en la memoria útil **y** rinda al menos
4 tokens por segundo. Por debajo de esa velocidad la conversación se siente rota
aunque el modelo quepa. El comando `doctor` muestra además el techo absoluto:
el mayor que cabe, se use o no.

## Telegram

Telegram permite un solo método de recepción por bot. Si `telegram` reporta un
webhook activo, el nodo no puede usar polling:

```bash
python3 cli/kynikos.py telegram --liberar          # quita el webhook (solo si ese bot no lo ocupa otro servicio)
python3 cli/kynikos.py telegram --webhook https://mi-nodo  # registra el nodo como destino
```

Nunca imprime tokens: los enmascara siempre.
