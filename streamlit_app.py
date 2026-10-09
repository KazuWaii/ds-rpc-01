import os
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

# roles.py n'a aucune dépendance : l'interface peut l'importer sans les paquets du backend
from app.core.roles import ROLE_PERMISSIONS

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
DATA_DIR = Path(__file__).parent / "resources" / "data"

# Comptes de démonstration : copie de users_db (app/main.py). L'interface est déployée
# sans les dépendances du backend (FastAPI, Chroma...), elle ne peut donc pas importer app.main.
DEMO_ACCOUNTS = [
    ("Tony", "password123", "engineering"),
    ("Peter", "pete123", "engineering"),
    ("Sam", "financepass", "finance"),
    ("Natasha", "hrpass123", "hr"),
    ("Bruce", "securepass", "marketing"),
    ("Sid", "sidpass123", "marketing"),
    ("Steve", "cap123", "employee"),
    ("Nick", "fury123", "admin"),
]

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


def login_sidebar():
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
        if "auth" in st.session_state:
            st.caption("Can read: " + ", ".join(sorted(ROLE_PERMISSIONS[st.session_state["role"]])))


def show_tutorial():
    st.markdown(
        "1. Pick one of the demo accounts below and log in from the sidebar. The first login can take "
        "up to a minute: the API scales to zero when idle and has to start up again.\n"
        "2. Ask a question on the **Chat** page, or click one of the suggested questions for your role.\n"
        "3. Each role can only read some departments: the documents of other departments are never "
        "searched, so the assistant can't answer from them. Log in with another account to compare.\n"
        "4. The **Documents** page shows the files your role can read, to check an answer against its sources."
    )
    # st.table plutôt que st.dataframe : 8 lignes toujours visibles, texte sélectionnable pour copier un mot de passe
    st.table(
        pd.DataFrame(
            [(user, password, role, ", ".join(sorted(ROLE_PERMISSIONS[role])))
             for user, password, role in DEMO_ACCOUNTS],
            columns=["Username", "Password", "Role", "Can read"],
        ),
        hide_index=True,
    )


def chat_page():
    st.title("FinSolve Internal Assistant")

    # Afficher l'historique de conversation si l'utilisateur est connecté
    if "auth" not in st.session_state:
        st.info("Log in from the sidebar to start chatting.")
        show_tutorial()
        return

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


def documents_page():
    st.title("Source documents")
    if "auth" not in st.session_state:
        st.info("Log in from the sidebar to see the documents your role can read.")
        return

    role = st.session_state["role"]
    allowed = ROLE_PERMISSIONS[role]
    st.caption(f"The files the `{role}` role can read. They are the only ones the assistant searches for this role.")
    paths = {p.relative_to(DATA_DIR).as_posix(): p for p in sorted(DATA_DIR.rglob("*.*"))
             if p.parent.name in allowed}
    path = paths[st.selectbox("Document", list(paths))]
    st.download_button("Download", path.read_bytes(), file_name=path.name)
    if path.suffix == ".csv":
        st.caption("Use the search icon at the top right of the table to find an employee.")
        st.dataframe(pd.read_csv(path), hide_index=True)
    else:
        st.markdown(path.read_text(encoding="utf-8").replace("$", "\\$"))  # "$" would otherwise start a LaTeX formula


def tutorial_page():
    st.title("How to use this demo")
    show_tutorial()


st.set_page_config(page_title="FinSolve Assistant", page_icon="💬")
login_sidebar()
st.navigation([
    st.Page(chat_page, title="Chat", url_path="chat", default=True),
    st.Page(documents_page, title="Documents", url_path="documents"),
    st.Page(tutorial_page, title="Tutorial", url_path="tutorial"),
], position="top").run()
