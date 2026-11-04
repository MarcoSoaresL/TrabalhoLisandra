import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from agente import prompts 

CABECALHO = """# Documentação dos agentes

> Arquivo gerado por `python scripts/gerar_doc_agentes.py` a partir de `agente/prompts.py`. Não edite à mão: altere os prompts e gere de novo.

O sistema tem **cinco agentes** com papéis distintos, cada um com seu próprio prompt de sistema. Eles são orquestrados por um grafo do LangGraph (`agente/grafo.py`).

| Agente | Função pedagógica | Quando é acionado |
|---|---|---|
| Roteador | Coordenação: identifica a intenção do aluno | Em toda mensagem |
| Tutor do conceito | Ensinar: conceito, quando usar/evitar, comparação com outros padrões, fechamento | Intenções `conceito`, `selecao`, `comparacao`, `fechamento` |
| Exemplificador | Exemplificar: código Java correto e usos incorretos com correção | Intenções `exemplo`, `uso_incorreto` |
| Inquiridor | Exercitar e diagnosticar: propõe exercícios, avalia tentativas, detecta conceitos equivocados, recusa solução pronta | Intenções `exercicio`, `avaliacao`, `codigo_pronto` |
| Guardião | Garantir confiabilidade: revisa toda resposta antes de ela chegar ao aluno | Depois de cada resposta do Tutor, do Exemplificador ou do Inquiridor |

## Como os agentes se coordenam

```
               +--------------------- regras determinísticas ---------------------+
               |  padrão inventado  -> recusa educada (sem chamar o modelo)        |
               |  "código pronto"   -> Inquiridor com instrução de recusa guiada   |
               +-------------------------------------------------------------------+
pergunta -> Roteador --conceito/selecao/comparacao/fechamento--> Tutor ---------+
                 |----exemplo/uso_incorreto--------------------> Exemplificador -+--> Guardião --OK--> resposta
                 |----exercicio/avaliacao/codigo_pronto--------> Inquiridor -----+       |
                 |----fora_escopo--> recusa educada                                     REVISAR (1x)
                                                                                         |
                                                     volta ao mesmo agente com o motivo <-+
```

1. **Regras determinísticas (antes do modelo).** Expressões regulares em `grafo.py` detectam pedidos para inventar um padrão ("invente um padrão chamado Z") e nomes fora do catálogo GoF ("o padrão Zeta"). Esses pedidos recebem uma recusa fixa, sem chamar o LLM, então o modelo não tem chance de alucinar. Pedidos explícitos de código pronto vão direto ao Inquiridor.
2. **Roteador.** Classifica a última mensagem em uma de 10 intenções, usando o histórico como contexto. Se a saída for inesperada, a intenção vira `conceito` e a pergunta cai no Tutor.
3. **Agente especialista.** Recebe o seu prompt de sistema, uma instrução específica da intenção, os trechos do material recuperados pelo RAG e as últimas 8 mensagens da conversa (memória).
4. **Guardião.** Recebe a pergunta, o mesmo material e o rascunho da resposta, e responde `OK` ou `REVISAR: <motivo>`. No caso de `REVISAR`, o grafo volta ao mesmo agente com o motivo anexado ao prompt (no máximo 1 vez). Se ainda assim reprovar, a resposta é entregue com um aviso de possível imprecisão.
5. **Memória.** O `MemorySaver` do LangGraph guarda as mensagens por `thread_id` (uma por sessão). Assim, o Inquiridor consegue avaliar a resposta a um exercício que ele mesmo propôs no turno anterior.

## Prompts de sistema completos

Nos agentes especialistas, `{MATERIAL}` é substituído pelos trechos de `agente/conhecimento/state.md` recuperados pelo RAG, e ao final é anexada a instrução da intenção (lista mais abaixo).
"""


def main():
    partes = [CABECALHO]
    for nome, papel in [("Tutor do conceito", prompts.TUTOR), ("Exemplificador", prompts.EXEMPLIFICADOR),
                        ("Inquiridor (diagnóstico)", prompts.INQUIRIDOR)]:
        partes.append(f"### {nome}\n\n```text\n{prompts.montar_system(papel, '{MATERIAL}')}\n```\n")
    partes.append(f"### Roteador\n\n```text\n{prompts.ROTEADOR_SYSTEM}\n```\n")
    partes.append("### Guardião\n\nMensagem enviada ao Guardião: `PERGUNTA: ... MATERIAL: ... RESPOSTA: ...`\n\n"
                  f"```text\n{prompts.GUARDIAO_SYSTEM}\n```\n")
    partes.append("### Instruções por intenção (anexadas ao prompt do agente)\n\n| Intenção | Instrução |\n|---|---|\n"
                  + "\n".join(f"| `{k}` | {v} |" for k, v in prompts.INSTRUCAO_POR_INTENCAO.items()) + "\n")
    partes.append(f"### Respostas fixas (sem LLM)\n\n- Padrão inventado: \"{prompts.RECUSA_INVENTADO}\"\n"
                  f"- Fora de escopo: \"{prompts.RECUSA_FORA_ESCOPO}\"\n")
    saida = RAIZ / "docs" / "agentes.md"
    saida.write_text("\n".join(partes), encoding="utf-8")
    print(f"Salvo em {saida}")


if __name__ == "__main__":
    main()
