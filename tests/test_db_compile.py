"""The SQL compiler (D-242, D-245): every recipe compiles, every rule becomes a named object, nothing unsafe gets in."""
import itertools

import pytest

from agents.database_generator.compile import UnsafeName, compile_schema, ident, literal, rule_name
from agents.planning import data_patterns as dp
from agents.state import DataEntity, DataField, DataRule


def _combos(recipe):
    ids = [s["id"] for s in recipe["switches"]]
    for values in itertools.product(*[[o["value"] for o in s["options"]] for s in recipe["switches"]]):
        yield dict(zip(ids, values))


@pytest.mark.parametrize("pattern_id", sorted(dp.load()))
def test_every_recipe_compiles_for_every_switch_combination(pattern_id):
    for switches in _combos(dp.load()[pattern_id]):
        entities, _ = dp.expand([{"pattern": pattern_id, "switches": switches}])
        for gist in (True, False):
            out = compile_schema(entities, "check_test", gist=gist)
            assert out.schema_sql.count("CREATE TABLE") >= len(entities)
            made = {m["rule_id"] for m in out.rules}
            assert made == {r.rule_id for e in entities for r in e.rules}, switches
            assert all(rule_name(r) in out.schema_sql for r in made)
            assert out.er.startswith("erDiagram")
            assert {t["name"] for t in out.schema_json["tables"]} == {e.name for e in entities}


def _salon():
    entities, _ = dp.expand([{"pattern": "appointments", "names": {"staff": "stylists"}}])
    return compile_schema(entities, "site_abc123")


def test_salon_schema_has_links_choices_and_rules():
    sql = _salon().schema_sql
    assert 'CREATE TABLE "site_abc123"."appointments"' in sql
    assert 'REFERENCES "site_abc123"."stylists" (id) ON DELETE RESTRICT' in sql
    assert '"status" IN (\'New\', \'Confirmed\', \'Done\', \'Cancelled\', \'No-show\')' in sql
    assert 'CREATE TABLE "site_abc123"."stylists__services"' in sql            # many services per stylist
    assert "EXCLUDE USING gist" in sql and "CREATE EXTENSION IF NOT EXISTS btree_gist" in sql
    assert "make_interval(mins => d.\"duration\")" in sql                      # end time from the service
    assert sql.index('"a_r_appointments__end_from_duration"') < sql.index('"c_r_appointments__within_hours"')
    assert "FORGE_RULE:appointments.lead_time" in sql and "'Asia/Karachi'" in sql


def test_without_btree_gist_overlap_is_a_locked_trigger():
    entities, _ = dp.expand([{"pattern": "appointments"}])
    sql = compile_schema(entities, "site_x", gist=False).schema_sql
    assert "EXCLUDE" not in sql and "btree_gist" not in sql
    assert "pg_advisory_xact_lock" in sql and "FORGE_RULE:appointments.no_overlap" in sql


def test_contract_lists_rules_with_their_error_names():
    contract = _salon().schema_json
    appt = next(t for t in contract["tables"] if t["name"] == "appointments")
    lead = next(r for r in appt["rules"] if r["kind"] == "lead_time")
    assert lead["error"] == "FORGE_RULE:appointments.lead_time" and lead["label"].endswith("2 hours ahead")
    assert next(c for c in appt["columns"] if c["name"] == "phone")["personal"] is True


@pytest.mark.parametrize("name", ["order", "user", "x; DROP TABLE y", 'a"b', "Bad", "", "a" * 64])   # over PostgreSQL's 63
def test_unsafe_identifiers_are_refused(name):
    with pytest.raises(UnsafeName):
        ident(name)


def test_values_are_escaped_and_nul_is_refused():
    assert literal("O'Brien") == "'O''Brien'"
    assert literal("'); DROP SCHEMA x; --") == "'''); DROP SCHEMA x; --'"
    assert literal(True) == "true" and literal(2.0) == "2" and literal(None) == "NULL"
    with pytest.raises(UnsafeName):
        literal("a\x00b")
    with pytest.raises(UnsafeName):
        literal(float("nan"))


def test_hostile_choice_options_stay_inside_quotes():
    e = DataEntity(name="notes", fields=[DataField(name="kind", type="choice", options=["a'); DROP TABLE x; --", "b"])])
    sql = compile_schema([e], "site_x").schema_sql
    assert "'a''); DROP TABLE x; --'" in sql and "DROP TABLE x;\n" not in sql


def test_unsafe_schema_name_or_time_zone_is_refused():
    with pytest.raises(UnsafeName):
        compile_schema([], "public")
    with pytest.raises(UnsafeName):
        compile_schema([], "site_x", tz="UTC'; DROP")


def test_disabled_rules_are_not_compiled():
    entities, _ = dp.expand([{"pattern": "appointments"}])
    appt = next(e for e in entities if e.name == "appointments")
    next(r for r in appt.rules if r.kind == "lead_time").enabled = False
    out = compile_schema(entities, "site_x")
    assert "FORGE_RULE:appointments.lead_time" not in out.schema_sql
    assert "appointments.lead_time" not in {m["rule_id"] for m in out.rules}


def test_custom_record_type_with_its_own_rules():
    pets = DataEntity(name="pets", label="Pets", role="submission", fields=[
        DataField(name="pet_name", type="text", label="Pet name"),
        DataField(name="age", type="number", min=0, max=40, required=False),
        DataField(name="status", type="choice", options=["New", "Done"], default="New")],
        rules=[DataRule(rule_id="pets.range", kind="range", params={"field": "age", "min": 0, "max": 30}),
               DataRule(rule_id="pets.status_flow", kind="status_flow", params={"field": "status", "moves": {"New": ["Done"]}})])
    sql = compile_schema([pets], "site_x").schema_sql
    assert '"age" BETWEEN 0 AND 30' in sql and '"age" >= 0' in sql and '"age" <= 40' in sql
    assert "FORGE_RULE:pets.status_flow" in sql


def test_a_long_table_name_still_gets_its_rules():
    """Live eval (journal #34): 'grooming_appointments' + 'end_from_duration' made a 42-character rule name, which
    the 41-character name check refused."""
    entities, _ = dp.expand([{"pattern": "appointments", "names": {"appointments": "grooming_appointments"}}])
    out = compile_schema(entities, "site_abc123")
    assert '"r_grooming_appointments__end_from_duration"' in out.schema_sql
    # triggers fire by name, so the end time (a_) must still come before the opening-hours check (c_)
    assert '"a_r_grooming_appointments__end_from_duration"' in out.schema_sql
    with pytest.raises(UnsafeName):
        ident("r_" + "x" * 62)          # 64 characters
