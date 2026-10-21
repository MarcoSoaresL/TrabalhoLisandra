from agente.grafo import detectar_padrao_inventado
from agente.sistema import Sistema


class GrafoQuebrado:
    def invoke(self, *a, **k):
        raise ConnectionError("ollama fora do ar")


def test_entrada_vazia():
    assert "nao digitou" in Sistema(GrafoQuebrado()).resposta("   ")


def test_falha_do_modelo_nao_derruba():
    assert "Falha ao consultar" in Sistema(GrafoQuebrado()).resposta("oi")


def test_padrao_inventado():
    assert detectar_padrao_inventado("Invente um padrão chamado Zeta e explique")
    assert not detectar_padrao_inventado("Explique o padrão chamado Strategy")
