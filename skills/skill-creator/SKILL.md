---
name: skill-creator
description: Guide for creating effective skills that extend Claude's capabilities with specialized knowledge, workflows, or tool integrations. Use when creating a new skill or updating an existing skill.
---

# Skill Creator

## About Skills

Skills are modular packages that extend Claude with specialized knowledge, workflows, and tools. They transform Claude from a general-purpose agent into a specialized agent with procedural knowledge.

### Anatomy of a Skill

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter: name + description (required)
│   └── Markdown instructions (required)
└── Bundled Resources (optional)
    ├── scripts/      - Executable code (Python/Bash)
    ├── references/   - Documentation loaded into context as needed
    └── assets/       - Files used in output (templates, icons, fonts)
```

### Progressive Disclosure

1. **Metadata** (name + description) — Always in context (~100 words)
2. **SKILL.md body** — When skill triggers (<5k words)
3. **Bundled resources** — As needed (unlimited; scripts can execute without reading)

## Skill Creation Process

### Step 1: Understand with Concrete Examples
Gather concrete usage examples. Ask:
- What functionality should the skill support?
- Can you give examples of how it would be used?
- What would a user say that should trigger this skill?

### Step 2: Plan Reusable Contents
For each example, analyze:
1. How to execute from scratch
2. What scripts, references, and assets would help when doing this repeatedly

Examples:
- PDF rotation → `scripts/rotate_pdf.py`
- Frontend webapp → `assets/hello-world/` boilerplate template
- BigQuery queries → `references/schema.md` with table schemas

### Step 3: Initialize the Skill
```bash
scripts/init_skill.py <skill-name> --path <output-directory>
```
Creates template directory with SKILL.md, scripts/, references/, assets/.

### Step 4: Edit the Skill

**Writing Style**: Imperative/infinitive form (verb-first instructions), not second person. Use "To accomplish X, do Y" not "You should do X."

Answer these questions in SKILL.md:
1. What is the purpose of the skill?
2. When should it be used?
3. How should Claude use it? (Reference all bundled resources)

**Key principles**:
- Keep SKILL.md lean; put detailed info in references/
- Information lives in SKILL.md OR references, not both
- Delete unused example directories from initialization

### Step 5: Package
```bash
scripts/package_skill.py <path/to/skill-folder>
```
Validates (frontmatter, naming, structure, description quality) then creates distributable zip.

### Step 6: Iterate
1. Use the skill on real tasks
2. Notice struggles or inefficiencies
3. Update SKILL.md or bundled resources
4. Test again
