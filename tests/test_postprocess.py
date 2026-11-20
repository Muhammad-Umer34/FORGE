"""Post-processors on model-written code (D-229): seeded mistakes are fixed or reported. No model, no Node."""
import pytest

from agents.build_worker import TEMPLATE
from agents.frontend_generator.postprocess import fix_colours, fix_icons, fix_imports, postprocess

FOLDER = "components/custom/custom-card/"
needs_lucide = pytest.mark.skipif(not (TEMPLATE / "node_modules" / "lucide-react").is_dir(),
                                  reason="site_template packages not installed")


def test_unused_imports_are_removed_and_foreign_ones_reported():
    code = ('import { useState, useEffect } from "react"\nimport { Button } from "@/components/ui/button"\n'
            'import axios from "axios"\n\nexport function A() { const [x] = useState(0); return <div>{x}</div> }\n')
    out, fixes, issues = fix_imports(code, FOLDER)
    assert 'import { useState } from "react"' in out and "@/components/ui/button" not in out
    assert any("axios" in i for i in issues) and len(fixes) == 2


@needs_lucide
def test_unknown_icons_become_real_ones_and_are_imported_once():
    code = 'import { Starr, Sparkles, MadeUpIconXyz } from "lucide-react"\nconst a = <><Starr /><MadeUpIconXyz /></>\n'
    out, fixes = fix_icons(code)
    assert "Starr" not in out and "MadeUpIconXyz" not in out and len(fixes) == 2
    assert out.splitlines()[0].count("Sparkles") == 1


def test_greys_become_tokens_and_other_colours_are_issues():
    code = '<div className="bg-gray-50 text-gray-600 border-gray-200 bg-white text-blue-600" style={{color: "#ff0000"}} />'
    out, fixes, issues = fix_colours(code)
    assert "bg-muted text-muted-foreground border-border bg-background" in out
    assert "text-blue-600" in out and issues and "text-blue-600" in issues[0] and "#ff0000" in issues[0]


def test_a_file_outside_the_part_folder_is_rejected():
    files, _, issues = postprocess({"components/Hero.tsx": "x", FOLDER + "custom-card.tsx": "export function A() {}"},
                                   FOLDER)
    assert list(files) == [FOLDER + "custom-card.tsx"] and "components/Hero.tsx" in issues


def test_clickable_divs_are_reported_but_buttons_and_roles_are_not():
    from agents.frontend_generator.postprocess import check_clickables
    code = ('<div className="p-4" onClick={() => toggle(name)}>row</div>\n'
            '<button type="button" onClick={() => toggle(name)}>ok</button>\n'
            '<div role="checkbox" aria-checked={on} onClick={() => toggle(name)}>ok</div>\n')
    issues = check_clickables(code)
    assert len(issues) == 1 and issues[0].startswith("line 1") and "<div>" in issues[0]
