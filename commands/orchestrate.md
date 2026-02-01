---
name: orchestrate
description: Sequential agent workflow for complex tasks. Chains specialized agents together with structured handoffs.
---

# Orchestrate: Sequential Agent Workflows

Chain specialized agents together for complex development tasks. Each agent passes a structured handoff to the next.

## Usage

`/orchestrate [workflow-type] [task-description]`

## Predefined Workflows

### feature
Full feature implementation: planner -> tdd-guide -> code-reviewer -> security-reviewer

### bugfix
Investigation and resolution: explorer -> tdd-guide -> code-reviewer

### refactor
Safe restructuring: architect -> code-reviewer -> tdd-guide

### security
Security-focused review: security-reviewer -> code-reviewer -> tdd-guide

### custom
Specify your own sequence: `/orchestrate custom "agent1,agent2,agent3" "task description"`

## Execution Process

For each agent in the sequence:

1. **Receive context** from previous agent's handoff (or initial task description)
2. **Perform specialized work** using the agent's expertise
3. **Create handoff document** for next agent:

```markdown
## Handoff: [agent-name] -> [next-agent-name]

### Context
[What this task is about]

### Findings
[What was discovered/implemented]

### Modified Files
[List of changed files]

### Open Questions
[Unresolved issues for next agent]

### Recommendations
[Suggestions for next steps]
```

4. **Pass to next agent** in sequence

## Final Report

After all agents complete, produce:

```markdown
## Orchestration Report

### Task: [description]
### Workflow: [type]

### Agent Results
1. [Agent 1]: [summary]
2. [Agent 2]: [summary]
...

### Files Changed
[consolidated list]

### Test Results
[pass/fail summary]

### Security Status
[clean / issues found]

### Recommendation: SHIP / NEEDS WORK / BLOCKED
[justification]
```

## Best Practices

- Start with planners for complex features
- Always include code review before merging
- Use security reviewer for auth, payments, user input
- Keep handoffs concise — focus on what the next agent needs
- Run verification between agents when appropriate
