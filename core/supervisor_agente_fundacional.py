import os
import json
from boto3.session import Session
from botocore.config import Config

# Configuración de AWS / Bedrock
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
PROFILE_NAME = "699541216231_IA_Dev"

session = Session(profile_name=PROFILE_NAME, region_name=REGION)
bedrock_client = session.client(
    "bedrock-runtime", config=Config(connect_timeout=3600, read_timeout=3600)
)

MODEL_ID = "amazon.nova-pro-v1:0"

def run_supervisor(system_prompt: str, messages: list, max_retries: int = 3) -> dict:
    """
    Llama al modelo Nova Pro pasando system_prompt y el historial de mensajes.
    - Si la respuesta es JSON válido, lo devuelve parseado.
    - Si no lo es, reintenta hasta 'max_retries' veces.
    - Si tras varios intentos sigue sin ser JSON, devuelve el último texto plano.
    """
    attempt = 0
    last_raw_text = None

    while attempt < max_retries:
        attempt += 1
        print(f"🧠 Intento {attempt} de {max_retries}...")

        payload = {
            "system": [{"text": system_prompt}],
            "messages": messages,
            "inferenceConfig": {
                "maxTokens": 1000,
                "temperature": 0.7
            }
        }

        # Invocar el modelo
        response = bedrock_client.invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )

        body_json = json.loads(response['body'].read().decode("utf-8"))
        text_str = body_json.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "").strip()

        if not text_str:
            print("⚠️ El modelo no devolvió texto.")
            continue

        # Intentar parsear como JSON
        try:
            decision_json = json.loads(text_str)
            print("✅ JSON válido recibido:")
            print(json.dumps(decision_json, indent=2, ensure_ascii=False))
            return decision_json
        except json.JSONDecodeError:
            print("⚠️ No se pudo parsear JSON. Texto devuelto:")
            print(text_str)
            last_raw_text = text_str

            # 👇 Opcional: forzar al modelo a responder en JSON en el siguiente intento
            # Puedes añadir un recordatorio en el prompt dinámicamente:
            messages.append({
                "role": "user",
                "content": "⚠️ Por favor, responde estrictamente en formato JSON válido."
            })

    # Si llegamos aquí, nunca obtuvimos JSON válido
    return {"raw_text": last_raw_text or "No se obtuvo respuesta del modelo."}
