from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from datetime import datetime
import streamlit as st

from slothdesk.scanner import scan_directory, find_exact_duplicates
from slothdesk.ai_planner import plan_organization, OllamaError
from slothdesk.schemas import PlanItem
from slothdesk.safety import validate_plan_item
from slothdesk.executor import apply_plan
from slothdesk.undo import undo_run
from slothdesk.database import init_db, save_run, list_runs, get_run

APP_TITLE = "SlothDesk"
st.set_page_config(page_title=APP_TITLE, page_icon="🦥", layout="wide")
init_db()

st.title("🦥 SlothDesk")
st.caption("A local-first AI file organizer. Qwen suggests; you review; SlothDesk validates and executes.")
st.info("Use a disposable test folder first. This app can move/rename files only after you explicitly approve a plan.")

with st.sidebar:
    st.header("Settings")
    root_text = st.text_input("Folder to organize", value=str(Path.home() / "SlothDesk-Demo"))
    model = st.text_input("Ollama model", value="qwen3:8b")
    st.caption("Ollama must be running locally at http://localhost:11434.")
    st.divider()
    st.subheader("Safety")
    st.write("• No model-generated shell commands")
    st.write("• Plan preview before changes")
    st.write("• Collision and path checks")
    st.write("• Run manifest and undo")
    st.write("• Exact duplicate detection only")

try:
    selected_root = Path(root_text).expanduser().resolve()
except Exception:
    selected_root = Path.home()

if "plan_items" not in st.session_state:
    st.session_state.plan_items = []
if "plan_root" not in st.session_state:
    st.session_state.plan_root = ""
if "last_run_id" not in st.session_state:
    st.session_state.last_run_id = None

tab_plan, tab_runs, tab_about = st.tabs(["Organize files", "Run history / Undo", "About"])

with tab_plan:
    st.subheader("1. Scan a folder")
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Create demo folder with sample files"):
            demo = Path.home() / "SlothDesk-Demo"
            demo.mkdir(parents=True, exist_ok=True)
            samples = {
                "IMG_20261014_093122.pdf": "Sample receipt dated 2026-10-14. This is synthetic demo content.",
                "meeting notes final FINAL.txt": "Sample meeting notes about project planning. Synthetic content.",
                "budget_2026_v3.csv": "item,amount\\nNotebook,120\\nPen,20\\n",
                "screenshot_001.txt": "Synthetic screenshot placeholder notes.",
                "research links.txt": "https://example.com\\nSynthetic research links placeholder.",
            }
            for name, content in samples.items():
                path = demo / name
                if not path.exists():
                    path.write_text(content, encoding="utf-8")
            st.success(f"Demo files created in {demo}. Set the folder field to this path if needed.")
    with c2:
        if st.button("Scan selected folder", type="primary"):
            if not selected_root.exists() or not selected_root.is_dir():
                st.error("That folder does not exist or is not a directory.")
            else:
                st.session_state.scan_root = str(selected_root)
                st.session_state.scan_rows = scan_directory(selected_root)
                st.session_state.plan_items = []
                st.session_state.plan_root = str(selected_root)
                st.success(f"Found {len(st.session_state.scan_rows)} eligible files.")

    scan_rows = st.session_state.get("scan_rows", [])
    if scan_rows and st.session_state.get("scan_root") == str(selected_root):
        st.write(f"**Scanned folder:** `{selected_root}`")
        st.dataframe(scan_rows, use_container_width=True, hide_index=True)
        duplicates = find_exact_duplicates(selected_root, scan_rows)
        if duplicates:
            with st.expander(f"Exact duplicate groups ({len(duplicates)})"):
                for group in duplicates:
                    st.write(" • " + "  |  ".join(group))
        else:
            st.caption("No exact duplicates detected in this scan.")

        st.subheader("2. Generate an AI organization plan")
        st.write("Only filenames and basic metadata are sent to the local Ollama process. File contents are not read by this MVP.")
        if st.button("Ask local Qwen to suggest organization", disabled=not scan_rows):
            with st.spinner(f"Planning with {model} locally…"):
                try:
                    plan = plan_organization(scan_rows, model=model)
                    st.session_state.plan_items = [item.model_dump() for item in plan]
                    st.session_state.plan_root = str(selected_root)
                    st.success(f"Generated {len(plan)} suggestions.")
                except OllamaError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error(f"Planning failed safely: {exc}")

    if st.session_state.plan_items and st.session_state.plan_root == str(selected_root):
        st.subheader("3. Review and approve")
        st.caption("Edit suggested names/categories below. Every item starts unchecked. The app validates the plan again before applying it.")
        edited = []
        for i, raw in enumerate(st.session_state.plan_items):
            item = PlanItem.model_validate(raw)
            with st.container(border=True):
                cols = st.columns([0.7, 2, 2, 1])
                approved = cols[0].checkbox("Apply", key=f"approve_{i}", value=False)
                cols[1].write(f"**Original**\n\n`{item.original_name}`")
                new_name = cols[2].text_input("New filename", value=item.suggested_name, key=f"name_{i}")
                category = cols[3].text_input("Category", value=item.category, key=f"cat_{i}")
                st.caption(f"Reason: {item.reason} · Confidence: {item.confidence:.0%}")
                edited.append({
                    "original_name": item.original_name,
                    "suggested_name": new_name.strip(),
                    "category": category.strip(),
                    "reason": item.reason,
                    "confidence": item.confidence,
                    "approved": approved,
                })

        approved_items = [x for x in edited if x["approved"]]
        st.write(f"Approved changes: **{len(approved_items)}** / {len(edited)}")
        confirm = st.checkbox("I understand files will be moved/renamed in the selected folder.")
        if st.button("Apply approved changes", type="primary", disabled=(not approved_items or not confirm)):
            try:
                validated = []
                for item in approved_items:
                    validated.append(validate_plan_item(selected_root, item))
                result = apply_plan(selected_root, validated)
                run_id = save_run(str(selected_root), model, result)
                st.session_state.last_run_id = run_id
                st.success(f"Applied {result['success_count']} change(s). Run ID: {run_id}")
                if result["errors"]:
                    st.warning("Some changes were skipped: " + "; ".join(result["errors"]))
                st.json(result)
                st.session_state.scan_rows = scan_directory(selected_root)
            except Exception as exc:
                st.error(f"No plan was applied: {exc}")

with tab_runs:
    st.subheader("Previous runs")
    runs = list_runs()
    if not runs:
        st.caption("No runs saved yet.")
    else:
        st.dataframe(runs, use_container_width=True, hide_index=True)
        run_ids = [r["id"] for r in runs]
        chosen = st.selectbox("Choose a run to undo", run_ids, format_func=lambda rid: f"Run {rid} · {next((r['created_at'] for r in runs if r['id']==rid), '')}")
        run_data = get_run(chosen)
        if run_data:
            st.caption(f"Folder: {run_data['root_path']} · Model: {run_data['model']}")
            st.json(run_data["result"])
            confirm_undo = st.checkbox("I have checked the run manifest and want to undo this run.", key="confirm_undo")
            if st.button("Undo selected run", disabled=not confirm_undo):
                try:
                    undo_result = undo_run(run_data["root_path"], run_data["result"])
                    st.success(f"Undo completed: {undo_result['restored']} item(s) restored.")
                    if undo_result["errors"]:
                        st.warning("; ".join(undo_result["errors"]))
                    st.json(undo_result)
                except Exception as exc:
                    st.error(f"Undo stopped safely: {exc}")

with tab_about:
    st.subheader("Local-first by design")
    st.markdown("""
- **Local inference:** sends requests to your local Ollama server.
- **Metadata-only planning:** the MVP does not read document contents.
- **Human approval:** suggestions are not executed automatically.
- **Safety checks:** paths must stay inside the selected folder and collisions are rejected.
- **Undo:** successful operations are recorded in a run manifest.
- **Limitations:** local files are still at risk if the operating system, storage, or application fails. Back up important data.
""")
    st.code("ollama pull qwen3:8b\nstreamlit run app.py", language="bash")
