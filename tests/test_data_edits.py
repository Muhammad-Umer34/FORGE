"""The owner's edits on "What your site will keep" (D-244): by code, with undo, refused when they would break things."""
import pytest

from agents.planning import data_edits as de
from agents.planning import data_patterns as dp
from agents.planning.data_edits import DataEdit, EditRefused
from agents.planning.nodes import apply_data_edit
from agents.state import ApiRoute, BuildPlan, FormRule, Limits, PlanningState, RunConfig

LIMITS = Limits()


def _salon(locked=None):
    entities, _ = dp.expand([{"pattern": "appointments"}], locked)
    return entities


def _appt(entities):
    return next(e for e in entities if e.name == "appointments")


def test_add_a_choice_field():
    entities = _salon()
    de.apply_one(entities, DataEdit(op="add_field", entity="appointments", label="Hair length", type="Choice from a list",
                                    options=["Short", "Medium", "Long", "Short"]), LIMITS)
    f = next(f for f in _appt(entities).fields if f.name == "hair_length")
    assert f.type == "choice" and f.options == ["Short", "Medium", "Long"] and not f.required


@pytest.mark.parametrize("edit, says", [
    (DataEdit(op="add_field", entity="appointments", label="Size", type="Choice from a list", options=["One"]), "2 and 20"),
    (DataEdit(op="add_field", entity="appointments", label="", type="Short text"), "Give the new field a name"),
    (DataEdit(op="add_field", entity="appointments", label="Phone", type="Phone"), "already has"),
    (DataEdit(op="add_field", entity="working_hours", label="Note", type="Short text"), "filled in by FORGE"),
    (DataEdit(op="remove_field", entity="appointments", field="phone"), "required"),
    (DataEdit(op="remove_field", entity="appointments", field="start_at"), "needed by a rule"),
    (DataEdit(op="remove_field", entity="appointments", field="service_id"), "needed by a rule"),
    (DataEdit(op="toggle_rule", entity="appointments", rule_id="appointments.end_from_duration", enabled=False), "cannot be turned off"),
    (DataEdit(op="set_number", entity="appointments", rule_id="appointments.lead_time", value=5000), "from 0 to 720"),
    (DataEdit(op="set_number", entity="appointments", rule_id="appointments.status_flow", value=3), "no number"),
    (DataEdit(op="toggle_rule", entity="nowhere", rule_id="x"), "not part of this plan"),
])
def test_edits_that_would_break_things_are_refused(edit, says):
    with pytest.raises(EditRefused, match=says):
        de.apply_one(_salon(), edit, LIMITS)


def test_owner_answers_cannot_be_edited_away():
    entities = _salon({"appointments.lead_time": "24h", "appointments.choose_staff": "yes"})
    with pytest.raises(EditRefused, match="follows one of your answers"):
        de.apply_one(entities, DataEdit(op="set_number", entity="appointments", rule_id="appointments.lead_time", value=1), LIMITS)


def test_numbers_and_toggles_change_the_rule_and_its_sentence():
    entities = _salon()
    de.apply_one(entities, DataEdit(op="set_number", entity="appointments", rule_id="appointments.lead_time", value=4), LIMITS)
    de.apply_one(entities, DataEdit(op="toggle_rule", entity="appointments", rule_id="appointments.within_hours", enabled=False), LIMITS)
    rules = {r.kind: r for r in _appt(entities).rules}
    assert rules["lead_time"].params["hours"] == 4 and rules["lead_time"].label.endswith("at least 4 hours ahead")
    assert rules["within_hours"].enabled is False


def test_replay_is_how_undo_works_and_stale_edits_drop_out():
    base = [e.model_dump(mode="json") for e in _salon()]
    edits = [DataEdit(op="add_field", entity="appointments", label="Hair length", type="Short text").model_dump(),
             DataEdit(op="remove_field", entity="appointments", field="email").model_dump(),
             DataEdit(op="add_field", entity="gone", label="X", type="Short text").model_dump()]
    entities, kept = de.replay(base, edits, LIMITS)
    names = {f.name for f in _appt(entities).fields}
    assert "hair_length" in names and "email" not in names and len(kept) == 2
    entities, _ = de.replay(base, kept[:-1], LIMITS)                         # undo the last
    assert "email" in {f.name for f in _appt(entities).fields}


def test_the_screen_view_explains_what_is_fixed():
    view = {e["name"]: e for e in de.view(_salon({"appointments.choose_staff": "yes"}))}
    fields = {f["name"]: f for f in view["appointments"]["fields"]}
    assert fields["email"]["removable"] and not fields["phone"]["removable"]
    assert fields["staff_id"]["why_fixed"] == "follows one of your answers" and fields["staff_id"]["kind"] == "Staff"
    lead = next(r for r in view["appointments"]["rules"] if r["rule_id"] == "appointments.lead_time")
    assert lead["number"] == {"value": 2, "unit": "hours", "min": 0, "max": 720} and lead["can_toggle"]
    assert not view["working_hours"]["can_add_field"]


def _state():
    entities = _salon()
    plan = BuildPlan(data_entities=entities,
                     api_routes=[ApiRoute(route_id="POST /api/appointments", method="POST", path="/api/appointments",
                                          entity="appointments", request_fields=["client_name"], used_by=["booking.booking"])],
                     form_rules=[FormRule(section_id="booking.booking", route_id="POST /api/appointments")])
    return {"plan": plan, "planning": PlanningState(status="awaiting_approval"), "run_config": RunConfig()}


def test_an_edit_on_the_plan_screen_updates_the_form_contract_and_can_be_undone():
    state = _state()
    out = apply_data_edit(state, state["planning"], DataEdit(op="add_field", entity="appointments", label="Hair length",
                                                             type="Short text"))
    plan, p = out["plan"], out["planning"]
    assert p.status == "awaiting_approval" and p.notice is None and len(p.data_edits) == 1
    post = plan.api_routes[0]
    assert "hair_length" in post.request_fields and "end_at" not in post.request_fields
    assert set(plan.form_rules[0].required_fields) >= {"client_name", "phone", "service_id", "start_at"}
    state["plan"], state["planning"] = plan, p
    out = apply_data_edit(state, p, DataEdit(op="undo"))
    assert out["planning"].data_edits == [] and "hair_length" not in out["plan"].api_routes[0].request_fields


def test_a_refused_edit_leaves_the_plan_and_says_why():
    state = _state()
    out = apply_data_edit(state, state["planning"], DataEdit(op="remove_field", entity="appointments", field="phone"))
    assert "required" in out["planning"].notice and out["planning"].data_edits == []
    assert {f.name for f in _appt(out["plan"].data_entities).fields} == {f.name for f in _appt(_salon()).fields}


def test_the_edit_limit():
    state = _state()
    state["run_config"] = RunConfig(limits=Limits(max_data_edits=1))
    p = state["planning"]
    out = apply_data_edit(state, p, DataEdit(op="add_field", entity="appointments", label="A", type="Short text"))
    state["plan"] = out["plan"]
    out = apply_data_edit(state, out["planning"], DataEdit(op="add_field", entity="appointments", label="B", type="Short text"))
    assert "No more changes" in out["planning"].notice and len(out["planning"].data_edits) == 1


def test_a_rule_is_locked_only_when_every_answer_behind_it_is_the_owners():
    entities = _salon({"appointments.choose_staff": "yes"})            # double booking: "Let FORGE decide"
    rules = {r.kind: r for r in _appt(entities).rules}
    assert not rules["no_overlap"].locked and not rules["within_hours"].locked
    both = _salon({"appointments.choose_staff": "yes", "appointments.double_booking": "one"})
    assert next(r for r in _appt(both).rules if r.kind == "no_overlap").locked


def test_setting_lists_are_not_edited_field_by_field():
    view = {e["name"]: e for e in de.view(_salon())}
    assert all(not f["can_toggle_required"] and f["why_fixed"] == "filled in by FORGE"
               for f in view["working_hours"]["fields"])
    with pytest.raises(EditRefused, match="filled in by FORGE"):
        de.apply_one(_salon(), DataEdit(op="set_required", entity="working_hours", field="day", required=False), LIMITS)
