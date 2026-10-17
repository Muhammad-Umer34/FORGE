# D:\FYP\FORGE-1\agents\clarification\schemas.py
"""
Schemas for the Clarification Agent's model calls (what the model must return) and for the
user's answers that resume a paused run (interrupt response schemas, D-122).
State models live in agents/state.py; these never go into the graph state.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field

# Features that answer "how do visitors contact you or order" (slot visitor_actions).
VISITOR_ACTION_FEATURES = ("contact-form", "order-request", "booking", "whatsapp-chat")
NO_VISITOR_ACTION = "none"


# ---------------------------------------------------------------- model outputs
class IntakeItem(BaseModel):
    text: str = Field(description="One thing the user asked for, short, in their own words.")
    kind: Literal["feature", "integration", "style", "content", "other"] = Field(
        description="feature: something the site does or shows. integration: a named outside "
                    "service or platform. style: look and feel. content: business details like prices or photos.")
    evidence: str = Field(description="The exact words copied from the request that show this item.")
    candidate_feature_id: Optional[str] = Field(
        default=None, description="The best matching id from the FEATURE LIST, or null if none fits.")
    alternative_feature_id: Optional[str] = Field(
        default=None, description="Only when a second FEATURE LIST id is equally likely. Otherwise null.")
    candidate_capability_id: Optional[str] = Field(
        default=None, description="The matching id from the UNSUPPORTED LIST, or null.")
    is_core: bool = Field(default=False, description="True only if this item is the main purpose of the whole site.")
    retracted: bool = Field(default=False, description="True if the user takes this item back later in the request.")


class IntakeOutput(BaseModel):
    message_kind: Literal["website_request", "greeting", "about_forge", "off_topic", "unclear"] = Field(
        description="website_request: the user wants a website built or changed (even if the message also greets). "
                    "greeting: hello or small talk only. about_forge: a question about FORGE itself (what it can build, "
                    "how it works, prices, payments). off_topic: anything else, such as maths, science, general "
                    "knowledge or writing tasks. unclear: cannot tell what the user wants.")
    detected_language: str = Field(description="Language of the request, e.g. 'en', 'ur', 'ur-Latn' for Roman Urdu.")
    romanized: bool = Field(description="True if a non-English language is written in Latin letters.")
    purpose_known: bool = Field(description="True if the request says what the site is for or what the business is.")
    is_business: bool = Field(description="True for a business or organisation; false for a personal or one-off event site.")
    business_type: Optional[str] = Field(default=None, description="Short label such as 'bakery' or 'dental clinic', or null.")
    goal: Optional[str] = Field(default=None, description="One short sentence in your own words: what the site should achieve. Null if unknown.")
    no_visitor_actions: bool = Field(
        default=False, description="True only if the user says visitors should not contact, order or book through the site.")
    style_hint: Optional[str] = Field(default=None, description="Look-and-feel words the user used, or null.")
    personality: Optional[Literal["professional", "calm", "warm", "bold", "elegant", "playful", "natural", "minimal"]] = Field(
        default=None, description="Only if the user described the look or feel. Otherwise null.")
    hue_family: Optional[Literal["red", "orange", "amber", "brown", "olive", "green", "teal", "blue", "navy",
                                 "purple", "pink", "charcoal"]] = Field(
        default=None, description="Only if the user named a colour for the site. Otherwise null.")
    prefers_dark: bool = Field(default=False, description="True only if the user asked for a dark website or dark background.")
    brand_colour: Optional[str] = Field(
        default=None, description="Only a hex code the user wrote, such as #1a7f5a. Never invent one. Otherwise null.")
    items: list[IntakeItem] = Field(default_factory=list)


class AnswerInterpretation(BaseModel):
    """Free-text answer to one question (D-114)."""
    understood: bool = Field(description="True if the answer clearly answers the question.")
    option_ids: list[str] = Field(default_factory=list, description="Ids of the listed options the answer means.")
    business_type: Optional[str] = Field(default=None, description="For a purpose question: short business label, or null.")
    goal: Optional[str] = Field(default=None, description="For a purpose question: one short sentence, or null.")
    is_business: Optional[bool] = None
    new_items: list[IntakeItem] = Field(default_factory=list, description="Extra things the user asked for in this answer.")


class EditInterpretation(BaseModel):
    """Free-text change requested on the confirmation screen."""
    understood: bool
    add_items: list[IntakeItem] = Field(default_factory=list)
    remove_feature_ids: list[str] = Field(default_factory=list, description="Ids from the CURRENT FEATURES to remove.")
    style_hint: Optional[str] = None


class BriefReview(BaseModel):
    """Conditional model review (D-126, D-141). Findings are shown to the user, not applied automatically."""
    invented_feature_ids: list[str] = Field(
        default_factory=list, description="Feature ids in the brief that the user did not ask for and did not choose.")
    missed_requests: list[str] = Field(
        default_factory=list, description="Things the user asked for that the brief does not cover, in the user's words.")


class GeneratedTest(BaseModel):
    requirement_ref: str = Field(description="The id of the feature this test checks.")
    kind: Literal["happy_path", "negative", "visual"]
    ears: str = Field(description="WHEN <event> THE SYSTEM SHALL <behaviour>")
    given: str
    when: str
    then: str
    check: Literal["element_present", "text_present", "navigation", "form_submit", "visual_judge"]
    description: str = Field(description="One plain sentence: what is tested.")
    expected_result: str = Field(description="One plain sentence: what must happen.")


class GeneratedTests(BaseModel):
    tests: list[GeneratedTest]


# ---------------------------------------------------------------- user answers (interrupt resume values)
class UserAnswer(BaseModel):
    question_id: str
    kind: Literal["option", "you_decide", "other"]
    option_ids: list[str] = Field(default_factory=list)
    text: Optional[str] = None


class ConfirmationDecision(BaseModel):
    decision: Literal["confirm", "edit", "cancel"]
    ticked_extra_ids: list[str] = Field(default_factory=list)
    unticked_default_ids: list[str] = Field(default_factory=list)
    theme_id: Optional[str] = None
    edit_text: Optional[str] = None
