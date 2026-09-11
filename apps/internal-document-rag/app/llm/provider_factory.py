from app.llm.base_provider import BaseLLMProvider
from app.llm.llm_router import LLMRouter

_router_instance = None


def get_llm_provider() -> BaseLLMProvider:

    global _router_instance
    if _router_instance is None:
        _router_instance = LLMRouter()
    return _router_instance
