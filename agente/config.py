import os
from pathlib import Path

PADRAO = "State"

MODELO = os.getenv("AGENTE_MODELO", "qwen2.5:7b")
MODELO_EMBEDDING = os.getenv("AGENTE_MODELO_EMBEDDING", "nomic-embed-text")
OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")  # servidor local

TEMPERATURA = 0.2
MAX_TOKENS_RESPOSTA = 1200             # folga para nao cortar codigo no meio
JANELA_CONTEXTO = 8192                 # o padrao do Ollama e pequeno
TIMEOUT_S = 300
MAX_MENSAGENS_HISTORICO = 8            # memoria enviada aos agentes
MAX_TENTATIVAS_GUARDIAO = 1            # quantas vezes o guardiao pode pedir revisao


LIMITE_LINHAS_CODIGO = {"tutor": 20, "exemplificador": None, "inquiridor": 5}

CONHECIMENTO = Path(__file__).parent / "conhecimento" / "state.md"
INDICE_RAG = Path(__file__).parent / "faiss_index"
RAG_K = 4                              # trechos do material recuperados por pergunta
RAG_TAMANHO_TRECHO = 1500

PADROES_GOF = {
    "factory method", "abstract factory", "builder", "prototype", "adapter",
    "bridge", "composite", "decorator", "facade", "flyweight", "proxy",
    "chain of responsibility", "command", "interpreter", "iterator",
    "mediator", "memento", "observer", "state", "strategy",
    "template method", "visitor", "singleton",
}

OUTROS_PADROES = PADROES_GOF - {PADRAO.lower()}
