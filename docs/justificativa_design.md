# Justificativa das decisões de design
## 1. Divisão de papéis

Seguimos a divisão sugerida no Anexo A (ensinar, exemplificar, exercitar/diagnosticar e garantir confiabilidade) e acrescentamos um **Roteador**. Ficaram cinco agentes:

- **Roteador.** Um único agente "faz-tudo" recebe um prompt enorme e, com um modelo local de 7B, tende a misturar os papéis: entrega código quando deveria perguntar e explica quando deveria exercitar. Separar a classificação da intenção (uma tarefa curta, de uma palavra) da geração da resposta deixa cada prompt pequeno e focado. Isso é coesão aplicada a agentes.
- **Tutor do conceito.** Concentra o conteúdo declarativo: intenção, problema, participantes, consequências, quando usar e evitar, comparação com o Strategy e fechamento.
- **Exemplificador.** Separado do Tutor porque mostrar código exige outra disciplina: usar só os exemplos validados do material, sem inventar classes, e explicar o papel de cada participante no código. Os usos incorretos também ficam com ele, porque precisam de código "errado" e "corrigido" lado a lado.
- **Inquiridor.** Tem uma regra pedagógica oposta à dos outros: **não** dar a resposta. Colocar essa regra no mesmo prompt de quem explica geraria conflito. O Inquiridor também recebe os pedidos de "código pronto", porque recusar e guiar em passos é justamente o comportamento socrático dele.
- **Guardião.** Revisor independente. O modelo que gera a resposta raramente detecta o próprio erro na mesma chamada. Uma segunda chamada, com outro papel e só o material como referência, funciona como uma revisão por pares.

A coordenação usa um grafo explícito (LangGraph) em vez de agentes conversando livremente. O fluxo fica previsível e testável, e o número de chamadas ao modelo, que é lento na máquina local, fica limitado: no máximo 5 por pergunta (roteador + agente + guardião + uma revisão).

## 2. Estratégia pedagógica

- **Ensino em camadas** (Tutor): primeiro o problema concreto (o Pedido cheio de if/else), depois a ideia central e só então os participantes e as consequências. Quem começa pelo diagrama UML não entende por que o padrão existe.
- **Um exemplo condutor**: o Pedido aparece no problema, na solução, nos usos incorretos e nos exercícios. O aluno reconhece o mesmo cenário e pode se concentrar no padrão.
- **Prática socrática** (Inquiridor): os exercícios vão do reconhecimento (identificar participantes) à aplicação (adicionar um estado) e à discriminação (State ou Strategy?). Ao avaliar, o Inquiridor nomeia o conceito equivocado e dá uma pista progressiva, sem entregar a solução.
- **Diagnóstico de conceitos equivocados**: o material traz, para cada exercício, a resposta esperada e os erros comuns. Isso dá ao Inquiridor um critério objetivo de correção, em vez de depender do "julgamento" do modelo.
- **Fechamento**: a intenção `fechamento` consolida o que foi estudado com o checklist do material, papel que o Anexo A atribui ao Guardião.
- **Toda resposta termina com uma pergunta**, para manter o aluno ativo no diálogo.

## 3. Uso da memória

- O `MemorySaver` do LangGraph guarda as mensagens da conversa por `thread_id`. Cada execução do `Sistema` gera um id próprio, então cada sessão tem a sua memória.
- Os agentes recebem as **últimas 8 mensagens** (4 turnos). Esse limite mantém o prompt dentro da janela de contexto (8192 tokens, configurada explicitamente porque o padrão do Ollama é menor e cortaria o material em silêncio) e evita que o modelo local fique lento.
- A memória é o que permite o ciclo exercício → tentativa → diagnóstico: quando o aluno responde, o Roteador vê no histórico que houve um exercício e classifica como `avaliacao`. O RAG também usa a mensagem anterior (o enunciado do exercício) para buscar a resposta esperada e os erros comuns.
- A memória também guarda a intenção do turno anterior. Depois que o Inquiridor propõe um exercício, a próxima mensagem do aluno é tratada como tentativa e vai para avaliação. Enquanto durar a prática, nenhum agente pode entregar código longo, para que o aluno não receba a solução por outro caminho.
- Os rascunhos e os pareceres do Guardião **não** entram na memória, só a resposta final. Assim o histórico não fica poluído com versões descartadas.

## 4. Regras anti-alucinação: implementação

O sistema tem cinco camadas (as duas primeiras são determinísticas, ou seja, não dependem do modelo obedecer), da mais rígida para a mais flexível:

1. **Regras determinísticas, sem LLM** (`grafo.py`): expressões regulares detectam pedidos de invenção ("invente um padrão"), nomes ligados à palavra "padrão" que não estão no catálogo GoF ("padrão chamado Z", "padrão Zeta") e pedidos de código pronto. Para padrões inventados, a recusa é um texto fixo e o modelo nem é chamado. Isso é deliberado: um modelo de 7B, quando recebe "explique o padrão Zeta", costuma inventar uma explicação plausível.
2. **Limite de código por agente, aplicado pelo Guardião sem LLM** (`config.LIMITE_LINHAS_CODIGO`): o Inquiridor pode usar no máximo 5 linhas por bloco e o Tutor, 20. Se a resposta passa do limite, o Guardião pede revisão sem chamar o modelo. Se o limite estourar de novo, os blocos longos são trocados por um aviso convidando o aluno a tentar sozinho. Criamos essa regra porque, nos testes, o modelo de 7B **ignorava** a instrução "não escreva código" do prompt e entregava a solução pronta. Pelo mesmo motivo, o Guardião também detecta sem LLM respostas que mudam de idioma (o Qwen às vezes troca para chinês).
3. **Material como única fonte de fatos** (RAG): o arquivo `state.md` foi escrito e revisado pela dupla com base no livro GoF. Os trechos relevantes são recuperados (FAISS com embeddings locais) e injetados no prompt com a instrução de usar *somente* esse material e dizer "não sei com segurança" quando faltar informação. O índice guarda um hash do material e é recriado quando o material muda, então nunca se responde com uma versão antiga.
4. **Regras no prompt de cada agente**: a seção "REGRAS ANTI-ALUCINAÇÃO" do Anexo B, além de restrições de escopo (o Exemplificador não cria exemplos fora do material).
5. **Guardião**: confere cada resposta contra o mesmo material e pede revisão quando há fato ausente ou errado, confusão State/Strategy, entrega de solução pronta ou explicação de padrão inexistente. Se a revisão também falha, a resposta sai com um aviso explícito, em vez de passar como confiável.

## 5. Como as regras foram testadas

- **Testes automatizados** (`tests/test_basico.py`, 18 testes) com um LLM falso, sem depender do Ollama: recusa de padrão inventado sem chamar o modelo, roteamento do pedido de código pronto, recusa fora de escopo, roteamento para cada agente, revisão pelo Guardião (uma vez, depois com aviso), memória entre turnos, limite de código (revisão e remoção) e tratamento de erros (entrada vazia, modelo fora do ar, saída vazia, rótulo inesperado do roteador).
- **Roteiro de cenários** (`scripts/rodar_roteiro.py`): executa as 7 categorias do enunciado e uma conversa de vários turnos com o modelo real, e salva as respostas em `docs/resultados_roteiro.md` para análise da dupla.

## 6. Decisões técnicas

- **LangGraph em vez de CrewAI**: o fluxo é um grafo explícito com arestas condicionais (roteamento e laço de revisão), fácil de testar com um LLM falso.
- **qwen2.5:7b**: o modelo sugerido para 16 GB de RAM, com bom português. Temperatura 0,2 para respostas mais estáveis e limite de 700 tokens por resposta.
- **Tratamento de erros**: entrada vazia, falha ou timeout do Ollama e saída vazia ou inesperada viram mensagens amigáveis. A falha do Guardião não derruba o sistema (a resposta é aprovada), e a falha do Roteador cai no Tutor.
