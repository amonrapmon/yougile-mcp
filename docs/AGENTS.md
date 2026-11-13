# Documentation-specific instructions

Inherits root AGENTS.md and CURRENT routed contracts.

- Durable behavior belongs in docs/contracts/, not in plans or issue recaps.
- Only CURRENT contracts are authoritative. DRAFT is proposed behavior;
  ARCHIVED provides historical context only.
- State system requirements in present tense and include verifiable
  outcomes. Keep research and implementation chronology in PR artifacts.
- Review existing canonical owner before adding a new contract.
- Update docs and applicable tests with implementation changes.
- Run python scripts/agent_contracts.py check for any contract change.
