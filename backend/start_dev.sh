#!/bin/bash
export $(cat .env.local | xargs)
export $(cat ../.env | xargs)
uvicorn app.main:app --reload --port 8000