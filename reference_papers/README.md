# Reference papers

This project builds directly on the following two papers. The PDFs are included
here for convenience; both are openly available on arXiv and should be cited via
their original sources.

1. **Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory**
   Prateek Chhikara, Dev Khant, Saket Aryan, Taranjeet Singh, Deshraj Yadav.
   arXiv:2504.19413. https://arxiv.org/abs/2504.19413
   File: [`mem0_2504.19413.pdf`](mem0_2504.19413.pdf)

   Source of the extraction → consolidation architecture (two-phase pipeline in
   which an LLM extracts candidate memories and then adjudicates
   ADD/UPDATE/DELETE/NOOP operations against retrieved existing memories), and of
   the LoCoMo evaluation methodology (LLM-as-a-judge "J" score per question
   category) that our LoCoMo harness reproduces.

2. **Evaluating Very Long-Term Conversational Memory of LLM Agents (LoCoMo)**
   Adyasha Maharana, Dong-Ho Lee, Sergey Tulyakov, Mohit Bansal, Francesco
   Barbieri, Yuwei Fang. arXiv:2402.17753. https://arxiv.org/abs/2402.17753
   File: [`locomo_2402.17753.pdf`](locomo_2402.17753.pdf)

   The benchmark itself: very-long-term multi-session conversations with QA
   pairs in five categories (multi-hop, temporal, open-domain, single-hop,
   adversarial). Dataset: https://github.com/snap-research/locomo (fetched by
   `scripts/fetch_locomo.py`; not redistributed here because the upstream repo
   does not attach an explicit data license).
