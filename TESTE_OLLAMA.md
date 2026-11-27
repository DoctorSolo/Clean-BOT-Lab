# Clean BOT Lab — teste real no CachyOS

## Preparação

Você já tem Ollama instalado. Confira `ollama list` e, se necessário, inicie o serviço conforme sua instalação (`systemctl status ollama`, caso use systemd). Se não estiver em execução, inicie `ollama serve` ou o serviço configurado na máquina, não os dois ao mesmo tempo.

Execute `bash iniciar-linux.sh`. O navegador abre em http://127.0.0.1:8765. O status deve indicar Ollama conectado e a quantidade de modelos. Nenhuma chamada do modo simulado será usada quando o motor estiver em Ollama.

## Roteiro de validação gráfica

| Teste | Procedimento | Resultado esperado |
|---|---|---|
| Conexão | Atualizar modelos | Os nomes disponíveis aparecem no seletor e na arena. |
| Identidade | Selecionar modelo; enviar “Quem é você?” | Resposta gerada pelo modelo com o prompt Clean BOT. |
| Sem memória | Escolher Sem memória, nova sessão; perguntar “Qual linguagem de programação eu prefiro?” | Zero memórias recuperadas; não deveria inventar preferência. |
| Semântica | Escolher Semântica; carregar cenário; repetir a pergunta | Telemetria mostra o registro Python; resposta deveria usar esse fato. |
| Episódica | Escolher Episódica; perguntar “Que palestra eu preparei em novembro de 2026?” | Registro do cenário recuperado. |
| Procedural | Escolher Procedural; perguntar “Como devo apresentar um projeto?” | Passos do cenário recuperados. |
| Trabalho | Escolher Trabalho; carregar cenário; perguntar “Qual é o objetivo desta sessão?”; iniciar nova sessão | Registro temporário recuperado primeiro; depois desaparece. |
| Escrita automática | Escolher Semântica e ativar extração; dizer “Eu prefiro a linguagem Rust.” | O modelo deve extrair e salvar a preferência se seguir o formato JSON. Confira o painel; modelos podem falhar. |
| Arena | Selecionar 2 modelos de chat e repetir uma pergunta | Duas respostas, latências, métricas quando fornecidas; nenhum novo registro. |
| Campo manual | Digitar o nome exato de outro modelo de chat | O campo manual tem prioridade sobre o seletor. |

A qualidade de resposta e extração depende do modelo. Verifique especialmente se ele respeita a memória fornecida e evita inventar dados quando ela está desligada. Se usar dados fictícios, deixe claro ao público que se trata de um cenário didático.

## Dicas de avaliação

- Comece com dois modelos pequenos que já estejam instalados. Não selecione modelos exclusivos de embeddings na arena.
- Desative extração automática para testar apenas respostas; isso evita uma segunda chamada ao LLM.
- Compare os modelos com a mesma memória e pergunta. Use uma sessão nova no chat ao trocar de modelo.
- Faça mais de uma rodada; a primeira chamada pode incluir tempo de carregamento. Latência e tokens/s não medem sozinhos a qualidade.
- Para testar embeddings, use um modelo de embeddings instalado separadamente. Se o modelo estiver indisponível, a aplicação usa busca textual e mostra um aviso.
- Se o Ollama falhar, o app mostra o erro; não troca silenciosamente para simulação.

## Limites da validação

O pacote foi testado com pytest e respostas HTTP controladas. O ambiente de desenvolvimento não tem acesso ao seu Ollama, GPU ou modelos locais. Execute os testes acima para validar a inferência real na sua máquina.
