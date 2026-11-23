# D:\FYP\FORGE-1\agents\planning\schemas.py
"""
What the Planning Agent's model calls must return (plan v2 §5). Kept flat: no free dictionaries and no
recursive types, so every output can be checked field by field.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field

from agents.planning.data_edits import DataEdit

from agents.state import (
    ApiRoute, DashboardView, DataEntity, DataField, DataFieldType, DataRule, DesignDirection, FieldType, FormRule,
    NeedKind, PlannedPage, RuleKind,
)


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
    showcase: Optional[str] = None             # a reason to write this section fresh for this site (D-224), or null


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
    sends: list[str] = Field(default_factory=list)   # fields it sends to the site's backend, if it is a form


class DirectionChangeOut(BaseModel):
    field: str                                 # one of the direction choices
    reason: str                                # why this business needs it, one line


class SiteDesign(BaseModel):
    """Call 1: pages, sections in order, component choices, settings and custom parts."""
    pages: list[PlannedPage]
    sections: list[SectionOut]                 # top to bottom on each page
    footer_links: list[str] = Field(default_factory=list)   # page ids
    custom_specs: list[CustomSpecOut] = Field(default_factory=list)
    direction: Optional[DesignDirection] = None              # the site's shape (D-224); set chosen=true
    direction_changes: list[DirectionChangeOut] = Field(default_factory=list)   # changes to the start (D-239)
    unsure: list[str] = Field(default_factory=list)         # choices made without enough information


# ---------------------------------------------------------------- call 2: data, from recipes (D-242)
class SwitchValue(BaseModel):
    switch: str                                # a switch id of the recipe
    value: str                                 # one of its option values


class Rename(BaseModel):
    entity: str                                # a record type the recipe makes, e.g. "staff"
    name: str = ""                             # new snake_case plural name, e.g. "stylists"; empty keeps it
    label: str = ""                            # what the owner sees, e.g. "Stylists"


class RecipeChoice(BaseModel):
    pattern: str                               # a recipe id
    feature_ids: list[str] = Field(default_factory=list)      # brief features it serves
    switches: list[SwitchValue] = Field(default_factory=list)  # only switches the owner did not answer
    renames: list[Rename] = Field(default_factory=list)


class DataFieldOut(BaseModel):
    name: str                                  # snake_case
    label: str = ""
    type: DataFieldType = "text"
    required: bool = True
    personal: bool = False
    options: list[str] = Field(default_factory=list)          # for "choice"
    multiple: bool = False
    reference: Optional[str] = None            # for "reference": the record type it links to
    on_delete: Literal["restrict", "cascade", "set_null"] = "restrict"
    unique: bool = False
    default: Optional[str] = None
    min: Optional[float] = None
    max: Optional[float] = None
    max_length: Optional[int] = None

    def to_field(self) -> DataField:
        return DataField(**self.model_dump())


class StatusMove(BaseModel):
    from_status: str
    to: list[str] = Field(default_factory=list)


class DataRuleOut(BaseModel):
    """A rule from the fixed menu, its settings flat (no free dictionaries). Only the settings its kind uses are set:
    unique_together: fields | no_overlap: start, end, resource?, ignore_statuses | capacity: parent +
    parent_capacity, or group_by + max_count; sum?, overflow, count_statuses | within_hours: start, end, hours,
    days_off, resource? | lead_time: start, hours, via? | max_advance: start, days, via? | status_flow: field, moves |
    range: field, min_value, max_value | required_if: field, when_field, when_value | end_from_duration: start, end,
    via, duration | date_order: start, end, min_days?"""
    kind: RuleKind
    fields: list[str] = Field(default_factory=list)
    field: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    resource: Optional[str] = None
    via: Optional[str] = None
    duration: Optional[str] = None
    parent: Optional[str] = None
    parent_capacity: Optional[str] = None
    group_by: list[str] = Field(default_factory=list)
    sum: Optional[str] = None
    max_count: Optional[int] = None
    overflow: Optional[Literal["refuse", "waitlist"]] = None
    count_statuses: list[str] = Field(default_factory=list)
    ignore_statuses: list[str] = Field(default_factory=list)
    hours: Optional[float] = None
    days: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    when_field: Optional[str] = None
    when_value: Optional[str] = None
    min_days: Optional[float] = None
    moves: list[StatusMove] = Field(default_factory=list)

    def to_rule(self) -> DataRule:
        raw = self.model_dump(exclude={"kind", "moves", "max_count", "min_value", "max_value"}, exclude_none=True)
        params = {k: v for k, v in raw.items() if v != []}
        if self.max_count is not None:
            params["max"] = self.max_count
        if self.min_value is not None:
            params["min"] = self.min_value
        if self.max_value is not None:
            params["max"] = self.max_value
        if self.moves:
            params["moves"] = {m.from_status: m.to for m in self.moves}
        return DataRule(rule_id="", kind=self.kind, params=params)


class DataEntityOut(BaseModel):
    """A record type the model writes itself when no recipe fits (pattern "custom")."""
    name: str
    label: str = ""
    role: Literal["submission", "catalogue", "setting"] = "submission"
    purpose: str = ""
    feature_ids: list[str] = Field(default_factory=list)
    fields: list[DataFieldOut] = Field(default_factory=list)
    rules: list[DataRuleOut] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)

    def to_entity(self) -> DataEntity:
        return DataEntity(name=self.name, label=self.label, role=self.role, purpose=self.purpose,
                          feature_ids=list(self.feature_ids), fields=[f.to_field() for f in self.fields],
                          rules=[r.to_rule() for r in self.rules], links=list(self.links), pattern="custom",
                          sample_rows=3)


class ExtraField(BaseModel):
    entity: str                                # a record type made by a recipe (after renames)
    field: DataFieldOut


class DataDesign(BaseModel):
    """Call 2: what the site stores and the contract between its frontend and backend. Recipes first (D-242):
    code expands them; `entities` only for record types no recipe makes."""
    recipes: list[RecipeChoice] = Field(default_factory=list)
    extra_fields: list[ExtraField] = Field(default_factory=list)
    entities: list[DataEntityOut] = Field(default_factory=list)       # custom record types
    routes: list[ApiRoute] = Field(default_factory=list)
    form_rules: list[FormRule] = Field(default_factory=list)
    dashboard_views: list[DashboardView] = Field(default_factory=list)


class SectionKey(BaseModel):
    page_id: str
    feature_id: str


class PageOrder(BaseModel):
    """New top-to-bottom order of a page's sections, by feature id; sections not listed keep their place after."""
    page_id: str
    feature_ids: list[str]


class PlanPatch(BaseModel):
    """A fix round or a user change: only what changes (D-220). Code merges it into the current design; everything
    not named here stays exactly as it is. Items are matched by their id and replaced whole."""
    pages: list[PlannedPage] = Field(default_factory=list)            # added or changed, by page_id
    remove_page_ids: list[str] = Field(default_factory=list)
    sections: list[SectionOut] = Field(default_factory=list)          # added or changed, by page_id + feature_id
    remove_sections: list[SectionKey] = Field(default_factory=list)
    section_order: list[PageOrder] = Field(default_factory=list)
    custom_specs: list[CustomSpecOut] = Field(default_factory=list)   # added or changed, by spec_id
    footer_links: Optional[list[str]] = None                         # the whole new list, only when it changes
    recipes: list[RecipeChoice] = Field(default_factory=list)         # added or changed, by pattern
    remove_recipes: list[str] = Field(default_factory=list)
    extra_fields: Optional[list[ExtraField]] = None                   # the whole new list, only when it changes
    entities: list[DataEntityOut] = Field(default_factory=list)       # custom record types, added or changed, by name
    remove_entities: list[str] = Field(default_factory=list)
    routes: list[ApiRoute] = Field(default_factory=list)              # added or changed, by route_id
    remove_route_ids: list[str] = Field(default_factory=list)
    form_rules: list[FormRule] = Field(default_factory=list)          # added or changed, by section_id
    dashboard_views: list[DashboardView] = Field(default_factory=list)   # added or changed, by entity


class TextOut(BaseModel):
    slot_id: str
    text: str


class SiteTexts(BaseModel):
    """Call 3: every text slot, plus three hero headlines, best first."""
    hero_headlines: list[str] = Field(default_factory=list)
    texts: list[TextOut] = Field(default_factory=list)


class PlanDecision(BaseModel):
    """The user's answer on the plan screen. "data_edit" changes what the site keeps, by code (D-244)."""
    decision: Literal["approve", "change", "cancel", "data_edit"]
    change_text: Optional[str] = None
    edit: Optional[DataEdit] = None
