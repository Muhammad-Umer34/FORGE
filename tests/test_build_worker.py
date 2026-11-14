"""The build worker (Phase 3 Group 1, D-231). Parsing and safety need no Node; the real builds run only when the site
template's packages are installed (`npm install` in site_template/), and take about 10 s (type check) and 50 s."""
import os

import pytest

from agents import build_worker as bw

INSTALLED = (bw.TEMPLATE / "node_modules" / "next").is_dir()
needs_node = pytest.mark.skipif(not INSTALLED, reason="site_template/node_modules not installed")


def test_typecheck_errors_become_file_line_and_message():
    out = ("components/custom/loyalty-stamp-card.tsx(14,9): error TS2304: Cannot find name 'stamps'.\n"
           "app\\page.tsx(3,10): error TS2305: Module '\"@/components/Hero\"' has no exported member 'Hro'.\n"
           "Found 2 errors.")
    issues = bw.parse_tsc(out)
    assert [(i.file, i.line, i.column, i.code) for i in issues] == [
        ("components/custom/loyalty-stamp-card.tsx", 14, 9, "TS2304"), ("app/page.tsx", 3, 10, "TS2305")]
    assert issues[0].message == "Cannot find name 'stamps'."


def test_build_errors_become_file_line_and_message():
    out = ("Failed to compile.\n\n./app/page.tsx:2:1\nModule not found: Can't resolve '@/components/Nope'\n"
           "  1 | import x\n> 2 | import { Nope } from \"@/components/Nope\"\n")
    issues = bw.parse_next(out)
    assert (issues[0].file, issues[0].line, issues[0].column) == ("app/page.tsx", 2, 1)
    assert issues[0].message.startswith("Module not found")
    assert bw.parse_next("Error: something odd\n")[0].message == "Error: something odd"   # no location: kept whole


@pytest.mark.parametrize("path", ["../outside.ts", "/abs/../../x.ts", "components/Hero.tsx", "components/ui/button.tsx",
                                  "package.json", "lib/utils.ts", "node_modules/x/index.js"])
def test_site_files_cannot_leave_the_folder_or_replace_the_template(tmp_path, path):
    with pytest.raises(bw.BuildError):
        bw._safe_path(tmp_path, path)


def test_site_files_may_go_anywhere_else_in_the_folder(tmp_path):
    assert bw._safe_path(tmp_path, "components/custom/stamp-card/stamp-card.tsx").name == "stamp-card.tsx"
    assert bw._safe_path(tmp_path, "app/menu/page.tsx").parent.name == "menu"


def test_the_build_gets_no_secrets(monkeypatch):
    monkeypatch.setenv("VERTEX_API_KEY", "secret")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgres://secret")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-secret")
    env = bw.build_env()
    assert not any("secret" in v for v in env.values())
    assert env["NEXT_TELEMETRY_DISABLED"] == "1" and "PATH" in {k.upper() for k in env}


@needs_node
def test_cleanup_never_touches_the_shared_packages():
    folder = bw.prepare({}, "test-cleanup")
    assert (folder / "node_modules" / "next").is_dir() and (folder / "components" / "Hero.tsx").is_file()
    bw.cleanup(folder)
    assert not folder.exists() and (bw.TEMPLATE / "node_modules" / "next").is_dir()


@needs_node
def test_a_broken_file_fails_the_typecheck_with_its_line():
    page = 'import { Hero } from "@/components/Hero"\n\nexport default function P() {\n  return <Hero stamps={3} />\n}\n'
    result = bw.build({"app/page.tsx": page}, "test-broken")
    assert not result.ok and [s.name for s in result.steps] == ["typecheck"]
    assert result.issues and result.issues[0].file == "app/page.tsx" and result.issues[0].line == 4


@needs_node
@pytest.mark.skipif(not os.getenv("FORGE_SLOW_TESTS"), reason="a full next build takes about 50 s; set FORGE_SLOW_TESTS=1")
def test_the_template_site_builds():
    result = bw.build({}, "test-template")
    assert result.ok, result.steps[-1].output
    assert [s.name for s in result.steps] == ["typecheck", "build"]
