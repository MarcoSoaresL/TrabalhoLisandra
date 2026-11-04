from langchain_core.messages import AIMessage

from agente.grafo import (detectar_padrao_inventado, detectar_pedido_codigo_pronto,
                          interpretar_rotulo, montar_grafo)
from agente.sistema import Sistema
from agente import prompts


class GrafoQuebrado:
    def invoke(self, *a, **k):
        raise ConnectionError("ollama fora do ar")


class LLMFalso:
    def __init__(self, rotulo="conceito", vereditos=("OK",)):
        self.rotulo = rotulo
        self.vereditos = list(vereditos)
        self.chamadas = []

    def invoke(self, mensagens):
        system = mensagens[0].content
        self.chamadas.append((system, mensagens[1:]))
        if system.startswith("ROLE: Roteador"):
            return AIMessage(content=self.rotulo)
        if system.startswith("ROLE: Guardiao"):
            return AIMessage(content=self.vereditos.pop(0) if self.vereditos else "OK")
        papel = system.splitlines()[0].removeprefix("ROLE: ")
        return AIMessage(content=f"resposta do {papel}")


class RAGFalso:
    def buscar_contexto(self, query):
        return "MATERIAL FALSO"


def sistema_falso(llm):
    return Sistema(montar_grafo(llm, rag_service=RAGFalso()))


# --- tratamento de erros -------------------------------------------------

def test_entrada_vazia():
    assert "nao digitou" in Sistema(GrafoQuebrado()).resposta("   ")


def test_falha_do_modelo_nao_derruba():
    assert "Falha ao consultar" in Sistema(GrafoQuebrado()).resposta("oi")


def test_saida_vazia_do_modelo():
    class LLMMudo(LLMFalso):
        def invoke(self, mensagens):
            r = super().invoke(mensagens)
            return AIMessage(content="") if "Tutor" in mensagens[0].content[:30] else r
    assert "reformular" in sistema_falso(LLMMudo()).resposta("O que e o State?")


def test_rotulo_inesperado_vira_conceito():
    assert interpretar_rotulo("Acho que e: exemplo.") == "exemplo"
    assert interpretar_rotulo("uso incorreto") == "uso_incorreto"
    assert interpretar_rotulo("blablabla") == "conceito"


# --- regras anti-alucinacao deterministicas -------------------------------

def test_padrao_inventado():
    assert detectar_padrao_inventado("Invente um padrão chamado Zeta e explique")
    assert detectar_padrao_inventado("Explique o padrão Zeta")
    assert not detectar_padrao_inventado("Explique o padrão chamado Strategy")
    assert not detectar_padrao_inventado("Explique o que é o padrão State e qual problema ele resolve.")
    assert not detectar_padrao_inventado("O padrão Chain of Responsibility é parecido?")


def test_pedido_codigo_pronto():
    assert detectar_pedido_codigo_pronto("Me entregue o código pronto de uma solução completa")
    assert not detectar_pedido_codigo_pronto("Dê um exemplo de aplicação do padrão State em Java.")


def test_recusa_padrao_inventado_sem_chamar_llm():
    llm = LLMFalso()
    assert sistema_falso(llm).resposta("Invente um padrão chamado Z e explique para mim") == prompts.RECUSA_INVENTADO
    assert llm.chamadas == []


def test_codigo_pronto_vai_para_inquiridor():
    llm = LLMFalso()
    assert sistema_falso(llm).resposta("Me entregue o código pronto de uma solução completa") == \
        "resposta do Inquiridor (diagnostico)"
    assert "Recuse com educacao" in llm.chamadas[0][0]


def test_fora_de_escopo():
    assert sistema_falso(LLMFalso(rotulo="fora_escopo")).resposta("Qual a capital da Franca?") == \
        prompts.RECUSA_FORA_ESCOPO


# --- coordenacao dos agentes e memoria ------------------------------------

def test_roteamento_para_cada_agente():
    for rotulo, papel in [("conceito", "Tutor"), ("exemplo", "Exemplificador"), ("exercicio", "Inquiridor")]:
        assert papel in sistema_falso(LLMFalso(rotulo=rotulo)).resposta("pergunta")


def test_guardiao_pede_revisao_uma_vez():
    llm = LLMFalso(vereditos=["REVISAR: confundiu com Strategy", "OK"])
    assert sistema_falso(llm).resposta("O que e o State?") == "resposta do Tutor do conceito"
    tutor = [s for s, _ in llm.chamadas if s.startswith("ROLE: Tutor")]
    assert len(tutor) == 2 and "confundiu com Strategy" in tutor[1]


def test_guardiao_reprova_duas_vezes_gera_aviso():
    llm = LLMFalso(vereditos=["REVISAR: erro", "REVISAR: erro"])
    assert "Aviso" in sistema_falso(llm).resposta("O que e o State?")


def test_memoria_entre_turnos():
    llm = LLMFalso()
    sistema = sistema_falso(llm)
    sistema.resposta("Primeira pergunta")
    sistema.resposta("Segunda pergunta")
    historico = [m.content for m in llm.chamadas[-2][1]]  # mensagens vistas pelo tutor no 2o turno
    assert historico == ["Primeira pergunta", "resposta do Tutor do conceito", "Segunda pergunta"]


CODIGO_LONGO = "Veja:\n```java\n" + "\n".join(f"linha{i};" for i in range(30)) + "\n```\nTente agora."


class LLMQueEntregaCodigo(LLMFalso):
    def __init__(self, respostas):
        super().__init__(rotulo="exercicio")
        self.respostas = list(respostas)

    def invoke(self, mensagens):
        r = super().invoke(mensagens)
        if mensagens[0].content.startswith("ROLE: Inquiridor"):
            return AIMessage(content=self.respostas.pop(0))
        return r


def test_inquiridor_com_codigo_longo_e_revisado():
    llm = LLMQueEntregaCodigo([CODIGO_LONGO, "Pense em quais classes criar."])
    assert sistema_falso(llm).resposta("Me passe um exercicio") == "Pense em quais classes criar."
    inquiridor = [s for s, _ in llm.chamadas if s.startswith("ROLE: Inquiridor")]
    assert "codigo demais" in inquiridor[1]
    assert not any(s.startswith("ROLE: Guardiao") for s, _ in llm.chamadas[:2])  # sem chamada ao LLM


def test_codigo_longo_insistente_e_removido():
    resposta = sistema_falso(LLMQueEntregaCodigo([CODIGO_LONGO, CODIGO_LONGO])).resposta("Me passe um exercicio")
    assert "linha0" not in resposta and "Codigo omitido" in resposta and "Tente agora." in resposta


def test_bloco_curto_e_mantido():
    from agente.grafo import maior_bloco_codigo, remover_codigo_longo
    curto = "```java\nint x = 1;\n```"
    assert maior_bloco_codigo(curto) == 1 and remover_codigo_longo(curto, 5) == curto
    assert maior_bloco_codigo("```java\n" + "a;\n" * 10) == 10  # bloco cortado sem fechamento


def test_resposta_depois_de_exercicio_vai_para_avaliacao():
    class LLMRoteiro(LLMFalso):
        rotulos = ["exercicio", "comparacao", "exemplo"]

        def invoke(self, mensagens):
            if mensagens[0].content.startswith("ROLE: Roteador"):
                return AIMessage(content=self.rotulos.pop(0))
            if mensagens[0].content.startswith("ROLE: Exemplificador"):
                self.chamadas.append((mensagens[0].content, mensagens[1:]))
                return AIMessage(content=CODIGO_LONGO)
            return super().invoke(mensagens)

    sistema = sistema_falso(LLMRoteiro())
    sistema.resposta("Me passe um exercicio")
    assert sistema.resposta("Acho que e Strategy") == "resposta do Inquiridor (diagnostico)"
    # turno seguinte ainda e pratica: o exemplificador nao pode entregar codigo longo
    assert "Codigo omitido" in sistema.resposta("Me mostra um exemplo")


def test_resposta_em_outro_idioma_e_revisada():
    class LLMPoliglota(LLMFalso):
        respostas = ["O State e util.\n### State与Strategy的混淆", "Resposta em portugues."]

        def invoke(self, mensagens):
            r = super().invoke(mensagens)
            return AIMessage(content=self.respostas.pop(0)) if mensagens[0].content.startswith("ROLE: Tutor") else r

    assert sistema_falso(LLMPoliglota()).resposta("O que e o State?") == "Resposta em portugues."
