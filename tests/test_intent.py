"""Code pre-filter and fixed replies for messages that are not website requests (D-150, D-151). No model calls."""
import pytest

from agents.clarification.intent import REPLIES, prefilter, reply_for


@pytest.mark.parametrize("text", [
    "hi", "Hello!", "Hi how are you ?", "hey there", "Assalam o alaikum", "salam, kya haal hai",
    "good morning", "thanks", "Hello FORGE",
])
def test_greetings_are_caught_without_a_model(text):
    assert prefilter(text) == "greeting"


@pytest.mark.parametrize("text", ["???", "123", ".", "!!!!", "a"])
def test_text_without_words_is_unclear(text):
    assert prefilter(text) == "unclear"


@pytest.mark.parametrize("text", [
    "hi, I need a website for my bakery",          # a request, even with a greeting
    "hi what is 2+2",                              # numbers or maths: the model decides
    "what is the capital of France",
    "can you build me a portfolio site",
    "ok",                                          # no greeting word: the model decides
])
def test_everything_else_goes_to_the_model(text):
    assert prefilter(text) is None


def test_reply_texts():
    assert reply_for("greeting", "how are you?").message.startswith("I'm doing well, thanks for asking.")
    assert reply_for("greeting", "thanks").message.startswith("You're welcome.")
    assert reply_for("greeting", "hello").message == REPLIES["greeting"]
    for kind in ("about_forge", "off_topic", "unclear"):
        assert reply_for(kind, "x").message == REPLIES[kind]
    assert "!" not in "".join(REPLIES.values())    # calm tone, no exclamation marks
