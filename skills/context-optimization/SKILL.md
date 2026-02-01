---
name: context-optimization
description: This skill should be used when the user asks to "optimize context", "reduce token costs", "improve context efficiency", "implement KV-cache optimization", "partition context", or mentions context limits, observation masking, context budgeting, or extending effective context capacity.
---

# Context Optimization Techniques

Context optimization extends the effective capacity of limited context windows through strategic compression, masking, caching, and partitioning. The goal is not to magically increase context windows but to make better use of available capacity. Effective optimization can double or triple effective context capacity without requiring larger models or longer contexts.

## When to Activate

Activate this skill when:
- Context limits constrain task complexity
- Optimizing for cost reduction (fewer tokens = lower costs)
- Reducing latency for long conversations
- Implementing long-running agent systems
- Needing to handle larger documents or conversations
- Building production systems at scale

## Core Concepts

Context optimization extends effective capacity through four primary strategies: compaction (summarizing context near limits), observation masking (replacing verbose outputs with references), KV-cache optimization (reusing cached computations), and context partitioning (splitting work across isolated contexts).

The key insight is that context quality matters more than quantity. Optimization preserves signal while reducing noise. The art lies in selecting what to keep versus what to discard, and when to apply each technique.

## Detailed Topics

### Compaction Strategies

Compaction is the practice of summarizing context contents when approaching limits, then reinitializing a new context window with the summary. This distills the contents of a context window in a high-fidelity manner, enabling the agent to continue with minimal performance degradation.

Priority for compression: tool outputs (replace with summaries), old turns (summarize early conversation), retrieved docs (summarize if recent versions exist). Never compress system prompt.

### Observation Masking

Tool outputs can comprise 80%+ of token usage in agent trajectories. Observation masking replaces verbose tool outputs with compact references.

Never mask: Observations critical to current task, most recent turn, active reasoning.
Consider masking: Observations from 3+ turns ago, verbose outputs with key points extractable.
Always mask: Repeated outputs, boilerplate headers/footers, already-summarized outputs.

### KV-Cache Optimization

Optimize for caching by reordering context elements to maximize cache hits. Place stable elements first (system prompt, tool definitions), then frequently reused elements, then unique elements last. Avoid dynamic content like timestamps, use consistent formatting.

### Context Partitioning

The most aggressive form: partition work across sub-agents with isolated contexts. Each sub-agent operates in a clean context focused on its subtask.

### Budget Management

Allocate tokens to categories: system prompt, tool definitions, retrieved docs, message history, reserved buffer. Monitor usage against budget. Trigger optimization when utilization exceeds 70-80%.

## Optimization Decision Framework

- Tool outputs dominate: observation masking
- Retrieved documents dominate: summarization or partitioning
- Message history dominates: compaction with summarization
- Multiple components: combine strategies

## Performance Targets

- Compaction: 50-70% token reduction with <5% quality degradation
- Masking: 60-80% reduction in masked observations
- Cache optimization: 70%+ hit rate for stable workloads
