"""
FORGE global run state (LangGraph), version 4.

One GraphState per request. The request id is the LangGraph thread id.
Rules:
  * Single writer per slice (see SLICE_OWNER). Fields that several parallel
    branches may touch carry an explicit reducer.
  * Agents get a projection of the state (see AGENT_READS), never the whole thing.
  * Large data (generated files, photos) is stored outside the state and
    referenced by path and hash.
  * Business details (ContentStore) are merged into the site by code and are
    never placed in a model prompt.
  * Numbers marked PLACEHOLDER are not measured. Set them from configuration.
  * A node that calls interrupt() is re-run from its first line when the graph
    resumes. Keep such nodes free of model calls, database writes and other side
    effects before the interrupt (tested with LangGraph 1.2.14).
  * Nothing becomes "ready" by default. A run is frozen only if can_freeze()
    says so, and any node failure is recorded in clarification.failure or errors
    and routed to FAILED. A fallback brief must never be reported
    as ready_for_planning.
  * There is no human escalation: users are non-technical, so a run that cannot
    continue ends in FAILED with a plain-language control.failure_reason.

Checkpoint serialisation: the Pydantic models and enums below are stored in
checkpoints. Recent LangGraph versions warn about unregistered types and will
block them. Pass msgpack_allowlist() to the serializer (see the example at the end).

This file has been run against LangGraph 1.2.14 with an in-memory checkpointer
(parallel writes, reducers, interrupt and resume, strict msgpack mode). It has
not been run inside the FORGE repo. Check the docs of the version you install.
"""
import enum
import inspect
import operator
import sys
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal, Optional, TypedDict

from pydantic import BaseModel, Field


# ---------------------------------------------------------------- enums
class Stage(str, Enum):
    CLARIFYING = "clarifying"
    AWAITING_USER = "awaiting_user"          # graph is paused at a checkpoint
    RETRIEVING = "retrieving"
    PLANNING = "planning"
    GENERATING = "generating"                # frontend, backend, database in parallel
    INTEGRATING = "integrating"
    MERGING_CONTENT = "merging_content"
    VERIFYING = "verifying"
    CORRECTING = "correcting"
    AWAITING_APPROVAL = "awaiting_approval"  # user reviews the live preview
    PUBLISHING = "publishing"
    DONE = "done"
    FAILED = "failed"
    OUT_OF_SCOPE = "out_of_scope"            # request cannot be built; nothing passed on
    REPLIED = "replied"                      # not a website request (greeting, question, off-topic): answered, no run
    CANCELLED = "cancelled"                  # the user cancelled at confirmation


Tier = Literal["catalogued", "custom", "unsupported"]
Priority = Literal["must", "should", "could"]
# user_delegated: the user chose "You decide"; the choice is also logged as an Assumption.
# baseline_default: added from the site baseline; listed on the confirmation screen, where the
# user can untick it, and logged as an Assumption (D-139).
# There is no source that means "added without the user knowing".
FeatureSource = Literal["user_stated", "user_confirmed", "user_delegated", "proposed_accepted", "baseline_default"]


# ---------------------------------------------------------------- request
class RequestInfo(BaseModel):
    """Written once by the Orchestrator. Read-only afterwards. `prompt` is untrusted text."""
    request_id: str
    parent_request_id: Optional[str] = None   # set for revision requests
    user_id: str
    project_id: str
    prompt: str
    language: str = "en"                      # interface language chosen by the user, NOT the
                                              # detected language of the prompt (see clarification)
    created_at: datetime


# ---------------------------------------------------------------- clarification
class Slot(BaseModel):
    """One entry of the fixed slot checklist (v6 Section 6). Importance is set by code, never by a model."""
    name: Literal["purpose", "visitor_actions", "style"]
    importance: Literal["blocking", "helpful", "optional"]
    status: Literal["missing", "answered", "assumed"] = "missing"
    values: list[str] = Field(default_factory=list)   # e.g. feature ids for visitor_actions, or ["none"]
    source: Optional[FeatureSource] = None             # how the slot was filled
    asks: int = 0                                      # times a question was asked for this slot


class RequestedItem(BaseModel):
    """
    One thing the user asked for, extracted by intake in the user's own words. The coverage check
    works on these: every item must end up as a feature, a custom item, an unsupported item, a
    note (style or content wish), or be dropped by the user. Nothing may stay 'unresolved'.
    """
    item_id: str
    text: str
    kind: Literal["feature", "integration", "style", "content", "other"] = "feature"
    evidence: str = ""                         # the words in the request that justify the item
    candidate_feature_id: Optional[str] = None     # model's best catalogue match (checked by code)
    alternative_feature_id: Optional[str] = None   # set when a second feature is equally plausible
    candidate_capability_id: Optional[str] = None  # model's unsupported-list match (checked by code)
    is_core: bool = False                      # the item is the main purpose of the site (D-109)
    retracted: bool = False                    # the user took it back ("actually no payments") (D-113)
    resolution: Literal[
        "unresolved", "ambiguous", "feature", "custom", "unsupported", "noted", "dropped_by_user",
    ] = "unresolved"
    resolved_to: Optional[str] = None          # feature_id, capability_id or "style"/"content"
    alternative_accepted: bool = False         # core unsupported item: the user accepted the alternative


class FeatureMatch(BaseModel):
    feature_id: str                            # catalogue featureId, or a slug for custom items
    name: str
    tier: Tier
    priority: Priority = "should"
    source: FeatureSource = "user_stated"
    requested_item_id: Optional[str] = None    # which user request this answers
    evidence: Optional[str] = None             # the words in the request that justify the match
    limitation: Optional[str] = None           # for partial support, e.g. "one location only"


class ProposedExtra(BaseModel):
    """A catalogue feature FORGE suggests that the user did not ask for. NOT in the brief until ticked."""
    feature_id: str
    name: str
    reason: str
    status: Literal["pending", "accepted", "rejected"] = "pending"


class QuestionOption(BaseModel):
    option_id: str                             # a featureId, a baseline id, an item id or "yes"/"no"
    label: str
    recommended: bool = False


class Question(BaseModel):
    """
    One question shown on its own screen (D-104). kind: A purpose, B visitor actions,
    C ambiguity, D core unsupported item, E size limit (custom features or pages).
    """
    question_id: str
    number: int                                # 1-based position among the questions of this request
    kind: Literal["A", "B", "C", "D", "E"]
    slot: str                                  # slot name, or "item:<item_id>", "custom_limit"
    text: str
    options: list[QuestionOption] = Field(default_factory=list)
    multi_select: bool = False
    max_selections: Optional[int] = None
    allow_you_decide: bool = False
    allow_other_text: bool = False
    answer_kind: Optional[Literal["option", "you_decide", "other"]] = None
    answer_option_ids: list[str] = Field(default_factory=list)
    answer_text: Optional[str] = None


class BriefCheck(BaseModel):
    """Result of the code checks and the conditional model review."""
    passed: bool = False
    uncovered_item_ids: list[str] = Field(default_factory=list)   # requested items with no resolution
    issues: list[str] = Field(default_factory=list)
    reviewed_by_model: bool = False
    repaired: bool = False


class ConfirmationState(BaseModel):
    """What the user saw on the confirmation screen and decided."""
    shown: bool = False
    limits_notice_shown: bool = False
    ticked_feature_ids: list[str] = Field(default_factory=list)
    decision: Optional[Literal["confirm", "edit", "cancel"]] = None
    edits_used: int = 0


class Assumption(BaseModel):
    text: str
    reason: str
    default_applied: Optional[str] = None


class FailureInfo(BaseModel):
    """Set when a clarification run cannot continue. While this is set the brief must not be frozen."""
    node: str
    category: Literal["understanding", "missing_info", "system"]
    message: str                               # plain-language text shown to the user
    detail: Optional[str] = None               # technical detail for logs, never shown to the user
    missing: list[str] = Field(default_factory=list)   # for missing_info: what is still unknown
    at: datetime


class ReplyInfo(BaseModel):
    """A message that is not a website request gets a fixed reply chosen by code (D-150); no build run follows."""
    kind: Literal["greeting", "about_forge", "off_topic", "unclear"]
    message: str                               # plain-language text shown to the user


class OutOfScopeInfo(BaseModel):
    reason: str                                # plain-language text shown to the user
    alternatives: list[str] = Field(default_factory=list)


class ClarificationState(BaseModel):
    """Working data of the Clarification Agent. No other agent reads this."""
    status: Literal[
        "idle", "analysing", "awaiting_answer", "drafting", "checking",
        "awaiting_confirmation", "generating_tests", "done", "failed", "out_of_scope", "cancelled", "replied",
    ] = "idle"
    detected_language: Optional[str] = None    # e.g. "en", "ur", "ur-Latn" (Roman Urdu)
    romanized: bool = False
    input_flags: list[str] = Field(default_factory=list)   # e.g. "instruction_like_text"
    is_website_request: Optional[bool] = None
    is_business: bool = True                   # a business or organisation (not a personal or event site)
    business_type: Optional[str] = None        # short label written by the agent, e.g. "bakery"
    goal: Optional[str] = None                 # one short sentence written by the agent
    style_hint: Optional[str] = None
    personality: Optional[str] = None          # theme feel the user described (agents/theming.py PERSONALITIES)
    hue_family: Optional[str] = None           # colour family the user named (agents/theming.py HUE_FAMILIES)
    brand_colour: Optional[str] = None         # '#rrggbb' the user gave, checked by code
    prefers_dark: bool = False                 # the user asked for a dark site: the theme opens in dark mode
    logo_colour: Optional[str] = None          # colour the user picked from their uploaded logo (D-163)
    screenshot_style: Optional[dict[str, Any]] = None   # {primary, background, is_dark} from a screenshot (D-164)
    reference_url: Optional[str] = None        # a website the user wants to look like (D-165)
    reference_style: Optional[dict[str, Any]] = None    # small style summary read from that site (D-166)
    theme_notice: Optional[str] = None         # plain message about a theme source that could not be used
    theme_source_tries: dict[str, int] = Field(default_factory=dict)   # per source kind, max 3 (D-169)
    pending_theme_source: Optional[dict[str, Any]] = None   # decision waiting for apply_confirmation
    baseline_hint: Optional[str] = None        # set when the user picked a baseline in question A
    requested_items: list[RequestedItem] = Field(default_factory=list)
    slots: list[Slot] = Field(default_factory=list)
    matches: list[FeatureMatch] = Field(default_factory=list)
    proposed_extras: list[ProposedExtra] = Field(default_factory=list)
    removed_feature_ids: list[str] = Field(default_factory=list)   # unticked defaults and features removed by an edit
    assumptions: list[Assumption] = Field(default_factory=list)  # kept here so redrafting the brief keeps them
    questions: list[Question] = Field(default_factory=list)
    pending_question_id: Optional[str] = None
    questions_used: int = 0
    repairs_used: int = 0
    calls_used: int = 0                        # model calls made by this agent, checked against call_hard_cap
    risk_flags: list[str] = Field(default_factory=list)   # triggers for the model review (D-126)
    check: Optional[BriefCheck] = None
    confirmation: ConfirmationState = Field(default_factory=ConfirmationState)
    pending_edit_text: Optional[str] = None    # free-text edit waiting to be interpreted
    out_of_scope: Optional[OutOfScopeInfo] = None
    reply: Optional[ReplyInfo] = None          # set when the message was not a website request
    failure: Optional[FailureInfo] = None


# ---------------------------------------------------------------- brief
class BriefFeature(BaseModel):
    """A feature the site will have. Carries the catalogue featureId only; Retrieval picks components (D-116)."""
    id: str                                    # catalogue featureId, or a slug for custom items
    name: str
    description: str = ""
    priority: Priority
    source: FeatureSource
    tier: Tier = "catalogued"
    requested_item_id: Optional[str] = None
    limitation: Optional[str] = None


class UnsupportedItem(BaseModel):
    """Shown to the user at confirmation and never built. Comes from the unsupported list or a size limit."""
    asked: str                                 # the user's words
    capability_id: Optional[str] = None
    group: Literal["feature", "integration", "unknown", "limit"] = "unknown"
    reason: str = ""
    alternative_text: str = ""
    alternative_feature_ids: list[str] = Field(default_factory=list)
    acknowledged_by_user: bool = False


class AcceptanceTest(BaseModel):
    """
    One acceptance test written from the confirmed brief, before any code exists (D-119).
    Declarative only: no CSS selectors. Later agents must never edit tests (D-120).
    """
    test_id: str
    requirement_ref: str                       # a BriefFeature.id
    kind: Literal["happy_path", "negative", "visual"]
    ears: str                                  # "WHEN ... THE SYSTEM SHALL ..."
    given: str
    when: str
    then: str
    check: Literal["element_present", "text_present", "navigation", "form_submit", "visual_judge"]
    description: str                           # stored in TEST_CASE.description
    expected_result: str                       # stored in TEST_CASE.expected_result


class ClarifiedBrief(BaseModel):
    """The single output of the Clarification Agent. Versioned and frozen."""
    version: int = 1
    status: Literal["draft", "ready"] = "draft"   # failed runs have no brief
    baseline: Optional[str] = None             # starting template (D-134); None when no baseline fits
    business_type: Optional[str] = None
    goal: str = ""                             # a short summary written by the agent, not a copy of the prompt
    audience: str = ""
    features: list[BriefFeature] = Field(default_factory=list)
    pages: list[dict[str, Any]] = Field(default_factory=list)   # {name, sections: [feature ids]}
    content_needs: list[str] = Field(default_factory=list)      # keys only; advisory, the plan's content_schema is final
    theme: Optional[dict[str, Any]] = None     # chosen theme: parameters, fonts, radius, tokens (light/dark) (D-159)
    integrations: list[dict[str, str]] = Field(default_factory=list)   # SUPPORTED links and embeds only (map, video, WhatsApp)
    unsupported: list[UnsupportedItem] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    clarified_text: str = ""                   # plain-language summary built by a code template (D-117)
    test_cases: list[AcceptanceTest] = Field(default_factory=list)
    frozen_at: Optional[datetime] = None       # set at freeze, after the user confirms


# ---------------------------------------------------------------- retrieval and plan
class ComponentCandidate(BaseModel):
    component_id: str
    score: float
    feature_id: Optional[str] = None           # the brief feature this candidate was retrieved for


class RetrievalResult(BaseModel):
    candidates: list[ComponentCandidate] = Field(default_factory=list)
    scaffold_info: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------- the build plan (Planning Agent, plan v2)
# The Planning Agent's output. The model designs pages, sections, custom parts, data, API and text; code
# fills the fixed parts, derives everything that follows from them and checks the whole plan (D-202).
NeedKind = Literal["copy", "fact", "list", "image", "setting", "live", "code"]   # as in component_needs.json
FieldType = Literal["text", "long_text", "number", "money", "date", "time", "datetime", "email", "phone", "url",
                    "boolean", "choice", "image"]


class PlannedPage(BaseModel):
    page_id: str                               # "home", "booking"
    route: str                                 # "/", "/booking"; unique
    title: str
    purpose: str = ""                          # one line, for the generators and the SRS
    in_menu: bool = True
    menu_order: int = 0
    section_ids: list[str] = Field(default_factory=list)   # top to bottom


class PlannedComponent(BaseModel):
    """One section of a page, or a site-wide part (page "all"): header, footer, WhatsApp button."""
    section_id: str                            # "home.hero", "all.footer"; unique
    page: str                                  # a PlannedPage.page_id, or "all"
    order: int = 0                             # position on its page, 0 = top
    role: Literal["layout", "feature", "custom"] = "feature"
    feature_id: Optional[str] = None           # the BriefFeature it serves; None for layout parts
    component_id: Optional[str] = None         # catalogue component; None when custom
    custom: bool = False
    custom_spec_id: Optional[str] = None       # -> CustomComponentSpec when custom
    settings: dict[str, Any] = Field(default_factory=dict)   # layout choices the component allows
    satisfies: list[str] = Field(default_factory=list)       # AcceptanceTest.test_id
    rationale: str = ""                        # why this component, one line


class Need(BaseModel):
    """One thing a part needs to render fully. Catalogue components get theirs from component_needs.json;
    the Planning Agent writes them for each custom part, with the same kinds (D-201)."""
    name: str                                  # "stamps_for_reward"
    kind: NeedKind
    label: str = ""                            # what the owner sees in the form ("Stamps needed for a free visit")
    type: FieldType = "text"
    required: bool = True
    max_length: Optional[int] = None           # for copy and text facts
    content_key: Optional[str] = None          # catalogue content key when one fits (phone, photos...)
    item_fields: list["Need"] = Field(default_factory=list)  # for kind "list"


class CustomComponentSpec(BaseModel):
    """A part the catalogue cannot build; the frontend generator writes its code from this."""
    spec_id: str                               # "custom-loyalty-card"
    feature_id: str                            # the custom BriefFeature.id
    name: str
    page: str                                  # where it goes (custom features have no page in the brief)
    purpose: str                               # what it is for, one or two sentences
    behaviour: list[str] = Field(default_factory=list)       # what it must do, plain sentences
    needs: list[Need] = Field(default_factory=list)          # owner facts, lists, images, text it needs
    ui_notes: str = ""                         # layout hints; theme tokens only, never colours
    limitation: Optional[str] = None           # copied from BriefFeature.limitation
    satisfies: list[str] = Field(default_factory=list)


class ContentField(BaseModel):
    """One thing the owner gives in the business details form. Derived by code from the needs of the chosen
    components and custom parts; values never enter the state or a model (ContentRef)."""
    key: str                                   # e.g. "phone", "address", "services", "stamps_for_reward"
    label: str
    kind: Literal["fact", "list", "image"] = "fact"
    type: FieldType = "text"
    required: bool = True
    item_fields: list[Need] = Field(default_factory=list)    # for lists: what each item has
    needed_by: list[str] = Field(default_factory=list)       # section ids
    help: str = ""                             # one plain line shown under the field


class TextSlot(BaseModel):
    """A piece of website text written by the model with the pitch rules: never a fact, facts only as
    placeholders such as {business_name}."""
    slot_id: str                               # "home.hero.headline"; unique
    section_id: str
    prop: str                                  # the component input it fills ("headline")
    text: str = ""
    max_length: int
    placeholders: list[str] = Field(default_factory=list)    # content keys used in the text
    alternatives: list[str] = Field(default_factory=list)    # other candidates (hero headline)


class DataField(BaseModel):
    name: str
    type: FieldType
    required: bool = True
    personal: bool = False                     # personal data: consent and careful handling


class DataEntity(BaseModel):
    """Something the generated site stores, e.g. booking requests."""
    name: str                                  # "booking_requests"
    purpose: str = ""
    fields: list[DataField] = Field(default_factory=list)
    feature_ids: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)           # names of entities it refers to


class ApiRoute(BaseModel):
    """The contract between the generated frontend and backend, fixed before any code is written."""
    route_id: str                              # "POST /api/bookings"
    method: Literal["GET", "POST", "PATCH", "DELETE"]
    path: str
    purpose: str = ""
    entity: Optional[str] = None               # DataEntity.name
    request_fields: list[str] = Field(default_factory=list)
    response_fields: list[str] = Field(default_factory=list)
    validation: list[str] = Field(default_factory=list)      # plain rules, e.g. "phone is required"
    used_by: list[str] = Field(default_factory=list)         # section ids
    satisfies: list[str] = Field(default_factory=list)


class FormRule(BaseModel):
    section_id: str                            # the form section
    route_id: str                              # where it posts
    required_fields: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)           # e.g. "no two bookings for the same slot"
    success_slot: Optional[str] = None         # TextSlot with the success message
    consent_required: bool = False             # set when it collects personal data
    spam_protection: bool = True


class DashboardView(BaseModel):
    """How the owner sees submissions in their FORGE project dashboard."""
    entity: str
    title: str
    columns: list[str] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=list)        # e.g. New -> Confirmed -> Done
    default_status: Optional[str] = None


class WorkTask(BaseModel):
    task_id: Literal["frontend", "backend", "database", "integration", "content_form"]
    depends_on: list[str] = Field(default_factory=list)
    skip: bool = False
    skip_reason: str = ""
    owns: list[str] = Field(default_factory=list)            # file paths or folders this task alone writes


class PlanTestLink(BaseModel):
    test_id: str                               # AcceptanceTest.test_id; tests are never changed (D-120)
    targets: list[str] = Field(default_factory=list)         # section ids and route ids that must satisfy it
    sample_input: dict[str, str] = Field(default_factory=dict)   # for form tests


class NotBuilt(BaseModel):
    asked: str
    reason: str = ""
    alternative: str = ""


class BuildPlan(BaseModel):
    version: int = 1
    status: Literal["draft", "approved"] = "draft"
    brief_version: int = 1
    built_by: Literal["model", "code"] = "model"             # "code": no model call was needed, or the fallback
    pages: list[PlannedPage] = Field(default_factory=list)
    footer_links: list[str] = Field(default_factory=list)   # page ids
    components: list[PlannedComponent] = Field(default_factory=list)
    custom_specs: list[CustomComponentSpec] = Field(default_factory=list)
    theme: dict[str, Any] = Field(default_factory=dict)      # exact copy of brief.theme; never written by a model
    content_schema: list[ContentField] = Field(default_factory=list)  # drives the business details form
    texts: list[TextSlot] = Field(default_factory=list)
    data_entities: list[DataEntity] = Field(default_factory=list)
    api_routes: list[ApiRoute] = Field(default_factory=list)
    form_rules: list[FormRule] = Field(default_factory=list)
    dashboard_views: list[DashboardView] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    execution_order: list[WorkTask] = Field(default_factory=list)
    test_map: list[PlanTestLink] = Field(default_factory=list)
    not_built: list[NotBuilt] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    approved_at: Optional[datetime] = None


class PlanningState(BaseModel):
    """Working data of the Planning Agent. No other agent reads this."""
    status: Literal["idle", "drafting", "checking", "writing_text", "awaiting_approval", "changing", "done",
                    "failed", "cancelled"] = "idle"
    calls_used: int = 0                        # model calls, checked against the planning limits
    fix_rounds_used: int = 0
    edits_used: int = 0
    text_rewrites_used: int = 0
    issues: list[str] = Field(default_factory=list)          # from the last check
    site_design: Optional[dict[str, Any]] = None             # model output of the site design call, as fixed
    data_design: Optional[dict[str, Any]] = None             # model output of the data and API call
    before_change: Optional[dict[str, Any]] = None           # designs and plan before a user change, to undo it
    before_fix: Optional[dict[str, Any]] = None              # designs, plan and issues before a fix round
    pending_change: Optional[str] = None                     # the user's change, waiting to be applied
    notice: Optional[str] = None                             # plain message for the approval screen
    failure: Optional[FailureInfo] = None


# ---------------------------------------------------------------- content (business details)
class ContentRef(BaseModel):
    """
    Status only. The values (phone, address, hours, handles) live in the content
    store table in the database, not in the graph state or its checkpoints, and
    are never sent to a model. The form writes to the database, and the content
    merge node reads the values from there when both the build and the form are ready.
    """
    store_id: Optional[str] = None
    form_status: Literal["not_shown", "shown", "partial", "submitted"] = "not_shown"
    filled_keys: list[str] = Field(default_factory=list)
    skipped_keys: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------- artifacts
class FileRef(BaseModel):
    path: str                                  # location in storage
    sha256: str
    kind: Literal["frontend", "backend", "database", "scaffold", "other"]


class AgentArtifacts(BaseModel):
    agent: Literal["frontend", "backend", "database", "integration"]
    status: Literal["pending", "running", "done", "failed"] = "pending"
    attempt: int = 0
    files: list[FileRef] = Field(default_factory=list)


# ---------------------------------------------------------------- verification
class CheckResult(BaseModel):
    check: str
    passed: bool
    detail: Optional[str] = None


class Diagnosis(BaseModel):
    target_agent: Literal["frontend", "backend", "database", "integration"]
    summary: str
    attempt: int


class VerificationState(BaseModel):
    builds: Optional[bool] = None
    results: list[CheckResult] = Field(default_factory=list)
    diagnoses: list[Diagnosis] = Field(default_factory=list)
    correction_attempts: int = 0


# ---------------------------------------------------------------- publication and documents
class PublicationState(BaseModel):
    approved_by_user: bool = False
    status: Literal["not_started", "submitted", "published", "failed"] = "not_started"
    url: Optional[str] = None
    provider: Optional[str] = None
    error: Optional[str] = None


class DocumentsState(BaseModel):
    """References to the ER diagram and the SRS, generated by code from the plan and schema."""
    er_diagram_ref: Optional[str] = None
    srs_ref: Optional[str] = None


# ---------------------------------------------------------------- control
class Limits(BaseModel):
    """Every bound in one place. The Orchestrator enforces them, not the prompts."""
    max_questions: int = 4                     # PLACEHOLDER, one question per screen (D-104)
    max_reasks_per_slot: int = 1               # design choice: a slot is asked at most twice
    max_repairs: int = 1                       # design choice
    call_hard_cap: int = 10                    # PLACEHOLDER; one call is always reserved for test generation
    max_confirmation_edits: int = 2            # PLACEHOLDER, set from config
    max_custom_features: int = 5               # PLACEHOLDER, "medium" size limit (D-135); no page or test cap (D-212)
    max_extras_shown: int = 3                  # PLACEHOLDER (D-131)
    max_agent_retries: int = 2                 # PLACEHOLDER, set from config
    max_correction_attempts: int = 3           # PLACEHOLDER, set from config
    max_plan_fix_rounds: int = 2               # plan v2: model fix rounds after the code checks
    max_plan_edits: int = 1                    # changes the user may make on the plan summary
    max_text_rewrites: int = 1                 # rewrite round for website text that fails the pitch rules
    max_data_entities: int = 6                 # size caps on the generated backend (plan v2 §4)
    max_api_routes: int = 10


class ErrorRecord(BaseModel):
    stage: str
    agent: Optional[str] = None
    message: str
    recoverable: bool = True
    at: datetime


# Raise when a change to the state or the graph means runs saved by older code can no longer be continued.
# 2: typed BuildPlan and the planning slice (D-202).
STATE_VERSION = 2


class RunConfig(BaseModel):
    """
    Snapshot of configuration taken when the run starts, written once by the
    Orchestrator and never changed. It makes a run reproducible (which models,
    which limits, which catalogue) and stops any agent from editing its own limits.
    """
    limits: Limits = Field(default_factory=Limits)
    state_version: int = STATE_VERSION          # code version that started the run; checked before a resume
    model_per_task: dict[str, str] = Field(default_factory=dict)   # task -> "provider/model"
    catalogue_version: Optional[str] = None     # which feature catalogue and component catalogue were used
    catalogue_hash: Optional[str] = None
    unsupported_list_hash: Optional[str] = None
    baselines_hash: Optional[str] = None
    embedding_model: Optional[str] = None
    prompt_versions: dict[str, str] = Field(default_factory=dict)  # node -> prompt version
    roman_urdu_enabled: bool = False            # experimental flag
    benchmark_run_id: Optional[str] = None


class ControlState(BaseModel):
    stage: Stage = Stage.CLARIFYING     # coarse stage; the one source of truth for routing
    retry_counts: dict[str, int] = Field(default_factory=dict)   # per agent
    failed: bool = False
    failure_reason: Optional[str] = None   # plain-language reason shown to the user


# ---------------------------------------------------------------- usage
class UsageSummary(BaseModel):
    """
    Running totals only. The per-call records (agent, model, tokens, latency,
    cost, token source) are written by the LLM gateway straight to the database
    (the LLM calls table), not appended to the state. Appending every call would
    make each checkpoint grow with the length of the run.
    """
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    unknown_token_calls: int = 0        # calls where the provider gave no token count
    total_latency_ms: int = 0
    estimated_cost_usd: float = 0.0


# ---------------------------------------------------------------- reducers
def merge_dict(old: dict, new: dict) -> dict:
    """Parallel branches write different keys, so merge them."""
    return {**(old or {}), **(new or {})}


def sum_usage(old: Optional[UsageSummary], new: Optional[UsageSummary]) -> UsageSummary:
    """Each node returns the usage of its own calls as a delta. Deltas are added."""
    old = old or UsageSummary()
    if new is None:
        return old
    return UsageSummary(
        calls=old.calls + new.calls,
        prompt_tokens=old.prompt_tokens + new.prompt_tokens,
        completion_tokens=old.completion_tokens + new.completion_tokens,
        unknown_token_calls=old.unknown_token_calls + new.unknown_token_calls,
        total_latency_ms=old.total_latency_ms + new.total_latency_ms,
        estimated_cost_usd=old.estimated_cost_usd + new.estimated_cost_usd,
    )


# ---------------------------------------------------------------- the graph state
class GraphState(TypedDict, total=False):
    request: RequestInfo
    run_config: RunConfig                                          # written once
    clarification: ClarificationState
    brief: Optional[ClarifiedBrief]                                # current version
    retrieval: Optional[RetrievalResult]
    plan: Optional[BuildPlan]
    planning: PlanningState                                        # the Planning Agent's working data
    content: ContentRef                                            # status only, values in the database
    artifacts: Annotated[dict[str, AgentArtifacts], merge_dict]    # keyed by agent
    verification: VerificationState
    publication: PublicationState
    documents: DocumentsState
    control: ControlState
    usage: Annotated[UsageSummary, sum_usage]                      # totals; details go to the database
    errors: Annotated[list[ErrorRecord], operator.add]


# ---------------------------------------------------------------- ownership and views
SLICE_OWNER = {
    "request": "orchestrator (once)",
    "run_config": "orchestrator (once)",
    "clarification": "clarification",
    "brief": "clarification",
    "retrieval": "context_retrieval",
    "plan": "planning",
    "planning": "planning",
    "content": "content_form node (status only)",
    "artifacts": "frontend | backend | database | integration (one key each)",
    "verification": "review_test_debug",
    "publication": "publication service",
    "documents": "documentation service",
    "control": "orchestrator join and routing nodes only, never a parallel branch",
    "usage": "every node returns its own delta",
    "errors": "any node (append only)",
}

# Slices an agent may read. Plan sections are cut by plan_section() below.
AGENT_READS = {
    "clarification": ["request", "clarification", "run_config"],
    "context_retrieval": ["brief"],
    "planning": ["brief", "retrieval", "planning", "run_config"],
    "frontend": ["plan"],
    "backend": ["plan"],
    "database": ["plan"],
    "integration": ["plan", "artifacts"],
    "content_form": ["plan", "content"],
    # An LLM-based agent never receives business detail values. Review/Test/Debug
    # gets only the content status, and tests run on sample data.
    "review_test_debug": ["brief", "plan", "artifacts", "content", "verification"],
    "orchestrator": list(SLICE_OWNER),
}

_PLAN_PARTS = {
    "frontend": ["pages", "footer_links", "components", "custom_specs", "theme", "content_schema", "texts",
                 "api_routes", "form_rules"],
    "backend": ["data_entities", "api_routes", "form_rules", "dependencies"],
    "database": ["data_entities"],
    "content_form": ["content_schema"],
}


def plan_section(plan: Optional[BuildPlan], agent: str) -> Optional[dict[str, Any]]:
    """Only the part of the build plan that a generator needs, to keep prompts small."""
    if plan is None or agent not in _PLAN_PARTS:
        return None
    full = plan.model_dump()
    return {k: full[k] for k in _PLAN_PARTS[agent]}


def view_for(agent: str, state: GraphState) -> dict[str, Any]:
    """Return only the slices an agent is allowed to read."""
    view = {k: state.get(k) for k in AGENT_READS[agent] if k in state}
    if agent in _PLAN_PARTS:
        view["plan"] = plan_section(state.get("plan"), agent)
    return view


# ---------------------------------------------------------------- the freeze gate
def can_freeze(state: GraphState) -> tuple[bool, list[str]]:
    """
    The only way a brief becomes final. Returns (ok, reasons). The freeze node must call this
    and route to FAILED or back to the loop when it returns False.
    A missing check, an unresolved requested item, a pending extra or a recorded failure all block it.
    """
    reasons: list[str] = []
    c: ClarificationState = state.get("clarification") or ClarificationState()
    brief: Optional[ClarifiedBrief] = state.get("brief")
    if c.failure is not None:
        reasons.append(f"clarification failed in node '{c.failure.node}': {c.failure.message}")
    if brief is None:
        reasons.append("no brief was produced")
    if c.check is None:
        reasons.append("the brief was not checked (C5 did not run)")
    elif not c.check.passed:
        reasons.append("the brief check failed: " + "; ".join(c.check.issues or ["no detail"]))
    unresolved = [i.text for i in c.requested_items if i.resolution == "unresolved"]
    if unresolved:
        reasons.append("requested items with no resolution: " + ", ".join(unresolved))
    pending = [e.name for e in c.proposed_extras if e.status == "pending"]
    if pending:
        reasons.append("proposed extras still waiting for the user: " + ", ".join(pending))
    if c.confirmation.decision != "confirm":
        reasons.append("the user has not confirmed the brief")
    if brief is not None and brief.unsupported and not c.confirmation.limits_notice_shown:
        reasons.append("unsupported items exist but the limits notice was not shown")
    if brief is not None and not brief.test_cases:
        reasons.append("no acceptance tests were generated")
    for slot in c.slots:
        if slot.importance == "blocking" and slot.status != "answered":
            reasons.append(f"blocking slot '{slot.name}' was not answered")
    return (not reasons), reasons


def initial_state(
    request: RequestInfo,
    config: Optional[RunConfig] = None,
    seed_brief: Optional[ClarifiedBrief] = None,
    seed_plan: Optional[BuildPlan] = None,
) -> GraphState:
    """
    A revision is a NEW run (new request id and thread, parent_request_id set),
    seeded with the previous brief and plan loaded from the database. History of
    earlier versions stays in the database, not in the state.
    """
    return GraphState(
        request=request,
        run_config=config or RunConfig(),
        clarification=ClarificationState(),
        brief=seed_brief,
        retrieval=None,
        plan=seed_plan,
        planning=PlanningState(),
        content=ContentRef(),
        artifacts={},
        verification=VerificationState(),
        publication=PublicationState(),
        documents=DocumentsState(),
        control=ControlState(),
        usage=UsageSummary(),
        errors=[],
    )


# ---------------------------------------------------------------- checkpoint serialisation
def msgpack_allowlist() -> list[tuple[str, str]]:
    """
    (module, class) pairs for every model and enum in this file, for LangGraph's
    JsonPlusSerializer(allowed_msgpack_modules=...). Needed so checkpoints keep loading
    when LangGraph blocks unregistered types.

        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
        serde = JsonPlusSerializer(allowed_msgpack_modules=msgpack_allowlist())
        checkpointer = SqliteSaver(conn, serde=serde)    # or MemorySaver(serde=serde)
    """
    mod = sys.modules[__name__]
    return [
        (__name__, name)
        for name, obj in vars(mod).items()
        if inspect.isclass(obj) and obj.__module__ == __name__
        and (issubclass(obj, BaseModel) or issubclass(obj, enum.Enum))
    ]


# ---------------------------------------------------------------- changes from version 2
# Found by running the version 2 results of the 15 test inputs against this design, and by
# adding the new catalogue (featureId, inclusion, notFor) and the unsupported list.
# 1. Failure is now representable: ClarificationState.failure, status "failed", and can_freeze().
#    The test run reported failed runs as ready_for_planning with stand-in features.
# 2. Added RequestedItem. Every thing the user asked for must resolve to a feature, a custom item,
#    an unsupported item or an explicit drop. This is what the coverage check (C5) compares against.
# 3. Added ProposedExtra (pending, accepted, rejected). Extras are not in the brief until accepted.
#    Version 2 had no place to hold them.
# 4. Added BriefCheck and ConfirmationState, so the C5 result and the C6 decision are in the state.
# 5. brief.unsupported is a typed UnsupportedItem (capability_id, group feature or integration, reason,
#    alternative components) instead of dict[str, str]. brief.integrations now means supported
#    links and embeds only.
# 6. FeatureMatch and BriefFeature carry requested_item_id, evidence, component_hint_ids and limitation
#    (for the "partial" tier in the unsupported list). ComponentCandidate carries feature_id.
# 7. FeatureSource: removed "assumed_accepted" (could mean "added silently"); added "user_delegated".
# 8. Language detection moved out of RequestInfo (which only the Orchestrator writes) into
#    clarification.detected_language and romanized. RequestInfo.language is the interface language.
# 9. RunConfig now records catalogue_version and hashes, embedding_model, prompt_versions and the
#    Roman Urdu flag, so benchmark runs can be reproduced after the catalogue changes.
# 10. Limits: added max_questions_per_round, call budgets for clear and vague requests, and
#     max_confirmation_edits. calls_used is counted in the clarification slice.
# 11. brief.goal is a summary written by the agent. The raw prompt is not copied into the brief or
#     the retrieval query. input_flags records instruction-like text in the prompt.
# 12. Added msgpack_allowlist() for checkpoint serialisation, and a warning that nodes with interrupt()
#     re-run from the top on resume.


# ---------------------------------------------------------------- changes from version 3 (2026-10-17)
# Clarification Agent v6 (design: FORGE_Clarification_Agent_Plan_v6, decisions D-101 - D-140).
# 1. Stage: added OUT_OF_SCOPE and CANCELLED. ESCALATED was removed earlier (D-005).
# 2. Slot is the fixed checklist (purpose, visitor_actions, style); importance is set by code (D-102).
# 3. RequestedItem carries the model's candidates (feature, alternative, capability), is_core and
#    retracted; code checks every id (D-113). New resolutions: "ambiguous" and "noted".
# 4. Question has kind A-E, typed options, multi-select and the answer (D-104, D-105).
# 5. FailureInfo has a category (understanding, missing_info, system) and a plain message (D-121).
# 6. ClarifiedBrief: baseline (D-134), business_type, clarified_text (D-117), test_cases (D-119).
#    component_hint_ids removed from FeatureMatch and BriefFeature (D-116). preset replaced by baseline.
# 7. FeatureSource: added baseline_default (D-139).
# 8. Limits: max_questions, max_reasks_per_slot, call_hard_cap, max_pages, max_extras_shown,
#    max_test_cases replace the round and budget fields (D-104, D-135).
# 9. can_freeze(): also requires acceptance tests and answered blocking slots.


# ---------------------------------------------------------------- changes for the Planning Agent (2026-11, D-202)
# 1. BuildPlan is typed: PlannedPage, PlannedComponent (section id, order, role, feature and tests it serves),
#    CustomComponentSpec with its own Needs, ContentField (kind, type, item fields), TextSlot (website text),
#    DataEntity, ApiRoute, FormRule, DashboardView, WorkTask (dependency graph), PlanTestLink, NotBuilt.
#    db_schema_ref was replaced by data_entities; pages and api_routes are no longer plain dicts.
# 2. Need has the same kinds as components/component_needs.json, so custom parts ask the owner for what they
#    need exactly like catalogue components (D-201).
# 3. Added the planning working slice (PlanningState) and its read rights; plan views now give each generator
#    and the business details form only its part of the plan.
# 4. Limits: max_plan_fix_rounds, max_plan_edits, max_text_rewrites, max_data_entities, max_api_routes.
# 5. STATE_VERSION 2: runs saved with the old plan format are not resumed.


# ---------------------------------------------------------------- Phase 0 fixes (2026-11-13)
# 1. Limits: max_pages and max_test_cases removed; every in-scope page and test is built (D-212).
#    Saved runs still load: pydantic ignores the two old fields.
