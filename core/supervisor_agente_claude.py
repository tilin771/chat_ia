import os
import json
from boto3.session import Session
from botocore.config import Config

# Configuración de AWS / Bedrock
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
PROFILE_NAME = "699541216231_IA_Dev"

session = Session(profile_name=PROFILE_NAME, region_name=REGION)
bedrock_client = session.client("bedrock-runtime", config=Config(connect_timeout=3600, read_timeout=3600))

MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"  # Modelo actualizado

def run_supervisor(system_prompt: str, messages: list) -> dict:
    """
    Llama al modelo Claude 3.5 Sonnet pasando system_prompt y el historial de mensajes.
    Devuelve un JSON con la decisión del supervisor.
    """

    payload = {
    "anthropic_version": "bedrock-2023-05-31",  # 
    "system": [
        {"type": "text", "text": system_prompt}
    ],
    "messages": messages,  # messages debe tener también type="text" en cada contenido
    "max_tokens": 1000,
    "temperature": 0
}
    

    # Llamar al modelo
    response = bedrock_client.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload)
    )

    # Procesar respuesta
    body_json = json.loads(response['body'].read().decode("utf-8"))

# Extraer el texto del assistant
    text_str = body_json["content"][0].get("text", "").strip()

    if not text_str:
        raise ValueError("⚠️ El modelo no devolvió texto en content[0].text")

    # Parsear directamente como JSON
    decision_json = json.loads(text_str)

    # Debug opcional
    print(json.dumps(decision_json, indent=4, ensure_ascii=False))

    return decision_json