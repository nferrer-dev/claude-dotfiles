---
name: iterative-retrieval
description: Use when a subagent or task needs to discover relevant files in an unfamiliar codebase. Employs a dispatch-evaluate-refine loop to find the right context without guessing.
---

# Iterative Retrieval Pattern

Solves the context problem in multi-agent workflows: subagents don't know which files matter until they start looking.

## The Problem

Sending all context exceeds token limits. Sending none leaves agents uninformed. Guessing usually fails.

## Four-Phase Cycle (max 3 iterations)

### 1. DISPATCH
Start with broad keyword searches across likely file patterns:
- Use Glob for file discovery (`**/*.ts`, `src/**/*.py`)
- Use Grep for keyword search across the codebase
- Cast a wide net in the first cycle

### 2. EVALUATE
Score retrieved files for relevance (0-1 scale):
- **High (0.8-1.0):** Directly implements or defines the target functionality
- **Medium (0.5-0.7):** Related types, interfaces, or utilities
- **Low (0.2-0.4):** Tangentially related
- **None (0-0.2):** Not relevant

Identify gaps: "I found the API handler but not the database layer."

### 3. REFINE
Update search criteria based on what you learned:
- Use terminology discovered in the code (e.g., codebase uses "throttle" not "rate-limit")
- Narrow file patterns based on project structure
- Search for imports/references found in high-relevance files

### 4. LOOP
Repeat until:
- You have 3+ files scoring >= 0.7 relevance
- OR you've completed 3 cycles without finding better results

## Key Principles

- **Learn the codebase's language first.** Early cycles reveal naming conventions.
- **Quality over quantity.** 3 highly relevant files > 10 marginally relevant ones.
- **Follow the imports.** High-relevance files reference other important files.
- **Stop when good enough.** Don't pursue exhaustive coverage.

## Example

Task: "Fix the rate limiting bug"

**Cycle 1:** Search for "rate limit" -> find nothing. But discover `middleware/` directory.
**Cycle 2:** Search `middleware/` for "throttle" -> find `throttle.ts` (0.9) and `config.ts` (0.6).
**Cycle 3:** Read imports in `throttle.ts` -> find `redis-cache.ts` (0.8). Done.

Return: `throttle.ts`, `redis-cache.ts`, `config.ts`
