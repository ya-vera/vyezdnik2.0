from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from app.agents.guard_agent import guard_agent
from app.agents.lawyer_agent import lawyer_agent
from app.agents.form_agent import form_agent
from app.agents.planner_agent import plan
from app.agents.censor_agent import censor


class AgentState(TypedDict):
    question: str
    country: str
    plan: dict
    step_index: int
    results: list
    final_answer: str
    prior_messages: list

def guard_node(state: AgentState):
    if not guard_agent(state["question"]):
        return {"final_answer": "Запрос не относится к теме поездок."}
    return {}


def planner_node(state: AgentState):
    p = plan(state["question"])
    return {"plan": p, "step_index": 0, "results": []}


def executor_node(state: AgentState):
    steps = state["plan"].get("steps", [])
    i = state["step_index"]

    if i >= len(steps):
        return {}

    step = steps[i]
    agent = step["agent"]

    if agent == "lawyer":
        res = lawyer_agent(state["question"], state["country"])
    elif agent == "form":
        res = form_agent(state["country"], state["question"])
    else:
        res = ""

    return {
        "results": state["results"] + [res],
        "step_index": i + 1
    }


def should_continue(state: AgentState):
    if state["step_index"] < len(state["plan"].get("steps", [])):
        return "executor"
    return "aggregate"


def aggregate_node(state: AgentState):
    final = "\n\n---\n\n".join(state["results"])
    return {"final_answer": final}


def censor_node(state: AgentState):
    ok = censor(state["question"], state["final_answer"])

    if ok:
        return {}

    # fallback
    fallback = lawyer_agent(state["question"], state["country"])
    return {"final_answer": fallback}


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("guard", guard_node)
    g.add_node("planner", planner_node)
    g.add_node("executor", executor_node)
    g.add_node("aggregate", aggregate_node)
    g.add_node("censor", censor_node)

    g.add_edge(START, "guard")
    g.add_edge("guard", "planner")
    g.add_edge("planner", "executor")

    g.add_conditional_edges("executor", should_continue, {
        "executor": "executor",
        "aggregate": "aggregate"
    })

    g.add_edge("aggregate", "censor")
    g.add_edge("censor", END)

    return g.compile()


GRAPH = build_graph()


def orchestrator(question: str, country: str = "thailand", prior_messages: list | None = None
):
    result = GRAPH.invoke({
        "question": question,
        "country": country,
        "prior_messages": prior_messages or []
    })

    return result.get("final_answer", "")