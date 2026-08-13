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
#
# These are NOT used as the main retrieval system.
#
# Semantic similarity still searches all 701 shlokas.
# These mappings only provide a small relevance boost when
# the user's situation clearly matches a known life topic.
#
# This helps prevent loosely related verses from beating
# highly useful teachings.
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

    Higher score means the vectors are more similar.
    """

    if not vector_a or not vector_b:
        return 0.0

    if len(vector_a) != len(vector_b):
        return 0.0

    dot_product = sum(
        a * b
        for a, b in zip(vector_a, vector_b)
    )

    magnitude_a = math.sqrt(
        sum(a * a for a in vector_a)
    )

    magnitude_b = math.sqrt(
        sum(b * b for b in vector_b)
    )

    if magnitude_a == 0 or magnitude_b == 0:
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
    Convert the user's message into a 768-dimensional
    retrieval-query embedding.
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
            output_dimensionality=EMBEDDING_DIMENSIONS,
        ),
    )

    if not response.embeddings:
        raise ValueError(
            "Gemini returned no query embedding."
        )

    embedding = response.embeddings[0].values

    if not embedding:
        raise ValueError(
            "Gemini returned an empty query embedding."
        )

    if len(embedding) != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Expected {EMBEDDING_DIMENSIONS} dimensions "
            f"but received {len(embedding)}."
        )

    return list(embedding)


# ============================================================
# DETECT LIFE TOPICS
# ============================================================

def detect_topics(message):
    """
    Detect obvious life situations in the user's message.

    Semantic search still does the actual retrieval.
    Topics only influence re-ranking.
    """

    message_lower = message.lower()

    detected_topics = []

    for topic_name, topic_data in LIFE_TOPICS.items():

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

    We deliberately keep this small so semantic similarity
    remains important.
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

    # Prevent several detected topics from creating an
    # excessively large artificial score.
    return min(boost, 0.24)


# ============================================================
# FIND RELEVANT SHLOKAS
# ============================================================

def find_relevant_shlokas(
    message,
    limit=3
):
    """
    Hybrid Bhagavad Gita retrieval.

    1. Understand user's message using an embedding.
    2. Compare it against all stored shloka embeddings.
    3. Detect obvious life topics.
    4. Give strongly related verses a small topic boost.
    5. Rank everything.
    6. Return the best verses.
    """

    # --------------------------------------------------------
    # QUERY EMBEDDING
    # --------------------------------------------------------

    query_embedding = (
        generate_query_embedding(
            message
        )
    )

    # --------------------------------------------------------
    # TOPIC DETECTION
    # --------------------------------------------------------

    detected_topics = detect_topics(
        message
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

        semantic_score = cosine_similarity(
            query_embedding,
            shloka.embedding
        )

        topic_boost = calculate_topic_boost(
            shloka,
            detected_topics
        )

        final_score = (
            semantic_score
            +
            topic_boost
        )

        scored_shlokas.append(
            {
                "shloka": shloka,

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