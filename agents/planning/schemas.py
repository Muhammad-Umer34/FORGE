# D:\FYP\FORGE-1\agents\planning\schemas.py
"""
What the Planning Agent's model calls must return (plan v2 §5). Kept flat: no free dictionaries and no
recursive types, so every output can be checked field by field.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field

from agents.state import ApiRoute, DashboardView, DataEntity, FieldType, FormRule, NeedKind, PlannedPage


class SettingOut(BaseModel):
    name: str                                  # a component input of kind "setting", e.g. "layout"
    value: str


class SectionOut(BaseModel):
    """One feature section. Layout parts (header, footer, hero, page headers) are added by code."""
    page_id: str
    feature_id: str                            # a feature of the brief
    component_id: Optional[str] = None         # one of the found components; empty when custom
    custom_spec_id: Optional[str] = None       # set when the section is a custom part
    settings: list[SettingOut] = Field(default_factory=list)
    rationale: str = ""


class ItemFieldOut(BaseModel):
    name: str
    kind: Literal["fact", "image", "setting", "code"] = "fact"
    type: FieldType = "text"
    required: bool = True


class NeedOut(BaseModel):
    name: str                                  # snake_case, e.g. "stamps_for_reward"
    kind: NeedKind
    label: str = ""                            # what the owner sees in the form
    type: FieldType = "text"
    required: bool = True
    max_length: Optional[int] = None           # for copy
    content_key: Optional[str] = None          # a catalogue content key when one fits
    item_fields: list[ItemFieldOut] = Field(default_factory=list)   # for kind "list"


class CustomSpecOut(BaseModel):
    spec_id: str
    feature_id: str
    name: str
    page_id: str
    purpose: str
    behaviour: list[str] = Field(default_factory=list)
    needs: list[NeedOut] = Field(default_factory=list)
    ui_notes: str = ""


class SiteDesign(BaseModel):
    """Call 1: pages, sections in order, component choices, settings and custom parts."""
    pages: list[PlannedPage]
    sections: list[SectionOut]                 # top to bottom on each page
    footer_links: list[str] = Field(default_factory=list)   # page ids
    custom_specs: list[CustomSpecOut] = Field(default_factory=list)
    unsure: list[str] = Field(default_factory=list)         # choices made without enough information


class DataDesign(BaseModel):
    """Call 2: what the site stores and the contract between its frontend and backend."""
    entities: list[DataEntity] = Field(default_factory=list)
    routes: list[ApiRoute] = Field(default_factory=list)
    form_rules: list[FormRule] = Field(default_factory=list)
    dashboard_views: list[DashboardView] = Field(default_factory=list)


class PlanFix(BaseModel):
    """A fix round or a user change: the whole corrected design."""
    site: SiteDesign
    data: DataDesign = Field(default_factory=DataDesign)


class TextOut(BaseModel):
    slot_id: str
    text: str


class SiteTexts(BaseModel):
    """Call 3: every text slot, plus three hero headlines, best first."""
    hero_headlines: list[str] = Field(default_factory=list)
    texts: list[TextOut] = Field(default_factory=list)


class PlanDecision(BaseModel):
    """The user's answer on the plan screen."""
    decision: Literal["approve", "change", "cancel"]
    change_text: Optional[str] = None
