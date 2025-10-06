import sys
import os
import streamlit as st
import json
import uuid

# Añadir carpeta raíz del proyecto al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.supervisor_agent import run_supervisor
from core.ticketing_agente import run_ticketing
from services.query_kb import consultar_kb_streaming
from app.utils.validators import validar_mensaje

st.title("🤖 Chatbot soporte Autoline con IA")

# ----------------------
# Funciones auxiliares
# ----------------------

def generar_contexto_kb(max_ultimos=5):
    """
    Genera un contexto acumulado de los últimos mensajes de usuario
    y asistente para mejorar las consultas a la KB.
    """
    contexto = ""
    ultimos_mensajes = st.session_state["messages"][-max_ultimos:]
    for msg in ultimos_mensajes:
        rol = "Usuario" if msg["role"] == "user" else "Asistente"
        contexto += f"{rol}: {msg['content']}\n"
    return contexto


def load_system_prompt(file_path="./data/system_prompt.txt"):
    """Carga el prompt del sistema desde un archivo"""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def inicializar_sesion():
    """Inicializa las variables de sesión de Streamlit"""
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())
    if "ultimo_estado" not in st.session_state:
        st.session_state["ultimo_estado"] = ""
    if "modo_ticket" not in st.session_state:
        st.session_state["modo_ticket"] = False
    if "ticket_iniciado" not in st.session_state:
        st.session_state["ticket_iniciado"] = False


def mostrar_respuesta(texto):
    """Muestra una respuesta del asistente y la guarda en el historial"""
    with st.chat_message("assistant"):
        st.markdown(texto)
    st.session_state["messages"].append({"role": "assistant", "content": texto})


def enviar_saludo_inicial():
    """Envía un saludo automático la primera vez que se inicia la sesión"""
    if "ia_inicializada" not in st.session_state:
        st.session_state["ia_inicializada"] = True
        session_id = st.session_state["session_id"]

        saludo = run_supervisor("Hola", session_id)
        try:
            saludo_json = json.loads(saludo)
            saludo_texto = saludo_json.get("userResponse", "")
        except json.JSONDecodeError:
            saludo_texto = "¡Hola! Estoy aquí para ayudarte con Autoline. 😊"

        st.session_state["messages"].append({"role": "assistant", "content": saludo_texto})

def generar_resumen_contexto():
    """
    Genera un resumen del historial de conversación para pasar a la creación del ticket.
    """
    resumen = "Resumen de la conversación para que lo tengas en cuenta a la hora de redactar el ticket:\n"
    
    for message in st.session_state["messages"]:
        role = "Usuario" if message["role"] == "user" else "Asistente"
        contenido = message["content"]
        resumen += f"{role}: {contenido}\n"
    
    return resumen


def manejar_ticket(user_input, response_placeholder=None):
    """Procesa un mensaje cuando estamos en modo ticket"""
    if "ticket_iniciado" not in st.session_state or not st.session_state["ticket_iniciado"]:
        st.session_state["ticket_iniciado"] = True
        resumen = generar_resumen_contexto()
        full_response = ""
        placeholder = response_placeholder or st.empty()
        with st.spinner("Procesando ticket automáticamente..."):
            for chunk in run_ticketing(resumen, st.session_state["session_id"]):
                full_response += chunk
                placeholder.markdown(full_response)
        # Guardar en historial
        st.session_state["messages"].append({"role": "assistant", "content": full_response})
    else:
        full_response = ""
        placeholder = response_placeholder or st.empty()
        with st.spinner("Actualizando ticket..."):
            for chunk in run_ticketing(user_input, st.session_state["session_id"]):
                full_response += chunk
                placeholder.markdown(full_response)
        st.session_state["messages"].append({"role": "assistant", "content": full_response})
        




def manejar_accion(decision, user_input):
    accion = decision.get("action", "")

    if accion == "query_kb":
        contexto = generar_contexto_kb(max_ultimos=5)  
        consulta_con_contexto = f"{contexto}\nPregunta del usuario: {user_input}"
        full_response = ""
        
        # ✅ Un solo mensaje, un solo placeholder
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            with st.spinner("Consultando base de conocimiento..."):
                for partial_response in consultar_kb_streaming(user_input, consulta_con_contexto, prioridad=7):
                    texto = partial_response.strip()
                    
                    if "create" in texto:
                        st.session_state["modo_ticket"] = True
                        # ✅ Reutilizamos el mismo placeholder → "reemplaza" visualmente
                        manejar_ticket(user_input, response_placeholder=response_placeholder)
                        return  # Salimos: todo ya se mostró en el mismo bloque

                    full_response += partial_response
                    response_placeholder.markdown(full_response)

            # Si llegamos aquí, no se activó el ticket
            full_response += f"\n\n**{decision.get('confirmationMessage', '')}**"
            response_placeholder.markdown(full_response)
            st.session_state["messages"].append({"role": "assistant", "content": full_response})

    elif accion == "create_ticket":
        st.session_state["modo_ticket"] = True
        # Aquí no hay placeholder externo → crea su propio mensaje
        manejar_ticket(user_input)

    else:
        mostrar_respuesta(decision.get("userResponse", ""))

    st.session_state["ultimo_estado"] = f"Estado: {decision.get('status', '')}, Paso siguiente: {decision.get('nextStep', '')}"



def procesar_mensaje(user_input):
    """Procesa el input del usuario"""
    session_id = st.session_state["session_id"]

    # Guardar mensaje del usuario
    st.session_state["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Validar mensaje
    errores = validar_mensaje(user_input)
    if errores:
        mensaje_errores = "Se encontraron los siguientes errores:\n\n" + "\n".join(f"- {e}" for e in errores)
        mostrar_respuesta(mensaje_errores)
        return

    # Si estamos en modo ticket
    if st.session_state["modo_ticket"]:
        manejar_ticket(user_input)
        return

    # Caso general: pedir decisión al supervisor
    decision = run_supervisor(user_input, session_id)
    try:
        decision = json.loads(decision)
    except json.JSONDecodeError:
        st.error("Error al procesar la respuesta de la IA")
        decision = {}

    manejar_accion(decision, user_input)


# ----------------------
# Código principal
# ----------------------

system_prompt = load_system_prompt()
inicializar_sesion()
enviar_saludo_inicial()

# Mostrar mensajes previos
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input del usuario
user_input = st.chat_input("Escribe tu consulta...")
if user_input:
    procesar_mensaje(user_input)
