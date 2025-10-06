from data.connections import bedrock_agent_client, MODEL_ARN, KB_ID


def consultar_kb_streaming(input_text, contexto, prioridad=7):
    metadata_filter = {"lessThanOrEquals": {"key": "Prioridad", "value": prioridad}}

    # Añadimos instrucción global
    prompt = (
        f"Contexto de la conversación:\n{contexto}\n\n"
        f"Consulta del usuario: {input_text}\n\n"
        "Estilo: Responde detalladamente yendo al grano a la solución del problema.\n"
        "Formato de la respuesta:\n"
        "- Si la información contiene pasos, preséntalos como lista numerada, con cada paso en una línea separada.\n"
        "- Usa saltos de línea claros entre secciones o ideas diferentes.\n"
        "- Mantén la respuesta clara, directa y profesional.\n"
        "Instrucciones obligatorias:\n"
        "- Si encuentras información relevante en la base de conocimiento, respóndela siguiendo el estilo y formato indicados.\n"
        "- Si NO hay información relevante o la información no es útil para resolver la consulta, responde *únicamente* con la palabra exacta: create_ticket\n"
        "- Está terminantemente prohibido escribir cualquier otra cosa además de create_ticket en ese caso. No expliques, no des contexto, no sugieras nada.\n"
        "- Si decides responder create_ticket, esa palabra debe ser la ÚNICA salida del modelo.\n"
    )


    response = bedrock_agent_client.retrieve_and_generate_stream(
        input={"text": prompt},
        retrieveAndGenerateConfiguration={
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": KB_ID,
                "modelArn": MODEL_ARN,
                "retrievalConfiguration": {
                    "vectorSearchConfiguration": {
                        "filter": metadata_filter,
                        "numberOfResults": 3
                    }
                }
            },
            "type": "KNOWLEDGE_BASE"
        }
    )

    for event in response['stream']:
        if 'output' in event and 'text' in event['output']:
            yield event['output']['text']
