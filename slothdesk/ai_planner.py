from __future__ import annotations
import json
import requests
from pydantic import TypeAdapter
from .schemas import PlanItem

OLLAMA_URL = "http://localhost:11434/api/generate"
PLAN_ADAPTER = TypeAdapter(list[PlanItem])

class OllamaError(RuntimeError):
    pass

def plan_organization(rows: list[dict], model: str = "qwen3:8b") -> list[PlanItem]:
    if not rows:
        return []
    # Keep prompt bounded; only metadata, never file contents.
    compact = [
        {
            "relative_path": row["relative_path"],
            "name": row["name"],
            "extension": row["extension"],
            "size_bytes": row["size_bytes"],
        }
        for row in rows[:150]
    ]
    schema = PLAN_ADAPTER.json_schema()
    prompt = (
        "You are a conservative file-organization planner. For each input file, return exactly "
        "one object with original_name, suggested_name, category, reason, confidence. "
        "Use only supplied metadata; do not claim to know file contents. "
        "Keep the original extension exactly. suggested_name must be a single filename, not a path. "
        "category should be a short relative folder such as Documents/Receipts or Images. "
        "Use Unsorted when uncertain. Never suggest deletion. Preserve original_name exactly. "
        "Return a JSON array only. Input files:\n" + json.dumps(compact, ensure_ascii=False)
    )
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "format": schema,
                "stream": False,
                "options": {"temperature": 0},
            },
            timeout=(5, 180),
        )
        response.raise_for_status()
        payload = response.json()
        raw = payload.get("response", "")
        plan = PLAN_ADAPTER.validate_json(raw)
    except requests.RequestException as exc:
        raise OllamaError(
            "Could not reach Ollama. Start Ollama and run `ollama pull qwen3:8b`. "
            f"Details: {exc}"
        ) from exc
    except Exception as exc:
        raise OllamaError(f"Model output was invalid or could not be parsed: {exc}") from exc

    # Require exact one-to-one mapping. Ignore any model-invented or duplicate entries.
    by_original = {}
    allowed = {row["name"] for row in compact}
    for item in plan:
        if item.original_name in allowed and item.original_name not in by_original:
            by_original[item.original_name] = item
    result = []
    for row in compact:
        item = by_original.get(row["name"])
        if item is None:
            item = PlanItem(
                original_name=row["name"],
                suggested_name=row["name"],
                category="Unsorted",
                reason="Fallback: model did not return a valid suggestion",
                confidence=0.0,
            )
        # Deterministically preserve original extension.
        original_suffix = __import__("pathlib").Path(row["name"]).suffix
        proposed = __import__("pathlib").Path(item.suggested_name)
        if proposed.suffix.lower() != original_suffix.lower():
            safe_stem = proposed.stem or "organized_file"
            item.suggested_name = safe_stem + original_suffix
        result.append(item)
    # Files beyond the model prompt cap are not silently omitted from the UI plan.
    for row in rows[150:]:
        result.append(PlanItem(
            original_name=row["name"],
            suggested_name=row["name"],
            category="Unsorted",
            reason="Not sent to model because the batch limit is 150 files",
            confidence=0.0,
        ))
    return result
