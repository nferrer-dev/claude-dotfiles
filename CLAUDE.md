## Workflow Orchestration

### 1. Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update tasks/lessons.md with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes -- don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests -- then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management

1. **Plan First**: Write plan to tasks/todo.md with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to tasks/todo.md
6. **Capture Lessons**: Update tasks/lessons.md after corrections

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Only touch what's necessary. No side effects with new bugs.
- **No Speculative Features**: Don't add features/flags unless actively needed.
- **No Premature Abstraction**: Don't create utilities until same code written 3 times.
- **Replace, Don't Deprecate**: Remove old code entirely, no backward-compatible shims.
- **Finish the Job**: Handle edge cases you can see, clean up what you touched, don't invent new scope.

## Code Quality Hard Limits

- 100 lines/function max, cyclomatic complexity 8 max
- 5 positional params max
- 100-char line length
- Absolute imports only
- Zero warnings policy -- fix every linter/type-checker/compiler warning

## Error Handling

- Fail fast with clear, actionable messages
- Never swallow exceptions silently
- Include context: what operation, what input, suggested fix

## Testing Methodology

- Test behavior, not implementation
- Test edges and errors, not just happy path
- Mock boundaries (network, filesystem, external services), not logic
- Verify tests catch failures -- break code, confirm test fails, then fix

## Commit Conventions

- Imperative mood, 72-char subject line, one logical change per commit
- Never push directly to main -- feature branches and PRs
- Never commit secrets/credentials
