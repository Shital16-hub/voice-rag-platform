import streamlit as st
import requests
import pandas as pd
from datetime import datetime

BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Voice RAG Platform",
    page_icon="🤖",
    layout="wide"
)

# ─────────────────────────────────────────
# Session state initialization
# ─────────────────────────────────────────
for key in ["token", "user_id", "tenant_id", "role", "messages"]:
    if key not in st.session_state:
        st.session_state[key] = None
if "messages" not in st.session_state:
    st.session_state.messages = []


# ─────────────────────────────────────────
# API helpers
# ─────────────────────────────────────────
def headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}


def api_get(path):
    r = requests.get(f"{BASE_URL}{path}", headers=headers())
    return r.json() if r.status_code == 200 else []


def api_post(path, data=None, files=None):
    h = headers()
    if files:
        r = requests.post(f"{BASE_URL}{path}", headers=h, files=files)
    else:
        h["Content-Type"] = "application/json"
        r = requests.post(f"{BASE_URL}{path}", headers=h, json=data, timeout=60)
    return r.json()


# ─────────────────────────────────────────
# Login page
# ─────────────────────────────────────────
def login_page():
    st.title("🤖 Voice RAG Platform")
    st.subheader("Login")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            r = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": email, "password": password}
            )
            if r.status_code == 200:
                data = r.json()
                st.session_state.token = data["access_token"]
                st.session_state.user_id = data["user_id"]
                st.session_state.tenant_id = data["tenant_id"]
                st.session_state.role = data["role"]
                st.session_state.messages = []
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid email or password")

    st.divider()
    st.caption("Demo credentials:")
    st.caption("Admin: admin@acme.com / password123")
    st.caption("Employee: john@acme.com / employee123")


# ─────────────────────────────────────────
# Chat page
# ─────────────────────────────────────────
def chat_page():
    st.title("💬 Chat")

    # load agents
    agents = api_get("/agents")
    if not agents:
        st.warning("No agents available")
        return

    agent_options = {a["name"]: a["id"] for a in agents}

    col1, col2 = st.columns([3, 1])
    with col1:
        selected_name = st.selectbox("Select Agent", list(agent_options.keys()))
    with col2:
        if st.button("Clear Chat"):
            st.session_state.messages = []
            st.rerun()

    selected_id = agent_options[selected_name]

    # display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("sources"):
                with st.expander(f"📚 Sources ({len(msg['sources'])})"):
                    for s in msg["sources"]:
                        st.write(f"**{s['filename']}** — score: {s['score']:.2f}")
                        st.caption(s["content"][:300])
                        st.divider()
            if msg.get("approval_needed"):
                st.warning("⏳ Action requires manager approval. Check Approvals page.")

    # chat input
    question = st.chat_input("Ask a question...")
    if question:
        st.session_state.messages.append({"role": "user", "content": question})

        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = api_post(
                    "/chat/message",
                    {"question": question, "agent_id": selected_id}
                )

            answer = result.get("answer", "Error getting response")
            sources = result.get("sources", [])
            approval_needed = "requires manager approval" in answer.lower()

            st.write(answer)

            if sources:
                with st.expander(f"📚 Sources ({len(sources)})"):
                    for s in sources:
                        st.write(f"**{s['filename']}** — score: {s['score']:.2f}")
                        st.caption(s["content"][:300])
                        st.divider()

            if approval_needed:
                st.warning("⏳ Action requires manager approval. Check Approvals page.")

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "approval_needed": approval_needed
        })


# ─────────────────────────────────────────
# Documents page (admin only)
# ─────────────────────────────────────────
def documents_page():
    st.title("📄 Documents")

    agents = api_get("/agents")
    if not agents:
        st.warning("No agents available")
        return

    agent_options = {a["name"]: a["id"] for a in agents}
    selected_name = st.selectbox("Select Agent", list(agent_options.keys()))
    selected_id = agent_options[selected_name]

    # show existing documents
    st.subheader("Uploaded Documents")
    docs = api_get(f"/documents?agent_id={selected_id}")

    if docs:
        df = pd.DataFrame([
            {
                "Filename": d["filename"],
                "Type": d["file_type"],
                "Status": d["ingestion_status"],
                "Chunks": d["chunk_count"] or 0,
                "Size (bytes)": d["file_size_bytes"],
                "Uploaded": d["created_at"][:10]
            }
            for d in docs
        ])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No documents uploaded yet")

    st.divider()

    # upload new document
    st.subheader("Upload New Document")
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "txt", "docx", "md"]
    )

    if uploaded_file and st.button("Upload and Process"):
        with st.spinner("Uploading..."):
            result = api_post(
                f"/documents/upload?agent_id={selected_id}",
                files={"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
            )

        if "id" in result:
            doc_id = result["id"]
            st.success(f"Uploaded: {result['filename']}")

            with st.spinner("Processing document... this may take a minute"):
                ingest_result = api_post(f"/documents/{doc_id}/ingest")

            if "completed" in str(ingest_result):
                st.success("Document processed and ready for search!")
            else:
                st.error(f"Processing issue: {ingest_result}")

            st.rerun()
        else:
            st.error(f"Upload failed: {result}")


# ─────────────────────────────────────────
# Approvals page (admin only)
# ─────────────────────────────────────────
def approvals_page():
    st.title("✅ Approvals")

    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 Refresh"):
            st.rerun()

    approvals = api_get("/approvals")

    if not approvals:
        st.success("No pending approvals")
        return

    st.warning(f"{len(approvals)} pending approval(s)")

    for a in approvals:
        with st.expander(
            f"🔔 {a['tool_name']} — requested {a['created_at'][:10]}"
        ):
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Tool:** `{a['tool_name']}`")
                st.write(f"**Status:** {a['status']}")
                st.write(f"**Expires:** {a['expires_at'][:10]}")
                st.write("**Parameters:**")
                for k, v in a["tool_input"].items():
                    st.write(f"  - {k}: `{v}`")

            with col2:
                note = st.text_input(
                    "Note",
                    placeholder="Optional note...",
                    key=f"note_{a['id']}"
                )
                st.write("")

                a_col, r_col = st.columns(2)
                with a_col:
                    if st.button("✅ Approve", key=f"approve_{a['id']}"):
                        result = api_post(
                            f"/approvals/{a['id']}/decide",
                            {"decision": "approved", "note": note}
                        )
                        if result.get("status") == "approved":
                            st.success("Approved!")
                            if result.get("tool_result"):
                                st.json(result["tool_result"])
                            st.rerun()

                with r_col:
                    if st.button("❌ Reject", key=f"reject_{a['id']}"):
                        result = api_post(
                            f"/approvals/{a['id']}/decide",
                            {"decision": "rejected", "note": note}
                        )
                        if result.get("status") == "rejected":
                            st.error("Rejected.")
                            st.rerun()


# ─────────────────────────────────────────
# Evaluation page (admin only)
# ─────────────────────────────────────────
def evaluation_page():
    st.title("📊 RAG Evaluation")

    st.info("Baseline metrics from our evaluation dataset (5 questions, 2 documents)")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Recall@3", "1.00")
    col2.metric("Avg MRR", "0.83")
    col3.metric("Grounded", "4/4")
    col4.metric("Unanswerable", "1/1 ✓")

    st.divider()

    st.subheader("Latency (with Groq LLM)")
    col1, col2, col3 = st.columns(3)
    col1.metric("Avg Retrieval", "422ms")
    col2.metric("Avg LLM", "~500ms")
    col3.metric("Avg Total", "~1500ms")

    st.divider()

    st.subheader("Evaluation Dataset Results")
    data = {
        "Question": [
            "How many leave days per year?",
            "How many sick leave days?",
            "Total days off?",
            "Company vacation policy?",
            "Weather forecast? (unanswerable)"
        ],
        "Difficulty": ["easy", "easy", "medium", "medium", "unanswerable"],
        "Recall@3": [1.0, 1.0, 1.0, 1.0, 1.0],
        "MRR": [1.0, 1.0, 1.0, 0.33, 1.0],
        "Grounded": ["✓", "✓", "✓", "✓", "N/A"]
    }
    st.dataframe(pd.DataFrame(data), use_container_width=True)

    st.divider()
    st.subheader("System Info")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**LLM:** Groq (allam-2-7b)")
        st.write("**Embeddings:** nomic-embed-text (local)")
        st.write("**Vector DB:** Qdrant")
    with col2:
        st.write("**Chunk size:** 500 chars")
        st.write("**Score threshold:** 0.5")
        st.write("**Top K:** 3")


# ─────────────────────────────────────────
# History page
# ─────────────────────────────────────────
def history_page():
    st.title("📜 Conversation History")

    conversations = api_get("/conversations")

    if not conversations:
        st.info("No conversations yet")
        return

    st.write(f"**{len(conversations)} conversations**")

    for conv in conversations[:20]:
        date = conv["created_at"][:10]
        with st.expander(f"Conversation — {date}"):
            messages = api_get(f"/conversations/{conv['id']}/messages")
            if messages:
                for msg in messages:
                    role_icon = "👤" if msg["role"] == "user" else "🤖"
                    st.write(f"{role_icon} **{msg['role'].title()}:** {msg['content']}")
                    if msg.get("latency_ms"):
                        st.caption(f"Response time: {msg['latency_ms']}ms")
                    st.divider()
            else:
                st.write("No messages")


# ─────────────────────────────────────────
# Main app with navigation
# ─────────────────────────────────────────
def main_app():
    with st.sidebar:
        st.title("🤖 Voice RAG")
        st.caption(f"Logged in as: **{st.session_state.role}**")
        st.divider()

        if st.session_state.role == "admin":
            pages = {
                "💬 Chat": chat_page,
                "📄 Documents": documents_page,
                "✅ Approvals": approvals_page,
                "📊 Evaluation": evaluation_page,
                "📜 History": history_page
            }
        else:
            pages = {
                "💬 Chat": chat_page,
                "📜 History": history_page
            }

        selected = st.radio("Navigation", list(pages.keys()))
        st.divider()

        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    pages[selected]()


# ─────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────
if st.session_state.token is None:
    login_page()
else:
    main_app()