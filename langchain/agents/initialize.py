"""Load agent."""
from typing import Any, List, Optional

from langchain.agents.agent import AgentExecutor
from langchain.agents.loading import AGENT_TO_CLASS, load_agent
from langchain.agents.tools import Tool
from langchain.callbacks.base import BaseCallbackManager
from langchain.llms.base import BaseLLM


def initialize_agent(
    tools: List[Tool],
    llm: BaseLLM,
    agent: Optional[str] = None,
    callback_manager: Optional[BaseCallbackManager] = None,
    agent_path: Optional[str] = None,
    agent_kwargs: Optional[dict] = None,
    **kwargs: Any,
) -> AgentExecutor:
    """Load agent given tools and LLM.

    Args:
        tools: List of tools this agent has access to.
        llm: Language model to use as the agent.
        agent: The agent to use. Valid options are:
            `zero-shot-react-description`
            `react-docstore`
            `self-ask-with-search`
            `conversational-react-description`
            If None and agent_path is also None, will default to
            `zero-shot-react-description`.
        callback_manager: CallbackManager to use. Global callback manager is used if
            not provided. Defaults to None.
        agent_path: Path to serialized agent to use.
        **kwargs: Additional key word arguments to pass to the agent.

    Returns:
        An agent.
    """
    if agent is None and agent_path is None:
        agent = "zero-shot-react-description"
    if agent is not None and agent_path is not None:
        raise ValueError(
            "Both `agent` and `agent_path` are specified, "
            "but at most only one should be."
        )
    if agent is not None:
        if agent not in AGENT_TO_CLASS:
            raise ValueError(
                f"Got unknown agent type: {agent}. "
                f"Valid types are: {AGENT_TO_CLASS.keys()}."
            )
        agent_cls = AGENT_TO_CLASS[agent]
        agent_kwargs = agent_kwargs or {}
        agent_obj = agent_cls.from_llm_and_tools(
            llm, tools, callback_manager=callback_manager, **agent_kwargs
        )
    elif agent_path is not None:
        agent_obj = load_agent(
            agent_path, llm=llm, tools=tools, callback_manager=callback_manager
        )
    else:
        raise ValueError(
            "Somehow both `agent` and `agent_path` are None, "
            "this should never happen."
        )
    return AgentExecutor.from_agent_and_tools(
        agent=agent_obj,
        tools=tools,
        callback_manager=callback_manager,
        **kwargs,
    )
