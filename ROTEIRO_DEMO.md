# Roteiro de demonstração ao vivo — 8 minutos

**Objetivo didático:** mostrar que o LLM não recebe "lembranças mágicas"; quem escolhe as informações, as guarda e as recupera é a aplicação Python.

## 1. Mostrar os módulos (1 min)

Mostre os quatro cartões do lado esquerdo:
- **Trabalho:** informação provisória para a tarefa atual; RAM.
- **Semântica:** fatos e preferências; SQLite.
- **Episódica:** eventos com contexto temporal; SQLite.
- **Procedural:** sequência de passos; SQLite.

Clique em **Carregar cenário de exemplo** e destaque as cores dos registros à direita. Com **Sem memória** ativo, as memórias aparecem como **DESLIGADA**, ou seja, guardadas mas inacessíveis ao agente.

## 2. Sem memória (1 min)

Deixe o modo **Sem memória** e pergunte:

> Qual linguagem de programação eu prefiro?

Mostre a telemetria: **zero recuperadas, zero criadas**. O agente ainda pode usar a conversa atual, mas não tem acesso à base.

## 3. Só memória semântica (1 min)

Ative **Semântica** e repita a pergunta. O app cria uma sessão nova automaticamente para não reaproveitar respostas anteriores. Agora o módulo semântico recupera a preferência relacionada a Python.

## 4. Memória procedural (1 min)

Ative **Procedural** e pergunte:

> Como devo apresentar um projeto?

Aponte o registro com os passos “primeiro explique o objetivo; depois execute a demonstração; por fim compare”.

## 5. Memória de trabalho versus persistente (1 min)

Ative **Todas** e clique novamente em **Carregar cenário de exemplo** (a troca de modo inicia uma nova sessão). Localize o cartão de trabalho com o objetivo desta sessão. Clique em **Nova sessão**: ele desaparece. Os fatos, eventos e procedimentos do SQLite continuam visíveis. Explique a diferença entre RAM e armazenamento persistente.

## 6. Teste lado a lado (2 min)

Recarregue o cenário (se necessário), ative **Todas** ou mantenha os tipos persistentes ativos e, na seção **Mesma pergunta. Duas IAs.**, envie:

> Qual linguagem de programação eu prefiro?

A comparação gera duas respostas com a **mesma pergunta e sem histórico**: uma sem contexto externo e outra com registros recuperados. Nenhuma memória é adicionada neste modo.

## 7. Encerramento (1 min)

Explique que armazenar não basta: um bom sistema precisa escolher o que é relevante e evitar memórias incorretas, desatualizadas ou sensíveis.

> “O desafio não é lembrar de tudo. É lembrar do que importa.”

### Ensaio e contingência

Para ensaiar sem riscos, use **Simulação didática (offline)**: respostas geradas por regras explícitas, sem LLM. Para apresentação com IA real, mude para **Ollama (modelo real)**, selecione o modelo instalado e teste o tempo de resposta antes do evento. A busca semântica é opcional e exige um modelo de embeddings separado.

### Extensão opcional — Arena de modelos

Compare dois modelos reais com a mesma pergunta e os mesmos módulos. Mostre as respostas e a telemetria de geração, sem declarar o modelo mais rápido como o melhor.
