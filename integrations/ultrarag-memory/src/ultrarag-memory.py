"""Independent stdio Memory MCP Server with UltraRAG build metadata."""

from functools import lru_cache

from ultrarag.server import UltraRAG_MCP_Server

from longmem.config import load_config, make_store
from longmem.generation import Generator, build_prompt

app = UltraRAG_MCP_Server("longmem")


@lru_cache(maxsize=1)
def services():
    config = load_config()
    return make_store(config), Generator(config["generation"])


@app.tool(output="content,memory_id,importance,source,supersedes,metadata->written_memory")
def memory_write(content: str, memory_id: str | None = None, importance: float = 0.5,
                 source: str = "user", supersedes: str | None = None, metadata: dict | None = None) -> dict:
    """Persist a fact; repeat the same memory_id and payload for an idempotent retry."""
    memory = services()[0].write(content, memory_id=memory_id, importance=importance,
                                 source=source, supersedes=supersedes, metadata=metadata)
    return {"written_memory": memory.to_dict()}


@app.tool(output="query,top_k->hits")
def memory_search(query: str, top_k: int = 5) -> dict:
    """Retrieve active facts with auditable memory IDs and similarity scores."""
    return {"hits": services()[0].search(query, top_k)}


@app.tool(output="memory_id->found_memory")
def memory_get(memory_id: str) -> dict:
    """Read a fact by its stable ID, including superseded history."""
    memory = services()[0].get(memory_id)
    return {"found_memory": memory.to_dict() if memory else None}


@app.tool(output="query,hits->constructed_prompt")
def prompt_construction(query: str, hits: list[dict]) -> dict:
    """Build an evidence-bearing prompt."""
    return {"constructed_prompt": build_prompt(query, hits)}


@app.tool(output="constructed_prompt,hits->answer")
def generator(constructed_prompt: str, hits: list[dict]) -> dict:
    """Generate using the explicitly configured model or test backend."""
    return {"answer": services()[1].generate(constructed_prompt, hits)}


@app.tool(output="query,answer,hits->response_memory")
def remember_response(query: str, answer: str, hits: list[dict]) -> dict:
    """Write generated output with provenance; it is not a user-confirmed fact."""
    memory = services()[0].write(
        f"Question: {query}\nAnswer: {answer}", importance=0.3, source="generated",
        metadata={"evidence_ids": [hit["memory"]["memory_id"] for hit in hits], "verified": False},
    )
    return {"response_memory": memory.to_dict()}


if __name__ == "__main__":
    app.run(transport="stdio")
