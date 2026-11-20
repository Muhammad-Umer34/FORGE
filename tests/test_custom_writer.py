"""The custom-part writer's contract (D-228), checked without a model: props fixed by code, the page imports a
written part with those props, a missing part falls back, and a reply outside the contract is refused."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_planning import built_plan  # noqa: E402

from agents.frontend_generator.compiler import Site, compile_site  # noqa: E402
from agents.frontend_generator.custom_writer import accept, parts_to_write, props_interface  # noqa: E402


def _part():
    brief, plan = built_plan()
    site = Site(plan, brief.business_type, "x")
    return brief, plan, parts_to_write(plan, site)[0]


def test_props_interface_follows_the_needs():
    code = props_interface("Card", [
        {"name": "title", "kind": "copy", "type": "text"},
        {"name": "stamps_for_reward", "kind": "fact", "type": "number"},
        {"name": "rewards", "kind": "list", "type": "text",
         "item_fields": [{"name": "name", "kind": "fact", "type": "text"}, {"name": "free", "type": "boolean"}]},
        {"name": "onSubmit", "kind": "code", "type": "text"}, {"name": "className", "kind": "setting"}])
    assert "export interface CardProps" in code and "title?: string" in code
    assert "stamps_for_reward?: number" in code and "rewards?: { name?: string; free?: boolean }[]" in code
    assert "onSubmit" not in code and "className" not in code


def test_the_salon_plans_custom_part_has_its_contract():
    _, plan, part = _part()
    spec = plan.custom_specs[0]
    assert (part.kind, part.file, part.export_name) == ("custom", spec.file, spec.export_name)
    assert part.folder == spec.file.rsplit("/", 1)[0] + "/" and "export interface" in part.props_code
    assert spec.purpose in part.brief and part.props_code in part.brief


def test_a_written_part_is_imported_with_its_props_and_a_missing_one_falls_back():
    brief, plan, part = _part()
    with_part = compile_site(plan, brief.business_type, "x",
                             {part.section_id: {"module": part.module, "export_name": part.export_name}})
    home = with_part["app/page.tsx"]
    assert f'import {{ {part.export_name} }} from "{part.module}"' in home and f"<{part.export_name} " in home
    assert "<CtaBanner" in compile_site(plan, brief.business_type, "x")["app/page.tsx"]


def test_replies_outside_the_contract_are_refused():
    _, _, part = _part()
    good = {part.file: f"export function {part.export_name}() {{ return null }}"}
    assert accept(part, good)[0] == good
    assert accept(part, {**good, "components/Hero.tsx": "x"})[0] is None
    assert accept(part, {part.file: "export function Other() {}"})[0] is None
    assert accept(part, {part.folder + "helper.ts": "x"})[0] is None
