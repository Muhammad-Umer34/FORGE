# D:\FYP\FORGE-1\scripts\run_forge_once.py
"""
Run the FORGE graph once in the terminal and save the final LangGraph state as JSON.
No website, sign-in or database: the graph runs with an in-memory checkpointer, and you answer
the questions and the confirmation screen by typing. Real Gemini calls are made (uses credits).

Run from the FORGE-1 folder:
    .venv\\Scripts\\python.exe scripts\\run_forge_once.py
    .venv\\Scripts\\python.exe scripts\\run_forge_once.py "a website for my hair salon with online booking"
"""
import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer  # noqa: E402
from langgraph.types import Command  # noqa: E402
from pydantic import BaseModel, ValidationError  # noqa: E402

from agents.clarification import slots  # noqa: E402
from agents.clarification.schemas import ConfirmationDecision, UserAnswer  # noqa: E402
from agents.orchestrator import build_forge_graph  # noqa: E402
from agents.state import Question, RequestInfo, initial_state, msgpack_allowlist  # noqa: E402
from backend.routes.requests import _run_config  # noqa: E402  the same run settings the API uses

OUTPUT_DIR = ROOT / "scripts" / "runs"   # gitignored


def to_json(value):
    """The state holds Pydantic models, enums and dates; turn everything into plain JSON."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {k: to_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):  # enums
        return value.value
    return value


def ask_question(payload: dict) -> dict:
    question = Question.model_validate({k: v for k, v in payload.items() if k != "type"})
    print(f"\nQUESTION {payload['number']} of {payload['max_questions']}: {question.text}")
    for n, option in enumerate(question.options, 1):
        print(f"  {n}. {option.label}{'  (recommended)' if option.recommended else ''}")
    hints = ["numbers" + (" separated by commas" if question.multi_select else "")]
    if question.allow_you_decide:
        hints.append("'d' = you decide")
    if question.allow_other_text:
        hints.append("or type your own answer")
    while True:
        raw = input(f"Your answer ({', '.join(hints)}): ").strip()
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if raw.lower() == "d":
            answer = UserAnswer(question_id=question.question_id, kind="you_decide")
        elif parts and all(p.isdigit() and 1 <= int(p) <= len(question.options) for p in parts):
            answer = UserAnswer(question_id=question.question_id, kind="option",
                                option_ids=[question.options[int(p) - 1].option_id for p in parts])
        else:
            try:
                answer = UserAnswer(question_id=question.question_id, kind="other", text=raw)
            except ValidationError as error:
                print(f"  Not accepted: {error.errors()[0]['msg']}")
                continue
        error = slots.validate_answer(question, answer)   # the same check the API runs
        if error is None:
            return answer.model_dump()
        print(f"  Not accepted: {error}")


def ask_confirmation(payload: dict) -> dict:
    print("\nCONFIRMATION\n" + payload["summary"])
    print("Pages:", ", ".join(payload["pages"]))
    print("Features:", ", ".join(f["name"] for f in payload["features"]))
    for item in payload["limits_notice"]:
        print(f"Not included: {item['asked']} - {item['reason']}")
    for n, theme in enumerate(payload["themes"], 1):
        mark = "  (selected)" if theme["id"] == payload["theme_selected"] else ""
        print(f"  Theme {n}: {theme['label']} - {theme['fonts']['heading']} / {theme['fonts']['body']}{mark}")
    choices = [a for a in payload["actions"] if a in ("confirm", "edit", "cancel")]
    while True:
        action = input(f"Type {' / '.join(choices)}: ").strip().lower()
        if action not in choices:
            continue
        decision = {"decision": action}
        if action == "edit":
            decision["edit_text"] = input("What should change? ").strip()
        if action == "confirm":
            pick = input("Theme number (Enter keeps the selected one): ").strip()
            if pick.isdigit() and 1 <= int(pick) <= len(payload["themes"]):
                decision["theme_id"] = payload["themes"][int(pick) - 1]["id"]
        try:
            return ConfirmationDecision(**decision).model_dump()
        except ValidationError as error:
            print(f"  Not accepted: {error.errors()[0]['msg']}")


async def main() -> None:
    prompt = " ".join(sys.argv[1:]).strip() or input("Describe the website you want: ").strip()
    request_id = f"req_local_{uuid.uuid4().hex[:8]}"
    saver = InMemorySaver(serde=JsonPlusSerializer(allowed_msgpack_modules=msgpack_allowlist()))
    graph = build_forge_graph().compile(checkpointer=saver)
    config = {"configurable": {"thread_id": request_id}}

    graph_input = initial_state(
        RequestInfo(request_id=request_id, user_id="local-dev", project_id="local-dev", prompt=prompt,
                    created_at=datetime.now(timezone.utc)),
        config=_run_config(),
    )
    while True:
        print("\n... FORGE is working ...")
        await graph.ainvoke(graph_input, config)
        snapshot = await graph.aget_state(config)
        if not snapshot.interrupts:
            break
        payload = snapshot.interrupts[0].value
        answer = ask_question(payload) if payload.get("type") == "question" else ask_confirmation(payload)
        graph_input = Command(resume=answer)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / f"{request_id}.json"
    out.write_text(json.dumps(to_json(snapshot.values), indent=2, ensure_ascii=False), encoding="utf-8")

    values = snapshot.values
    print("\nDONE")
    print("Clarification status:", values["clarification"].status)
    print("Stage now:", to_json(values["control"].stage))
    if values.get("brief"):
        brief = values["brief"]
        print(f"Brief: {len(brief.features)} features, {len(brief.pages)} pages, {len(brief.test_cases)} tests")
    print("Model calls:", values["usage"].calls if values.get("usage") else "n/a")
    print("Full final state saved to:", out)


if __name__ == "__main__":
    asyncio.run(main())
