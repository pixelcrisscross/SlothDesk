from pydantic import BaseModel, Field, field_validator
import re

class PlanItem(BaseModel):
    original_name: str
    suggested_name: str
    category: str = "Unsorted"
    reason: str = "Suggested by local model"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    @field_validator("original_name", "suggested_name")
    @classmethod
    def simple_filename(cls, value: str) -> str:
        value = value.strip()
        if not value or value in {".", ".."} or "/" in value or "\\" in value:
            raise ValueError("Expected a filename, not a path.")
        if "\x00" in value:
            raise ValueError("NUL bytes are not allowed.")
        return value

    @field_validator("category")
    @classmethod
    def safe_category(cls, value: str) -> str:
        value = value.strip().replace("\\", "/")
        parts = [p for p in value.split("/") if p not in ("", ".")]
        if not parts or any(p == ".." for p in parts):
            raise ValueError("Invalid category path.")
        if any(":" in p for p in parts):
            raise ValueError("Invalid category path.")
        return "/".join(parts)
