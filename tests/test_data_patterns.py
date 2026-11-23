"""Data recipes (D-242): every recipe expands into a data model the SQL compiler can rely on, for every switch value."""
import itertools

import pytest

from agents.planning import data_patterns as dp
from agents.state import BuildPlan, DataEntity, DataField


def _combos(recipe):
    ids = [s["id"] for s in recipe["switches"]]
    for values in itertools.product(*[[o["value"] for o in s["options"]] for s in recipe["switches"]]):
        yield dict(zip(ids, values))


@pytest.mark.parametrize("pattern_id", sorted(dp.load()))
def test_every_switch_combination_expands_cleanly(pattern_id):
    recipe = dp.load()[pattern_id]
    for switches in _combos(recipe):
        entities, problems = dp.expand([{"pattern": pattern_id, "switches": switches}])
        assert not problems, (switches, problems)
        assert entities, switches
        assert dp.problems_in(entities) == [], (switches, dp.problems_in(entities))
        for e in entities:
            assert e.label and e.pattern == pattern_id
            if e.role == "submission" and not e.name.endswith("_items"):
                assert any(r.kind == "status_flow" for r in e.rules), (e.name, switches)
            assert all(r.label and r.rule_id for r in e.rules)


def test_recipe_file_is_well_formed():
    families = set()
    for p in dp.load().values():
        families.add(p["family"])
        for s in p["switches"]:
            assert s["default"] in {o["value"] for o in s["options"]}, (p["id"], s["id"])
            assert s["question"].endswith("?")
        assert sum(o.get("recommended", False) for s in p["switches"] if s.get("ask") for o in s["options"]) \
            == sum(1 for s in p["switches"] if s.get("ask")), p["id"]
    assert families == {"messages", "time_bookings", "sessions", "orders_quotes", "catalogues", "applications"}


def _salon(locked=None, **switches):
    entities, problems = dp.expand([{"pattern": "appointments", "switches": switches, "feature_ids": ["booking"],
                                     "names": {"staff": "stylists"}, "labels": {"staff": "Stylists"}}], locked)
    assert not problems
    return {e.name: e for e in entities}


def test_salon_with_stylists_gets_the_six_rules():
    e = _salon()
    assert set(e) == {"services", "stylists", "working_hours", "days_off", "appointments"}
    appt = e["appointments"]
    assert {r.kind for r in appt.rules} == {"end_from_duration", "no_overlap", "within_hours", "lead_time",
                                            "max_advance", "status_flow"}
    staff = next(f for f in appt.fields if f.name == "staff_id")
    assert staff.reference == "stylists"                       # renamed everywhere
    labels = {r.kind: r.label for r in appt.rules}
    assert labels["no_overlap"] == "No two appointments for the same stylist at overlapping times"
    assert labels["lead_time"] == '"Date and time" must be at least 2 hours ahead'
    assert labels["max_advance"] == '"Date and time" can be at most 60 days ahead'
    assert "stylists" in appt.links and appt.feature_ids == ["booking"]
    assert all(f.personal for f in appt.fields if f.name in ("client_name", "phone", "email"))


def test_any_free_person_drops_staff_and_overlaps_globally():
    e = _salon(choose_staff="no")
    assert "stylists" not in e
    assert all(f.name != "staff_id" for f in e["appointments"].fields)
    overlap = next(r for r in e["appointments"].rules if r.kind == "no_overlap")
    assert "resource" not in overlap.params and overlap.label == "No two appointments at overlapping times"


def test_owner_answer_beats_the_model_and_is_locked():
    e = _salon(locked={"appointments.lead_time": "24h", "appointments.choose_staff": "yes"},
               lead_time="1h", choose_staff="no")
    appt = e["appointments"]
    lead = next(r for r in appt.rules if r.kind == "lead_time")
    assert lead.params["hours"] == 24 and lead.locked and lead.label == '"Date and time" must be at least 1 day ahead'
    assert next(f for f in appt.fields if f.name == "staff_id").locked


def test_unknown_switch_values_are_reported_and_defaulted():
    entities, problems = dp.expand([{"pattern": "appointments", "switches": {"lead_time": "5h", "colour": "red"}}])
    assert any("no option '5h'" in p for p in problems) and any("no switch 'colour'" in p for p in problems)
    lead = next(r for e in entities for r in e.rules if r.kind == "lead_time")
    assert lead.params["hours"] == 2                             # the default


def test_two_recipes_making_the_same_table_is_a_problem():
    _, problems = dp.expand([{"pattern": "contact"}, {"pattern": "contact"}])
    assert any("both make 'contact_messages'" in p for p in problems)


def test_classes_waitlist_and_restaurant_seats():
    e = {x.name: x for x in dp.expand([{"pattern": "classes", "switches": {"seats": "25"}}])[0]}
    cap = next(r for r in e["registrations"].rules if r.kind == "capacity")
    assert cap.params["overflow"] == "waitlist" and next(f for f in e["sessions"].fields if f.name == "capacity").default == "25"
    assert cap.label == 'Each class time takes at most its "Places"; extra bookings go on the waitlist'
    r = {x.name: x for x in dp.expand([{"pattern": "table_reservations", "switches": {"seats": "none"}}])[0]}
    assert not any(x.kind == "capacity" for x in r["reservations"].rules)
    party = next(f for f in r["reservations"].fields if f.name == "party_size")
    assert party.max == 10 and party.min == 1


def test_recipes_for_a_feature_prefer_the_business():
    assert dp.recipes_for("booking", "Italian restaurant")[0] == "table_reservations"
    assert dp.recipes_for("booking", "hair salon")[0] == "appointments"
    assert dp.recipes_for("booking", "car rental")[0] == "rentals"
    assert dp.recipes_for("booking", "yoga studio")[0] == "classes"
    assert dp.recipes_for("contact-form", None)[0] == "contact"


@pytest.mark.parametrize("entity, expected", [
    (DataEntity(name="order", fields=[DataField(name="x", type="text")]), "26: record type name 'order'"),
    (DataEntity(name="a", fields=[DataField(name="select", type="text")]), "26: field name 'a.select'"),
    (DataEntity(name="a", fields=[DataField(name="b_id", type="reference", reference="nowhere")]), "20:"),
    (DataEntity(name="a", fields=[DataField(name="size", type="choice", options=["One"])]), "23:"),
    (DataEntity(name="a", fields=[DataField(name="Bad Name", type="text")]), "26:"),
])
def test_unsafe_or_broken_models_are_caught(entity, expected):
    assert any(p.startswith(expected) for p in dp.problems_in([entity])), dp.problems_in([entity])


def test_required_link_loop_is_caught():
    a = DataEntity(name="a", fields=[DataField(name="b_id", type="reference", reference="b")])
    b = DataEntity(name="b", fields=[DataField(name="a_id", type="reference", reference="a")])
    assert any(p.startswith("21:") for p in dp.problems_in([a, b]))


def test_old_plans_without_v2_fields_still_load():
    plan = BuildPlan.model_validate({"data_entities": [{"name": "booking_requests", "fields": [
        {"name": "full_name", "type": "text", "personal": True}, {"name": "date", "type": "date"}]}]})
    e = plan.data_entities[0]
    assert e.role == "submission" and e.rules == [] and e.fields[0].options == []


def test_a_catalogue_list_that_clashes_with_a_recipes_own_list_gives_way():
    """Live (pet groomer): the model added the catalogue recipe renamed to "services" next to appointments."""
    entities, problems = dp.expand([{"pattern": "catalogue", "names": {"listings": "services"}},
                                    {"pattern": "appointments"}])
    assert problems == []
    services = next(e for e in entities if e.name == "services")
    assert services.pattern == "appointments" and any(f.name == "duration" for f in services.fields)
    assert dp.problems_in(entities) == []
