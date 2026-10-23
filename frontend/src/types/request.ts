// D:\FYP\FORGE-1\frontend\src\types\request.ts
// Website-request API types. They mirror backend/models/requests.py and the
// payloads built in agents/clarification (question and confirmation screens).

export type RequestStatus =
  | "needs_clarification"
  | "awaiting_confirmation"
  | "complete"
  | "out_of_scope"
  | "failed"
  | "cancelled"
  | "reply"
  | "processing" // a step is running right now
  | "paused"; // stopped mid-way (crash or model outage); can be continued

export interface QuestionOption {
  option_id: string;
  label: string;
  recommended: boolean;
}

export interface QuestionData {
  type: "question";
  question_id: string;
  number: number;
  max_questions: number;
  reask: boolean; // the last answer did not answer this question
  kind: "A" | "B" | "C" | "D" | "E";
  slot: string;
  text: string;
  options: QuestionOption[];
  multi_select: boolean;
  max_selections: number | null;
  allow_you_decide: boolean;
  allow_other_text: boolean;
}

export type FeatureSource =
  | "user_stated"
  | "user_confirmed"
  | "user_delegated"
  | "proposed_accepted"
  | "baseline_default";

/** A generated theme preview: real computed colours (agents/theming.py), fonts and corner radius. */
export interface ThemeCard {
  id: string;
  kind: "match" | "alternative" | "brand" | "contrast" | "logo" | "screenshot" | "reference" | "combined";
  label: string;
  reason: string;
  fonts: { heading: string; body: string };
  radius: string;
  default_mode: "light" | "dark"; // the user asked for a dark site
  notes: string[]; // e.g. a paid font replaced by the closest free one
  swatch: Record<"light" | "dark", Record<"background" | "card" | "foreground" | "muted" | "primary" | "primary-foreground" | "accent", string>>;
}

export interface ConfirmationData {
  type: "confirmation";
  summary: string;
  pages: string[];
  features: { id: string; name: string; source: FeatureSource; can_untick: boolean }[];
  extras: { id: string; name: string; reason: string }[];
  themes: ThemeCard[];
  theme_selected: string;
  limits_notice: { asked: string; reason: string; alternative: string }[];
  assumptions: string[];
  please_check: string[];
  business_details_note: string;
  edits_left: number;
  actions: ("confirm" | "edit" | "cancel" | "theme_source")[];
  theme_notice: string | null; // a logo, screenshot or website that could not be used
  theme_sources_left: Record<ThemeSourceKind, number>;
}

export interface BriefFeature {
  id: string;
  name: string;
  priority: "must" | "should" | "could";
  source: FeatureSource;
  tier: "catalogued" | "custom" | "unsupported";
}

export interface AcceptanceTest {
  test_id: string;
  requirement_ref: string;
  kind: "happy_path" | "negative" | "visual";
  ears: string;
  description: string;
  expected_result: string;
}

export interface Requirement {
  version: number;
  baseline: string | null;
  business_type: string | null;
  goal: string;
  features: BriefFeature[];
  pages: { name: string; sections: string[] }[];
  theme: { theme_id: string; label: string; fonts: { heading: string; body: string }; radius: string } | null;
  unsupported: { asked: string; reason: string; alternative_text: string }[];
  assumptions: { text: string; reason: string }[];
  clarified_text: string;
  frozen_at: string | null;
}

export interface CompleteData {
  requirement: Requirement;
  test_cases: AcceptanceTest[];
}

export interface OutOfScopeData {
  reason: string;
  alternatives: string[];
}

export interface FailedData {
  category: "understanding" | "missing_info" | "system";
  message: string;
  missing: string[];
}

/** A message that was not a website request (greeting, question about FORGE, off-topic, unclear). */
export interface ReplyData {
  kind: "greeting" | "about_forge" | "off_topic" | "unclear";
  message: string;
}

export type RequestEnvelope =
  | { request_id: string; status: "needs_clarification"; data: QuestionData }
  | { request_id: string; status: "awaiting_confirmation"; data: ConfirmationData }
  | { request_id: string; status: "complete"; data: CompleteData }
  | { request_id: string; status: "out_of_scope"; data: OutOfScopeData }
  | { request_id: string; status: "failed"; data: FailedData }
  | { request_id: string; status: "cancelled"; data: Record<string, never> }
  | { request_id: string; status: "reply"; data: ReplyData }
  | { request_id: string; status: "paused" | "processing"; data: { message: string } };

export interface UserAnswer {
  question_id: string;
  kind: "option" | "you_decide" | "other";
  option_ids?: string[];
  text?: string;
}

export type ThemeSourceKind = "logo" | "screenshot" | "website";

/** The user's own material for the theme (theme Phase 2). Images never go here, only the chosen colours. */
export interface ThemeSource {
  kind: ThemeSourceKind;
  colour?: string | null;
  background?: string | null;
  is_dark?: boolean | null;
  url?: string | null;
}

/** Colours read from an uploaded logo or screenshot by our backend (no model call). */
export interface ImageColours {
  kind: "logo" | "screenshot";
  colours: string[];
  monochrome?: boolean;
  background?: string;
  primary?: string | null;
  is_dark?: boolean;
}

export interface ConfirmationDecision {
  decision: "confirm" | "edit" | "cancel" | "theme_source";
  theme_source?: ThemeSource;
  ticked_extra_ids?: string[];
  unticked_default_ids?: string[];
  theme_id?: string;
  edit_text?: string;
}
