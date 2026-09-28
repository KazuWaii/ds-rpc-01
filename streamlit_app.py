import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

SUGGESTED_QUESTIONS = {
    "finance": [
        "What drove the increase in vendor expenses in 2024?",
        "What was the company's gross margin in 2024?",
        "What is the reimbursement policy for travel expenses?",
    ],
    "marketing": [
        "What was the Q4 2024 marketing spend?",
        "What new feature did FinNova launch during its European expansion?",
        "What marketing channels were used in 2024?",
    ],
    "hr": [
        "What is the company's leave policy?",
        "What is Aadhya Patel's job title?",
        "How is employee performance reviewed?",
    ],
    "engineering": [
        "What authentication protocol does FinSolve's authentication service use?",
        "What database does FinSolve use for caching and session management?",
        "What cloud infrastructure does FinSolve run on?",
    ],
    "admin": [
        "What drove the increase in vendor expenses in 2024?",
        "What is the company's leave policy?",
        "What was the Q4 2024 marketing spend?",
    ],
    "employee": [
        "What is the reimbursement policy?",
        "What are the company's holiday policies?",
        "What training programs are offered to new employees?",
    ],
}

st.set_page_config(page_title="FinSolve Assistant", page_icon="💬")
st.title("FinSolve Internal Assistant")


def ask(question):
    st.session_state["messages"].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    try:
        resp = requests.post(
            f"{API_URL}/chat",
            json={"message": question},
            auth=st.session_state["auth"],
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        answer, sources = data["answer"], data["sources"]
    except requests.RequestException as e:
        answer, sources = f"Error contacting the API: {e}", []

    with st.chat_message("assistant"):
        st.markdown(answer)
        if sources:
            st.caption("Sources: " + ", ".join(sources))
    st.session_state["messages"].append(
        {"role": "assistant", "content": answer, "sources": sources}
    )


# Configuration de la session pour stocker les informations d'authentification et l'historique des messages
with st.sidebar:
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Log in"):
        try:
            # Long timeout: the deployed backend scales to zero when idle, so
            # the first request after a period of inactivity has to wait for
            # the container to cold-start (pull image, load the embedding
            # model) before it can even check the password.
            resp = requests.get(f"{API_URL}/login", auth=(username, password), timeout=120)
            if resp.ok:
                st.session_state["auth"] = (username, password)
                st.session_state["role"] = resp.json()["role"]
                st.session_state["messages"] = []
                st.success(f"Logged in as {username} ({st.session_state['role']})")
            else:
                st.error("Invalid credentials")
        except requests.ConnectionError:
            st.error("Can't reach the API. Is it running on http://127.0.0.1:8000?")


# Afficher l'historique de conversation si l'utilisateur est connecté
if "auth" not in st.session_state:
    st.info("Log in from the sidebar to start chatting.")
else:
    st.caption(f"Role: **{st.session_state['role']}**")
    st.session_state.setdefault("messages", [])

    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                st.caption("Sources: " + ", ".join(msg["sources"]))

    # Suggestions de questions adaptées au rôle, affichées tant qu'aucune
    # conversation n'a encore commencé.
    if not st.session_state["messages"]:
        suggestions = SUGGESTED_QUESTIONS.get(st.session_state["role"], [])
        if suggestions:
            st.caption("Try asking:")
            columns = st.columns(len(suggestions))
            for column, suggestion in zip(columns, suggestions):
                with column:
                    if st.button(suggestion, use_container_width=True):
                        ask(suggestion)
                        st.rerun()

    # Envoyer un message à l'API lorsque l'utilisateur soumet une question
    if question := st.chat_input("Ask about company data..."):
        ask(question)
