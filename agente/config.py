from pathlib import Path

PADRAO = "State"
MODELO = "qwen2.5:7b"                
OLLAMA_URL = "http://localhost:11434"  
TEMPERATURA = 0.2
MAX_TOKENS_RESPOSTA = 700
TIMEOUT_S = 180
MAX_MENSAGENS_HISTORICO = 8            
MAX_TENTATIVAS_GUARDIAO = 1           

CONHECIMENTO = Path(__file__).parent / "conhecimento" / "state.md"

PADRAO = "State"

PADROES_GOF = {
    "factory method", "abstract factory", "builder", "prototype", "adapter",
    "bridge", "composite", "decorator", "facade", "flyweight", "proxy",
    "chain of responsibility", "command", "interpreter", "iterator",
    "mediator", "memento", "observer", "strategy",
    "template method", "visitor", "singleton",
}

OUTROS_PADROES = PADROES_GOF - {PADRAO.lower()}
