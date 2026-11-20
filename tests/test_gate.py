"""The build gate's fix rounds (D-230) with fake builds and a fake model: code fixes first, a model fix is kept only
when it helps, a part still failing after 4 rounds falls back, and FORGE's own failures stop the run."""
from agents.build_worker import BuildResult, Issue, Step
from agents.frontend_generator import gate
from agents.frontend_generator.custom_writer import Part
from agents.gateway import CallUsage

PART = Part("home.card", "custom", "Loyalty card", "components/custom/card/card.tsx", "Card",
            "export interface CardProps {}")
GOOD = 'export function Card() { return <section className="bg-muted">ok</section> }\n'
BAD = "export function Card() { return <section>{stmps}</section> }\n"


def _result(*issues: Issue) -> BuildResult:
    if not issues:
        return BuildResult(True, [Step("typecheck", True, 1.0), Step("build", True, 1.0)], 2.0)
    return BuildResult(False, [Step("typecheck", False, 1.0, list(issues))], 1.0)


def _err(file="components/custom/card/card.tsx", msg="Cannot find name 'stmps'.", code="TS2304"):
    return Issue(file, 1, 1, msg, code)


def _builder():
    """A fake build: fails while the part's file holds 'stmps' or 'broken', or the page holds 'pagebug'."""
    calls = []

    def build(files, build_id=None):
        calls.append(files)
        part = files.get(PART.file, "")
        if "pagebug" in files.get("app/page.tsx", ""):
            return _result(_err("app/page.tsx", "Type 'x' is not assignable"))
        return _result(_err()) if ("stmps" in part or "broken" in part) else _result()
    return build, calls


def _run(monkeypatch, part_code, replies, page="export default function P() { return <Card /> }"):
    build, calls = _builder()
    sent = iter(replies)
    monkeypatch.setattr(gate, "call_files", lambda *a, **k: ({PART.file: next(sent)}, CallUsage()))
    compile_site = lambda written: {"app/page.tsx": page if written else "export default function P() {}"}
    lines = []
    res = gate.run_gate(compile_site, {PART.section_id: PART}, {PART.section_id: {PART.file: part_code}}, 1.0,
                        lines.append, build=build)
    return res, calls, lines


def test_a_good_part_passes_with_one_build(monkeypatch):
    res, calls, _ = _run(monkeypatch, GOOD, [])
    assert res.ok and res.builds == 1 and res.rounds == 0 and PART.section_id in res.written


def test_did_you_mean_is_fixed_by_code_without_a_model_call(monkeypatch):
    monkeypatch.setattr(gate, "_DID_YOU_MEAN", gate._DID_YOU_MEAN)
    build, _ = _builder()

    def build_with_hint(files, build_id=None):
        r = build(files)
        if not r.ok:
            r.steps[0].issues = [_err(msg="Cannot find name 'stmps'. Did you mean 'stamps'?", code="TS2552")]
        return r
    res = gate.run_gate(lambda w: {}, {PART.section_id: PART}, {PART.section_id: {PART.file: BAD}}, 1.0,
                        lambda m: None, build=build_with_hint)
    assert res.ok and res.code_fixes == 1 and res.rounds == 0 and "stamps" in res.files[PART.file]


def test_a_model_fix_that_helps_is_kept(monkeypatch):
    res, _, lines = _run(monkeypatch, BAD, [GOOD])
    assert res.ok and res.rounds == 1 and res.files[PART.file] == GOOD
    assert any("Fix round 1" in line for line in lines)


def test_a_part_still_failing_after_4_rounds_falls_back(monkeypatch):
    res, _, lines = _run(monkeypatch, BAD, [BAD.replace("stmps", "broken")] * 4)
    assert res.ok and res.rounds == 4 and PART.section_id not in res.written
    assert res.fallbacks and "4 fix rounds" in res.fallbacks[0][1] and PART.file not in res.files
    assert any("did not help" in line for line in lines)


def test_a_failure_in_forge_code_stops_with_a_message(monkeypatch):
    build, _ = _builder()
    res = gate.run_gate(lambda w: {"app/layout.tsx": "x"}, {}, {}, 1.0, lambda m: None,
                        build=lambda files, build_id=None: _result(_err("app/layout.tsx", "boom")))
    assert not res.ok and "FORGE's own code" in res.message and "app/layout.tsx" in res.message


def test_a_code_check_issue_gets_a_fix_round_and_a_better_fix_is_kept(monkeypatch):
    clickable = 'export function Card() { return <div onClick={() => go()}>row</div> }\n'
    res, _, lines = _run(monkeypatch, clickable, [GOOD])
    assert res.ok and res.check_rounds == 1 and res.files[PART.file] == GOOD
    assert any("code-check issue" in line for line in lines)


def test_code_check_issues_never_drop_a_part(monkeypatch):
    clickable = 'export function Card() { return <div onClick={() => go()}>row</div> }\n'
    res, _, _ = _run(monkeypatch, clickable, [clickable, clickable])
    assert res.ok and res.check_rounds == 2 and PART.section_id in res.written and not res.fallbacks
