from data.connections import bedrock_agent_client, MODEL_ARN, KB_ID


def consultar_kb_streaming(input_text, prioridad=7):
    metadata_filter = {"lessThanOrEquals": {"key": "Prioridad", "value": prioridad}}

    # Añadimos instrucción global
    prompt = (
        f"Analiza la siguiente consulta: {input_text}\n\n"
        "Estilo: Responde detalladamente yendo al grano a la solución del problema"
        " Instrucciones obligatorias:\n"
        "- Si encuentras información relevante en la base de conocimiento, respóndela normalmente siguiendo el estilo indicado.\n"
        "- Si NO hay información relevante, responde *únicamente* con la palabra exacta: create_ticket\n"
        "- No agregues explicaciones, frases adicionales, saludos, ni justificaciones si respondes create_ticket.\n"
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
