from langchain_ollama import ChatOllama
from . import config


def get_llm() -> ChatOllama:
    return ChatOllama(
        model=config.MODELO,
        base_url=config.OLLAMA_URL,
        temperature=config.TEMPERATURA,
        num_predict=config.MAX_TOKENS_RESPOSTA,
        client_kwargs={"timeout": config.TIMEOUT_S},
    )
