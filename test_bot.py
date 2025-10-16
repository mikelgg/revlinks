#!/usr/bin/env python3
# -*- coding: utf-8 -*-

print("Iniciando bot...")

try:
    from telegram import Update
    print("✓ Telegram importado correctamente")
except ImportError as e:
    print(f"✗ Error importando telegram: {e}")
    exit(1)

try:
    import requests
    print("✓ Requests importado correctamente")
except ImportError as e:
    print(f"✗ Error importando requests: {e}")
    exit(1)

print("Todas las librerías están disponibles")

# Importar y ejecutar el bot principal
try:
    import sys
    import os
    
    # Añadir el directorio actual al path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Importar el bot
    from bot import main
    print("Bot importado correctamente, iniciando...")
    main()
    
except Exception as e:
    print(f"Error ejecutando el bot: {e}")
    import traceback
    traceback.print_exc()
