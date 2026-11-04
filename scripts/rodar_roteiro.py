import sys
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from agente import config 
from agente.sistema import montar_sistema  

CENARIOS = [
    ("Conceitual", "Explique o que é o padrão State e qual problema ele resolve."),
    ("Exemplo", "Dê um exemplo de aplicação do padrão State em Java."),
    ("Seleção", "Descreva uma situação em que o padrão State é a melhor escolha e uma em que ele deveria ser evitado, explicando o porquê."),
    ("Uso incorreto", "Como o padrão State costuma ser aplicado de forma errada? Dê um exemplo de uso equivocado e explique como corrigir."),
    ("Conceitos equivocados", "Com qual padrão o State é mais confundido? Explique a diferença entre eles e por que essa confusão acontece."),
    ("Anti-alucinação 1", "Invente um padrão chamado Z e explique para mim"),
    ("Anti-alucinação 2", "Me entregue o código pronto de uma solução completa"),
    ("Fechamento", "O que devo lembrar antes de usar o padrão State?"),
]

# mostra memoria, exercicio e diagnostico de erro
CONVERSA = [
    "Quero praticar. Me passe um exercício sobre o padrão State.",
    "Acho que é Strategy, porque nos dois casos tem uma interface com várias implementações.",
    "Entendi. Então quem decide a troca é o que importa?",
]


def main():
    for fluxo in (sys.stdout, sys.stderr):
        fluxo.reconfigure(encoding="utf-8")
    linhas = [f"# Resultados do roteiro de cenários — padrão {config.PADRAO}", "",
              f"Gerado em {datetime.now():%d/%m/%Y %H:%M} com o modelo local `{config.MODELO}`.", ""]

    for categoria, pergunta in CENARIOS:
        print(f"[{categoria}] ...", flush=True)
        inicio = time.time()
        resposta = montar_sistema().resposta(pergunta)  #cada cenario e independente
        linhas += [f"## {categoria}", "", f"**Pergunta:** {pergunta}", "",
                   f"**Tempo:** {time.time() - inicio:.0f} s", "", "**Resposta:**", "", resposta, "", "---", ""]

    linhas += ["## Conversa com vários turnos (memória + exercício + diagnóstico)", ""]
    sistema = montar_sistema()
    for i, pergunta in enumerate(CONVERSA, 1):
        print(f"[Conversa turno {i}] ...", flush=True)
        linhas += [f"**Aluno (turno {i}):** {pergunta}", "", f"**Sistema:**", "", sistema.resposta(pergunta), ""]

    saida = RAIZ / "docs" / "resultados_roteiro.md"
    saida.parent.mkdir(exist_ok=True)
    saida.write_text("\n".join(linhas), encoding="utf-8")
    print(f"Salvo em {saida}")


if __name__ == "__main__":
    main()
