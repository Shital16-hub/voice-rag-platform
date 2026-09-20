import pytest
import pytest_asyncio
import httpx
import asyncio

BASE_URL = "http://localhost:8000"

# test data - matches what we created
ACME_EMAIL = "admin@acme.com"
ACME_PASSWORD = "password123"
BETA_EMAIL = "admin@beta.com"
BETA_PASSWORD = "password123"
BETA_AGENT_ID = "a82c82d5-9ad5-4fae-8997-fcf04c1b0b6d"
ACME_AGENT_ID = "d357a032-144f-48a4-91f7-3b2feb967dd0"


async def get_token(email: str, password: str) -> str:
    """Helper to login and get token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password}
        )
        assert response.status_code == 200
        return response.json()["access_token"]


@pytest.mark.asyncio
async def test_acme_cannot_access_beta_agent():
    """
    Acme Corp admin must not be able to query Beta Ltd agent.
    This is the core isolation test.
    """
    # login as Acme admin
    acme_token = await get_token(ACME_EMAIL, ACME_PASSWORD)

    # try to access Beta agent with Acme token
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/chat/message",
            json={
                "question": "How do I create a support ticket?",
                "agent_id": BETA_AGENT_ID
            },
            headers={"Authorization": f"Bearer {acme_token}"}
        )

    # must be 404 not found
    assert response.status_code == 404
    print("PASS: Acme cannot access Beta agent")


@pytest.mark.asyncio
async def test_beta_cannot_access_acme_agent():
    """
    Beta Ltd admin must not be able to query Acme Corp agent.
    """
    # login as Beta admin
    beta_token = await get_token(BETA_EMAIL, BETA_PASSWORD)

    # try to access Acme agent with Beta token
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/chat/message",
            json={
                "question": "How many leave days do employees get?",
                "agent_id": ACME_AGENT_ID
            },
            headers={"Authorization": f"Bearer {beta_token}"}
        )

    # must be 404 not found
    assert response.status_code == 404
    print("PASS: Beta cannot access Acme agent")


@pytest.mark.asyncio
async def test_acme_can_access_own_agent():
    """
    Acme Corp admin must be able to query their own agent.
    """
    acme_token = await get_token(ACME_EMAIL, ACME_PASSWORD)

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{BASE_URL}/chat/message",
            json={
                "question": "How many leave days do employees get?",
                "agent_id": ACME_AGENT_ID
            },
            headers={"Authorization": f"Bearer {acme_token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    print(f"PASS: Acme can access own agent answer={data['answer'][:50]}")


@pytest.mark.asyncio
async def test_unauthenticated_access_blocked():
    """
    Requests without token must be rejected.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/chat/message",
            json={
                "question": "How many leave days do employees get?",
                "agent_id": ACME_AGENT_ID
            }
        )

    assert response.status_code == 403
    print("PASS: Unauthenticated access blocked")


@pytest.mark.asyncio
async def test_acme_cannot_upload_to_beta_agent():
    """
    Acme admin must not be able to upload documents to Beta agent.
    """
    acme_token = await get_token(ACME_EMAIL, ACME_PASSWORD)

    # create a simple test file
    file_content = b"This is a test document"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/documents/upload",
            params={"agent_id": BETA_AGENT_ID},
            files={"file": ("test.txt", file_content, "text/plain")},
            headers={"Authorization": f"Bearer {acme_token}"}
        )

    assert response.status_code == 404
    print("PASS: Acme cannot upload to Beta agent")