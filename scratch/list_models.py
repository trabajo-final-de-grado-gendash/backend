import os
from dotenv import load_dotenv
from google import genai

# Intentar cargar .env desde varios niveles arriba si es necesario
load_dotenv()
if not os.getenv("GEMINI_API_KEY"):
    load_dotenv("../.env")

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY no encontrada. Asegúrate de que el .env esté en la raíz del backend.")
    exit(1)

client = genai.Client(api_key=api_key)

print(f"Usando clave (primeros 10): {api_key[:10]}...")
print("\n--- Modelos con soporte de Embeddings ---")

try:
    print("--- Modelos disponibles ---")
    for m in client.models.list():
        print(f"- {m.name}")
except Exception as e:
    print(f"Fallo al conectar con Gemini: {e}")
