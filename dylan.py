import json
import os
import uuid
from google import genai
from google.genai import types
import streamlit as st

st.set_page_config(page_title="Dylan AI", layout="centered")

ARQUIVO_HISTORICO = "historico_chats.json"


# --- FUNÇÕES DE PERSISTÊNCIA (SALVAR/CARREGAR EM DISCO) ---
def carregar_todos_chats():
    """Carrega o histórico de todas as conversas salvas em disco."""
    if os.path.exists(ARQUIVO_HISTORICO):
        try:
            with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def salvar_todos_chats(chats_dict):
    """Salva o dicionário de chats no arquivo JSON."""
    with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as f:
        json.dump(chats_dict, f, ensure_ascii=False, indent=2)


# --- INICIALIZAÇÃO DO ESTADO DO STREAMLIT ---
if "todos_chats" not in st.session_state:
    st.session_state.todos_chats = carregar_todos_chats()

# Garante que há um chat ativo válido selecionado
if (
    "chat_atual_id" not in st.session_state
    or st.session_state.chat_atual_id not in st.session_state.todos_chats
):
    if st.session_state.todos_chats:
        st.session_state.chat_atual_id = list(
            st.session_state.todos_chats.keys()
        )[0]
    else:
        novo_id = str(uuid.uuid4())[:8]
        st.session_state.chat_atual_id = novo_id
        st.session_state.todos_chats[novo_id] = {
            "titulo": "Novo Chat",
            "messages": [],
        }
        salvar_todos_chats(st.session_state.todos_chats)

# --- BARRA LATERAL: GERENCIADOR DE CHATS E CONFIGURAÇÕES ---
with st.sidebar:
    st.title("Meus Chats")

    if st.button("➕ Novo Chat", use_container_width=True):
        novo_id = str(uuid.uuid4())[:8]
        st.session_state.chat_atual_id = novo_id
        st.session_state.todos_chats[novo_id] = {
            "titulo": "Novo Chat",
            "messages": [],
        }
        salvar_todos_chats(st.session_state.todos_chats)
        st.rerun()

    st.markdown("---")

    st.subheader("Histórico")
    for chat_id, chat_data in list(st.session_state.todos_chats.items()):
        titulo = chat_data.get("titulo", "Conversa")
        is_active = chat_id == st.session_state.chat_atual_id
        label = f"👉 {titulo}" if is_active else titulo

        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            if st.button(label, key=f"btn_{chat_id}", use_container_width=True):
                st.session_state.chat_atual_id = chat_id
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"del_{chat_id}"):
                del st.session_state.todos_chats[chat_id]
                salvar_todos_chats(st.session_state.todos_chats)
                if chat_id == st.session_state.chat_atual_id:
                    outros_ids = list(st.session_state.todos_chats.keys())
                    if outros_ids:
                        st.session_state.chat_atual_id = outros_ids[0]
                    else:
                        novo_id = str(uuid.uuid4())[:8]
                        st.session_state.chat_atual_id = novo_id
                        st.session_state.todos_chats[novo_id] = {
                            "titulo": "Novo Chat",
                            "messages": [],
                        }
                        salvar_todos_chats(st.session_state.todos_chats)
                st.rerun()

    st.markdown("---")
    st.header("⚙️ Configurações")

    api_key = st.text_input(
        "Gemini API Key:",
        value="AQ.Ab8RN6Ivf8WRAVfAOGpfnQIssXU0w9QgB_lfatfzASe1wL1OeQ",
        type="password",
    )

    prompt_padrao = (
        "Você é o Dylan (Dylanbb). Responda exatamente como um amigo de WhatsApp.\n\n"
        "Estilo de escrita:\n"
        "- Use minúsculas e pouca pontuação formal.\n"
        "- Use bastante as gírias: 'cz', 'pdp', 'br', 'krl', 'chapei', 'dnv', 'viado'.\n"
        "- Abrevie palavras: vc, n, q, hj, agr, msm, tmb.\n"
        "- Seja direto, tranquilo, meio desligado, mas parceiro dos amigos."
    )

    prompt_sistema = st.text_area(
        "Instrução do Sistema:", value=prompt_padrao, height=180
    )

# --- ÁREA PRINCIPAL DO CHAT ---
chat_atual = st.session_state.todos_chats[st.session_state.chat_atual_id]

st.title(f"Dylan 0.3 - {chat_atual['titulo']}")

for msg in chat_atual["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Fala com o Dylan...")

if user_input:
    if not api_key:
        st.error("Por favor, insira sua API Key na barra lateral!")
    else:
        with st.chat_message("user"):
            st.markdown(user_input)

        try:
            client = genai.Client(api_key=api_key)
            configuracao = types.GenerateContentConfig(
                system_instruction=prompt_sistema
            )

            historico_sdk = []
            for m in chat_atual["messages"]:
                role_sdk = "user" if m["role"] == "user" else "model"
                historico_sdk.append(
                    {"role": role_sdk, "parts": [{"text": m["content"]}]}
                )

            chat = client.chats.create(
                model="gemini-3.6-flash",
                history=historico_sdk,
                config=configuracao,
            )

            response = chat.send_message(user_input)

            with st.chat_message("assistant"):
                st.markdown(response.text)

            if len(chat_atual["messages"]) == 0:
                titulo_curto = (
                    user_input[:20] + "..."
                    if len(user_input) > 20
                    else user_input
                )
                chat_atual["titulo"] = titulo_curto

            chat_atual["messages"].append({"role": "user", "content": user_input})
            chat_atual["messages"].append(
                {"role": "assistant", "content": response.text}
            )

            salvar_todos_chats(st.session_state.todos_chats)
            st.rerun()

        except Exception as e:
            if "429" in str(e):
                st.warning(
                    "Aguarde cerca de 10 a 15 segundos antes de mandar a próxima mensagem."
                )
            else:
                st.error(f"Erro na API: {e}")