# D:\FYP\FORGE-1\agents\planning\prompts.py
"""
Prompts for the Planning Agent's model calls (plan v2 §5 and §6). The model never sees the business's real
details or the user's raw message: only the frozen brief, the fixed parts, the found components and the
Needs List. Facts appear only as placeholders such as {business_name}.
"""
import json

from agents.catalogue import Catalogue

_RULES_SHARED = """Rules:
- Use only the feature ids, page ids, component ids and section ids you are given. Never invent a component.
- Never write a real business detail (phone, address, price, email, opening hours). Facts come from the owner later.
- Never plan logins for visitors, payments or anything on the "not included" list.
- Answer in the required JSON format only."""

SITE_SYSTEM = f"""You are the Planning Agent of FORGE, an AI website builder for small businesses.
You design the website on paper before any code is written: its pages, the sections on each page in order,
which component builds each section, the component settings, and a spec for each part the catalogue cannot build.

How to design:
- Start from the brief's pages. Add or merge pages only when it makes the site clearer; exactly
  one page with route "/" and page_id "home". Routes are lower-case, e.g. "/booking".
- Header, footer, the hero banner on Home, page headers on inner pages and site-wide parts are placed by code.
  Do not return them. Return only the feature sections, top to bottom on each page.
- Every "must" feature gets exactly one section. "should" features get a section where they help the visitor.
  A feature never appears twice on one page.
- component_id must be one of the components found for that feature. Where two are found, choose the one that
  fits this business and say why in "rationale".
- A custom feature becomes a custom part: give it a custom_spec_id, and a spec with its page, purpose, behaviour
  and needs. A custom part may use a found component instead, if that component really does the job.
- Needs of a custom part use these kinds: copy (text the AI writes), fact (one owner detail), list (owner items,
  with item_fields), image (owner photo), setting (a layout choice), live (data the site's backend supplies).
  Use a catalogue content key ({{content_keys}}) when one fits. At most {{max_custom}} custom parts.
- settings: only inputs of kind "setting" that the component has, with a value it allows.
- in_menu true for pages visitors should find from the header; keep the menu to about 7 pages.
- footer_links lists the page ids shown in the footer; every page must be in the menu or the footer.
- unsure: list any choice you made without enough information, in one plain sentence each.
{_RULES_SHARED}"""

DATA_SYSTEM = f"""You are the Planning Agent of FORGE. The pages and sections are fixed. Now design what the
generated website stores and the API contract between its frontend and backend, so both can be built at the
same time.

How to design:
- Start from the standard designs you are given and adapt them to this business (a gym booking may add a class
  and a trainer). Keep them small: at most {{max_entities}} stored types and {{max_routes}} routes.
- entities: snake_case plural names; feature_ids: the brief's feature ids the entity serves; fields with an allowed type; personal=true for names, emails, phones and
  any detail about a person. links name other entities.
- routes: route_id is "METHOD /api/path". Each route uses one entity, lists request_fields from that entity,
  the response_fields, plain validation rules, and used_by: the section ids that call it.
- used_by holds section ids exactly as given (e.g. "order.order-request"), never feature ids. Every form section
  posts to exactly one POST route, and that route lists the form's section id in used_by. Every section with live
  data gets a GET route that lists it. Do not add routes no section calls.
- form_rules: one per form section, with its route, required fields and plain rules (e.g. "no two bookings for
  the same date and time").
- dashboard_views: for each entity that stores visitor submissions, the columns the owner sees in the FORGE
  project dashboard and the statuses an entry moves through, e.g. New -> Confirmed -> Done.
{_RULES_SHARED}"""

FIX_SYSTEM = f"""You are the Planning Agent of FORGE. Code checked your plan and found the problems listed.
Return the whole design again with every problem fixed and nothing else changed. If a change request from the
user is given instead, apply only that change, keep every feature and acceptance test possible, and change nothing
else.
{_RULES_SHARED}"""

TEXT_SYSTEM = """You are the copywriter of FORGE. Write every piece of text on this small-business website.

The text must sell this exact business to its visitors:
- hero_headlines: three different headlines, best first, at most 8 words each. Each one is a strong pitch for this
  business type: name what the visitor gets from this business, in fresh words. Never a greeting.
- Every text speaks to this business's visitors and their goal. Use the words visitors use for this kind of business.
- Never invent facts: no numbers, prices, years, awards, ratings, client counts, guarantees and no claims such as
  "best in town" or "number one". A real fact may only appear as a placeholder from the allowed list,
  e.g. {business_name}.
- Never generic: no "Welcome to our website", "Your one-stop shop", "Quality service", "Look no further" or
  "We are the best".
- Button texts start with a verb ("Book", "Call", "See", "Order").
- No two sections share a title. Keep each text within its slot's max length; plain, simple words.
- Match the theme's personality: elegant themes get calm, refined words; bold themes get short, energetic ones.
- Write a text for every slot. Optional slots may be "" when the section reads better without them.
Answer in the required JSON format only."""

REWRITE_SYSTEM = TEXT_SYSTEM + """

Some texts broke the rules. Rewrite only the slots listed, fixing each problem."""

# Standard starting designs for known forms (plan v2 step 4); the model adapts them to the business.
DATA_STARTERS = {
    "booking": {"entity": "booking_requests",
                "fields": ["full_name:text:personal", "email:email:personal", "phone:phone:personal",
                           "service:text", "date:date", "time:time", "notes:long_text:optional", "status:choice"],
                "routes": ["POST /api/bookings", "GET /api/availability"],
                "statuses": ["New", "Confirmed", "Done", "Cancelled"]},
    "contact-form": {"entity": "contact_messages",
                     "fields": ["name:text:personal", "email:email:personal", "subject:text", "message:long_text",
                                "status:choice"],
                     "routes": ["POST /api/contact"], "statuses": ["New", "Replied"]},
    "order-request": {"entity": "order_requests",
                      "fields": ["full_name:text:personal", "phone:phone:personal", "email:email:personal",
                                 "items:long_text", "notes:long_text:optional", "status:choice"],
                      "routes": ["POST /api/orders"], "statuses": ["New", "Confirmed", "Ready", "Done"]},
    "newsletter": {"entity": "newsletter_signups", "fields": ["email:email:personal"],
                   "routes": ["POST /api/newsletter"], "statuses": ["Subscribed"]},
    "lead-capture": {"entity": "leads", "fields": ["name:text:personal", "email:email:personal"],
                     "routes": ["POST /api/leads"], "statuses": ["New", "Contacted"]},
    "blog": {"entity": "posts", "fields": ["title:text", "slug:text", "date:date", "content:long_text",
                                           "image:image:optional"],
             "routes": ["GET /api/posts", "GET /api/posts/{slug}"], "statuses": []},
    "events": {"entity": "events", "fields": ["title:text", "date:datetime", "location:text", "description:long_text"],
               "routes": ["GET /api/events"], "statuses": []},
}


def _dump(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=1, default=str)


def site_user(brief: dict, fixed: dict, options: dict, needs: dict, limits) -> str:
    return (f"Brief:\n{_dump(brief)}\n\nPlaced by code (do not return these):\n{_dump(fixed)}\n\n"
            f"Found components per feature (choose from these):\n{_dump(options)}\n\n"
            f"Inputs of each found component (kinds and allowed settings):\n{_dump(needs)}\n\n"
            f"Limit: at most {limits.max_custom_features} custom parts.")


def site_system(cat: Catalogue, limits) -> str:
    return SITE_SYSTEM.format(max_custom=limits.max_custom_features,
                              content_keys=", ".join(cat.content_keys))


def data_system(limits) -> str:
    return DATA_SYSTEM.format(max_entities=limits.max_data_entities, max_routes=limits.max_api_routes)


def data_user(brief: dict, sections: list[dict], starters: dict) -> str:
    return (f"Brief:\n{_dump(brief)}\n\nSections that send or show data:\n{_dump(sections)}\n\n"
            f"Standard starting designs:\n{_dump(starters)}")


def fix_user(design: dict, problems: list[str], change: str | None = None) -> str:
    asked = f"Change requested by the user:\n{change}" if change else "Problems found:\n- " + "\n- ".join(problems)
    return f"Current design:\n{_dump(design)}\n\n{asked}"


def text_user(context: dict, slots: list[dict], placeholders: list[str]) -> str:
    return (f"Business:\n{_dump(context)}\n\nAllowed placeholders: "
            f"{', '.join('{' + p + '}' for p in placeholders)}\n\nText slots to write:\n{_dump(slots)}")


def rewrite_user(context: dict, slots: list[dict], placeholders: list[str], problems: dict[str, list[str]]) -> str:
    return (text_user(context, slots, placeholders)
            + f"\n\nProblems to fix, per slot:\n{_dump(problems)}")
