# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VeriFlow is an AI-driven synthesis agent that transforms behavioral product requirements (written in a custom DSL) into synthesizable Verilog code. It bridges Product Manager specifications and digital logic design using a state machine DSL.

## Running the Project

```bash
# Install dependencies
pip install -r requirements.txt

# Run the CLI-based agent (rule-based validation)
python digital_design_agent.py

# Run the LLM-powered RAG agent (requires Google Gemini API key)
export GOOGLE_API_KEY="your-key"
python rag_agent.py
```

No test suite, linter, or CI/CD is currently configured.

## Architecture

Two entry points with shared core logic:

- **`digital_design_agent.py`** — Main agent with four classes:
  - `StateMachine` — JSON-based state machine data model; persists to `state_machine.json`
  - `DSLParser` — Regex-based parser that converts DSL text into a `StateMachine`; handles three mandatory sections: `GLOBAL_TRANSITIONS`, `STATE_LIST`, `TRANSITIONS`
  - `Validator` — Checks for undefined states, deadlocks, and extracts design intent from comments (`# CRITICAL:`, `# Intent:`, `# Note:`)
  - `DigitalDesignAgent` — Orchestrator that ties parse → validate → save together

- **`rag_agent.py`** — LangChain/LangGraph agent using Google Gemini 1.5 Pro:
  - Exposes `analyze_dsl_and_critique` and `read_current_design` as LangChain tools
  - Maintains chat history for multi-turn conversations
  - Wraps the same `DSLParser`, `StateMachine`, and `Validator` from `digital_design_agent.py`

**Data flow:** DSL text → `DSLParser.parse()` → `StateMachine` (JSON) → `Validator.validate()` → critique/save

## DSL Design Constraints

The DSL follows Moore Machine architecture (outputs tied to states, not transitions). Key rules:
- Flat state hierarchy only (no nesting) — combine states like `CLOSED_LOCKED`
- Every event must have a defined outcome (determinism)
- Timers are started in transitions, triggered via `ON_TIMEOUT` within states
- Special comments (`# CRITICAL:`, `# Intent:`, `# Note:`) guide synthesis optimization (timing priority, power gating, future-proofing)
