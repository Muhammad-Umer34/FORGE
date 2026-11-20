# D:\FYP\FORGE-1\agents\frontend_generator\gate.py
"""
The build gate with fix rounds (D-230). Every site is type-checked and production-built before it is called ready.
When the model-written parts break the build:
1. code first: a TypeScript "Did you mean 'x'?" error is fixed by code at its line, no model call;
2. then up to MAX_ROUNDS model fix rounds per part: only that part's errors from the first failing layer go back,
   with its file and props; a fix that does not reduce its error count is thrown away (the D-214 rule);
3. then a fallback: a part that still fails is dropped and the page shows its fallback section, so the rest of the
   site still builds.
A failure in a code-made file that no part caused is a FORGE bug: the gate stops with a clear message.
"""
import re
from dataclasses import dataclass, field
from typing import Callable

from agents import build_worker
from agents.frontend_generator.custom_writer import Part, accept, system_prompt
from agents.frontend_generator.postprocess import postprocess
from agents.gateway import BudgetExceededError, CallUsage, call_files

TASK = "frontend_fix"
MAX_ROUNDS = 4                                    # D-230 (raised from 2 by the team, 2026-11-14)
MAX_CHECK_ROUNDS = 2                              # code-check issues (colours, keyboard): they never stop a build (D-241)
_DID_YOU_MEAN = re.compile(r"'([\w$]+)'.*Did you mean '([\w$]+)'\?")


@dataclass
class GateResult:
    ok: bool
    files: dict[str, str]                          # the whole site as it last built (or failed)
    written: dict[str, Part]                       # parts still in the site, by section id
    fallbacks: list[tuple[str, str]] = field(default_factory=list)   # (part name, why)
    rounds: int = 0                                # model fix rounds used (build errors and code checks)
    check_rounds: int = 0                          # of which for code-check issues
    code_fixes: int = 0
    builds: int = 0
    usage: list[CallUsage] = field(default_factory=list)
    message: str = ""


def _first_failure(result: build_worker.BuildResult) -> build_worker.Step | None:
    return next((s for s in result.steps if not s.ok), None)


def _owner(issue: build_worker.Issue, parts: dict[str, Part], files: dict[str, str]) -> str | None:
    """The section id of the part an error belongs to: in its folder, or on a page line that uses it."""
    for sid, part in parts.items():
        if issue.file.startswith(part.folder):
            return sid
    line = (files.get(issue.file, "").splitlines() or [""])[max(issue.line - 1, 0):issue.line + 3]
    for sid, part in parts.items():
        if part.export_name in issue.message or any(f"<{part.export_name}" in ln for ln in line):
            return sid
    return None


def _code_fix(files: dict[str, str], issues: list[build_worker.Issue]) -> int:
    """Apply every "Did you mean" the compiler offers, in place; returns how many."""
    done = 0
    for issue in issues:
        m = _DID_YOU_MEAN.search(issue.message)
        if not m or issue.file not in files:
            continue
        lines = files[issue.file].splitlines(keepends=True)
        if 0 < issue.line <= len(lines):
            new = re.sub(rf"(?<![\w$]){re.escape(m.group(1))}(?![\w$])", m.group(2), lines[issue.line - 1], count=1)
            if new != lines[issue.line - 1]:
                lines[issue.line - 1] = new
                files[issue.file] = "".join(lines)
                done += 1
    return done


def _fix_prompt(part: Part, files: dict[str, str], layer: str, issues: list[build_worker.Issue]) -> str:
    errors = "\n".join(f"- {i.file}:{i.line} {i.code} {i.message}".rstrip() for i in issues[:20])
    current = "\n".join(f'<file path="{p}">\n{c}\n</file>' for p, c in files.items() if p.startswith(part.folder))
    return (f"The part below failed the {layer}. Errors:\n{errors}\n\nFix only these errors. Keep its file path, "
            f"export name and props. Return every file of the part, whole.\n\nProps (unchanged):\n```ts\n"
            f"{part.props_code}\n```\n\nCurrent files:\n{current}")


def run_gate(compile_site: Callable[[dict[str, Part]], dict[str, str]], parts: dict[str, Part],
             part_files: dict[str, dict[str, str]], budget_usd: float, progress: Callable[[str], None],
             build: Callable = build_worker.build, build_id: str = "gate") -> GateResult:
    """Build until the site passes, fixing or dropping model-written parts on the way.
    `compile_site(written)` = the code-made files for the parts still in; `part_files` = each part's files."""
    written, files_of = dict(parts), {sid: dict(f) for sid, f in part_files.items()}
    rounds_of = {sid: 0 for sid in parts}
    res = GateResult(False, {}, written)

    def site() -> dict[str, str]:
        out = compile_site(written)
        for sid in written:
            out.update(files_of[sid])
        return out

    def drop(sid: str, why: str) -> None:
        res.fallbacks.append((written[sid].name, why))
        progress(f"Replaced {written[sid].name} with a plain section ({why})")
        written.pop(sid)

    def ask_fix(sid: str, layer: str, issues: list[build_worker.Issue]) -> dict[str, str] | None:
        """One model fix of one part: the cleaned files, or None (no usable reply; over budget drops the part)."""
        part = written[sid]
        try:
            reply, usage = call_files(TASK, system_prompt(), _fix_prompt(part, files_of[sid], layer, issues),
                                      budget_usd - sum(u.cost_usd for u in res.usage))
        except BudgetExceededError:
            drop(sid, "the spending limit was reached")
            return None
        except Exception as error:                     # a broken reply counts as a round that did not help
            progress(f"The fix for {part.name} could not be used ({type(error).__name__})")
            return None
        res.usage.append(usage)
        accepted, why = accept(part, reply)
        if not accepted:
            progress(f"The fix for {part.name} broke its contract ({why}); kept the previous version")
            return None
        return postprocess(accepted, part.folder)[0]

    def check_issues(sid: str, files: dict[str, str]) -> list[build_worker.Issue]:
        found = postprocess(files, written[sid].folder)[2]
        return [build_worker.Issue(path, int((re.match(r"line (\d+)", m) or [0, 1])[1]), 1, m, "CHECK")
                for path, messages in found.items() for m in messages]

    for _ in range(MAX_CHECK_ROUNDS):                  # 0. code checks the build cannot see (keyboard, colours)
        failing = {sid: check_issues(sid, files_of[sid]) for sid in list(written)}
        failing = {sid: issues for sid, issues in failing.items() if issues}
        if not failing:
            break
        for sid, issues in failing.items():
            res.rounds += 1
            res.check_rounds += 1
            progress(f"Fix round for {written[sid].name}: {len(issues)} code-check issue"
                     f"{'s' if len(issues) > 1 else ''} ({issues[0].message[:80]})")
            fixed = ask_fix(sid, "code checks", issues)
            if fixed is not None and len(check_issues(sid, fixed)) < len(issues):
                files_of[sid] = fixed
            elif sid in written:
                progress(f"The fix for {written[sid].name} did not help; kept the previous version")

    tried_code_fix, code_passes, cached = False, 0, None
    while True:
        res.files = site()
        if cached and cached[0] == res.files:          # the last round's check already built exactly this site
            result = cached[1]
        else:
            result = build(res.files, build_id=build_id)
            res.builds += 1
        cached = None
        failed = _first_failure(result)
        if failed is None:
            res.ok = True
            return res
        layer = "type check" if failed.name == "typecheck" else "production build"
        by_part: dict[str, list[build_worker.Issue]] = {}
        orphans = []
        for issue in failed.issues:
            sid = _owner(issue, written, res.files)
            (by_part.setdefault(sid, []) if sid else orphans).append(issue)
        if not by_part:
            if written:                                # unattributed, with model code in: drop it all and retry
                for sid in list(written):
                    drop(sid, f"the {layer} failed without naming a file")
                continue
            first = failed.issues[0] if failed.issues else None
            res.message = (f"The {layer} failed in FORGE's own code"
                           + (f": {first.file}:{first.line} {first.message}" if first else f": {failed.output[-300:]}"))
            return res
        if not tried_code_fix and code_passes < MAX_ROUNDS:   # 1. code first (bounded, so it can never cycle)
            tried_code_fix = True
            fixed = sum(_code_fix(files_of[sid], issues) for sid, issues in by_part.items())
            if fixed:
                code_passes += 1
                res.code_fixes += fixed
                progress(f"Fixed {fixed} error{'s' if fixed > 1 else ''} by code (no model call)")
                continue
        tried_code_fix = False
        candidates: dict[str, dict[str, str]] = {}
        for sid, issues in by_part.items():            # 2. one model fix round for every failing part
            part = written[sid]
            if rounds_of[sid] >= MAX_ROUNDS:
                drop(sid, f"still failing after {MAX_ROUNDS} fix rounds")
                continue
            rounds_of[sid] += 1
            res.rounds += 1
            progress(f"Fix round {rounds_of[sid]} for {part.name}: {len(issues)} error{'s' if len(issues) > 1 else ''}"
                     f" in the {layer}")
            fixed = ask_fix(sid, layer, issues)
            if fixed is not None:
                candidates[sid] = fixed
        if not candidates:
            continue
        trial_of = {**files_of, **candidates}          # all fixes checked by one build
        trial = compile_site(written)
        for sid in written:
            trial.update(trial_of[sid])
        check = build(trial, build_id=build_id)
        res.builds += 1
        after_fail = _first_failure(check)
        for sid in candidates:
            after = 0 if after_fail is None else sum(1 for i in after_fail.issues if _owner(i, written, trial) == sid)
            before = len(by_part[sid])
            if after_fail is None or after < before or (failed.name == "typecheck" and after_fail.name == "build"):
                files_of[sid] = candidates[sid]
            else:
                progress(f"The fix for {written[sid].name} did not help; kept the previous version")
        cached = (site(), check)
