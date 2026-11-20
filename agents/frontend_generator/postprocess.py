# D:\FYP\FORGE-1\agents\frontend_generator\postprocess.py
"""
Post-processors (D-229): plain code that cleans every model-written file before any build. Model code errs often in
small, predictable ways; fixing those by code costs nothing, while a build plus a model fix round costs time and money.

Each check fixes what it safely can and reports the rest as an issue, which goes to the build gate's fix round:
1. imports: only allowed modules; unused imports removed;
2. icons: every lucide-react name exists in the installed package, else the closest real name;
3. colours: raw greys, white and black become theme tokens; other raw colours and hex values are issues;
4. paths: a file outside the part's own folder is rejected (the template and library are read-only);
5. packages: only what the site template has installed (no installs);
6. keyboard: a clickable <div> (or span, li…) with no role is reported (found in a live run, 2026-11-20).
"""
import difflib
import re
from functools import lru_cache

from agents.build_worker import TEMPLATE

UI_PARTS = {p.stem for p in (TEMPLATE / "components" / "ui").glob("*.tsx")}
# shortcut: the allow-list is what the template already installs; extra packages need an install step on the worker.
ALLOWED = {"react", "next/link", "lucide-react", "@/lib/utils"} | {f"@/components/ui/{p}" for p in UI_PARTS}
_IMPORT = re.compile(r'^import\s+(?P<what>[\s\S]*?)\s+from\s+["\'](?P<mod>[^"\']+)["\'];?[ \t]*\n?', re.M)
_GREY = r"(?:slate|gray|zinc|neutral|stone)"
_HUE = r"(?:red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)"


@lru_cache(maxsize=1)
def lucide_icons() -> frozenset[str]:
    dts = TEMPLATE / "node_modules" / "lucide-react" / "dist" / "lucide-react.d.ts"
    return frozenset(re.findall(r"declare const (\w+): LucideIcon", dts.read_text(encoding="utf-8")))


def _names(what: str) -> list[tuple[str, str]]:
    """(imported name, local name) of an import clause: `A, { B, C as D }`, `type { E }`, `* as F`."""
    what = re.sub(r"^type\s+", "", what.strip())
    out = []
    braces = re.search(r"\{([^}]*)\}", what)
    if braces:
        for item in braces.group(1).split(","):
            item = re.sub(r"^type\s+", "", item.strip())
            if item:
                parts = re.split(r"\s+as\s+", item)
                out.append((parts[0].strip(), parts[-1].strip()))
    default = re.sub(r"\{[^}]*\}", "", what).strip(" ,")
    if default:
        out.append((default.removeprefix("* as ").strip(), default.removeprefix("* as ").strip()))
    return out


def _used(code: str, name: str) -> bool:
    return len(re.findall(rf"(?<![\w$.]){re.escape(name)}(?![\w$])", code)) > 0


def fix_imports(code: str, folder: str) -> tuple[str, list[str], list[str]]:
    fixes, issues = [], []
    body = _IMPORT.sub("", code)
    for m in list(_IMPORT.finditer(code)):
        mod, what = m.group("mod"), m.group("what")
        own = mod.startswith("./") or mod.startswith("@/" + folder)
        if mod not in ALLOWED and not own:
            issues.append(f"import from '{mod}' is not allowed; use only: {', '.join(sorted(ALLOWED))}")
            continue
        names = _names(what)
        keep = [(a, b) for a, b in names if _used(body, b)]
        if names and not keep:
            code = code.replace(m.group(0), "", 1)
            fixes.append(f"removed unused import from {mod}")
        elif len(keep) < len(names) and "{" in what and not re.sub(r"\{[^}]*\}", "", what).strip(" ,"):
            kind = "import type" if what.strip().startswith("type") else "import"
            items = ", ".join(a if a == b else f"{a} as {b}" for a, b in keep)
            code = code.replace(m.group(0), f'{kind} {{ {items} }} from "{mod}"\n', 1)
            fixes.append(f"removed unused names from {mod}")
    return code, fixes, issues


def fix_icons(code: str) -> tuple[str, list[str]]:
    fixes, real = [], lucide_icons()
    for m in _IMPORT.finditer(code):
        if m.group("mod") != "lucide-react":
            continue
        for name, _local in _names(m.group("what")):
            if name in real or name == "LucideIcon":
                continue
            guess = difflib.get_close_matches(name, real, n=1, cutoff=0.6)
            new = guess[0] if guess and guess[0] not in code else "Sparkles"
            code = re.sub(rf"(?<![\w$]){re.escape(name)}(?![\w$])", new, code)
            fixes.append(f"icon {name} does not exist; used {new}")
    if fixes:   # two wrong names may now be the same real one: import each name once
        for m in _IMPORT.finditer(code):
            if m.group("mod") == "lucide-react" and "{" in m.group("what"):
                items = list(dict.fromkeys(a if a == b else f"{a} as {b}" for a, b in _names(m.group("what"))))
                code = code.replace(m.group(0), f'import {{ {", ".join(items)} }} from "lucide-react"\n', 1)
                break
    return code, fixes


def _grey(prefix: str, shade: int) -> str | None:
    if prefix == "bg":
        return "bg-muted" if shade <= 200 else "bg-foreground" if shade >= 800 else None
    if prefix == "text":
        return "text-muted-foreground" if shade <= 600 else "text-foreground"
    if prefix in ("border", "divide"):
        return f"{prefix}-border"
    if prefix == "ring":
        return "ring-ring"
    return None


def fix_colours(code: str) -> tuple[str, list[str], list[str]]:
    fixes, issues = [], []

    def grey(m: re.Match) -> str:
        new = _grey(m.group("p"), int(m.group("n")))
        if new:
            fixes.append(f"{m.group(0)} -> {new}")
            return new
        return m.group(0)

    code = re.sub(rf"(?<![\w-])(?P<p>bg|text|border|divide|ring)-{_GREY}-(?P<n>\d{{2,3}})(?![\w-])", grey, code)
    for old, new in (("bg-white", "bg-background"), ("text-black", "text-foreground"),
                     ("text-white", "text-primary-foreground"), ("bg-black", "bg-foreground")):
        if re.search(rf"(?<![\w-]){old}(?![\w-])", code):
            code = re.sub(rf"(?<![\w-]){old}(?![\w-])", new, code)
            fixes.append(f"{old} -> {new}")
    left = sorted(set(re.findall(rf"(?<![\w-])[a-z]+-(?:{_HUE}|{_GREY})-\d{{2,3}}(?![\w-])", code)))
    hexes = sorted(set(re.findall(r"#[0-9a-fA-F]{3,8}\b", code)))
    if left or hexes:
        issues.append("raw colours are not allowed, use the theme tokens (bg-primary, text-muted-foreground, "
                      "bg-muted, border-border, text-destructive for errors): " + ", ".join(left + hexes))
    return code, fixes, issues


_NOT_INTERACTIVE = {"div", "span", "li", "p", "section", "article", "td", "tr", "img", "label"}


def check_clickables(code: str) -> list[str]:
    """Clickable elements that a keyboard cannot reach: an onClick on a <div> (or span, li…) with no role. A model
    wrote exactly this for a price calculator: it worked with a mouse, and not at all with a keyboard."""
    issues = []
    for m in re.finditer(r"\bonClick\s*=", code):
        start = code.rfind("<", 0, m.start())
        tag = re.match(r"<([a-z][\w]*)", code[start:start + 20])
        if tag and tag.group(1) in _NOT_INTERACTIVE and "role=" not in code[start:m.start()]:
            line = code.count("\n", 0, m.start()) + 1
            issues.append(f"line {line}: a clickable <{tag.group(1)}> cannot be used with a keyboard; use "
                          f'<button type="button"> (or an <input type="checkbox"> with a <label>) instead')
    return issues


def postprocess(files: dict[str, str], folder: str) -> tuple[dict[str, str], list[str], dict[str, list[str]]]:
    """(cleaned files, what was fixed, issues per file that code could not fix)."""
    out, fixes, issues = {}, [], {}
    for path, code in files.items():
        if not path.startswith(folder):
            issues.setdefault(path, []).append(f"{path} is outside the part's folder {folder}")
            continue
        if path.endswith((".tsx", ".ts")):
            code, f1, i1 = fix_imports(code, folder)
            code, f2 = fix_icons(code)
            code, f3, i3 = fix_colours(code)
            i4 = check_clickables(code)
            fixes += [f"{path}: {f}" for f in f1 + f2 + f3]
            if i1 + i3 + i4:
                issues[path] = i1 + i3 + i4
        out[path] = code
    return out, fixes, issues
