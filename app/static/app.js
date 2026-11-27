"use strict";
const $ = (id) => document.getElementById(id);
const KINDS = ["working", "semantic", "episodic", "procedural"];
const LABELS = {working:"Trabalho", semantic:"Semântica", episodic:"Episódica", procedural:"Procedural"};
const SYMBOLS = {working:"◷", semantic:"◇", episodic:"▤", procedural:"⌘"};
const PRESETS = {none:[], working:["working"], semantic:["semantic"], episodic:["episodic"], procedural:["procedural"], all:[...KINDS]};
const state = {sessionId:newSessionId(), active:[], preset:"none", provider:"ollama", model:"", memoryFilter:"all", memories:[], lastTrace:null, busy:false, ollamaConnected:false, models:[]};
let toastTimeout = null;
function newSessionId(){return "lab_" + (typeof crypto!=="undefined" && crypto.randomUUID ? crypto.randomUUID().replace(/-/g,"") : Math.random().toString(36).slice(2)+Date.now().toString(36));}
function setText(id, value){$(id).textContent = value;}
function node(tag, cls, text){const el=document.createElement(tag); if(cls) el.className=cls; if(text!==undefined) el.textContent=text; return el;}
function toast(msg, error=false){const el=$("toast");el.textContent=msg;el.classList.toggle("error",error);el.classList.add("visible");if(toastTimeout)clearTimeout(toastTimeout);toastTimeout=setTimeout(()=>el.classList.remove("visible"),3400);}
async function api(path, opts={}){
  const response=await fetch(path,{headers:{"Content-Type":"application/json"},...opts});
  if(!response.ok){let error={};try{error=await response.json()}catch{};let detail=error.detail||`Erro HTTP ${response.status}`;if(Array.isArray(detail))detail=detail.map(x=>x.msg).join("; ");throw Error(detail);}
  return response.json();
}
async function refreshStatus(){
  try{
    const data=await api("/api/status");state.ollamaConnected=data.connected;state.models=data.models||[];
    $("live-dot").classList.toggle("connected",data.connected);
    setText("connection-label",data.connected?`Ollama conectado · ${state.models.length} modelo(s)`:"Ollama desconectado · offline disponível");
    const select=$("model"), existing=state.model || select.value;
    select.replaceChildren();
    if(!state.models.length){select.append(node("option",null,"Nenhum modelo encontrado"));select.options[0].value="";state.model="";}
    else{state.models.forEach(m=>{const opt=node("option",null,m);opt.value=m;select.append(opt);});
      state.model=state.models.includes(existing)?existing:state.models[0];select.value=state.model;}
    renderArenaModels();
    renderControls();
    if(state.provider==="ollama" && (!data.connected || !state.models.length)){
      $("provider-explain").textContent = "Ollama não está pronto ou não tem modelos disponíveis. Verifique o serviço local; o campo manual continua disponível.";
    }
  }catch(err){setText("connection-label","Status indisponível");}
}
async function refreshMemories(){
  try{const data=await api(`/api/memories?session_id=${encodeURIComponent(state.sessionId)}`);state.memories=data.memories;renderMemories();}
  catch(err){toast("Não foi possível ler as memórias: "+err.message,true);}
}
function currentPreset(types){for(const [key,list] of Object.entries(PRESETS))if(list.length===types.length && list.every(t=>types.includes(t)))return key;return "custom";}
function renderControls(){
  document.querySelectorAll(".preset").forEach(b=>b.classList.toggle("active",b.dataset.preset===state.preset));
  document.querySelectorAll(".module .switch-input").forEach(c=>c.checked=state.active.includes(c.dataset.kind));
  setText("current-mode",!state.active.length?"Sem memória conectada":state.active.length===4?"Todos os módulos ativos":state.active.map(k=>LABELS[k]).join(" + "));
  setText("current-provider",state.provider==="simulation"?"Simulação didática":`Ollama · ${chosenModel() || "selecione um modelo"}`);
  setText("arena-context",`Contexto compartilhado: ${state.active.length?state.active.map(k=>LABELS[k]).join(" + "):"sem memória modular"}`);
  setText("flow-desc",!state.active.length?"Memória desconectada: apenas histórico do chat desta sessão.":`${state.active.length} módulo(s) ativo(s) · recuperação + escrita seletiva.`);
  const isOllama=state.provider==="ollama";
  document.querySelectorAll(".ollama-only").forEach(el=>el.classList.toggle("hidden",!isOllama));
  $("provider").value=state.provider;
  if(!isOllama)$("provider-explain").textContent="A simulação usa regras explícitas: não gera respostas com IA. Ideal para ensaiar sem depender do Ollama.";
  else if(state.ollamaConnected)$("provider-explain").textContent="Respostas e extração automática pelo modelo local. Instale um modelo de embeddings separadamente se habilitar a busca vetorial.";
  renderMemories();
}
async function changeMode(types){
  if(state.busy)return;
  const normalized=KINDS.filter(k=>types.includes(k));
  if(JSON.stringify(normalized)===JSON.stringify(state.active))return;
  const old=state.sessionId;state.active=normalized;state.preset=currentPreset(normalized);
  state.sessionId=newSessionId();clearChat();renderControls();
  try{await api("/api/session/reset",{method:"POST",body:JSON.stringify({session_id:old})});}catch{}
  await refreshMemories();
  toast(`Modo: ${state.preset==="none"?"Sem memória":state.preset==="custom"?"Personalizado":state.active.map(k=>LABELS[k]).join(" + ")}. Nova sessão iniciada.`);
}
function clearChat(){const area=$("chat-messages");area.replaceChildren();const placeholder=node("div","empty-chat");placeholder.id="empty-chat";placeholder.innerHTML='<div class="empty-icon"><img src="/assets/clean-bot.jpg" alt=""/></div><h3>Clean BOT na escuta!</h3><p>Faça uma pergunta ao agente ou carregue um cenário para explorar as memórias.</p><div class="suggestion-list"><button class="suggestion" data-question="Qual linguagem de programação eu prefiro?">Qual linguagem eu prefiro? <span>↗</span></button><button class="suggestion" data-question="Como devo demonstrar o projeto na palestra?">Como devo demonstrar o projeto? <span>↗</span></button></div>';area.append(placeholder);setText("trace-time","Aguardando interação");$("trace-details").replaceChildren(node("div","trace-empty","As memórias recuperadas e armazenadas aparecerão aqui."));$("trace-steps").querySelectorAll(".trace-step").forEach(x=>x.classList.remove("active","dim"));}
function renderMemories(){
  const all=state.memories;
  setText("stat-total",all.length);
  setText("stat-active",all.filter(m=>state.active.includes(m.type)).length);
  setText("stat-persistent",all.filter(m=>!m.temporary).length);
  document.querySelectorAll(".memory-bars .bar").forEach((b,i)=>{const count=all.filter(m=>m.type===KINDS[i]).length;b.style.flex=String(Math.max(1,count));b.title=`${LABELS[KINDS[i]]}: ${count}`;b.style.opacity=count?"1":".16";});
  const search=$("memory-search").value.toLocaleLowerCase("pt-BR");
  const filtered=all.filter(m=>(state.memoryFilter==="all"||state.memoryFilter===m.type)&&m.content.toLocaleLowerCase("pt-BR").includes(search));
  const wrap=$("memory-list");wrap.replaceChildren();
  if(!filtered.length){wrap.append(node("div","memories-empty",all.length?"Nenhuma memória corresponde ao filtro.":"Ainda não existem memórias. Carregue o cenário ou adicione uma manualmente."));return;}
  filtered.forEach(m=>{
    const item=node("article","memory-item"+(!state.active.includes(m.type)?" off":""));
    const top=node("div","memory-top");const type=node("span",`memory-type ${m.type}`);const dot=node("span","dot "+m.type+"-bg");type.append(dot,node("span",null,LABELS[m.type]));top.append(type,node("span","memory-state",state.active.includes(m.type)?"ACESSÍVEL":"DESLIGADA"));
    const desc=node("p",null,m.content);
    const foot=node("div","memory-actions");const source=node("small",null,`${m.temporary?"RAM · efêmera":"SQLite · persistente"} · ${m.source}`);
    const acts=node("div");const edit=node("button",null,"Editar");edit.type="button";edit.title="Editar conteúdo";edit.addEventListener("click",()=>editMemory(m));const del=node("button","delete","Excluir");del.type="button";del.addEventListener("click",()=>deleteMemory(m));acts.append(edit,del);foot.append(source,acts);
    item.append(top,desc,foot);wrap.append(item);
  });
}
function addMessage(role, text, meta){
  $("empty-chat")?.remove();const row=node("div",`message ${role}`);const avatar=node("div","message-avatar",role==="user"?"◉":"✦");if(role==="agent"){avatar.textContent="";const img=node("img");img.src="/assets/clean-bot.jpg";img.alt="Clean BOT";avatar.append(img);}const bubble=node("div","bubble");bubble.append(node("div","message-text",text));bubble.append(node("div","message-meta",meta||new Date().toLocaleTimeString("pt-BR",{hour:"2-digit",minute:"2-digit"})));row.append(avatar,bubble);$("chat-messages").append(row);$("chat-messages").scrollTop=$("chat-messages").scrollHeight;return row;
}
function showTyping(){const row=addMessage("agent","", "Processando...");const text=row.querySelector(".message-text");text.replaceChildren();const bubble=node("span","typing");for(let i=0;i<3;i++)bubble.append(node("i"));text.append(bubble);return row;}
function setBusy(b){state.busy=b;document.querySelectorAll(".preset, .switch-input, #provider, #model, #manual-model, #refresh-models, #reset-session, #send-button, #compare-button, #arena-button, #auto-capture, #use-embeddings, #embedding-model, #seed-demo, #wipe-demo, #open-memory-form, #memory-form button, .memory-actions button, #arena-models input, #arena-manual").forEach(el=>el.disabled=b);$("send-button").querySelector("span").textContent=b?"Em operação...":"Enviar";}
function chosenModel(){return $("manual-model").value.trim() || state.model;}
let arenaSelected=new Set();
function renderArenaModels(){
  const wrap=$("arena-models");wrap.replaceChildren();
  if(!state.models.length){wrap.append(node("p","muted-note","Nenhum modelo detectado. Use o campo manual abaixo."));return;}
  for(const model of state.models){const label=node("label","arena-chip");const input=node("input");input.type="checkbox";input.value=model;input.checked=arenaSelected.has(model);input.disabled=state.busy;input.addEventListener("change",()=>{if(input.checked)arenaSelected.add(model);else arenaSelected.delete(model);});label.append(input,node("span",null,model));wrap.append(label);}
}
async function arena(event){
  event.preventDefault();if(state.busy)return;
  const models=[...new Set([...state.models.filter(m=>arenaSelected.has(m)),...$("arena-manual").value.split(/[,\n]/).map(m=>m.trim()).filter(Boolean)])];
  const text=$("arena-question").value.trim();if(!text||models.length<2||models.length>4){toast("Escolha de 2 a 4 modelos distintos e digite uma pergunta.",true);return;}
  const payload={...chatPayload(text),provider:"ollama",models,auto_capture:false};
  setBusy(true);const wrap=$("arena-results");wrap.replaceChildren(node("div","comparison-placeholder",`Executando ${models.length} modelos reais, um por vez. Modelos grandes podem demorar.`));
  try{const data=await api("/api/compare-models",{method:"POST",body:JSON.stringify(payload)});wrap.replaceChildren();
    for(const r of data.results){const card=node("article","comparison-card arena-card");card.append(node("div","comparison-title",r.model),node("p",null,r.error||r.answer));const meta=node("div","arena-metrics");meta.append(node("span","tag",`${(r.elapsed_ms/1000).toFixed(2)} s`));if(r.tokens_per_second!=null)meta.append(node("span","tag good",`${r.tokens_per_second} tokens/s`));if(r.eval_count!=null)meta.append(node("span","tag",`${r.eval_count} tokens`));if(r.load_ms!=null)meta.append(node("span","tag",`Carga ${(r.load_ms/1000).toFixed(2)} s`));if(r.done_reason==="length")meta.append(node("span","tag","Limite de geração"));if(r.error)meta.append(node("span","tag","Falha"));card.append(meta);wrap.append(card);}
    wrap.append(node("div","comparison-context",`${data.retrieved.length} memória(s) compartilhada(s) · ${data.trace.retrieval} · Sem histórico · Sem novas memórias`));
    for(const m of data.retrieved)wrap.append(node("div","comparison-context",`${LABELS[m.type]}: ${m.content}`));
    for(const w of data.trace.warnings||[])wrap.append(node("div","comparison-context",`Aviso: ${w}`));
  }catch(err){wrap.replaceChildren(node("div","comparison-placeholder",err.message));toast(err.message,true);}finally{setBusy(false);}
}
function chatPayload(text){return {session_id:state.sessionId,text,enabled_types:state.active,provider:state.provider,model:chosenModel(),auto_capture:$("auto-capture").checked,use_embeddings:$("use-embeddings").checked,embedding_model:$("embedding-model").value.trim()||"embeddinggemma"};}
async function sendMessage(text){
  if(state.busy||!text.trim())return;
  if(state.provider==="ollama"&&!chosenModel()){toast("Instale um modelo no Ollama para usar respostas reais.",true);return;}
  text=text.trim();$("message-input").value="";addMessage("user",text);
  const waiting=showTyping();setBusy(true);
  try{
    const result=await api("/api/chat",{method:"POST",body:JSON.stringify(chatPayload(text))});
    waiting.querySelector(".message-text").textContent=result.answer;
    waiting.querySelector(".message-meta").textContent=`${state.provider==="ollama"?`Clean BOT · ${chosenModel()}`:"Clean BOT · simulação"} · ${result.trace.elapsed_ms} ms`;
    renderTrace(result);
    await refreshMemories();
  }catch(err){waiting.querySelector(".message-text").textContent=`Não consegui completar esta resposta. ${err.message}`;waiting.querySelector(".message-meta").textContent="Erro de execução";toast(err.message,true);}
  finally{setBusy(false);$("chat-messages").scrollTop=$("chat-messages").scrollHeight;$("message-input").focus();}
}
function renderTrace(result){
  const data=result.trace;setText("trace-time",`${data.elapsed_ms} ms · ${data.retrieval}`);
  const steps=$("trace-steps").querySelectorAll(".trace-step");steps.forEach((el,i)=>{el.classList.toggle("active",i===2||i===0&&result.retrieved.length>0||i===3&&result.saved.length>0);el.classList.toggle("dim",i===0&&!data.enabled.length||i===3&&!data.auto_capture)});
  const wrap=$("trace-details");wrap.replaceChildren();const summary=node("div","trace-summary");summary.append(node("span","tag",`Módulos ativos: ${data.enabled.length}`),node("span","tag",`Histórico anterior: ${data.history_turns} turnos`),node("span","tag good",`Recuperadas: ${result.retrieved.length}`),node("span","tag",`Criadas: ${result.saved.length}`));wrap.append(summary);
  if(!data.enabled.length){wrap.append(node("div","trace-memory","Memória externa desconectada. O agente usou somente a conversa desta sessão."));}
  else if(!result.retrieved.length){wrap.append(node("div","trace-memory","Nenhuma memória relevante foi recuperada para esta pergunta."));}
  result.retrieved.forEach(m=>{const el=node("div","trace-memory");const b=node("b",null,`${LABELS[m.type]} · relevância ${(m.score*100).toFixed(0)}% — `);el.append(b,document.createTextNode(m.content));wrap.append(el);});
  if(result.saved.length){const head=node("div","trace-memory");head.append(node("b",null,"Nova(s) memória(s) salva(s): "));head.append(document.createTextNode(result.saved.map(x=>LABELS[x.type]).join(", ")));wrap.append(head);}
  (data.warnings||[]).forEach(w=>wrap.append(node("div","trace-memory",`Aviso: ${w}`)));
}
async function resetSession(){if(state.busy)return;const old=state.sessionId;state.sessionId=newSessionId();clearChat();await api("/api/session/reset",{method:"POST",body:JSON.stringify({session_id:old})});await refreshMemories();toast("Nova sessão! Histórico e memória de trabalho apagados; SQLite preservado.");}
async function addMemory(){const type=$("memory-type").value,content=$("memory-content").value.trim();if(!content){toast("Escreva o conteúdo da memória.",true);return;}try{const res=await api("/api/memories",{method:"POST",body:JSON.stringify({session_id:state.sessionId,type,content})});$("memory-form").classList.add("hidden");$("memory-content").value="";await refreshMemories();toast(res.created?"Memória adicionada ao laboratório.":"Essa memória já existe no banco.");}catch(err){toast(err.message,true);}}
async function editMemory(record){const content=prompt(`Editar memória ${LABELS[record.type]}:`,record.content);if(content===null||content===record.content)return;if(!content.trim()){toast("O conteúdo não pode ficar vazio.",true);return;}try{await api(`/api/memories/${record.id}`,{method:"PATCH",body:JSON.stringify({session_id:state.sessionId,content})});await refreshMemories();toast("Memória atualizada.");}catch(err){toast(err.message,true);}}
async function deleteMemory(record){if(!confirm(`Excluir esta memória ${LABELS[record.type]}?\n\n${record.content}`))return;try{await api(`/api/memories/${record.id}?session_id=${encodeURIComponent(state.sessionId)}`,{method:"DELETE"});await refreshMemories();toast("Memória excluída.");}catch(err){toast(err.message,true);}}
async function compare(event){event.preventDefault();if(state.busy)return;const text=$("compare-question").value.trim();if(!text){toast("Digite uma pergunta para comparar.",true);return;}if(state.provider==="ollama"&&!chosenModel()){toast("Selecione um modelo instalado no Ollama.",true);return;}setBusy(true);$("comparison-results").replaceChildren(node("div","comparison-placeholder","Executando duas respostas sem histórico..."));try{const data=await api("/api/compare",{method:"POST",body:JSON.stringify(chatPayload(text))});
    const wrap=$("comparison-results");wrap.replaceChildren();
    for(const [klass,title,value] of [["without","◌  SEM MEMÓRIA",data.without],["with","✦  COM MEMÓRIA",data.with_memory]]){const card=node("article",`comparison-card ${klass}`);card.append(node("div","comparison-title",title),node("p",null,value));wrap.append(card);}
    const info=node("div","comparison-context");info.append(node("b",null,`${data.retrieved.length} memória(s) recuperada(s)`),document.createTextNode(` · Busca: ${data.trace.retrieval} · ${(data.trace.elapsed_ms/1000).toFixed(1)} s · Pergunta idêntica · Sem histórico · Sem novas gravações`));wrap.append(info);
    (data.trace.warnings||[]).forEach(w=>wrap.append(node("div","comparison-context",`Aviso: ${w}`)));
  }catch(err){$("comparison-results").replaceChildren(node("div","comparison-placeholder",err.message));toast(err.message,true);}finally{setBusy(false);}}
function bind(){
  $("preset-list").addEventListener("click",event=>{const button=event.target.closest(".preset");if(button)changeMode(PRESETS[button.dataset.preset]);});
  $("module-list").addEventListener("change",event=>{const input=event.target.closest("input[data-kind]");if(input){const types=new Set(state.active);if(input.checked)types.add(input.dataset.kind);else types.delete(input.dataset.kind);changeMode([...types]);}});
  $("provider").addEventListener("change",async event=>{const old=state.sessionId;state.provider=event.target.value;state.sessionId=newSessionId();clearChat();renderControls();try{await api("/api/session/reset",{method:"POST",body:JSON.stringify({session_id:old})});}catch{}await refreshMemories();toast(`Motor alterado para ${state.provider==="ollama"?"Ollama real":"simulação"}. Nova sessão iniciada.`);});
  $("model").addEventListener("change",event=>{state.model=event.target.value;$("manual-model").value="";renderControls();});
  $("manual-model").addEventListener("input",renderControls);
  $("refresh-models").addEventListener("click",refreshStatus);
  $("arena-form").addEventListener("submit",arena);
  $("reset-session").addEventListener("click",()=>resetSession().catch(err=>toast(err.message,true)));
  $("chat-form").addEventListener("submit",e=>{e.preventDefault();sendMessage($("message-input").value);});
  $("message-input").addEventListener("keydown",event=>{if(event.key==="Enter"&&!event.shiftKey){event.preventDefault();$("chat-form").requestSubmit();}});
  $("chat-messages").addEventListener("click",event=>{const hint=event.target.closest(".suggestion");if(hint)sendMessage(hint.dataset.question);});
  $("open-memory-form").addEventListener("click",()=>{$("memory-form").classList.toggle("hidden");$("memory-content").focus();});
  $("cancel-memory").addEventListener("click",()=>$("memory-form").classList.add("hidden"));
  $("memory-form").addEventListener("submit",event=>{event.preventDefault();addMemory();});
  $("memory-search").addEventListener("input",renderMemories);
  $("memory-filters").addEventListener("click",event=>{const button=event.target.closest("button[data-filter]");if(!button)return;state.memoryFilter=button.dataset.filter;document.querySelectorAll(".filter").forEach(b=>b.classList.toggle("active",b===button));renderMemories();});
  $("seed-demo").addEventListener("click",async()=>{try{const res=await api("/api/demo/seed",{method:"POST",body:JSON.stringify({session_id:state.sessionId})});await refreshMemories();toast(`${res.created.length} novas memórias de exemplo adicionadas.`);}catch(err){toast(err.message,true);}});
  $("wipe-demo").addEventListener("click",async()=>{if(!confirm("Apagar permanentemente TODAS as memórias persistentes deste laboratório? A conversa atual também será reiniciada."))return;try{await api("/api/demo/wipe",{method:"POST",body:JSON.stringify({session_id:state.sessionId})});state.sessionId=newSessionId();clearChat();await refreshMemories();toast("Banco SQLite esvaziado; sessão reiniciada.");}catch(err){toast(err.message,true);}});
  $("compare-form").addEventListener("submit",compare);
  $("help-button").addEventListener("click",()=>$("guide-dialog").showModal());
  $("close-guide").addEventListener("click",()=>$("guide-dialog").close());
  $("guide-ok").addEventListener("click",()=>$("guide-dialog").close());
}
async function start(){bind();renderControls();await Promise.all([refreshStatus(),refreshMemories()]);setInterval(()=>{if(!state.busy)refreshStatus();},20000);}
start().catch(err=>toast(err.message,true));
