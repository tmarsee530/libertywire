# Semantic quality amplification gate

Rally Point keeps the semantic audit non-mutating: audit findings do not delete history or silently rewrite canonical timelines.

High-severity findings do, however, stop amplification. The Fast Wire cycle runs the semantic audit after newsroom generation, then removes affected timeline IDs from the derived social distribution queue. The email adapter reads the same audit and omits affected timelines from email event ingestion.

Medium-severity findings remain review signals and do not automatically suppress distribution.

This separation preserves the historical record while ensuring that known high-confidence defects such as cross-event contamination, commentary promoted as current status, and current-status mismatch are not pushed to acquisition channels.
