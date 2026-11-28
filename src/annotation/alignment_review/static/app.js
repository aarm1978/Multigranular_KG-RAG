"use strict";
const el = id => document.getElementById(id);
function add(parent, tag, text, cls) {
  const n = document.createElement(tag);
  if (text != null) n.textContent = text;
  if (cls) n.className = cls;
  parent.append(n);
  return n;
}
function link(parent, text, href) {
  const a = add(parent, "a", text);
  a.href = href;
  if (!href.startsWith("#")) { a.target = "_blank"; a.rel = "noopener noreferrer"; }
  return a;
}
let state, token, unit, editing = false, moving = false, reachedEnd = false;
let queue = Promise.resolve(), lastClock = performance.now(), lastInput = lastClock, active = 0;
let foreground = !document.hidden && document.hasFocus();
function clock() {
  const now = performance.now();
  if (editing && foreground && now-lastClock <= 20000)
    active += Math.max(0, Math.min(now, lastInput + 60000) - lastClock) / 1000;
  lastClock = now;
}
for (const event of ["keydown","pointerdown","pointermove","scroll"]) {
  window.addEventListener(event, () => {clock(); lastInput = performance.now();}, {passive:true});
}
function focusChange() { clock(); foreground = !document.hidden && document.hasFocus(); }
window.addEventListener("focus", focusChange); window.addEventListener("blur", focusChange);
document.addEventListener("visibilitychange", focusChange);
const status = m => { el("status").textContent = m; };
function report(err) {status(err.message || String(err));}
async function get(path) {
  const res = await fetch(path);
  if (!res.ok) throw Error("Unable to load the local session");
  return res.json();
}
function event(data) {
  const task = queue.then(async () => {
    clock();
    const seconds = active;
    active = 0;
    const response = await fetch("/api/action", {method:"POST",headers:{"Content-Type":"application/json","X-Review-Token":token},
      body:JSON.stringify({revision:state.revision, sourceUnitID:state.cursor, activeSeconds:seconds, ...data})});
    const result = await response.json();
    if (!response.ok) throw Error(result.error);
    state = result;
    progress();
  });
  queue = task.catch(report);
  return task;
}
function progress() {
  const rows = Object.values(state.records);
  el("progress").textContent = rows.filter(r=>r.judgment).length+" of "+rows.length+" judged";
}
const choices = ["Supported","Unsupported","Insufficient evidence"];
function answer() {
  const judgment = document.querySelector("input[name=judgment]:checked")?.value || null;
  return {judgment, completeReview:unit.phase==="Identity" && judgment==="Supported",
          comment:el("comment").value, problematic:el("problematic").value};
}
const draftKey = () => "alignment-review:"+state.package+":"+unit.id;
const saves = new BoundSaveCoordinator(async snapshot => {
  await event(snapshot);
  if (unit && snapshot.sourceUnitID===unit.id && JSON.stringify(answer())===JSON.stringify({
    judgment:snapshot.judgment,completeReview:snapshot.completeReview,comment:snapshot.comment,problematic:snapshot.problematic})) {
    localStorage.removeItem(draftKey()); status("Saved locally");
  }
}, 300);
function changed() {
  const value=answer();
  localStorage.setItem(draftKey(),JSON.stringify({value,base:state.records[unit.id].visits}));
  saves.schedule({type:"save",sourceUnitID:unit.id,...value});
  status("Saving…");
}
function quote(parent, id, seen) {
  if (seen.has(id)) {link(parent,"See original excerpt "+id,"#"+id);return;}
  seen.add(id);
  const q=add(parent,"blockquote",unit.excerpts[id]);
  q.id=id; q.setAttribute("aria-label","Original excerpt "+id);
}
function renderEvidence() {
  const root=el("evidence"), seen=new Set(), contexts=new Map();
  root.replaceChildren();
  for(const art of unit.artifacts) {
    const section=add(root,"section",null,"artifact");
    add(section,"h3",art.id+" · "+art.families.join(", "));
    if (/^https?:\/\//.test(art.source || "")) link(section,art.source,art.source);
    for(const m of unit.occurrences.filter(o=>o.artifact===art.id)) {
      const block=add(section,"section",null,"member");
      block.id=m.id;
      add(block,"strong",m.id+" · "+(m.labels.join(" / ") || "Unlabelled occurrence"));
      const meta=[m.ontologyClass,...Object.entries(m.details).map(([k,v])=>k+" "+v)];
      if(m.granularity && m.granularity!=="unspecified_requires_context_review")meta.push(m.granularity);
      for(const [k,v] of Object.entries(m.versions))meta.push(k+" "+JSON.stringify(v));
      add(block,"p",meta.join(" · "),"meta");
      if(!m.evidence.length)add(block,"p","No original excerpt available.");
      for(const e of m.evidence) {
        const description=Object.entries(e.location).map(([k,v])=>k+" "+v).join(" · ");
        add(block,"p",[e.quote,description].filter(Boolean).join(" · "),"meta");
        if(/^https?:\/\//.test(e.location.sourceLocation || ""))link(block,"Open source location",e.location.sourceLocation);
        if(e.quote)quote(block,e.quote,seen); else add(block,"p","Original excerpt unavailable.");
        if(e.relationEvidence) {
          add(block,"p","Cited relation evidence · "+e.relationEvidence.join(", "),"meta");
          for(const q of e.relationEvidence.filter(q=>q!==e.quote))quote(block,q,seen);
        }
        if(e.contextID) {
          const id=e.contextID, context=unit.contexts[id];
          if(contexts.has(id)) {
            const a=link(block,"See surrounding source text "+id,"#"+id);
            a.onclick=()=>{contexts.get(id).open=true;};
          } else {
            const d=add(block,"details");d.id=id;contexts.set(id,d);
            add(d,"summary","Surrounding source text "+id);
            const body=add(d,"p",context.before,"context");
            link(body," ["+context.quote+"] ","#"+context.quote);body.append(context.after);
          }
        } else if(e.context) {
          const d=add(block,"details");add(d,"summary","Surrounding source text");
          const body=add(d,"p",e.context[0],"context");
          link(body," ["+e.quote+"] ","#"+e.quote);body.append(e.context[1]);
        }
      }
    }
  }
}
function renderForm(saved) {
  const identity=unit.phase==="Identity";
  el("question").textContent=identity?"Do all occurrences refer to the same entity at a compatible level of granularity?":
    "Does the evidence support the proposed predicate and direction between these referents?";
  const help=identity?["I reviewed the complete group and every member supports the same referent.",
    "At least one member establishes a material incompatibility. An early counterexample is sufficient.",
    "Whole-group identity cannot be established from the available evidence."]:
    ["The evidence supports this predicate in the proposed direction.","The evidence establishes a material incompatibility with the proposed relation or direction.",
    "The available evidence cannot establish the directed relation."];
  const opts=el("options");opts.replaceChildren();
  choices.forEach((v,i)=>{
    const label=add(opts,"label",null,"choice"),r=add(label,"input");
    r.type="radio";r.name="judgment";r.value=v;r.checked=saved.judgment===v;
    r.disabled=identity && i===0 && !reachedEnd;
    label.append(" "+v);add(label,"small",help[i]);r.onchange=changed;
  });
  el("comment").value=saved.comment;el("problematic").value=saved.problematic;
}
async function load() {
  unit=await get("/api/unit/"+state.cursor);
  const ids=Object.keys(state.records), pos=ids.indexOf(unit.id), identity=unit.phase==="Identity";
  const saved=state.records[unit.id];
  el("phase").textContent="Phase "+(identity?"1 · Identity":"2 · Typed relation")+"  /  "+unit.id+"  /  Case "+(pos+1)+" of "+ids.length;
  el("hypothesis").textContent=identity?unit.label:unit.endpoints[0].label+" → "+unit.predicate+" → "+unit.endpoints[1].label;
  el("description").textContent=identity?"Proposed common referent · "+unit.ontologyClass:
    unit.endpoints.map((end,i)=>(i?"Object":"Subject")+" · "+end.ontologyClass+" · "+end.size+" "+(unit.memberUnit || "source occurrence")+(end.size===1?"":"s")+" · cited here: "+end.occurrences.join(", ")).join("   →   ");
  el("definition").replaceChildren();
  for(const def of unit.definitions || []) {
    add(el("definition"),"h2",unit.predicate+" · Ontology v0.1.9");
    add(el("definition"),"p",[].concat(def.domain).join(" / ")+" → "+[].concat(def.range).join(" / "));
    add(el("definition"),"p",def.note);add(el("definition"),"p",def.evidence);
  }
  el("counts").textContent=unit.occurrences.length+" "+(unit.memberUnit ? unit.memberUnit+"s" : "occurrences")+" · "+unit.artifacts.length+" source artifacts";
  renderEvidence();
  let draft=JSON.parse(localStorage.getItem(draftKey()) || "null");
  // A crash can leave an unacknowledged local edit from the immediately preceding visit.
  if(draft && draft.base!==saved.visits-1 && draft.base!==saved.visits)draft=null;
  reachedEnd=saved.completeReview || Boolean(draft?.value.completeReview);
  renderForm(draft?draft.value:saved);
  el("prev").disabled=pos===0;el("next").textContent=pos===ids.length-1?"Save & finish":"Save & Next";
  el("workspace").hidden=false; el("welcome").hidden=true; el("pause").hidden=false;
  window.scrollTo(0,0);observer.disconnect();observer.observe(el("end"));
  status(identity && !reachedEnd?"Review all artifact sections before selecting Supported.":"Saved locally");
  if(draft)changed();
}
const observer=new IntersectionObserver(items=>{
  if(editing && items.some(i=>i.isIntersecting)) {
    reachedEnd=true;const first=document.querySelector("input[name=judgment]");if(first)first.disabled=false;
  }
});
function transition(fn) {
  return async () => {
    if(moving)return;
    moving=true;el("form").inert=true;
    try {await fn();}catch(err){report(err);}finally{moving=false;el("form").inert=false;}
  };
}
function welcome() {
  editing=false;observer.disconnect();el("workspace").hidden=true;el("pause").hidden=true;
  el("welcome").hidden=false;el("resume").textContent="Resume review";
}
async function leave(target) {
  await saves.flush();
  if(target){await event({type:"go",target});await load();}
  else {await event({type:"pause"});welcome();status("Session saved. You can return to any case.");}
}
el("prev").onclick=transition(()=>leave(Object.keys(state.records)[Object.keys(state.records).indexOf(state.cursor)-1]));
el("next").onclick=transition(()=>leave(Object.keys(state.records)[Object.keys(state.records).indexOf(state.cursor)+1]));
el("pause").onclick=transition(()=>leave(null));
el("resume").onclick=transition(async()=>{await event({type:"open"});editing=true;lastInput=lastClock=performance.now();await load();});
el("comment").oninput=changed;el("problematic").oninput=changed;
el("clear").onclick=()=>{document.querySelectorAll("input[name=judgment]").forEach(r=>r.checked=false);changed();};
el("export").onclick=transition(async()=>{
  await saves.flush(); if(editing)await event({type:"tick"});
  const response=await fetch("/api/export");if(!response.ok)throw Error("Export failed");
  const url=URL.createObjectURL(await response.blob()),a=document.createElement("a");
  a.href=url;a.download="alignment-review-results.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
setInterval(()=>{if(editing && !moving)event({type:"tick"}).catch(report);},5000);
get("/api/state").then(s=>{state=s;token=s.csrfToken;progress();el("resume").disabled=false;
  if(state.revision)el("resume").textContent="Resume review";
}).catch(report);
