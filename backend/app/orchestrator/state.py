from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class GraphState(TypedDict):
    """Workflow state: short-term memory for LangGraph."""

    messages: Annotated[list[BaseMessage], add_messages]
    user_prompt: str
    safe_prompt: str
    enhanced_prompt: str
    input_blocked: bool
    input_reasons: list[str]
    input_guard_details: dict[str, Any]
    prompt_valid: bool
    prompt_guidance: str
    prompt_validation_details: dict[str, Any]
    prompt_enhancement_details: dict[str, Any]
    assigned_agents: list[str]
    financial_payload: dict[str, Any]
    draft_report: str
    llm_output: dict[str, Any]
    final_report: str
    output_redactions: list[str]
