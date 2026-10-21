
## Intencao
Permitir que um objeto altere seu comportamento quando seu estado interno muda. O objeto parece ter mudado de classe.

## Problema
Uma classe com varios if/switch sobre um atributo de estado, repetidos em muitos metodos (ex.: Pedido com status Novo, Pago, Enviado).

## Participantes
- Context: mantem referencia ao estado atual e delega o comportamento a ele (ex.: Pedido).
- State: interface com as operacoes dependentes de estado (ex.: EstadoPedido).
- ConcreteState: implementa o comportamento de um estado (ex.: EstadoNovo, EstadoPago, EstadoEnviado).

## Transicoes
Podem ser feitas pelo Context ou pelos proprios ConcreteStates. No exemplo abaixo, os ConcreteStates trocam o estado do Context.

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
