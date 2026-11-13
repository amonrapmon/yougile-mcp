---
name: author-contract
description: Write durable status-driven architecture and behavior records used by agent rule routing.
---

# Author a durable contract

1. Search affected paths and existing owners with the contracts CLI.
2. Edit an existing canonical owner when possible.
3. Describe stable observable behavior in present tense; no PR chronology,
   sprint status or research dump. Requirements must permit equivalent
   internal implementations.
4. Classify authority: draft for undecided, current only with maintainer
   approval, archived with superseded_by and a replacement.
5. List actual applicable paths; choose the narrowest set.
6. Include numbered invariants, non-goals, and verifiable pass/fail evidence.
7. Run python scripts/agent_contracts.py check and for affected paths.
8. Put approval and evidence in the PR, not in a claim of magical authority.
