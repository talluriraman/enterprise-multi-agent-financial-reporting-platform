"""
LangGraph orchestrator: input guard → validate → (guidance | enhance) → agents → output guard.

Agents communicate only through orchestrator state (no direct agent-to-agent calls).
"""

from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, StateGraph

from app.agents.financial_data import run_financial_data_agent
from app.agents.report_synthesis import run_report_synthesis_agent
from app.guardrails.enhance import build_prompt_enhancement, enhancement_to_dict
from app.guardrails.input import InputGuardResult, guard_user_prompt
from app.guardrails.output import guard_output
from app.guardrails.user_messages import VALIDATION_FAILED_SHORT
from app.guardrails.validation import assess_financial_prompt_quality
from app.orchestrator.state import GraphState


def _guard_from_state(state: GraphState) -> InputGuardResult:
    d = state.get("input_guard_details") or {}
    return InputGuardResult(
        safe_prompt=state["safe_prompt"],
        blocked=state["input_blocked"],
        reasons=list(d.get("reasons", state["input_reasons"])),
        risk_level=str(d.get("risk_level", "none")),
        injection_categories=list(d.get("injection_categories", [])),
        signals=list(d.get("signals", [])),
    )


def _route_agents(prompt: str, blocked: bool) -> list[str]:
    if blocked:
        return []
    if re.search(r"expense|financial|report|monthly|ledger|p&l|budget", prompt, re.I):
        return ["financial_data", "report_synthesis"]
    return ["financial_data", "report_synthesis"]


async def node_input_guard(state: GraphState) -> dict[str, Any]:
    res = guard_user_prompt(state["user_prompt"])
    input_guard_details = {
        "blocked": res.blocked,
        "reasons": res.reasons,
        "risk_level": res.risk_level,
        "injection_categories": res.injection_categories,
        "signals": res.signals,
    }
    return {
        "safe_prompt": res.safe_prompt,
        "input_blocked": res.blocked,
        "input_reasons": res.reasons,
        "input_guard_details": input_guard_details,
        "messages": [HumanMessage(content=state["user_prompt"])],
    }


async def node_validate_prompt(state: GraphState) -> dict[str, Any]:
    """Augmentation / quality gate: only when injection guard passed."""
    if state["input_blocked"]:
        return {
            "prompt_valid": True,
            "prompt_guidance": "",
            "prompt_validation_details": {
                "acceptable": True,
                "code": "skipped_input_blocked",
                "guidance": "",
                "hints": [],
            },
        }
    q = assess_financial_prompt_quality(state["user_prompt"])
    return {
        "prompt_valid": q.acceptable,
        "prompt_guidance": q.guidance,
        "prompt_validation_details": q.to_dict(),
    }


def route_after_validate(state: GraphState) -> str:
    if not state["input_blocked"] and not state["prompt_valid"]:
        return "guidance_only"
    return "continue"


async def node_guidance_only(state: GraphState) -> dict[str, Any]:
    """Skip LLM agents; user-facing message is a single short line (details stay in validation JSON)."""
    text = VALIDATION_FAILED_SHORT
    details = {
        "template_version": "guidance-only",
        "augmentation_skipped": True,
        "validation_code": (state.get("prompt_validation_details") or {}).get("code"),
        "user_message": text,
        "validation_hints": (state.get("prompt_validation_details") or {}).get("hints"),
    }
    return {
        "enhanced_prompt": state["user_prompt"].strip(),
        "prompt_enhancement_details": details,
        "assigned_agents": [],
        "financial_payload": {"skipped": True, "reason": "prompt_validation"},
        "draft_report": text,
        "llm_output": {},
        "messages": [AIMessage(content=text[:4000])],
    }


async def node_enhance(state: GraphState) -> dict[str, Any]:
    guard = _guard_from_state(state)
    pe = build_prompt_enhancement(state["safe_prompt"], state["input_blocked"], guard)
    return {
        "enhanced_prompt": pe.enhanced_prompt,
        "prompt_enhancement_details": enhancement_to_dict(pe),
    }


async def node_assign(state: GraphState) -> dict[str, Any]:
    agents = _route_agents(state["enhanced_prompt"], state["input_blocked"])
    return {"assigned_agents": agents}


async def node_financial_data(state: GraphState) -> dict[str, Any]:
    if state["input_blocked"] or "financial_data" not in state["assigned_agents"]:
        return {"financial_payload": {"skipped": True}}
    payload = await run_financial_data_agent(state["enhanced_prompt"])
    return {"financial_payload": payload}


async def node_report_synthesis(state: GraphState) -> dict[str, Any]:
    if state["input_blocked"]:
        text = (
            "Your request could not be processed due to input policy violations. "
            + ", ".join(state["input_reasons"] or ["policy"])
        )
        return {"draft_report": text, "llm_output": {}}
    draft, llm_meta = await run_report_synthesis_agent(state["enhanced_prompt"], state["financial_payload"])
    return {
        "draft_report": draft,
        "llm_output": llm_meta,
        "messages": [AIMessage(content=draft[:4000])],
    }


async def node_output_guard(state: GraphState) -> dict[str, Any]:
    g = guard_output(state["draft_report"])
    return {"final_report": g.text, "output_redactions": g.redactions}


def build_graph():
    g = StateGraph(GraphState)
    g.add_node("input_guard", node_input_guard)
    g.add_node("validate_prompt", node_validate_prompt)
    g.add_node("guidance_only", node_guidance_only)
    g.add_node("enhance", node_enhance)
    g.add_node("assign", node_assign)
    g.add_node("financial_data", node_financial_data)
    g.add_node("report_synthesis", node_report_synthesis)
    g.add_node("output_guard", node_output_guard)

    g.set_entry_point("input_guard")
    g.add_edge("input_guard", "validate_prompt")
    g.add_conditional_edges(
        "validate_prompt",
        route_after_validate,
        {
            "guidance_only": "guidance_only",
            "continue": "enhance",
        },
    )
    g.add_edge("guidance_only", "output_guard")
    g.add_edge("enhance", "assign")
    g.add_edge("assign", "financial_data")
    g.add_edge("financial_data", "report_synthesis")
    g.add_edge("report_synthesis", "output_guard")
    g.add_edge("output_guard", END)

    return g.compile()


graph_app = build_graph()


async def run_orchestration(user_prompt: str) -> dict[str, Any]:
    initial: GraphState = {
        "messages": [],
        "user_prompt": user_prompt,
        "safe_prompt": "",
        "enhanced_prompt": "",
        "input_blocked": False,
        "input_reasons": [],
        "input_guard_details": {},
        "prompt_valid": True,
        "prompt_guidance": "",
        "prompt_validation_details": {},
        "prompt_enhancement_details": {},
        "assigned_agents": [],
        "financial_payload": {},
        "draft_report": "",
        "llm_output": {},
        "final_report": "",
        "output_redactions": [],
    }
    out = await graph_app.ainvoke(initial)
    return out
