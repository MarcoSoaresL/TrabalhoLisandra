# Tutor multiagente do padrao State (LangGraph + Ollama)

## Execucao (100% local, custo zero)
1. Instale o Ollama e rode: `ollama pull qwen2.5:7b`
2. `python -m venv .venv && source .venv/bin/activate`
3. `pip install -r requirements.txt`
4. `python -m agente "Explique o que e o padrao State"`
   ou `python -m agente` para o modo conversa ('sair' encerra).

Testes: `pip install pytest && pytest`
