import sys
import os
import streamlit as st
import json
import uuid

# Agrega la carpeta raíz del proyecto al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.supervisor_agente_fundacional import run_supervisor
from services.query_kb import consultar_kb_streaming
from app.utils.validators import validar_mensaje

st.title("🤖 Chatbot soporte Autoline con IA")

def load_system_prompt(file_path="system_prompt.txt"):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

system_prompt = load_system_prompt("./data/system_prompt.txt")

# Inicializar sesión y mensajes
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())
if "ultimo_estado" not in st.session_state:
    st.session_state["ultimo_estado"] = ""  # Para trackear el estado resumido previo

# Mostrar mensajes anteriores
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input del usuario
user_input = st.chat_input("Escribe tu consulta...")

if user_input:
    # Guardar mensaje del usuario
    st.session_state["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Validar mensaje
    errores = validar_mensaje(user_input)
    if errores:
        mensaje_errores = ("⚠️ Se encontraron los siguientes errores en tu mensaje:\n\n" +
                           "\n".join(f"- {e}" for e in errores))
        with st.chat_message("assistant"):
            st.markdown(mensaje_errores)
        st.session_state["messages"].append({"role": "assistant", "content": mensaje_errores})
    else:
        # Construir historial para Bedrock
        historial_bedrock = []
        for msg in st.session_state["messages"]:
            historial_bedrock.append({
                "role": msg["role"],
                "content": [{"text": msg["content"]}]
            })

        # --- Adjuntar estado resumido previo al prompt ---
        ultimo_estado = st.session_state.get("ultimo_estado", "")
        system_prompt_con_estado = system_prompt
        if ultimo_estado:
            system_prompt_con_estado += f"\n\nEstado resumido previo de la conversación: {ultimo_estado}"

        # Llamar al modelo
        decision = run_supervisor(system_prompt_con_estado, historial_bedrock)

        # Manejar respuesta según acción
        if decision["action"] == "query_kb":
            full_response = ""
            with st.chat_message("assistant") as chat_msg:
                response_placeholder = st.empty()
                with st.spinner("Consultando base de conocimiento..."):
                    for partial_response in consultar_kb_streaming(user_input, prioridad=9):
                        full_response += partial_response
                        response_placeholder.markdown(full_response)
                # Concatenar mensaje de confirmación en negrita
                full_response += f"\n\n**{decision['confirmationMessage']}**"
                response_placeholder.markdown(full_response)
        else:
            full_response = ""
            with st.chat_message("assistant") as chat_msg:
                response_placeholder = st.empty()
                with st.spinner("Generando respuesta..."):
                    full_response = decision.get("userResponse", "")
                    response_placeholder.markdown(full_response)

        # Guardar la respuesta en el chat
        st.session_state["messages"].append({"role": "assistant", "content": full_response})

        # --- Actualizar estado resumido para el siguiente turno ---
        # Solo guardamos lo relevante: nextStep y status
        st.session_state["ultimo_estado"] = f"Estado: {decision.get('status', '')}, Paso siguiente: {decision.get('nextStep', '')}"
