"""Grafo LangGraph: rotear -> agente -> guardiao -> (fim | revisao)."""
import re
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from . import config, prompts
from .rag import rag_service as default_rag_service 


class EstadoGrafo(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]  # memoria da conversa
    intencao: str
    rascunho: str
    feedback: str
    tentativas: int
    aprovada: bool
    contexto: str 


AGENTE_POR_INTENCAO = {
    "conceito": "tutor",
    "exemplo": "exemplificador",
    "exercicio": "inquiridor",
    "avaliacao": "inquiridor",
    "codigo_pronto": "inquiridor",
}
PAPEIS = {
    "tutor": prompts.TUTOR,
    "exemplificador": prompts.EXEMPLIFICADOR,
    "inquiridor": prompts.INQUIRIDOR,
}
_PADRAO_INVENTADO = re.compile(r"padr[ãa]o\s+(?:chamado|denominado|de nome)\s+[\"']?([\w\- ]+?)[\"']?(?:\s+e\s|[,.?!]|$)", re.I)


def _texto(msg) -> str:
    if isinstance(msg, str):
        return msg
    return getattr(msg, "content", str(msg))


def detectar_padrao_inventado(texto: str) -> bool:
    """Regra deterministica anti-alucinacao: nome citado fora do catalogo GoF."""
    m = _PADRAO_INVENTADO.search(texto)
    return bool(m) and m.group(1).strip().lower() not in config.PADROES_GOF


def montar_grafo(llm, rag_service=None):
    rag = rag_service or default_rag_service

    def chamar(system: str, msgs: list[BaseMessage]) -> str:
        return _texto(llm.invoke([SystemMessage(content=system)] + msgs)).strip()

    def rotear(state: EstadoGrafo):
        ultima = _texto(state["messages"][-1])
        base = {"tentativas": 0, "feedback": "", "aprovada": False, "rascunho": ""}
        if detectar_padrao_inventado(ultima):
            return {**base, "intencao": "padrao_inventado"}
        try:
            rotulo = chamar(prompts.ROTEADOR_SYSTEM, state["messages"][-config.MAX_MENSAGENS_HISTORICO:])
            rotulo = rotulo.lower().strip().split()[0].strip(".,:;\"'") if rotulo else ""
        except Exception:
            rotulo = ""
        valido = set(AGENTE_POR_INTENCAO) | {"fora_escopo"}
        return {**base, "intencao": rotulo if rotulo in valido else "conceito"}

    def decidir_agente(state: EstadoGrafo) -> str:
        intencao = state["intencao"]
        if intencao == "padrao_inventado":
            return "recusa_inventado"
        if intencao == "fora_escopo":
            return "recusa_fora_escopo"
        return AGENTE_POR_INTENCAO[intencao]

    def criar_agente(chave: str):
        def no(state: EstadoGrafo):
            ultima_msg = _texto(state["messages"][-1])

            contexto = rag.buscar_contexto(ultima_msg)
            system = prompts.montar_system(PAPEIS[chave], contexto)
            system += "\n\n" + prompts.INSTRUCAO_POR_INTENCAO[state["intencao"]]
            if state.get("feedback"):
                system += f"\n\nREVISAO PEDIDA PELO GUARDIAO: {state['feedback']} Corrija a resposta."
            hist = state["messages"][-config.MAX_MENSAGENS_HISTORICO:]
            return {"rascunho": chamar(system, hist), "contexto": contexto}
        return no

    def recusa(texto: str):
        def no(state: EstadoGrafo):
            return {"messages": [AIMessage(content=texto)]}
        return no

    def guardiao(state: EstadoGrafo):
        rascunho = state.get("rascunho", "")
        contexto_usado = state.get("contexto", "Material sobre o padrão State.")
        if not rascunho:
            return {"aprovada": True, "messages": [AIMessage(content="Nao consegui gerar uma resposta. Pode reformular?")]}
        try:
            veredito = chamar(
                prompts.GUARDIAO_SYSTEM,
                [__import__("langchain_core.messages", fromlist=["HumanMessage"]).HumanMessage(
                    content=f"MATERIAL:\n{contexto_usado}\n\nRESPOSTA:\n{rascunho}")],
            )
        except Exception:
            veredito = "OK"  # falha do revisor nao deve derrubar o sistema

        if veredito.upper().startswith("REVISAR") and state.get("tentativas", 0) < config.MAX_TENTATIVAS_GUARDIAO:
            return {"aprovada": False, "feedback": veredito, "tentativas": state.get("tentativas", 0) + 1}
        texto = rascunho
        if veredito.upper().startswith("REVISAR"):
            texto += "\n\n(Aviso: esta resposta pode conter imprecisoes; confira no material da disciplina.)"
        return {"aprovada": True, "messages": [AIMessage(content=texto)]}

    def depois_guardiao(state: EstadoGrafo) -> str:
        return END if state.get("aprovada") else AGENTE_POR_INTENCAO[state["intencao"]]

    g = StateGraph(EstadoGrafo)
    g.add_node("rotear", rotear)
    for chave in PAPEIS:
        g.add_node(chave, criar_agente(chave))
    g.add_node("recusa_inventado", recusa(prompts.RECUSA_INVENTADO))
    g.add_node("recusa_fora_escopo", recusa(prompts.RECUSA_FORA_ESCOPO))
    g.add_node("guardiao", guardiao)

    g.add_edge(START, "rotear")
    g.add_conditional_edges("rotear", decidir_agente,
                            [*PAPEIS, "recusa_inventado", "recusa_fora_escopo"])
    for chave in PAPEIS:
        g.add_edge(chave, "guardiao")
    g.add_conditional_edges("guardiao", depois_guardiao, [*PAPEIS, END])
    g.add_edge("recusa_inventado", END)
    g.add_edge("recusa_fora_escopo", END)
    return g.compile(checkpointer=MemorySaver())
