# Clean BOT Lab — laboratório visual de memórias modulares

Aplicação gráfica local para demonstrar a diferença entre uma IA **sem memória externa** e um chatbot/miniagente que **recupera e registra memórias**. Desenvolvida em **Python + FastAPI + SQLite**, com integração ao **Ollama** (motor padrão), sem Node.js, npm ou serviços em nuvem.

## O que é possível fazer?

- Escolher **sem memória, trabalho, semântica, episódica, procedural, todas** ou combinar os quatro módulos livremente.
- Conversar no chat e ver **quais registros foram recuperados** e **quais novos registros foram criados**.
- Ver, filtrar, criar, editar e excluir registros na interface.
- Demonstrar a diferença entre memória **temporária** (RAM) e **persistente** (SQLite), incluindo reiniciar uma sessão.
- Comparar **a mesma pergunta com e sem memória lado a lado**, sem histórico e sem escrever registros.
- Rodar no **modo Ollama** (padrão), com seleção automática ou manual dos modelos locais; modo simulação como contingência.
- Comparar de **2 a 4 modelos reais** na Arena de modelos, com o mesmo contexto, latência e tokens/s.
- Usar busca por **palavras-chave** ou, opcionalmente, **embeddings** via Ollama.

> Importante: o modo **Simulação didática** é baseado em regras simples; não é uma IA real. O modo **Ollama** faz chamadas reais ao modelo escolhido. A classificação automática pelo LLM pode cometer erros. A busca por palavras-chave é um protótipo educacional, não um mecanismo de recuperação completo.

## Executar (Linux — KDE, Ubuntu, Arch etc.)

Requisitos: **Python 3.10+** e acesso à internet **somente na primeira instalação** das dependências. Descompacte o projeto.

1. Clique em `iniciar-linux.sh` e escolha **Executar** (se o gerenciador de arquivos oferecer essa opção).
2. Se o Linux não permitir iniciar pelo gerenciador de arquivos, execute uma vez: `bash iniciar-linux.sh`.
3. Aguarde a janela do navegador abrir em **http://127.0.0.1:8765**. Você usa o laboratório **inteiramente pelo navegador**.

O launcher cria um ambiente virtual, instala as dependências e inicia o servidor. Para encerrar, feche o processo da janela que iniciou o aplicativo (Ctrl+C no terminal, se tiver sido iniciado pelo terminal). Em execuções seguintes, as dependências já estarão instaladas.

No **Windows**, execute `iniciar-windows.bat`. No **macOS**, execute `iniciar-macos.command`.

### Execução manual (opcional)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.launch
```

## Ollama local — motor padrão

O modo simulação funciona **sem Ollama**. Para testar um modelo real:

1. Instale Ollama: https://ollama.com/download
2. Inicie o serviço local do Ollama (em Linux, `ollama serve` se necessário).
3. Se já tem modelos instalados, não precisa baixar outros. Use `ollama list` para conferir os nomes e verifique a RAM/VRAM disponível.
4. Abra o Clean BOT Lab. **Ollama (modelo real)** já está selecionado. Escolha um modelo detectado automaticamente em `/api/tags` ou digite o nome exato no campo manual (que tem prioridade). Use “Atualizar modelos” se necessário.
5. (Opcional) Para embeddings, instale `ollama pull embeddinggemma`, mantenha esse nome no campo de embeddings e ative a caixa **Busca por significado**.

Referência das APIs usadas:
- Chat (`POST /api/chat`): https://docs.ollama.com/api/chat
- Embeddings (`POST /api/embed`): https://docs.ollama.com/api/embed

### Arena de modelos (comparação real)

1. Selecione os módulos desejados no painel de controle. Para um teste neutro, desative todos.
2. Abra **Arena de modelos** e marque de 2 a 4 modelos detectados ou digite os nomes manualmente, separados por vírgulas.
3. Envie a mesma pergunta. A aplicação recupera as memórias uma única vez, monta o mesmo prompt e envia para cada modelo, sequencialmente, sem histórico e sem criar registros de memória. O cache de embeddings pode ser atualizado.
4. Compare respostas, latência total, tokens gerados, velocidade de geração (tokens/s quando informada pelo Ollama) e tempo de carregamento. A ordem e o estado do cache podem alterar as latências; repita os testes com ordens diferentes (ou reinicie os modelos) para comparar desempenho. Não há ranking automático de qualidade.

Modelos exclusivamente de embeddings não respondem a chat. A arena informa falhas individuais sem descartar as demais respostas. A seleção de outro modelo no chat mantém a conversa atual; use **Nova sessão** se quiser uma avaliação independente.

**Validação:** testes automatizados do contrato HTTP executados com respostas controladas, não com inferência de um LLM real. Faça um teste local com seus modelos antes da palestra. O arquivo `TESTE_OLLAMA.md` contém o roteiro.

### Para apresentar em 1 hora

**Roteiro de 6 minutos de demonstração:**

1. Clique em **Carregar cenário de exemplo**. Mostre as quatro categorias à direita.
2. Com **Sem memória**, pergunte *“Qual linguagem de programação eu prefiro?”*. Observe no rastreamento que nenhuma memória foi recuperada.
3. Ative **Semântica**; o chat inicia nova sessão por justiça experimental. Pergunte a mesma coisa e observe a recuperação do registro de Python.
4. Ative **Procedural** e pergunte *“Como devo apresentar um projeto?”*. Mostre o procedimento encontrado.
5. Use **Nova sessão**: a memória de trabalho some, mas semântica, episódica e procedural continuam em SQLite.
6. Vá para **Mesma pergunta. Duas IAs.** e compare as respostas sem histórico.

**Dica:** prepare o ambiente antes da palestra e tenha o **modo simulação** como backup se o modelo local não responder a tempo.

## Como os módulos funcionam (de verdade)

| Módulo | Onde vive | Como é usado |
|---|---|---|
| **Trabalho** | Dicionário Python em memória, por sessão | Notas e objetivos temporários; apagados ao criar outra sessão ou reiniciar o servidor |
| **Semântica** | SQLite | Fatos e preferências guardados entre sessões |
| **Episódica** | SQLite | Eventos ou experiências datadas conforme o registro |
| **Procedural** | SQLite | Instruções e passos para realizar tarefas |
| **Nenhum** | Sem acesso ao repositório de memórias | Histórico da conversa atual ainda é usado; nenhum registro é lido ou escrito |

A seleção de módulos controla **a busca e a escrita automática**. Memórias persistentes de módulos desligados continuam no painel, mas **não são usadas pelo agente**. Ao trocar o modo, começa uma sessão nova e o histórico anterior deixa de ser enviado ao modelo, para evitar contaminação do experimento.

**Fluxo real:** `Mensagem → Retriever → Contexto → LLM / simulação → Writer → Storage`. Escrita automática via Ollama usa saída JSON do modelo; na simulação são apenas regras simples de exemplo. A busca por palavras-chave usa palavras normalizadas. Embeddings só são usados se a opção for habilitada e o modelo correspondente estiver disponível no Ollama. Se falharem, a busca volta para palavras-chave e exibe um aviso.

## Estrutura

```text
app/
  main.py             # API, controle de sessões, endpoint de comparação
  memory.py           # Retriever, Writer, pontuação e prompts
  storage.py          # SQLite e memória de trabalho em RAM
  ollama_client.py    # HTTP local Ollama chat/embeddings
  launch.py           # Inicia servidor e abre navegador
  static/
    index.html        # Interface
    styles.css        # Visual responsivo
    app.js            # Interações e visualização
requirements.txt
iniciar-linux.sh
iniciar-windows.bat
iniciar-macos.command
tests/
```

## Limites e privacidade

- Executa apenas em **127.0.0.1**, porta 8765; os dados ficam no computador, em `data/memories.sqlite3`. Não é preciso login no modo local. Não compartilhe o servidor publicamente.
- A memória persistente é **global para este laboratório local**, não multiusuário. Não insira dados confidenciais de pessoas reais na demonstração.
- A extração automática pode salvar algo desnecessário ou incorreto. É possível revisar, editar e excluir registros no painel.
- O pipeline é um **protótipo didático**, não um agente autônomo com chamadas de ferramentas. Mostra o componente de memória de um agente e a influência desse componente nas respostas do chatbot.
- O teste de comparação limita-se a comparar os contextos; a saída de um LLM real pode variar entre chamadas mesmo com os mesmos dados.
- Dependendo do modelo, a execução do Ollama e a geração de embeddings podem consumir bastante tempo ou memória da máquina.

## Testes

Com dependências instaladas e `pytest` disponível: `python -m pytest -q`.

Projeto educacional criado para uma palestra de 60 minutos.

### Atalho no KDE Plasma (opcional)

Depois que o projeto já estiver iniciando corretamente, execute **uma única vez** `bash criar-atalho-kde.sh`. Isso cria a entrada **Clean BOT Lab** no menu de aplicativos do KDE. A partir daí, você pode abrir o projeto pelo menu, sem usar um terminal. Se mover a pasta do projeto, execute novamente o criador de atalhos.
