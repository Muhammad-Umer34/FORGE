# D:\FYP\FORGE-1\agents\database_generator\agent.py
"""
The Database Agent's step in the build (D-242 - D-245). Code only, no model call:
gate (scratch schema, rule tests, rolled back) -> provision the site's own schema -> save the files.
A failing gate is a FORGE bug (all SQL is code-made), so the build stops with a clear message.
"""
from typing import Callable

from agents.database_generator import gate, provision
from agents.file_store import active_store
from agents.planning import data_patterns
from agents.state import AgentArtifacts, BuildPlan, RunConfig

TIME_ZONE = "Asia/Karachi"            # shortcut: one time zone for every site; ask the owner when FORGE serves other countries


class DatabaseBuildError(RuntimeError):
    """The generated schema failed its own checks. Never the user's fault."""


def database_url() -> str:
    """Where sites keep their data: SITE_DB_URL, else FORGE's own database (D-247)."""
    from backend.core.config import settings
    return settings.SITE_DB_URL or settings.SUPABASE_DB_URL


def app_url() -> str:
    from backend.core.config import settings
    return settings.SUPABASE_DB_URL


def run(plan: BuildPlan, request_id: str, project_id: str, config: RunConfig, progress: Callable[[dict], None],
        url: str | None = None, report: dict | None = None, registry_url: str | None = None) -> AgentArtifacts:
    def say(message: str, **extra) -> None:
        progress({"agent": "database", "message": message, **extra})

    if not plan.data_entities:
        say("No data to store: this site only shows information")
        return AgentArtifacts(agent="database", status="done")
    unsafe = data_patterns.problems_in(plan.data_entities)
    if unsafe:                                           # a plan from before D-242 (plain tables, no recipes)
        say(f"Database: this plan's data was designed before recipes and cannot be built ({unsafe[0]}); "
            "plan the site again to get its storage")
        return AgentArtifacts(agent="database", status="failed")
    rules = sum(1 for e in plan.data_entities for r in e.rules if r.enabled)
    n = len(plan.data_entities)
    say(f"Database: designing {n} table{'s' if n != 1 else ''} with {rules} rule{'s' if rules != 1 else ''}")
    if not config.database:
        say("Database: storage is switched off for this run (FORGE_DATABASE=off); files only")
        files = gate.compile_schema(plan.data_entities, provision.schema_for(project_id), TIME_ZONE).files()
        files["db/seed.sql"] = gate.seed_sql(plan.data_entities, provision.schema_for(project_id), TIME_ZONE)
        return _save(request_id, files, "done", report, None)
    url = url or database_url()
    result, _ = gate.run_gate(plan.data_entities, provision.plain_url(url), request_id, TIME_ZONE)
    if report is not None:
        report.update(db_gate=result.ok, db_tables=result.tables, db_rules=result.rules,
                      db_tests=len(result.tests), db_tests_passed=result.passed)
    say(f"Database: {result.passed}/{len(result.tests)} rule tests passed")
    if not result.ok:
        say(f"Database: {result.message}. This is a FORGE bug, not yours.")
        raise DatabaseBuildError(result.message)
    made = provision.provision(plan.data_entities, url, project_id, TIME_ZONE)
    if report is not None:                               # the Backend Agent's gate runs on this storage (D-247)
        report.update(db_role=made["role"], db_contract=made["contract"])
    if made["kept_old_schema"]:
        say(f"Database: your earlier data was kept in {made['kept_old_schema']}")
    from agents import preview                          # the run may have made the key already (D-253)
    key = provision.register(registry_url or app_url(), project_id, made, request_id, preview.site_key(request_id))
    if key:                                              # the live preview's server talks to FORGE with it (D-247)
        preview.set_site_key(request_id, key)
    say("Database: site storage ready")
    return _save(request_id, {**made["files"], "db/seed.sql": made["seed"]}, "done", report, made["schema"])


def _save(request_id: str, files: dict[str, str], status: str, report: dict | None, schema: str | None) -> AgentArtifacts:
    refs = active_store().put(request_id, files, "code", kind="database")
    if report is not None:
        report.update(db_files=len(files), db_schema=schema)
    return AgentArtifacts(agent="database", status=status, files=refs)
