"""Plan checks 20-28 (D-242): record types made from recipes are safe to compile and keep the owner's answers."""
from agents.planning import data_patterns as dp
from agents.planning.checks import _data_model
from agents.state import BuildPlan, ClarifiedBrief, DataEntity, DataField, Limits


def _plan(switches=None, locked=None):
    inst = {"pattern": "appointments", "switches": switches or {}, "feature_ids": ["booking"]}
    entities, problems = dp.expand([inst], locked)
    assert not problems
    values, _ = dp.resolve_switches(dp.load()["appointments"], inst["switches"], locked or {})
    return BuildPlan(data_entities=entities, data_recipes=[{**inst, "switches": values}])


def _numbers(plan, brief=None, limits=None):
    return sorted({p.split(":")[0] for p in _data_model(plan, brief or ClarifiedBrief(), limits or Limits())})


def test_a_recipe_plan_passes_every_data_check():
    assert _data_model(_plan(), ClarifiedBrief(), Limits()) == []


def test_plans_from_before_recipes_are_left_alone():
    old = BuildPlan(data_entities=[DataEntity(name="order", fields=[DataField(name="status", type="choice")])])
    assert _data_model(old, ClarifiedBrief(), Limits()) == []


def test_personal_data_must_be_marked():
    plan = _plan()
    appt = next(e for e in plan.data_entities if e.name == "appointments")
    next(f for f in appt.fields if f.name == "phone").personal = False
    assert _numbers(plan) == ["24"]


def test_submissions_need_a_status_and_its_moves():
    plan = _plan()
    appt = next(e for e in plan.data_entities if e.name == "appointments")
    appt.rules = [r for r in appt.rules if r.kind != "status_flow"]
    assert _numbers(plan) == ["25"]
    appt.fields = [f for f in appt.fields if f.name != "status"]
    assert "25" in _numbers(plan)


def test_child_rows_of_a_submission_need_no_status():
    entities, _ = dp.expand([{"pattern": "orders"}])
    plan = BuildPlan(data_entities=entities, data_recipes=[{"pattern": "orders", "switches": {}}])
    assert _data_model(plan, ClarifiedBrief(), Limits()) == []          # order_items has no status


def test_size_limits():
    plan = _plan()
    assert _numbers(plan, limits=Limits(max_fields_per_entity=3, max_rules_per_entity=2)) == ["27"]
    plan.data_entities[0].pattern = "custom"
    assert _numbers(plan, limits=Limits(max_custom_entities=0)) == ["27"]


def test_owner_answers_must_be_kept():
    brief = ClarifiedBrief(data_choices={"appointments.choose_staff": "yes"})
    assert _data_model(_plan(locked=brief.data_choices), brief, Limits()) == []
    drifted = _plan(switches={"choose_staff": "no"})                  # planned without the owner's answer
    assert _numbers(drifted, brief) == ["28"]


def test_compile_problems_are_reported_through_the_plan_checks():
    plan = _plan()
    plan.data_entities[0].fields.append(DataField(name="select", type="text"))
    assert "26" in _numbers(plan)


def test_visitor_details_must_have_a_field():
    """Live (pet groomer, D-246): the request named the pet's name, breed and age; the plan kept none of them."""
    brief = ClarifiedBrief(visitor_details=["pet's name", "pet's breed", "pet's age"])
    plan = _plan()
    assert _numbers(plan, brief) == ["30"]
    assert sum(p.startswith("30:") for p in _data_model(plan, brief, Limits())) == 3
    appt = next(e for e in plan.data_entities if e.name == "appointments")
    appt.fields += [DataField(name="pet_breed", label="Pet's breed", type="text"),
                    DataField(name="pet_age", label="Age of your pet", type="number")]
    assert [p for p in _data_model(plan, brief, Limits()) if p.startswith("30:")] == [
        "30: the request says visitors give 'pet's name', but no field holds it; add it to the record type they send"]
    plan.data_entities.append(DataEntity(name="pets", label="Pets", pattern="custom", role="catalogue",
                                         fields=[DataField(name="name", type="text")]))
    assert _data_model(plan, brief, Limits()) == []                 # "name" on "pets" holds "pet's name"


def test_detail_matching_needs_every_word():
    entities = _plan().data_entities
    assert dp.detail_covered("phone", entities)                       # appointments.phone
    assert not dp.detail_covered("pet's name", entities)              # client_name is not the pet's name
    assert not dp.detail_covered("car model", entities)
