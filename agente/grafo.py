"""Grafo LangGraph: rotear -> agente -> guardiao -> (fim | revisao)."""
import re
import unicodedata
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from . import config, prompts
from .rag import get_rag_service


class EstadoGrafo(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]  # memoria da conversa
    intencao: str
    rascunho: str
    feedback: str
    tentativas: int
    aprovada: bool
    contexto: str
    em_pratica: bool   # o aluno esta resolvendo um exercicio proposto antes


AGENTE_POR_INTENCAO = {
    "conceito": "tutor",
    "selecao": "tutor",
    "comparacao": "tutor",
    "fechamento": "tutor",
    "exemplo": "exemplificador",
    "uso_incorreto": "exemplificador",
    "exercicio": "inquiridor",
    "avaliacao": "inquiridor",
    "codigo_pronto": "inquiridor",
}
INTENCOES_PRATICA = {"exercicio", "avaliacao", "codigo_pronto"}
PAPEIS = {
    "tutor": prompts.TUTOR,
    "exemplificador": prompts.EXEMPLIFICADOR,
    "inquiridor": prompts.INQUIRIDOR,
}

_PADRAO_CHAMADO = re.compile(
    r"padrao\s+(?:de projeto\s+)?(?:chamado|denominado|de nome|nomeado)\s+[\"']?([\w\- ]+?)[\"']?(?:\s+e\s|[,.?!]|$)")
_PADRAO_NOME_PROPRIO = re.compile(r"[Pp]adrao\s+(?:de projeto\s+)?([A-Z][\w\-]*(?:\s+[A-Z][\w\-]*)?)")
_PEDIDO_INVENCAO = re.compile(r"\b(invente|inventar|inventa|crie|criar|cria)\s+(um|uma|o|a)?\s*(novo\s+)?padrao\b")
_PEDIDO_CODIGO_PRONTO = re.compile(
    r"(codigo|solucao|resposta|programa)\s+(\w+\s+)?(pronto|pronta)|solucao\s+(\w+\s+)?completa|resolva\s+(o exercicio\s+)?(para|pra)\s+mim")


def _sem_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def _texto(msg) -> str:
    if isinstance(msg, str):
        return msg
    return getattr(msg, "content", str(msg))


def _eh_padrao_gof(nome: str) -> bool:
    nome = nome.strip().lower()
    primeira = nome.split()[0] if nome else ""
    return nome in config.PADROES_GOF or primeira == "gof" or any(
        p.split()[0] == primeira for p in config.PADROES_GOF)


def detectar_padrao_inventado(texto: str) -> bool:
    # Regra anti-alucinacao
    texto = _sem_acentos(texto)
    if _PEDIDO_INVENCAO.search(texto.lower()):
        return True
    m = _PADRAO_CHAMADO.search(texto.lower())
    if m and not _eh_padrao_gof(m.group(1)):
        return True
    return any(not _eh_padrao_gof(m.group(1)) for m in _PADRAO_NOME_PROPRIO.finditer(texto))


def detectar_pedido_codigo_pronto(texto: str) -> bool:
    return bool(_PEDIDO_CODIGO_PRONTO.search(_sem_acentos(texto).lower()))


_BLOCO_CODIGO = re.compile(r"```[\w]*\n(.*?)(?:```|$)", re.S)  # bloco sem fechamento conta ate o fim
AVISO_CODIGO_OMITIDO = ("[Codigo omitido pelo Guardiao: tente escrever esta parte voce mesmo seguindo os passos "
                        "acima. Se travar, me mostre sua tentativa que eu te ajudo a corrigir.]")
AVISO_CODIGO_LONGO = "[Trecho de codigo longo omitido: peca um exemplo em Java para ver o codigo completo comentado.]"


_OUTRO_ALFABETO = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯]")  # chines, japones, coreano


def mudou_de_idioma(texto: str) -> bool:
    # casos que troca de idioma
    return bool(_OUTRO_ALFABETO.search(texto))


def maior_bloco_codigo(texto: str) -> int:
    return max((len(b.strip().splitlines()) for b in _BLOCO_CODIGO.findall(texto)), default=0)


def remover_codigo_longo(texto: str, limite: int, aviso: str = AVISO_CODIGO_OMITIDO) -> str:
    def trocar(m):
        return m.group(0) if len(m.group(1).strip().splitlines()) <= limite else aviso
    return _BLOCO_CODIGO.sub(trocar, texto)


def interpretar_rotulo(saida: str) -> str:
    saida = _sem_acentos(saida).lower().replace(" ", "_")
    validos = sorted([*AGENTE_POR_INTENCAO, "fora_escopo"], key=len, reverse=True)
    return next((r for r in validos if r in saida), "conceito")


def montar_grafo(llm, rag_service=None):

    def chamar(system: str, msgs: list[BaseMessage]) -> str:
        return _texto(llm.invoke([SystemMessage(content=system)] + msgs)).strip()

    def rotear(state: EstadoGrafo):
        ultima = _texto(state["messages"][-1])
        base = {"tentativas": 0, "feedback": "", "aprovada": False, "rascunho": "", "contexto": "",
                "em_pratica": state.get("intencao") in INTENCOES_PRATICA}  # intencao do turno anterior
        if detectar_padrao_inventado(ultima):
            return {**base, "intencao": "padrao_inventado"}
        if detectar_pedido_codigo_pronto(ultima):
            return {**base, "intencao": "codigo_pronto"}
        try:
            saida = chamar(prompts.ROTEADOR_SYSTEM, state["messages"][-config.MAX_MENSAGENS_HISTORICO:])
        except Exception:
            saida = ""  # sem roteador, cai no tutor
        intencao = interpretar_rotulo(saida)
        # Depois de um exercicio proposto, a resposta do aluno e uma tentativa a ser avaliada
        if state.get("intencao") == "exercicio" and intencao not in {"exercicio", "fora_escopo"}:
            intencao = "avaliacao"
        return {**base, "intencao": intencao}

    def decidir_agente(state: EstadoGrafo) -> str:
        intencao = state["intencao"]
        if intencao == "padrao_inventado":
            return "recusa_inventado"
        if intencao == "fora_escopo":
            return "recusa_fora_escopo"
        return AGENTE_POR_INTENCAO[intencao]

    def consulta_rag(state: EstadoGrafo) -> str:
        consulta = _texto(state["messages"][-1])
        # Para avaliar uma tentativa, o material do exercicio proposto antes tambem e relevante
        if state["intencao"] == "avaliacao" and len(state["messages"]) >= 2:
            consulta = _texto(state["messages"][-2])[:1000] + "\n" + consulta
        return consulta

    def criar_agente(chave: str):
        def no(state: EstadoGrafo):
            contexto = state.get("contexto") or (rag_service or get_rag_service()).buscar_contexto(consulta_rag(state))
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
        if not rascunho:
            return {"aprovada": True, "contexto": "",
                    "messages": [AIMessage(content="Nao consegui gerar uma resposta. Pode reformular a pergunta?")]}
        agente = AGENTE_POR_INTENCAO[state["intencao"]]
        limite = config.LIMITE_LINHAS_CODIGO.get(agente)
        pratica = state.get("em_pratica") or agente == "inquiridor"
        if state.get("em_pratica"):  # durante a pratica nenhum agente entrega a solucao
            limite = config.LIMITE_LINHAS_CODIGO["inquiridor"]
        codigo_demais = limite is not None and maior_bloco_codigo(rascunho) > limite

        outro_idioma = mudou_de_idioma(rascunho)

        # nao gastam chamada
        if outro_idioma:
            veredito = "REVISAR: a resposta mudou de idioma. Escreva tudo em portugues do Brasil."
        elif codigo_demais:
            veredito = (f"REVISAR: codigo demais para o seu papel (maximo {limite} linhas por bloco). "
                        "Nao entregue a solucao: remova o codigo e oriente em texto.")
        else:
            try:
                veredito = chamar(prompts.GUARDIAO_SYSTEM, [HumanMessage(content=(
                    f"PERGUNTA:\n{_texto(state['messages'][-1])}\n\n"
                    f"MATERIAL:\n{state.get('contexto', '')}\n\nRESPOSTA:\n{rascunho}"))])
            except Exception:
                veredito = "OK"  # falha do revisor nao deve derrubar o sistema

        revisar = veredito.upper().lstrip("\"' ").startswith("REVISAR")
        if revisar and state.get("tentativas", 0) < config.MAX_TENTATIVAS_GUARDIAO:
            return {"aprovada": False, "feedback": veredito, "tentativas": state.get("tentativas", 0) + 1}
        texto = rascunho
        if outro_idioma:  # mantem so a parte em portugues
            texto = texto[:_OUTRO_ALFABETO.search(texto).start()].rstrip()
            texto = texto[:texto.rfind("\n")] if "\n" in texto else texto  # descarta a linha misturada
            texto += "\n\n(Parte da resposta foi descartada por erro do modelo. Pode repetir a pergunta?)"
        if codigo_demais:
            texto = remover_codigo_longo(texto, limite, AVISO_CODIGO_OMITIDO if pratica else AVISO_CODIGO_LONGO)
        elif revisar and not outro_idioma:
            texto += "\n\n(Aviso: esta resposta pode conter imprecisoes; confira no material da disciplina.)"
        # contexto e limpo para o proximo turno buscar o material de novo
        return {"aprovada": True, "contexto": "", "messages": [AIMessage(content=texto)]}

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
