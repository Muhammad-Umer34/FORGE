# D:\FYP\FORGE-1\agents\clarification\intent.py
"""
Messages that are not website requests (decisions D-150 - D-152).

Users may greet FORGE, ask what it can do, ask an unrelated question (maths, science, general
knowledge) or type something unclear. Those get a short, fixed reply chosen by code and no build
run starts. The model only classifies the message (in the intake call); it never writes the reply,
so FORGE cannot give a wrong answer to an off-topic question. Obvious greetings and text with no
words are caught here first, without a model call (D-151).
"""
import re

from agents.state import ReplyInfo

# Every word of a pure greeting comes from this list (English and Roman Urdu).
_GREETING_WORDS = {
    "hi", "hii", "hiii", "hello", "helo", "hey", "heya", "hiya", "yo", "sup", "howdy", "greetings",
    "salam", "salaam", "slam", "assalam", "asalam", "aslam", "assalamu", "assalamualaikum", "alaikum",
    "alaykum", "o", "aoa", "walaikum", "wa", "good", "morning", "afternoon", "evening", "day",
    "how", "are", "you", "u", "r", "doing", "is", "it", "going", "whats", "what's", "what", "up",
    "there", "forge", "dear", "friend", "bro", "sir", "maam", "madam", "thanks", "thank", "ok", "okay",
    "kya", "haal", "hal", "hai", "he", "kaise", "kese", "ho", "aap", "ap", "theek", "nice", "to", "meet",
}
# At least one of these must be present, so "ok" or "what is it" alone is not a greeting.
_GREETING_MARKERS = {
    "hi", "hii", "hiii", "hello", "helo", "hey", "heya", "hiya", "yo", "sup", "howdy", "greetings",
    "salam", "salaam", "slam", "assalam", "asalam", "aslam", "assalamu", "assalamualaikum", "aoa",
    "morning", "afternoon", "evening", "thanks", "thank", "haal", "hal", "kaise", "kese",
}
_HOW_ARE_YOU = re.compile(r"how\s*(are|r)\s*(you|u)|how'?s it going|kya\s*ha+l|kaise\s*ho|kese\s*ho", re.IGNORECASE)
_THANKS = re.compile(r"\bthank(s| you)\b", re.IGNORECASE)
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
_NUMBERS_OR_MATHS = re.compile(r"[\d=+*/^%]")

MAX_GREETING_WORDS = 8

REPLIES = {
    "greeting": (
        "Hello, I'm FORGE. I build websites from a plain description. Tell me about the website you "
        "need: what it's for and what visitors should be able to do."
    ),
    "about_forge": (
        "FORGE turns a plain description into a website. You describe it, answer a few quick questions, "
        "confirm a summary, and FORGE plans and builds it. It makes small-to-medium sites, for example to "
        "show products or a menu, take bookings, show your work, or tell people about your business. "
        "It can't take online payments, user logins or online-store checkouts yet."
    ),
    "off_topic": (
        "I can only help with building websites, so I can't answer that. If you have a website in mind, "
        "tell me what it's for and I'll get started."
    ),
    "unclear": (
        "I couldn't tell what you need. Try describing the website: what it's for and what visitors "
        "should be able to do."
    ),
}


def prefilter(text: str) -> str | None:
    """'greeting' or 'unclear' when code can tell without a model; otherwise None (the intake call decides)."""
    words = [w.lower() for w in _WORD.findall(text)]
    if not any(len(w) >= 2 for w in words):
        return "unclear"                      # no real words: "???", "123", "."
    if _NUMBERS_OR_MATHS.search(text):
        return None                           # "hi what is 2+2" is a question, not a greeting
    if len(words) <= MAX_GREETING_WORDS and set(words) <= _GREETING_WORDS and set(words) & _GREETING_MARKERS:
        return "greeting"
    return None


def reply_for(kind: str, text: str) -> ReplyInfo:
    message = REPLIES[kind]
    if kind == "greeting":
        if _HOW_ARE_YOU.search(text):
            message = "I'm doing well, thanks for asking. " + message
        elif _THANKS.search(text):
            message = "You're welcome. " + message.replace("Hello, I'm FORGE. ", "")
    return ReplyInfo(kind=kind, message=message)
