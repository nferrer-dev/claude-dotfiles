---
name: mcp-builder
description: Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. Use when building MCP servers to integrate external APIs or services, whether in Python (FastMCP) or Node/TypeScript (MCP SDK).
---

# MCP Server Development Guide

## Overview

Create MCP servers that enable LLMs to effectively interact with external services. Quality is measured by how well the server enables LLMs to accomplish real-world tasks.

## Process

### Phase 1: Deep Research and Planning

#### 1.1 Agent-Centric Design Principles

- **Build for Workflows, Not Endpoints**: Consolidate related operations (e.g., `schedule_event` that checks availability AND creates event)
- **Optimize for Limited Context**: Return high-signal info, not data dumps. Provide "concise" vs "detailed" options. Default to human-readable identifiers over IDs.
- **Actionable Error Messages**: Suggest next steps: "Try using filter='active_only' to reduce results"
- **Natural Task Subdivisions**: Tool names should reflect how humans think about tasks
- **Evaluation-Driven Development**: Create realistic eval scenarios early, iterate based on agent performance

#### 1.2 Study MCP Protocol
Fetch: `https://modelcontextprotocol.io/llms-full.txt`

#### 1.3 Study SDK Documentation
- Python: `https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md`
- TypeScript: `https://raw.githubusercontent.com/modelcontextprotocol/typescript-sdk/main/README.md`

#### 1.4 Exhaustively Study Target API Documentation
Read ALL available API docs: auth, rate limiting, pagination, error responses, endpoints, data models.

#### 1.5 Create Implementation Plan
- **Tool Selection**: Most valuable endpoints, prioritized by use case importance
- **Shared Utilities**: Common request patterns, pagination helpers, error handling
- **Input/Output Design**: Validation models (Pydantic/Zod), consistent response formats, truncation strategies
- **Error Handling Strategy**: Graceful failures, actionable messages, rate limiting, auth errors

### Phase 2: Implementation

#### 2.1 Project Structure
- **Python**: Single .py or modules, MCP Python SDK, Pydantic models
- **TypeScript**: Proper project structure, package.json + tsconfig.json, Zod schemas

#### 2.2 Core Infrastructure First
Build before implementing tools: API request helpers, error handling, response formatting, pagination, auth management.

#### 2.3 Implement Tools Systematically

For each tool:
1. **Input Schema**: Pydantic/Zod with constraints, clear descriptions, examples
2. **Docstrings**: Summary, detailed explanation, parameter types, return schema, usage examples, error docs
3. **Tool Logic**: Shared utilities, async/await, error handling, multiple response formats, pagination, truncation
4. **Annotations**: `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`

### Phase 3: Review and Refine

#### 3.1 Code Quality Review
- DRY: No duplicated code
- Composability: Shared logic extracted
- Consistency: Similar operations → similar formats
- Error Handling: All external calls covered
- Type Safety: Full coverage
- Documentation: Every tool documented

#### 3.2 Test and Build

**Important**: MCP servers are long-running processes. Running directly will hang your process.

Safe testing:
- Use evaluation harness (recommended)
- Run in tmux
- Use timeout: `timeout 5s python server.py`

Python: `python -m py_compile your_server.py`
TypeScript: `npm run build`

### Phase 4: Create Evaluations

Create 10 evaluation questions that are:
- Independent, read-only, complex, realistic, verifiable, stable

Output format:
```xml
<evaluation>
  <qa_pair>
    <question>Your question here</question>
    <answer>Expected answer</answer>
  </qa_pair>
</evaluation>
```
