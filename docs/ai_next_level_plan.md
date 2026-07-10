# Next-Level AI Engineering: An Action Plan

A structured study and practice plan for going from "I use AI every day" to "I can design, evaluate, and ship production AI systems." Built for a senior engineer who wants both theoretical depth and applied skill.

**Suggested cadence:** 8 to 10 weeks, 5 to 8 focused hours per week. Each phase has required reading, optional deeper reading, and a small applied exercise. Treat the exercises as the actual learning. Reading without building is forgetting in slow motion.

---

## Mental Model First: The Shift That Frames Everything

Before any specific technique, internalize this shift. The industry moved from **prompt engineering** (crafting a perfect instruction for a single turn) to **context engineering** (managing the entire token state across multi-turn, tool-using, long-running agents). Every topic below (RAG, memory, caching, agents, fine-tuning, evals) is a sub-discipline of context engineering: each one is a strategy for getting the right tokens into the model's finite attention budget at the right moment, then measuring whether the output is actually good.

Read this first, it reframes everything else:

- **[Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)** (Anthropic, Sep 2025). The defining post on this shift. Concepts to anchor: attention budget, just-in-time retrieval, compaction, sub-agents.
- **[Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)** (Anthropic, Dec 2024). Agents vs. workflows, the five canonical patterns (prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer).

If you only read two things this week, read those two.

---

## Phase 1: Foundations and Architecture (Week 1)

**Goal:** Refresh the mechanical mental model of how transformers process tokens, so later topics (context windows, caching, attention degradation) connect to first principles rather than feel like magic settings.

### Core reading

- **[Attention Is All You Need](https://arxiv.org/abs/1706.03762)** (Vaswani et al., 2017). The transformer paper. Even if you have read summaries, read the original. Focus on the attention mechanism and the cost of self-attention being quadratic in sequence length, which is why context windows are expensive and why caching matters.
- **[The Illustrated Transformer](https://jalammar.github.io/illustrated-transformer/)** (Jay Alammar). The clearest visual companion to the paper.
- **[Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/abs/2201.11903)** (Wei et al., 2022). The paper that started the reasoning era.

### Deeper (optional)

- **[Scaling Laws for Neural Language Models](https://arxiv.org/abs/2001.08361)** (Kaplan et al., 2020) and the **[Chinchilla paper](https://arxiv.org/abs/2203.15556)** (Hoffmann et al., 2022). Why model size, data, and compute trade off the way they do.
- **[The Expressive Power of Transformers with Chain of Thought](https://arxiv.org/abs/2310.07923)** (Merrill and Sabharwal). Why CoT actually increases what transformers can compute.

### Applied exercise

Build a 30-line script that takes any text and computes its token count for Claude (or GPT). Plot token count growth as you append chunks. Internalize: a 100-page PDF is roughly 50k tokens, a 1M-token window holds about 750k words, and every cached vs. uncached token has a real dollar cost. This is the unit economics of everything that follows.

---

## Phase 2: Context Engineering as the Spine (Week 2)

**Goal:** Stop thinking "prompt." Start thinking "context budget across six layers: system rules, memory, retrieved docs, tool schemas, recent conversation, current task." Every downstream decision falls out of this framing.

### Core reading

- **[Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)** (re-read deliberately this time, taking notes).
- **[Writing tools for AI agents (with AI agents)](https://www.anthropic.com/engineering/writing-tools-for-agents)** (Anthropic). Tool design as a context-engineering discipline.
- **[Context Engineering Explained](https://pub.towardsai.net/context-engineering-explained-the-anthropic-guide-thats-changing-how-developers-work-with-ai-40fae176a18d)** (Towards AI, plain-English companion to the Anthropic post).
- **[Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)** (Anthropic, Oct 2025). Progressive disclosure as a context strategy. Open standard at `agentskills.io`.

### Deeper (optional)

- **[Code execution with MCP: Building more efficient agents](https://www.anthropic.com/engineering/code-execution-with-mcp)** (Anthropic, Nov 2025). Turning MCP tools into code reduces both token cost and chained-error risk.
- **[Context-Rot: How Increasing Input Tokens Impacts LLM Performance](https://research.trychroma.com/context-rot)** (Chroma technical report). Empirical evidence that all models degrade with long context. This is why "just stuff it in" is wrong.

### Applied exercise

Take a workflow you already use AI for. Diagram its current context across the six layers (system, memory, retrieved, tools, history, task). Identify one layer that is overloaded and one that is underused. Rebuild the prompt as a structured context, measure latency and quality before and after on 10 representative inputs.

For your vertical-AI startup specifically: this is the exercise that pays the most. Domain expertise lives in well-engineered context, not in fine-tuned weights, at least until you have proven the wedge.

---

## Phase 3: RAG and Retrieval (Weeks 3 to 4)

**Goal:** Understand RAG as a spectrum (naive, advanced, modular, agentic, GraphRAG) rather than a single technique. Know when retrieval is the right move and when it is hiding a context-engineering problem.

### Core reading

- **[Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401)** (Lewis et al., 2020). The original RAG paper.
- **[Retrieval-Augmented Generation for Large Language Models: A Survey](https://arxiv.org/abs/2312.10997)** (Gao et al., updated through 2024). The most cited RAG survey. Read the taxonomy (Naive, Advanced, Modular).
- **[A Systematic Literature Review of Retrieval-Augmented Generation: Techniques, Metrics, and Challenges](https://arxiv.org/abs/2508.06401)** (Brown et al., 2025). PRISMA-based review of 128 RAG papers through May 2025. Use it as a map of the landscape.
- **[Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection](https://arxiv.org/abs/2310.11511)** (Asai et al., 2023). The model learns to decide when to retrieve.
- **[Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval)** (Anthropic). Prepending chunk-specific context before embedding. Combined with BM25 and reranking, cuts retrieval failure rates by up to 67%. Implementation notebook in the [Anthropic cookbook](https://github.com/anthropics/anthropic-cookbook).
- **[Enhancing Retrieval-Augmented Generation: A Study of Best Practices](https://arxiv.org/abs/2501.07391)** (Li et al., Jan 2025). Empirical comparison of query expansion, novel retrieval strategies, and Contrastive In-Context Learning RAG.

### Deeper (optional)

- **[From Local to Global: A GraphRAG Approach to Query-Focused Summarization](https://arxiv.org/abs/2404.16130)** (Microsoft Research). When entities and relationships matter more than text similarity.
- **[REALM: Retrieval-Augmented Language Model Pre-training](https://arxiv.org/abs/2002.08909)** (Guu et al., 2020). Retrieval baked into pre-training.
- **[Awesome Generative AI Guide: RAG research updates](https://github.com/aishwaryanr/awesome-generative-ai-guide/blob/main/research_updates/rag_research_table.md)**. Curated table of recent RAG papers, updated regularly.

### Applied exercise

Build a small RAG over a corpus you actually care about (your own notes, your codebase, or vertical documents like restoration industry standards). Implement three variants on the same data: (1) naive embedding retrieval, (2) hybrid BM25 plus embeddings with reranking, (3) contextual retrieval per Anthropic's recipe. Measure retrieval precision and recall on 20 hand-built queries. The point is not "which is best." The point is feeling, in your own data, where retrieval fails and what fixes it.

Tooling worth knowing: LlamaIndex, LangChain, Chroma, Qdrant, Pinecone, Weaviate, FAISS, pgvector. Pick one stack, do not yak-shave evaluating six.

---

## Phase 4: Agents, Tools, and Workflows (Weeks 4 to 5)

**Goal:** Build an actual agent. Understand the difference between a workflow (predetermined steps) and an agent (LLM in a loop with tools), and when each is correct.

### Core reading

- **[Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)** (Anthropic, Dec 2024). Re-read.
- **[Building agents with the Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)** (Anthropic, Sep 2025). The primitives: bash, file edit, file search, plus memory and sub-agents.
- **[ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)** (Yao et al., 2022). The pattern most agents still use.
- **[Toolformer: Language Models Can Teach Themselves to Use Tools](https://arxiv.org/abs/2302.04761)** (Schick et al., 2023).
- **[A practical guide to building agents](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)** (OpenAI). Complementary perspective.
- **[Model Context Protocol (MCP) specification](https://modelcontextprotocol.io/)**. The de facto standard for connecting agents to tools and data.

### Deeper (optional)

- **[Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366)** (Shinn et al., 2023). Agents that learn from their own errors within a session.
- **[Voyager: An Open-Ended Embodied Agent with Large Language Models](https://arxiv.org/abs/2305.16291)** (Wang et al., 2023). Skill libraries built by the agent.
- **[Establishing Best Practices for Building Rigorous Agentic Benchmarks](https://arxiv.org/abs/2507.02825)** (2025). How to evaluate agents fairly.

### Applied exercise

Build a small agent that solves a real, narrow problem from your domain (for a vertical AI startup, ideal: a triage agent that takes a free-form incident description and routes it through three or four tool calls to produce a structured intake record). Use the Claude Agent SDK or build raw with the Anthropic Messages API. Constraints: maximum five tools, each with a one-paragraph description an outsider could understand. When you finish, count tokens per run and ask: which tools were called more than once? Which descriptions confused the model?

---

## Phase 5: Memory Systems (Week 5)

**Goal:** Understand memory as more than "long context." Know the difference between short-term context, working memory, long-term memory, and episodic memory, and the architectural choices behind each.

### Core reading

- **[Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory](https://arxiv.org/abs/2504.19413)** (Chhikara et al., ECAI 2025). Establishes the LoCoMo benchmark and compares 10 memory approaches.
- **[Zep: A Temporal Knowledge Graph Architecture for Agent Memory](https://arxiv.org/abs/2501.13956)** (Rasmussen et al., 2025). Memory as a time-aware graph.
- **[A-MEM: Agentic Memory for LLM Agents](https://arxiv.org/abs/2502.12110)** (Xu et al., NeurIPS 2025). Zettelkasten-inspired dynamic memory.
- **[Designing Memory Systems for LLM Agents](https://medium.com/@candemir13/designing-memory-systems-for-llm-agents-from-short-term-context-to-long-term-knowledge-b27a1d4d5516)** (Can Demir, Oct 2025). Practical synthesis of STM and LTM patterns.

### Deeper (optional)

- **[Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers](https://arxiv.org/abs/2603.07670)** (2026 survey). Excellent breadth.
- **[Agent Memory Paper List](https://github.com/Shichun-Liu/Agent-Memory-Paper-List)**. Curated list, updated monthly.
- **[State of AI Agent Memory 2026](https://mem0.ai/blog/state-of-ai-agent-memory-2026)** (Mem0 blog). Production-oriented summary.

### Applied exercise

Take the agent from Phase 4 and add memory. Implement two layers: a session-scoped working memory (compaction summaries) and a user-scoped long-term memory (a vector store of distilled facts with timestamps). Run the same query in three sessions across three days. Verify the agent retrieves only what is relevant and does not bloat its context with stale facts.

---

## Phase 6: Prompt Caching and Long Context (Week 6)

**Goal:** Cut your inference cost by 60 to 90% and your latency by 2 to 5x by understanding cache mechanics. Most engineers leave this on the table.

### Core reading

- **[Prompt caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)** (Anthropic docs). The mechanics: cache breakpoints, 5-minute and 1-hour TTLs, pricing tiers.
- **[Prompt caching cookbook](https://github.com/anthropics/anthropic-cookbook/blob/main/misc/prompt_caching.ipynb)** (Anthropic). Runnable examples.
- **[Don't Break the Cache: An Evaluation of Prompt Caching for Long-Horizon Agentic Tasks](https://arxiv.org/abs/2601.06007)** (PwC, 2026). Cost reductions of 41 to 80% and TTFT improvements of 13 to 31% across providers. Reveals that naive full-context caching can paradoxically increase latency.
- **[Prompt caching: 10x cheaper LLM tokens, but how?](https://ngrok.com/blog/prompt-caching)** (ngrok, Dec 2025). Compares OpenAI's automatic caching vs. Anthropic's explicit control.

### Deeper (optional)

- **[Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172)** (Liu et al., 2023). The "lost in the middle" effect, still relevant for placement decisions.
- **[Long-context isn't all you need](https://arxiv.org/abs/2407.01370)**. Long context windows do not replace retrieval.

### Applied exercise

Take your Phase 4 agent. Identify the static prefix (system prompt, tool definitions, examples). Add a cache breakpoint at the end of that prefix. Measure: cost per request before and after, TTFT before and after, on 50 runs. Try the variation where dynamic content is moved to the end of the system prompt vs. interleaved. Confirm the PwC paper finding in your own data.

---

## Phase 7: Evals and Observability (Weeks 6 to 7)

**Goal:** Stop shipping AI features blind. Build the equivalent of unit tests, integration tests, and production monitoring for non-deterministic systems. Without this you cannot improve anything because you cannot tell whether you made things better or worse.

### Core reading

- **[A pragmatic guide to LLM evals for devs](https://newsletter.pragmaticengineer.com/p/evals)** (Pragmatic Engineer, Dec 2025). Best practical starting point. Distinguishes code-based, LLM-as-judge, and human evals.
- **[Your AI Product Needs Evals](https://hamel.dev/blog/posts/evals/)** (Hamel Husain). The post that convinced many teams to take evals seriously.
- **[Building an LLM evaluation framework: best practices](https://www.datadoghq.com/blog/llm-evaluation-framework-best-practices/)** (Datadog). Production framing.
- **[LLM Observability: Best Practices for 2025](https://www.getmaxim.ai/articles/llm-observability-best-practices-for-2025/)** (Maxim AI). Distributed tracing, token accounting, eval pipelines.
- **[Anthropic's testing and evaluation guide](https://docs.anthropic.com/en/docs/test-and-evaluate/strengthen-guardrails/empirical-strength)** (docs).

### Deeper (optional)

- **[Establishing Best Practices for Building Rigorous Agentic Benchmarks](https://arxiv.org/abs/2507.02825)** (Jul 2025).
- **[Awesome LLM Evaluation](https://alopatenko.github.io/LLMEvaluation/)**. Comprehensive guide and paper list.
- **[Chain-of-Thought Is Not Explainability](https://aigi.ox.ac.uk/wp-content/uploads/2025/07/Cot_Is_Not_Explainability.pdf)** (Barez et al., Oxford WhiteBox, 2025). Why you cannot just read the model's CoT to know what it did.

### Tooling to evaluate

- **Open-source:** Arize Phoenix, Comet Opik, Langfuse, OpenInference, DeepEval, Ragas (for RAG specifically).
- **Commercial:** Maxim AI, Braintrust, LangSmith, Datadog LLM Observability.

### Applied exercise

For your Phase 4 agent, build a golden dataset of 50 inputs with expected behaviors (not necessarily exact outputs). Implement three eval layers: (1) deterministic code-based checks for structured output, (2) LLM-as-judge with a rubric for quality dimensions, (3) cost and latency tracking. Run it in CI on every prompt or model change. The first time your eval suite catches a regression you would have shipped, the discipline pays for itself.

---

## Phase 8: Fine-tuning and Custom Models (Weeks 7 to 8)

**Goal:** Know exactly when fine-tuning is the right answer (rarely) and how to do it cheaply when it is (almost always LoRA or QLoRA). The right sequence is **Prompt then RAG then Fine-tune then Distill**, in that order. Most teams asking about fine-tuning have not done the prerequisite work.

### Core reading

- **[LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685)** (Hu et al., 2021). The technique that made fine-tuning affordable.
- **[QLoRA: Efficient Finetuning of Quantized LLMs](https://arxiv.org/abs/2305.14314)** (Dettmers et al., 2023). LoRA on quantized base weights.
- **[Direct Preference Optimization](https://arxiv.org/abs/2305.18290)** (Rafailov et al., 2023). DPO replaces RLHF for many use cases.
- **[Fine-Tuning LLMs in 2026: When RAG Isn't Enough](https://bigdataboutique.com/blog/fine-tuning-llms-when-rag-isnt-enough)** (BigData Boutique). Honest framing of when to fine-tune.
- **[A Practical Guide to LLM Fine Tuning](https://www.databricks.com/blog/llm-fine-tuning)** (Databricks). PEFT, LoRA, when fine-tune vs. RAG.
- **[LLM Fine-Tuning in 2025: A Hands-On, Test-Driven Blueprint](https://medium.com/@tabers77/llm-fine-tuning-in-2025-a-hands-on-test-driven-blueprint-dd1c7887bb99)** (Medium). End-to-end SFT then DPO walkthrough with TRL and PEFT.

### Deeper (optional)

- **[InstructGPT paper: Training language models to follow instructions with human feedback](https://arxiv.org/abs/2203.02155)** (Ouyang et al., 2022). The RLHF foundation.
- **[ORPO: Monolithic Preference Optimization without Reference Model](https://arxiv.org/abs/2403.07691)** (Hong et al., 2024).
- **[Comparing Retrieval-Augmentation and Parameter-Efficient Fine-Tuning for Personalization](https://arxiv.org/abs/2409.09510)** (2025). When RAG matches or beats fine-tuning.

### Applied exercise

Do not start by fine-tuning. Start by writing a one-page document for your own project answering: (1) what behavior change am I after, (2) is it style, format, or knowledge, (3) have I exhausted prompt engineering and RAG, (4) how will I measure success and detect regression. Then, if the answer is still "fine-tune," fine-tune a small open model (Llama 3 8B or Qwen 2.5 7B) with QLoRA on 500 examples in JSONL format. Use TRL plus PEFT plus Unsloth for speed. Compare against your prompt-and-RAG baseline on the same eval suite.

For a vertical AI startup, the brutally honest answer most of the time is: fine-tuning is not the moat. Domain context, evals, and workflow integration are.

---

## Phase 9: Advanced Prompt Engineering (interleaved throughout)

This is not really a separate phase. Advanced prompt techniques are tools you will reach for inside every phase above. Treat this as a reference list.

### Core reading

- **[A Systematic Survey of Prompt Engineering in Large Language Models](https://arxiv.org/abs/2402.07927)** (Sahoo et al., updated 2025). Taxonomy of 58 prompting techniques.
- **[Anthropic prompt engineering overview](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview)** (Anthropic docs). Practical, model-specific.
- **[Self-Consistency Improves Chain of Thought Reasoning](https://arxiv.org/abs/2203.11171)** (Wang et al., 2022).
- **[Tree of Thoughts: Deliberate Problem Solving with LLMs](https://arxiv.org/abs/2305.10601)** (Yao et al., 2023).
- **[Least-to-Most Prompting Enables Complex Reasoning](https://arxiv.org/abs/2205.10625)** (Zhou et al., 2022). Decomposition pattern.

### Deeper (optional)

- **[The Prompt Report: A Systematic Survey of Prompting Techniques](https://arxiv.org/abs/2406.06608)** (Schulhoff et al., 2024). 200+ techniques cataloged.

---

## Cross-cutting: Staying Current Without Drowning

The field moves fast. Pick four sources and ignore the rest until you have shipped something.

- **[Anthropic Engineering blog](https://www.anthropic.com/engineering)**. High signal, ships infrequently.
- **[Simon Willison's blog](https://simonwillison.net/)**. Daily, well-curated, opinionated.
- **[Latent Space podcast and newsletter](https://www.latent.space/)**. Practitioner-focused interviews.
- **arXiv cs.CL and cs.AI new submissions**, filtered through Twitter/X lists or [Hugging Face Daily Papers](https://huggingface.co/papers).

Avoid the temptation to read every announcement. Most of what you read in week 1 will be obsolete by week 12. Build, measure, ship.

---

## Synthesis: Putting It Together for a Vertical AI Startup

For your specific situation (vertical AI in US construction tech, water damage restoration), the order of operations that maximizes leverage is:

1. **Context engineering first.** Deeply specified system prompts and tool descriptions encoding domain knowledge from your insider contact.
2. **RAG second.** Industry standards (IICRC S500, S520), insurance carrier guidelines, equipment specs, historical job records. Contextual retrieval plus reranking, not naive embedding.
3. **Evals third.** Without a golden dataset of "what a good response looks like in this domain," you cannot improve anything. The insider contact is the source of truth here.
4. **Caching fourth.** Once the static parts of your prompts stabilize, caching turns unit economics from break-even to attractive.
5. **Agents fifth.** Once your workflows are stable, wrap them as agents with structured tool calls (intake, scheduling, estimate generation, insurance form filling).
6. **Memory sixth.** For repeat customers, technicians, properties.
7. **Fine-tuning last, if at all.** Only after you have shipped, gathered real user data, and identified a specific behavior that prompt and RAG cannot fix.

The unfair advantage in vertical AI is rarely the model layer. It is the data layer (your insider's knowledge encoded as context and retrieval) and the workflow layer (the agent design that fits how the industry actually operates). Spend your engineering budget there.

---

## Quick Reference: One-Line Heuristics

- "Prompt engineering is enough" until it is not. Most problems are prompt problems hiding as model problems.
- Knowledge gap? Use RAG. Behavior gap? Use fine-tuning. Reasoning gap? Use better prompting or a stronger model.
- Long context is expensive. Cache the static prefix or pay the price 100 times.
- If a human engineer cannot tell which tool to use, the agent cannot either.
- The minimum viable eval is 20 hand-built examples. Ship the eval before the feature.
- All models degrade with long context. Compact aggressively.
- Fine-tuning teaches form, not facts. Use RAG for facts.
- LoRA gets 90% of full fine-tuning performance at 5% of the cost.
- LLM-as-judge needs a rubric. Free-form scoring is noise.
- The right sequence is Prompt then RAG then Fine-tune then Distill.

---

## Suggested Eight-Week Schedule

| Week | Focus | Reading load | Build |
|------|-------|--------------|-------|
| 1 | Mental model + transformer refresh | Medium | Token-counting script |
| 2 | Context engineering | Medium | Rebuild one workflow as six-layer context |
| 3 | RAG fundamentals | Heavy | Naive vs. hybrid vs. contextual RAG, same data |
| 4 | RAG advanced + start agents | Heavy | Agent with 3 to 5 tools |
| 5 | Agents + memory | Medium | Add memory to the agent |
| 6 | Caching + start evals | Light | Cache the agent, build eval set |
| 7 | Evals + start fine-tuning theory | Medium | CI eval pipeline |
| 8 | Fine-tuning (only if needed) + synthesis | Light | Decision doc, optional LoRA run |

If you finish in six weeks, great. If you take twelve, also great. The schedule is a frame, not a target.
