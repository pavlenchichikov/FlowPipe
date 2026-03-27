"""Tests for the FastAPI server endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from flowpipe.server import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_list_nodes(client):
    res = await client.get("/api/nodes")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0
    types = {n["type"] for n in data}
    assert "CSVSource" in types
    assert "FilterRows" in types
    assert "CSVDestination" in types


@pytest.mark.asyncio
async def test_run_sample_pipeline(client):
    payload = {
        "nodes": [
            {"id": "n1", "type": "SampleData", "params": {"dataset": "sales", "rows": 10}},
            {"id": "n2", "type": "FilterRows", "params": {"condition": "quantity > 5"}},
        ],
        "edges": [{"source": "n1", "target": "n2"}],
    }
    res = await client.post("/api/run", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["nodes"]) == 2


@pytest.mark.asyncio
async def test_codegen_endpoint(client):
    payload = {
        "nodes": [
            {"id": "n1", "type": "SampleData", "params": {"dataset": "sales", "rows": 10}},
        ],
        "edges": [],
    }
    res = await client.post("/api/codegen", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "script" in data
    assert "pandas" in data["script"]


@pytest.mark.asyncio
async def test_list_uploads(client):
    res = await client.get("/api/uploads")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


@pytest.mark.asyncio
async def test_run_empty_pipeline(client):
    payload = {"nodes": [], "edges": []}
    res = await client.post("/api/run", json=payload)
    assert res.status_code == 200
