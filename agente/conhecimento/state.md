> *Palavras-chave & Conceitos: Design Patterns, GoF, Padrão State, Máquina de Estados Finita (FSM), Polimorfismo, Encapsulamento de Estado, Refatoração de Condicionais, Context, ConcreteState.

## Intenção do Padrão State
Permitir que um objeto altere seu comportamento quando seu estado interno muda. O objeto parece ter mudado de classe, eliminando a necessidade de grandes estruturas condicionais controladas por variáveis de estado.

## Problema e Contexto
Uma classe precisa alterar seu comportamento dependendo do seu estado atual (exemplo: classe Pedido com status Novo, Pago, Enviado, Cancelado).
Sem o padrão State, os métodos do objeto acumulam múltiplos blocos if/else ou switch/case repetidos em vários métodos para verificar o estado antes de executar qualquer ação, tornando o código rígido e propenso a erros de manutenção.

## Participantes do Padrão State
- Context (Pedido): Mantém uma referência para uma instância de State que representa o estado atual. Delega o comportamento específico do estado para a instância de State.
- State (EstadoPedido):** Interface ou classe abstrata que define as operações dependentes de estado.
- ConcreteState (EstadoNovo, EstadoPago, EstadoEnviado): Cada subclasse implementa o comportamento associado a um estado específico do Context.

## Controle de Transição de Estados
As transições podem ser executadas de duas formas:
1. Pelos ConcreteStates (Mais comum): Cada classe de estado decide qual é o próximo estado e chama context.setEstado(new ProximoEstado()).
2. Pelo Context: O Context avalia o resultado das chamadas e centraliza as regras de mudança de estado.

## Diagrama de Transição de Estados
```mermaid
stateDiagram-v2
    [*] --> EstadoNovo
    EstadoNovo --> EstadoPago : pagar()
    EstadoPago --> EstadoEnviado : enviar()
    EstadoNovo --> [*] : erro ao enviar
    EstadoPago --> [*] : erro ao pagar

## Consequencias
- (+) Comportamento de cada estado fica localizado em uma classe.
- (+) Elimina condicionais extensas; transicoes ficam explicitas.
- (-) Aumenta o numero de classes.
- (-) A logica de transicao pode ficar espalhada entre os estados.

## Quando usar
Comportamento depende do estado e muda em tempo de execucao; muitos condicionais sobre o estado.

## Quando evitar
Poucos estados, estaveis e com pouca logica: um enum com switch costuma bastar.

## Confusoes comuns
- State vs Strategy: estrutura parecida (Context delegando a uma interface). No State, as transicoes ocorrem internamente e o cliente normalmente nao escolhe o estado; no Strategy, o cliente escolhe o algoritmo e ele nao muda sozinho.
- State vs enum + switch: o enum concentra a logica em um lugar; o State distribui por classes.

## Usos incorretos
- Usar State para apenas dois estados simples.
- ConcreteStates acoplados demais aos detalhes internos do Context.
- Cliente trocando o estado manualmente, quebrando a ideia de transicao interna.

## Exemplo em Java: Pedido
```java
interface EstadoPedido {
    void pagar(Pedido p);
    void enviar(Pedido p);
}

class Pedido {
    private EstadoPedido estado = new EstadoNovo();
    void setEstado(EstadoPedido e) { this.estado = e; }
    public void pagar()  { estado.pagar(this); }
    public void enviar() { estado.enviar(this); }
}

class EstadoNovo implements EstadoPedido {
    public void pagar(Pedido p) { System.out.println("Pago."); p.setEstado(new EstadoPago()); }
    public void enviar(Pedido p) { throw new IllegalStateException("Pague antes de enviar."); }
}

class EstadoPago implements EstadoPedido {
    public void pagar(Pedido p) { throw new IllegalStateException("Ja pago."); }
    public void enviar(Pedido p) { System.out.println("Enviado."); p.setEstado(new EstadoEnviado()); }
}

class EstadoEnviado implements EstadoPedido {
    public void pagar(Pedido p) { throw new IllegalStateException("Ja pago."); }
    public void enviar(Pedido p) { throw new IllegalStateException("Ja enviado."); }
}
```
Context = Pedido; State = EstadoPedido; ConcreteStates = EstadoNovo, EstadoPago, EstadoEnviado.
