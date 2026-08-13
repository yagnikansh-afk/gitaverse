import math

from django.conf import settings
from google import genai
from google.genai import types

from gita.models import Shloka


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_NAME = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768


# ============================================================
# LIFE TOPICS
# ============================================================

LIFE_TOPICS = {

    "results_and_failure": {
        "keywords": [
            "exam",
            "marks",
            "grade",
            "grades",
            "failed",
            "failure",
            "result",
            "results",
            "studied",
            "study",
            "success",
            "unsuccessful",
        ],

        "verses": [
            (2, 47),
            (2, 48),
            (2, 38),
        ],
    },

    "motivation": {
        "keywords": [
            "motivation",
            "unmotivated",
            "lazy",
            "give up",
            "giving up",
            "quit",
            "trying again",
            "worth it",
            "hopeless",
        ],

        "verses": [
            (6, 5),
            (6, 6),
            (3, 8),
        ],
    },

    "anger": {
        "keywords": [
            "anger",
            "angry",
            "rage",
            "furious",
            "temper",
            "hate",
        ],

        "verses": [
            (2, 62),
            (2, 63),
        ],
    },

    "fear": {
        "keywords": [
            "fear",
            "afraid",
            "scared",
            "terrified",
            "frightened",
        ],

        "verses": [
            (2, 40),
            (18, 66),
        ],
    },

    "anxiety": {
        "keywords": [
            "anxiety",
            "anxious",
            "worried",
            "worry",
            "stress",
            "stressed",
            "overthinking",
            "overthink",
        ],

        "verses": [
            (2, 48),
            (6, 35),
        ],
    },

    "sadness": {
        "keywords": [
            "sad",
            "sadness",
            "upset",
            "unhappy",
            "grief",
            "grieving",
            "hurt",
        ],

        "verses": [
            (2, 14),
            (2, 38),
        ],
    },

    "death": {
        "keywords": [
            "death",
            "die",
            "dying",
            "dead",
            "mortality",
        ],

        "verses": [
            (2, 20),
            (2, 27),
        ],
    },

    "mind_control": {
        "keywords": [
            "mind",
            "concentrate",
            "concentration",
            "focus",
            "distracted",
            "distraction",
            "restless",
            "thoughts",
        ],

        "verses": [
            (6, 26),
            (6, 35),
        ],
    },

    "duty_and_work": {
        "keywords": [
            "work",
            "job",
            "career",
            "duty",
            "responsibility",
            "responsibilities",
        ],

        "verses": [
            (2, 47),
            (3, 8),
            (3, 19),
        ],
    },
}


# ============================================================
# COSINE SIMILARITY
# ============================================================

def cosine_similarity(vector_a, vector_b):
    """
    Calculate semantic similarity between two vectors.
    """

    if not vector_a or not vector_b:
        return 0.0

    if len(vector_a) != len(vector_b):
        return 0.0

    dot_product = sum(
        a * b
        for a, b in zip(
            vector_a,
            vector_b
        )
    )

    magnitude_a = math.sqrt(
        sum(
            a * a
            for a in vector_a
        )
    )

    magnitude_b = math.sqrt(
        sum(
            b * b
            for b in vector_b
        )
    )

    if (
        magnitude_a == 0
        or magnitude_b == 0
    ):
        return 0.0

    return (
        dot_product
        /
        (magnitude_a * magnitude_b)
    )


# ============================================================
# GENERATE QUERY EMBEDDING
# ============================================================

def generate_query_embedding(message):
    """
    Convert the retrieval query into a
    768-dimensional embedding.
    """

    if not settings.GEMINI_API_KEY:

        raise ValueError(
            "GEMINI_API_KEY is not configured."
        )

    client = genai.Client(
        api_key=settings.GEMINI_API_KEY
    )

    response = client.models.embed_content(
        model=MODEL_NAME,

        contents=message,

        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=(
                EMBEDDING_DIMENSIONS
            ),
        ),
    )

    if not response.embeddings:

        raise ValueError(
            "Gemini returned no query embedding."
        )

    embedding = (
        response.embeddings[0].values
    )

    if not embedding:

        raise ValueError(
            "Gemini returned an empty query embedding."
        )

    if len(embedding) != EMBEDDING_DIMENSIONS:

        raise ValueError(
            f"Expected {EMBEDDING_DIMENSIONS} "
            f"dimensions but received "
            f"{len(embedding)}."
        )

    return list(embedding)


# ============================================================
# BUILD RETRIEVAL QUERY
# ============================================================

def build_retrieval_query(
    message,
    conversation_history=None
):
    """
    Build a context-aware retrieval query.

    The current message gets the strongest emphasis,
    while recent conversation history provides context
    for short follow-up questions.
    """

    if not conversation_history:

        return message.strip()

    history_parts = []

    # Use only the latest few messages so the embedding
    # query doesn't become unnecessarily large.
    recent_history = (
        conversation_history[-6:]
    )

    for item in recent_history:

        role = item.get(
            "role",
            ""
        )

        content = item.get(
            "content",
            ""
        ).strip()

        if not content:
            continue

        if role == "user":

            history_parts.append(
                f"User previously said: {content}"
            )

        elif role == "assistant":

            # We include a small amount of AI context,
            # but avoid allowing the AI's previous answer
            # to dominate retrieval.
            history_parts.append(
                f"Previous guidance: {content}"
            )

    if not history_parts:

        return message.strip()

    return (
        "Previous conversation context:\n"
        + "\n".join(history_parts)
        + "\n\n"
        + "Current user question:\n"
        + message.strip()
    )


# ============================================================
# DETECT LIFE TOPICS
# ============================================================

def detect_topics(message):
    """
    Detect obvious life situations.

    These topics influence re-ranking only.
    Semantic retrieval remains the main mechanism.
    """

    message_lower = message.lower()

    detected_topics = []

    for topic_name, topic_data in (
        LIFE_TOPICS.items()
    ):

        for keyword in topic_data["keywords"]:

            if keyword in message_lower:

                detected_topics.append(
                    topic_name
                )

                break

    return detected_topics


# ============================================================
# TOPIC BOOST
# ============================================================

def calculate_topic_boost(
    shloka,
    detected_topics
):
    """
    Give known highly relevant verses a small boost.
    """

    boost = 0.0

    verse_key = (
        shloka.chapter.number,
        shloka.verse_number
    )

    for topic_name in detected_topics:

        topic_data = LIFE_TOPICS.get(
            topic_name
        )

        if not topic_data:
            continue

        if verse_key in topic_data["verses"]:

            boost += 0.12

    return min(
        boost,
        0.24
    )


# ============================================================
# FIND RELEVANT SHLOKAS
# ============================================================

def find_relevant_shlokas(
    message,
    limit=3,
    conversation_history=None
):
    """
    Hybrid, conversation-aware Bhagavad Gita retrieval.

    Steps:

    1. Build a retrieval query using the current message
       plus recent conversation context.

    2. Generate a semantic embedding.

    3. Compare it against all stored shloka embeddings.

    4. Detect life topics from the combined context.

    5. Apply a small topic boost.

    6. Rank all shlokas.

    7. Return the best results.
    """

    # --------------------------------------------------------
    # BUILD CONTEXT-AWARE QUERY
    # --------------------------------------------------------

    retrieval_query = (
        build_retrieval_query(
            message,
            conversation_history
        )
    )

    # --------------------------------------------------------
    # QUERY EMBEDDING
    # --------------------------------------------------------

    query_embedding = (
        generate_query_embedding(
            retrieval_query
        )
    )

    # --------------------------------------------------------
    # TOPIC DETECTION
    # --------------------------------------------------------

    detected_topics = detect_topics(
        retrieval_query
    )

    # --------------------------------------------------------
    # GET EMBEDDED SHLOKAS
    # --------------------------------------------------------

    shlokas = (
        Shloka.objects
        .select_related("chapter")
        .prefetch_related("translations")
        .exclude(
            embedding__isnull=True
        )
    )

    scored_shlokas = []

    # --------------------------------------------------------
    # SCORE EVERY SHLOKA
    # --------------------------------------------------------

    for shloka in shlokas:

        if not shloka.embedding:
            continue

        semantic_score = (
            cosine_similarity(
                query_embedding,
                shloka.embedding
            )
        )

        topic_boost = (
            calculate_topic_boost(
                shloka,
                detected_topics
            )
        )

        final_score = (
            semantic_score
            +
            topic_boost
        )

        scored_shlokas.append(
            {
                "shloka":
                    shloka,

                "semantic_score":
                    semantic_score,

                "topic_boost":
                    topic_boost,

                "final_score":
                    final_score,
            }
        )

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    scored_shlokas.sort(
        key=lambda item: item["final_score"],
        reverse=True
    )

    # --------------------------------------------------------
    # RETURN TOP RESULTS
    # --------------------------------------------------------

    return [
        item["shloka"]
        for item in scored_shlokas[:limit]
    ]