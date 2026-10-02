# Voice RAG Platform — Project Context

## What This Project Is
A multi-tenant Voice RAG Platform where organizations configure
specialized AI agents that operate over isolated knowledge bases,
use tools through LangGraph workflows, support HITL approval,
and are evaluated with measurable metrics.

## Tech Stack
- Backend: FastAPI + Python (async)
- LLM: Groq (allam-2-7b) via OpenAI-compatible API
- Embeddings: nomic-embed-text via Ollama (local Docker)
- Vector DB: Qdrant (Docker)
- App DB: PostgreSQL (Docker)
- Agent orchestration: LangGraph
- Frontend: Streamlit
- Auth: JWT tokens

## Project Location
~/voice-rag-platform/

## Folder Structure
backend/
  app/
    api/          → auth_router, document_router, chat_router,
                    tenant_router, hitl_router, agent_router,
                    conversation_router, user_router
    agents/       → agent_state.py, nodes.py, tool_registry.py,
                    generic_agent.py
    core/         → config.py, database.py, logger.py,
                    security.py, dependencies.py, qdrant_client.py
    ingestion/    → document_parser.py, text_chunker.py,
                    ingestion_pipeline.py
    models/       → models.py (all DB tables)
    schemas/      → auth_schema, document_schema, chat_schema,
                    hitl_schema, tenant_schema
    services/     → auth_service, document_service,
                    embedding_service, retrieval_service,
                    llm_service, chat_service, hitl_service,
                    mcp_service, tenant_service
    main.py
  alembic/
  tests/
    test_isolation.py
  mcp_servers/
    hr_mcp_server.py
  scripts/
    create_test_data.py
    create_beta_tenant.py
    create_employee.py
  requirements_noversion.txt
  venv_new/       ← Python virtual environment

frontend/
  app.py          ← Streamlit UI
  venv/           ← separate Python environment
  api_client.py   ← (not used, logic is in app.py directly)

eval/
  hr_eval_dataset.json
  metrics.py
  run_evaluation.py
  eval_results.json

## Database Tables
tenants, agents, users, documents, doc_chunks,
conversations, messages, approval_requests

## Test Data
Acme Corp tenant:  c230676f-a74d-4204-a471-ac9a4917ad18
HR Agent:          d357a032-144f-48a4-91f7-3b2feb967dd0
Beta Ltd tenant:   f63848c8-3234-4cf0-8ba5-3ff6e5951e02
Support Agent:     a82c82d5-9ad5-4fae-8997-fcf04c1b0b6d
Admin user:        21effd2f-ed7d-4960-8983-4092ce087293

## Login Credentials
admin@acme.com / password123  (Acme admin)
admin@beta.com / password123  (Beta admin)
john@acme.com / employee123   (Acme employee - if created)

## How To Start The Project
Terminal 1 (Docker):
  cd ~/voice-rag-platform
  docker compose up -d
  sudo systemctl stop ollama

Terminal 2 (Backend):
  cd ~/voice-rag-platform/backend
  source venv_new/bin/activate
  export POSTGRES_HOST=localhost QDRANT_HOST=localhost OLLAMA_HOST=localhost
  uvicorn app.main:app --reload --port 8000

Terminal 3 (Frontend):
  cd ~/voice-rag-platform/frontend
  source venv/bin/activate
  streamlit run app.py

## API Endpoints
POST /auth/login
GET  /agents
POST /chat/message
GET  /documents?agent_id=ID
POST /documents/upload?agent_id=ID
POST /documents/{id}/ingest
GET  /documents/{id}/status
GET  /approvals
POST /approvals/{id}/decide
GET  /conversations
GET  /conversations/{id}/messages
GET  /users
POST /users
PATCH /users/{id}/toggle
POST /tenants
GET  /tenants
POST /tenants/{id}/agents
GET  /tenants/{id}/agents
GET  /health

## What Is Working
Phase 1: RAG foundation          COMPLETE
Phase 2: Multi-tenant isolation  COMPLETE (5/5 tests passing)
Phase 3: RAG evaluation          COMPLETE (Recall@3=1.00, MRR=0.83)
Phase 4: LangGraph agents        COMPLETE
  - Generic agent graph
  - Keyword + LLM hybrid routing
  - Built-in tool registry
  - Structured output with Pydantic
Phase 5: HITL approval           COMPLETE
  - Create approval request
  - List pending approvals
  - Approve/reject with tool execution
Phase 6: Voice                   NOT STARTED
Phase 7: Observability           NOT STARTED
Phase 8: Testing                 PARTIAL (isolation tests only)
Phase 9: Deployment              NOT STARTED
Phase 10: Terraform              NOT STARTED
Phase 11: Streamlit UI           IN PROGRESS
  - Login page                   DONE
  - Chat page                    DONE
  - Documents page               DONE
  - Approvals page               DONE
  - Evaluation page              DONE
  - History page                 DONE
  - Users page                   NOT DONE YET
Phase 12: Portfolio packaging    NOT STARTED

## What We Are Currently Doing
Building Streamlit UI Users page.
Just added backend user management endpoints (GET /users, POST /users, PATCH /users/{id}/toggle).
Next step: Add Users page to frontend/app.py

## Known Issues / Decisions
- LLM model: allam-2-7b on Groq (llama-3.2-3b-preview not available)
- Ollama used only for embeddings (nomic-embed-text)
- MCP: designed but not fully integrated (stdio vs SSE transport issue)
- venv_new is the active backend venv (not venv)
- Node.js installed inside WSL for MCP server testing

## Isolation Strategy
Qdrant: per-agent collection named tenant_{id}_agent_{id}
PostgreSQL: tenant_id on every query
JWT: tenant_id in token, cannot be changed by user

## RAG Pipeline
Parse → Chunk (500 chars, 50 overlap) → Embed (nomic-embed-text)
→ Store (Qdrant) → Search (cosine similarity, threshold 0.5, top 3)
→ Generate (Groq) → Return with citations

## LangGraph Flow
router → rag_only → retrieve → generate → END
router → tool_required → tool → generate → END
router → tool_required → tool → hitl → END
router → unanswerable → generate → END

## Remaining Work
1. Finish Streamlit UI (Users page)
2. Test full UI flow
3. Voice (LiveKit + STT + TTS)
4. Observability (Langfuse)
5. Testing (more tests)
6. Deployment (Docker + AWS + CI/CD)
7. Terraform
8. Portfolio packaging (README, ADRs, diagrams)