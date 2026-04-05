"""Constants for project knowledge uploads and RAG."""

# Manifest schema stored in knowledge/manifest.json
MANIFEST_VERSION = 1

# Upload limits
MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_TOTAL_KNOWLEDGE_BYTES = 200 * 1024 * 1024

# Text longer than this is classified rag_only by default (chars)
INLINE_CHAR_THRESHOLD = 10_000

# Chunking (characters)
CHUNK_SIZE = 1_000
CHUNK_OVERLAP = 200

# Retrieval
RETRIEVAL_TOP_K = 8

# Inline cap when forcing inline (chars) — model context protection
MAX_INLINE_CHARS = 24_000

# OpenAI embeddings (must match dimension below)
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
