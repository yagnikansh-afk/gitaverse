import random
import time

from django.conf import settings
from google import genai
from google.genai import types


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_NAME = "gemini-3.5-flash"

MAX_OUTPUT_TOKENS = 5000

MAX_RETRIES = 3


# ============================================================
# SYSTEM INSTRUCTION
# ============================================================

SYSTEM_INSTRUCTION = """
You are GitaVerse AI, an AI spiritual guide that explains
teachings from the Shrimad Bhagavad Gita.

IMPORTANT RULES:

1. Never claim that you are Shri Krishna, God, a guru,
   or a divine being.

2. You are an AI guide explaining teachings from the
   Shrimad Bhagavad Gita.

3. Use ONLY the Bhagavad Gita verses supplied in the context
   as scriptural evidence.

4. Never invent a chapter number, verse number, Sanskrit
   shloka, translation, or quotation.

5. If the supplied verses only partially relate to the
   question, clearly say so.

6. Use simple and understandable language.

7. Be compassionate, respectful, calm, and practical.

8. Do not guarantee success, wealth, health, recovery,
   exam results, relationships, or future outcomes.

9. Scripture must not be presented as a replacement for
   professional medical, mental-health, legal, financial,
   or emergency assistance when such help is appropriate.

10. When conversation history is supplied, use it to
    understand what the user is referring to.

11. A short follow-up such as "what if I fail again?",
    "what about him?", "and then?", or "why?" may depend
    on earlier messages. Use the conversation history
    to understand these references.

12. Do not repeat the entire conversation unnecessarily.

13. Do not give an unnecessarily long introduction.

14. Do not invent personal stories and present them as
    real events.

15. Do not fabricate real people, companies, studies,
    statistics, news events, or historical events.

16. When giving a modern example, prefer a realistic
    everyday real-world situation that people commonly
    experience.

17. The modern example must directly relate to the user's
    situation.

18. Do NOT use random fictional examples such as:
    - an imaginary athlete
    - a superhero
    - a movie character
    - a made-up celebrity
    - an invented dramatic story

19. Do NOT create a specific person's story and claim
    that it actually happened.

20. If you describe an everyday scenario that is not about
    a specific known person, make it clear that it is a
    realistic/common situation rather than a verified event.

21. If the user asks specifically for a real person,
    real event, current event, statistic, or verified
    real-world example, do not invent one. State that
    verification is needed if you cannot verify it.

22. Keep the modern example practical and directly useful
    to the user's situation.

Your answer MUST contain all of these sections:

### Situation

Briefly explain what the user appears to be dealing with.

### Bhagavad Gita Guidance

Explain the most relevant supplied verses.

Mention their chapter and verse numbers.

### Simple Explanation

Explain the teaching in simple modern language.

### Modern Example

Give a realistic real-world example directly connected
to the user's situation.

Prefer an ordinary situation that people actually
experience.

Do not use an unrelated fictional story.

Clearly distinguish a realistic/common scenario from
a verified real event.

### Life Lesson

Explain the main lesson the user can take from the verses.

### Practical Action Steps

Give 3 to 5 realistic actions the user can take.

### Reflection

End with one short reflection or question.

Aim for approximately 500 to 800 words.

Do not stop after the first section.

Complete every section before finishing the response.
"""


# ============================================================
# GET ENGLISH TRANSLATION
# ============================================================

def get_english_translation(shloka):
    """
    Get the English translation from the Translation table.
    """

    for translation in shloka.translations.all():

        if translation.language_code == "en":
            return translation.text

    return shloka.english_translation or ""


# ============================================================
# BUILD GITA CONTEXT
# ============================================================

def build_gita_context(shlokas):
    """
    Convert retrieved Bhagavad Gita shlokas into context
    for Gemini.
    """

    context_parts = []

    for shloka in shlokas:

        english_translation = (
            get_english_translation(shloka)
        )

        verse_context = f"""
Bhagavad Gita {shloka.chapter.number}.{shloka.verse_number}

Sanskrit:
{shloka.sanskrit}

Transliteration:
{shloka.transliteration}

English Translation:
{english_translation}

Commentary:
{shloka.explanation}
""".strip()

        context_parts.append(
            verse_context
        )

    return "\n\n------------------------------\n\n".join(
        context_parts
    )


# ============================================================
# BUILD CONVERSATION HISTORY
# ============================================================

def build_conversation_history(
    conversation_history
):
    """
    Convert previous messages into readable context
    for Gemini.
    """

    if not conversation_history:
        return "No previous conversation."

    history_parts = []

    for message in conversation_history:

        role = message.get(
            "role",
            "unknown"
        )

        content = message.get(
            "content",
            ""
        )

        if not content:
            continue

        if role == "user":
            label = "USER"

        elif role == "assistant":
            label = "GITAVERSE AI"

        else:
            label = role.upper()

        history_parts.append(
            f"{label}:\n{content}"
        )

    if not history_parts:
        return "No previous conversation."

    return "\n\n------------------------------\n\n".join(
        history_parts
    )


# ============================================================
# RETRYABLE ERROR CHECK
# ============================================================

def is_retryable_error(error):
    """
    Detect temporary Gemini errors.

    429 = rate limit
    500 = server error
    502 = gateway error
    503 = service unavailable
    504 = timeout
    """

    error_text = str(error).lower()

    retryable_signals = [
        "429",
        "resource_exhausted",
        "too many requests",

        "500",
        "internal",

        "502",
        "bad gateway",

        "503",
        "unavailable",
        "high demand",

        "504",
        "deadline_exceeded",
        "timeout",
    ]

    return any(
        signal in error_text
        for signal in retryable_signals
    )


# ============================================================
# CALL GEMINI
# ============================================================

def call_gemini(
    client,
    prompt
):
    """
    Generate a response from Gemini.

    Temporary errors are automatically retried.
    """

    last_error = None

    for attempt in range(
        MAX_RETRIES + 1
    ):

        try:

            response = (
                client.models.generate_content(
                    model=MODEL_NAME,

                    contents=prompt,

                    config=types.GenerateContentConfig(
                        system_instruction=(
                            SYSTEM_INSTRUCTION
                        ),

                        max_output_tokens=(
                            MAX_OUTPUT_TOKENS
                        ),
                    ),
                )
            )

            if not response.text:

                raise ValueError(
                    "Gemini returned an empty response."
                )

            return response

        except Exception as error:

            last_error = error

            if not is_retryable_error(
                error
            ):
                raise

            if attempt >= MAX_RETRIES:
                break

            delay = (
                (2 ** attempt)
                +
                random.uniform(
                    0,
                    0.5
                )
            )

            print(
                f"Gemini temporary error. "
                f"Retrying in {delay:.2f} seconds..."
            )

            time.sleep(delay)

    raise last_error


# ============================================================
# GENERATE GITA GUIDANCE
# ============================================================

def generate_gita_guidance(
    user_message,
    shlokas,
    conversation_history=None
):
    """
    Generate personalized Bhagavad Gita guidance.

    The AI receives:

    - Current user message
    - Previous conversation messages
    - Relevant Bhagavad Gita verses
    """

    # --------------------------------------------------------
    # CHECK API KEY
    # --------------------------------------------------------

    if not settings.GEMINI_API_KEY:

        raise ValueError(
            "GEMINI_API_KEY is not configured."
        )

    # --------------------------------------------------------
    # CHECK SHLOKAS
    # --------------------------------------------------------

    if not shlokas:

        raise ValueError(
            "No relevant Bhagavad Gita shlokas were found."
        )

    # --------------------------------------------------------
    # CREATE CLIENT
    # --------------------------------------------------------

    client = genai.Client(
        api_key=settings.GEMINI_API_KEY
    )

    # --------------------------------------------------------
    # BUILD CONTEXT
    # --------------------------------------------------------

    gita_context = build_gita_context(
        shlokas
    )

    conversation_context = (
        build_conversation_history(
            conversation_history or []
        )
    )

    # --------------------------------------------------------
    # BUILD PROMPT
    # --------------------------------------------------------

    prompt = f"""
CONVERSATION HISTORY:

========================================

{conversation_context}

========================================


CURRENT USER MESSAGE:

{user_message}


RETRIEVED BHAGAVAD GITA MATERIAL:

========================================

{gita_context}

========================================


TASK:

Respond to the CURRENT user message.

Use the conversation history to understand references
to earlier messages.

For example, if the previous conversation was about
failing an exam and the user now says:

"But what if I fail again?"

understand that "again" refers to the exam situation.

Do not treat the current message as completely unrelated
when it is clearly a continuation of the conversation.

Use the supplied Bhagavad Gita material as the ONLY
scriptural grounding.

When referring to a verse, use the exact chapter and
verse number provided in the retrieved material.

Do not invent additional Bhagavad Gita verses.

Do not pretend to be Shri Krishna.

Do not repeat the entire conversation.

Do not begin with a long greeting.


MODERN EXAMPLE REQUIREMENT:

The Modern Example section is important.

Give a realistic, everyday real-world scenario that
directly relates to the user's situation.

For example, if the user is talking about failing an exam,
use a realistic student/education situation.

If the user is talking about work, use a realistic
workplace situation.

If the user is talking about family conflict, use a
realistic family situation.

If the user is talking about money, use a realistic
financial decision situation.

Do NOT suddenly introduce an unrelated athlete,
superhero, movie character, celebrity, or fictional story.

Do NOT invent a specific person's name and pretend their
story is real.

Do NOT claim that a particular real person experienced
something unless it is verified.

It is acceptable to describe a common realistic scenario,
such as:

"A student prepares for an important entrance exam for
months but receives a score below the expected cutoff.
Instead of treating the result as proof that all their
effort was useless, they review their mistakes, identify
weak subjects, change their preparation strategy, and
prepare for another attempt."

Make it clear through the wording that this is a
realistic/common scenario, not a claimed verified event.

Connect the example directly to the Gita's teaching.


COMPLETE RESPONSE STRUCTURE:

### Situation

### Bhagavad Gita Guidance

### Simple Explanation

### Modern Example

### Life Lesson

### Practical Action Steps

### Reflection


IMPORTANT:

Complete all seven sections.

Do not stop after Situation.

Do not stop after Bhagavad Gita Guidance.

Do not stop in the middle of a sentence.

Finish Practical Action Steps and Reflection before
ending the response.

Keep the final response approximately 500 to 800 words.
""".strip()

    # --------------------------------------------------------
    # GENERATE
    # --------------------------------------------------------

    response = call_gemini(
        client,
        prompt
    )

    # --------------------------------------------------------
    # GET TEXT
    # --------------------------------------------------------

    assistant_text = (
        response.text or ""
    ).strip()

    # --------------------------------------------------------
    # VALIDATE
    # --------------------------------------------------------

    if not assistant_text:

        raise ValueError(
            "Gemini returned an empty response."
        )

    return assistant_text