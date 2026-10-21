import uuid
from langchain_core.messages import HumanMessage

from . import config
from .grafo import montar_grafo
from .llm import get_llm


class Sistema:
    """Fachada exigida pelo enunciado: sistema.resposta(pergunta)."""

    def __init__(self, grafo):
        self.grafo = grafo
        self.thread_id = str(uuid.uuid4())  # memoria da conversa por sessao

    def resposta(self, pergunta: str) -> str:
        pergunta = (pergunta or "").strip()
        if not pergunta:
            return "Voce nao digitou nada. Pergunte algo sobre o padrao State."
        try:
            saida = self.grafo.invoke(
                {"messages": [HumanMessage(content=pergunta)]},
                config={"configurable": {"thread_id": self.thread_id}},
            )
            texto = saida["messages"][-1].content
            if not isinstance(texto, str) or not texto.strip():
                return "Recebi uma saida inesperada do modelo. Pode reformular a pergunta?"
            return texto
        except Exception as e:  # Ollama fora do ar, timeout, modelo ausente...
            return (f"Falha ao consultar o modelo local ({type(e).__name__}). "
                    f"Verifique se o Ollama esta rodando e se o modelo '{config.MODELO}' foi baixado.")


def montar_sistema() -> Sistema:
    conhecimento = config.CONHECIMENTO.read_text(encoding="utf-8")
    return Sistema(montar_grafo(get_llm(), conhecimento))
