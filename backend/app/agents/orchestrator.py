"""
Multi-agent orchestration via LangGraph.

The graph mirrors the previous linear orchestrator: guard → router →
conditional lawyer / form branches and the same merge rules (including
fallback to lawyer when the form agent has no data).
"""

import time
from typing import Literal

from langgraph.graph import END, START, StateGraph
from typing_extensions import NotRequired, TypedDict

from app.agents.form_agent import form_agent
from app.agents.guard_agent import guard_agent
from app.agents.lawyer_agent import lawyer_agent
from app.agents.router_agent import detect_intent
from app.metrics import agent_calls_total, agent_duration_seconds, orchestrator_runs_total


class AgentState(TypedDict):
    question: str
    country: str
    guard_allowed: NotRequired[bool]
    intent: NotRequired[str]
    lawyer_text: NotRequired[str]
    form_text: NotRequired[str]
    final_answer: NotRequired[str]


def _guard_node(state: AgentState) -> dict:
    start = time.perf_counter()
    try:
        allowed = guard_agent(state["question"])
        agent_calls_total.labels(
            agent="guard", outcome="allow" if allowed else "deny"
        ).inc()
        return {"guard_allowed": allowed}
    except Exception:
        agent_calls_total.labels(agent="guard", outcome="error").inc()
        raise
    finally:
        agent_duration_seconds.labels(agent="guard").observe(
            time.perf_counter() - start
        )


def _router_node(state: AgentState) -> dict:
    start = time.perf_counter()
    try:
        intent = detect_intent(state["question"]).strip().upper()
        if intent not in ("LAW", "FORM", "BOTH"):
            intent = "BOTH"
        agent_calls_total.labels(agent="router", outcome=intent).inc()
        return {"intent": intent}
    except Exception:
        agent_calls_total.labels(agent="router", outcome="error").inc()
        raise
    finally:
        agent_duration_seconds.labels(agent="router").observe(
            time.perf_counter() - start
        )


def _lawyer_node(state: AgentState) -> dict:
    start = time.perf_counter()
    try:
        text = lawyer_agent(state["question"], state["country"])
        agent_calls_total.labels(agent="lawyer", outcome="ok").inc()
        return {"lawyer_text": text}
    except Exception:
        agent_calls_total.labels(agent="lawyer", outcome="error").inc()
        raise
    finally:
        agent_duration_seconds.labels(agent="lawyer").observe(
            time.perf_counter() - start
        )


def _form_node(state: AgentState) -> dict:
    start = time.perf_counter()
    try:
        text = form_agent(state["country"], state["question"])
        agent_calls_total.labels(agent="form", outcome="ok").inc()
        return {"form_text": text}
    except Exception:
        agent_calls_total.labels(agent="form", outcome="error").inc()
        raise
    finally:
        agent_duration_seconds.labels(agent="form").observe(
            time.perf_counter() - start
        )


def _merge_law_only(state: AgentState) -> dict:
    orchestrator_runs_total.labels(result="success").inc()
    return {"final_answer": state.get("lawyer_text") or ""}


def _merge_form_only(state: AgentState) -> dict:
    form_response = state.get("form_text") or ""
    if "нет информации" in form_response.lower():
        lawyer_response = lawyer_agent(state["question"], state["country"])
        orchestrator_runs_total.labels(result="success").inc()
        return {"final_answer": lawyer_response}
    orchestrator_runs_total.labels(result="success").inc()
    return {"final_answer": form_response}


def _merge_both(state: AgentState) -> dict:
    lawyer_response = state.get("lawyer_text") or ""
    form_response = state.get("form_text") or ""
    if "нет информации" in form_response.lower():
        lawyer_again = lawyer_agent(state["question"], state["country"])
        orchestrator_runs_total.labels(result="success").inc()
        return {"final_answer": lawyer_again}
    orchestrator_runs_total.labels(result="success").inc()
    return {
        "final_answer": lawyer_response + "\n\n---\n\n" + form_response,
    }


def _deny_node(_state: AgentState) -> dict:
    orchestrator_runs_total.labels(result="denied").inc()
    return {"final_answer": "Запрос не относится к теме поездок и въезда."}


def _route_after_guard(state: AgentState) -> Literal["router", "deny"]:
    if state.get("guard_allowed"):
        return "router"
    return "deny"


def _route_after_router(
    state: AgentState,
) -> Literal["lawyer", "form", "lawyer_for_both"]:
    intent = state.get("intent") or "BOTH"
    if intent == "LAW":
        return "lawyer"
    if intent == "FORM":
        return "form"
    return "lawyer_for_both"


def _route_after_lawyer(state: AgentState) -> Literal["merge_law", "form_after_both"]:
    intent = state.get("intent") or "BOTH"
    if intent == "BOTH":
        return "form_after_both"
    return "merge_law"


def _build_graph():
    g = StateGraph(AgentState)

    g.add_node("guard", _guard_node)
    g.add_node("router", _router_node)
    g.add_node("lawyer", _lawyer_node)
    g.add_node("form", _form_node)
    g.add_node("form_after_both", _form_node)
    g.add_node("merge_law_only", _merge_law_only)
    g.add_node("merge_form_only", _merge_form_only)
    g.add_node("merge_both", _merge_both)
    g.add_node("deny", _deny_node)

    g.add_edge(START, "guard")
    g.add_conditional_edges(
        "guard",
        _route_after_guard,
        {"router": "router", "deny": "deny"},
    )
    g.add_conditional_edges(
        "router",
        _route_after_router,
        {
            "lawyer": "lawyer",
            "form": "form",
            "lawyer_for_both": "lawyer",
        },
    )
    g.add_conditional_edges(
        "lawyer",
        _route_after_lawyer,
        {"merge_law": "merge_law_only", "form_after_both": "form_after_both"},
    )
    g.add_edge("form", "merge_form_only")
    g.add_edge("form_after_both", "merge_both")
    g.add_edge("merge_law_only", END)
    g.add_edge("merge_form_only", END)
    g.add_edge("merge_both", END)
    g.add_edge("deny", END)

    return g.compile()


_COMPILED = _build_graph()


def orchestrator(question: str, country: str = "thailand") -> str:
    result = _COMPILED.invoke({"question": question, "country": country})
    return result.get("final_answer", "")
