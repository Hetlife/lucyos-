"""Local recall engine: hybrid retrieval on top of LucyOS's canonical SQLite
memory store.

This package never owns memory -- aion_core.memory / aion_core.db remain
canonical.  Everything here builds queries, ranks candidates and assembles
evidence from what is already there.
"""
