# Research alignment and limits

The motivating research question is whether individually constrained components can
still create unsafe data exchanges when combined, and whether monitoring their
interaction can prevent selected failures.

The demonstration separates component capability from permission to use it: Agent B
holds synthetic financial fields, but Agent A may not receive them. Governance checks
the exchange and either denies it or converts an over-broad proposal into permitted,
purpose-required fields. The audit explains why the exchange was allowed or stopped.

This document states the project's experimental framing, not a verified literature
gap or novelty claim. The team's literature review must substantiate any academic
comparison or publication claim separately; no citations or measured improvements
are invented here.

Limitations include fixed rules and purposes, simulated agents, a small synthetic
dataset, session-local probing, and unauthenticated demo review. Passing finite tests
does not prove protection against arbitrary prompts, malicious Python code, covert
channels, or compromised agents. Response-content governance is future work.
