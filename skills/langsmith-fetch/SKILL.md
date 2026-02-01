---
name: langsmith-fetch
description: Debug LangChain and LangGraph agents by retrieving execution traces from LangSmith Studio. Use when debugging agent errors, analyzing tool calls, reviewing memory operations, or investigating performance issues in LangChain/LangGraph applications.
---

# LangSmith Fetch - Agent Debugging

## Setup

```bash
pip install langsmith-fetch
export LANGSMITH_API_KEY="your-key"
export LANGSMITH_PROJECT="your-project"
```

Verify: `langsmith-fetch traces --last-n-minutes 1 --limit 1`

## Workflows

### Quick Debug
```bash
langsmith-fetch traces --last-n-minutes 5 --limit 5
```
Check: success/failure status, tool invocations, duration, token usage.

### Deep Dive (specific trace)
```bash
langsmith-fetch trace <trace-id> --format json
```
Reconstruct execution flow, identify failure points, suggest fixes.

### Export Sessions
```bash
langsmith-fetch export --last-n-minutes 60 --output ./debug-session
```
Creates timestamped folder with traces and thread data.

### Error Detection
```bash
langsmith-fetch errors --last-n-minutes 30
```
Categorize by error type, frequency, affected components.

## Common Scenarios

### Agent Not Responding
Check if tracing is enabled. Look for: missing traces (agent not running), traces with no tool calls (stuck in reasoning), timeout errors.

### Wrong Tool Selection
Review agent reasoning in trace. Look for: ambiguous tool descriptions, missing context, incorrect parameter passing.

### Memory Not Working
Check memory operations: `langsmith-fetch traces --filter "memory" --last-n-minutes 10`
Verify: recall operations return data, store operations succeed, memory key consistency.

### Performance Issues
Analyze latencies: `langsmith-fetch traces --last-n-minutes 30 --format json`
Check: individual step durations, token counts per step, external API response times.

## Output Formats
- `--format pretty` — Visual inspection (default)
- `--format json` — Detailed parsing
- `--format raw` — Command piping
