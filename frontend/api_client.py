import requests
import streamlit as st

BASE_URL = "http://localhost:8000"


def login(email: str, password: str) -> dict:
    """Login and get token."""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password}
    )
    if response.status_code == 200:
        return response.json()
    return None


def get_headers() -> dict:
    """Get auth headers from session state."""
    return {"Authorization": f"Bearer {st.session_state.token}"}


def upload_document(agent_id: str, file) -> dict:
    """Upload a document to an agent."""
    response = requests.post(
        f"{BASE_URL}/documents/upload?agent_id={agent_id}",
        headers=get_headers(),
        files={"file": (file.name, file, file.type)}
    )
    return response.json()


def ingest_document(document_id: str) -> dict:
    """Trigger document ingestion."""
    response = requests.post(
        f"{BASE_URL}/documents/{document_id}/ingest",
        headers=get_headers()
    )
    return response.json()


def get_document_status(document_id: str) -> dict:
    """Check document ingestion status."""
    response = requests.get(
        f"{BASE_URL}/documents/{document_id}/status",
        headers=get_headers()
    )
    return response.json()


def chat(question: str, agent_id: str) -> dict:
    """Send a question to an agent."""
    response = requests.post(
        f"{BASE_URL}/chat/message",
        headers={**get_headers(), "Content-Type": "application/json"},
        json={"question": question, "agent_id": agent_id},
        timeout=60
    )
    return response.json()


def get_pending_approvals() -> list:
    """Get pending approvals."""
    response = requests.get(
        f"{BASE_URL}/approvals",
        headers=get_headers()
    )
    return response.json()


def decide_approval(approval_id: str, decision: str, note: str) -> dict:
    """Approve or reject an action."""
    response = requests.post(
        f"{BASE_URL}/approvals/{approval_id}/decide",
        headers={**get_headers(), "Content-Type": "application/json"},
        json={"decision": decision, "note": note}
    )
    return response.json()


def get_agents() -> list:
    """Get agents for current tenant."""
    tenant_id = st.session_state.tenant_id
    response = requests.get(
        f"{BASE_URL}/tenants/{tenant_id}/agents",
        headers=get_headers()
    )
    if response.status_code == 200:
        return response.json()
    return []