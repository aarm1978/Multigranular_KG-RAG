"use strict";

const $ = (id) => document.getElementById(id);
const state = {
  bootstrap:null, filtered:[], currentID:null, draft:{}, coordinator:null,
  navigationChain:Promise.resolve(), changeSerial:0, loading:false, currentRevisit:false
};
const editableText = ["screeningRationale", "screeningNotes"];
const booleans = ["distributedEvidenceLikely", "sectionContextUseful", "deterministicEndpointLikely"];

async function api(path, options={}) {
  const response = await fetch(path, {headers:{"Content-Type":"application/json"}, ...options});
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
  return body;
}

function notify(message, error=false) {
  const box=$("notice"); box.textContent=message; box.style.background=error?"#8b2828":"#163f35"; box.classList.remove("hidden");
  window.setTimeout(()=>box.classList.add("hidden"), 5200);
}

function escapeHTML(value) { const span=document.createElement("span"); span.textContent=String(value); return span.innerHTML; }

function radioControls(containerID, name, values) {
  $(containerID).innerHTML=values.map(value=>`<label><input type="radio" name="${name}" value="${value}">${escapeHTML(value)}</label>`).join("");
}

function initControls() {
  radioControls("expectedAssertionDensity","expectedAssertionDensity",state.bootstrap.controls.densities);
  radioControls("expectedRelationDensity","expectedRelationDensity",state.bootstrap.controls.densities);
  radioControls("routingComplexity","routingComplexity",state.bootstrap.controls.routingComplexities);
  booleans.forEach(field=>radioControls(field,field,["yes","no"]));
  $("recurringDistinctions").innerHTML=state.bootstrap.controls.recurringDistinctions.map(value=>`<label><input type="checkbox" value="${escapeHTML(value)}">${escapeHTML(value)}</label>`).join("");
  const papers=[...new Set(state.bootstrap.units.map(x=>x.paperID))].sort((a,b)=>a.localeCompare(b,undefined,{numeric:true}));
  const roles=[...new Set(state.bootstrap.units.map(x=>x.sectionRole))].sort();
  papers.forEach(value=>$("paperFilter").add(new Option(value,value)));
  roles.forEach(value=>$("roleFilter").add(new Option(value,value)));
  renderTargets("node"); renderTargets("relation");
  document.querySelectorAll("input, textarea, select").forEach(el=>{
    if (!["paperFilter","roleFilter","statusFilter","goToID","nodeSearch","relationSearch","reviewerInput","rationaleTemplate"].includes(el.id)) el.addEventListener("change", scheduleAutosave);
  });
  editableText.forEach(id=>$(id).addEventListener("input",scheduleAutosave));
  Object.keys(ScreeningUIAids.rationaleTemplates).forEach(name=>$("rationaleTemplate").add(new Option(name,name)));
}

function renderTargets(kind) {
  const host=$(kind+"Targets"); const groups=new Map();
  state.bootstrap.targets.filter(t=>t.targetKind===kind).forEach(t=>{ if(!groups.has(t.displayGroup)) groups.set(t.displayGroup,[]); groups.get(t.displayGroup).push(t); });
  host.innerHTML=[...groups].map(([group,targets])=>`<section class="target-group" data-group="${escapeHTML(group)}"><h4>${escapeHTML(group.replaceAll("_"," "))}</h4>${targets.map(target=>{
    const relation=kind==="relation"?`<details><summary>Domain / range</summary><div>Domain: ${escapeHTML(target.domainClasses.join(", "))}</div><div>Range: ${escapeHTML(target.rangeClasses.join(", "))}</div></details>`:"";
    return `<div class="target" data-search="${escapeHTML((target.displayLabel+" "+target.shortDefinition+" "+target.boundaryHint+" "+target.operationalTargetID).toLowerCase())}"><label><input type="checkbox" name="${kind}Target" value="${escapeHTML(target.operationalTargetID)}"><span>${escapeHTML(target.displayLabel)} <span class="badge">${escapeHTML(target.pilotTreatment.replaceAll("_"," "))}</span> <span class="badge">${escapeHTML(target.decisionRole.replaceAll("_"," "))}</span></span></label><small>${escapeHTML(target.shortDefinition)}<br><em>Boundary:</em> ${escapeHTML(target.boundaryHint)}</small>${relation}</div>`;
  }).join("")}</section>`).join("");
  host.querySelectorAll("input").forEach(el=>el.addEventListener("change",()=>{ renderExhaustive(); scheduleAutosave(); }));
}

function filterTargets(kind) {
  const term=$(kind+"Search").value.trim().toLowerCase();
  $(kind+"Targets").querySelectorAll(".target").forEach(el=>el.classList.toggle("hidden",term && !el.dataset.search.includes(term)));
  $(kind+"Targets").querySelectorAll(".target-group").forEach(group=>group.classList.toggle("hidden",![...group.querySelectorAll(".target")].some(x=>!x.classList.contains("hidden"))));
}

function selected(name) { return [...document.querySelectorAll(`input[name="${name}"]:checked`)].map(x=>x.value); }

function renderExhaustive(notifyCleared=true) {
  const previously=new Set(selected("exhaustiveTarget"));
  const routed=new Set([...selected("nodeTarget"),...selected("relationTarget")]);
  const choices=state.bootstrap.targets.filter(t=>routed.has(t.operationalTargetID)&&t.pilotTreatment==="extract_and_evaluate");
  $("exhaustiveTargets").innerHTML=choices.length?choices.map(t=>`<label><input type="checkbox" name="exhaustiveTarget" value="${escapeHTML(t.operationalTargetID)}" ${previously.has(t.operationalTargetID)?"checked":""}>${escapeHTML(t.displayLabel)}</label>`).join(""):"<p class=\"muted\">No currently routed extract-and-evaluate targets.</p>";
  $("exhaustiveTargets").querySelectorAll("input").forEach(el=>el.addEventListener("change",scheduleAutosave));
  const cleared=[...previously].filter(id=>!choices.some(t=>t.operationalTargetID===id));
  if(notifyCleared&&cleared.length) notify(`Cleared ${cleared.length} exhaustive-empty selection(s) because the target was unrouted.`);
}

function collectDraft() {
  const value=(name)=>document.querySelector(`input[name="${name}"]:checked`)?.value||"";
  const yesNo=(name)=>{const v=value(name); return v==="yes"?true:v==="no"?false:null;};
  return {
    screeningRationale:$("screeningRationale").value,
    likelyExhaustiveEmptyTargetIDs:selected("exhaustiveTarget"),
    likelyRecurringDistinctions:[...$("recurringDistinctions").querySelectorAll("input:checked")].map(x=>x.value),
    expectedAssertionDensity:value("expectedAssertionDensity"), expectedRelationDensity:value("expectedRelationDensity"), routingComplexity:value("routingComplexity"),
    distributedEvidenceLikely:yesNo("distributedEvidenceLikely"), sectionContextUseful:yesNo("sectionContextUseful"), deterministicEndpointLikely:yesNo("deterministicEndpointLikely"),
    routedNodeOperationalTargetIDs:selected("nodeTarget"), routedRelationOperationalTargetIDs:selected("relationTarget"), screeningNotes:$("screeningNotes").value
  };
}

function setRadio(name,value) { document.querySelectorAll(`input[name="${name}"]`).forEach(x=>x.checked=x.value===value); }
function populateDraft(draft) {
  state.draft=draft; $("screeningRationale").value=draft.screeningRationale||""; $("screeningNotes").value=draft.screeningNotes||"";
  setRadio("expectedAssertionDensity",draft.expectedAssertionDensity||""); setRadio("expectedRelationDensity",draft.expectedRelationDensity||""); setRadio("routingComplexity",draft.routingComplexity||"");
  booleans.forEach(name=>setRadio(name,draft[name]===true?"yes":draft[name]===false?"no":""));
  $("recurringDistinctions").querySelectorAll("input").forEach(x=>x.checked=(draft.likelyRecurringDistinctions||[]).includes(x.value));
  document.querySelectorAll("input[name=nodeTarget],input[name=relationTarget]").forEach(x=>x.checked=[...(draft.routedNodeOperationalTargetIDs||[]),...(draft.routedRelationOperationalTargetIDs||[])].includes(x.value));
  renderExhaustive(false); $("exhaustiveTargets").querySelectorAll("input").forEach(x=>x.checked=(draft.likelyExhaustiveEmptyTargetIDs||[]).includes(x.value));
  $("completionBadge").textContent=draft.completed?"Reviewed":"Pending"; $("saveStatus").textContent=draft.updatedAt?`Saved ${draft.updatedAt}`:"Not saved";
}

function applyFilters(keepCurrent=true) {
  const paper=$("paperFilter").value, role=$("roleFilter").value, status=$("statusFilter").value;
  state.filtered=state.bootstrap.units.filter(u=>(!paper||u.paperID===paper)&&(!role||u.sectionRole===role)&&(!status||(status==="revisit"?u.revisit:(status==="reviewed")===u.completed)));
  let index=state.filtered.findIndex(u=>u.sourceUnitID===state.currentID); if(index<0) index=0;
  if(state.filtered.length && (!keepCurrent || !state.filtered.some(u=>u.sourceUnitID===state.currentID))) navigateSafely(state.filtered[index].sourceUnitID);
  else updatePosition();
}

function updatePosition() {
  const index=state.filtered.findIndex(u=>u.sourceUnitID===state.currentID); $("filterPosition").textContent=state.filtered.length?`Unit ${index+1} of ${state.filtered.length} in current filter`:"No units match this filter";
  $("previousButton").disabled=index<=0; $("nextButton").disabled=index<0||index>=state.filtered.length-1;
}

function setFormBusy(disabled) {
  $("form").querySelectorAll("input,textarea,button").forEach(control=>control.disabled=disabled);
}

async function loadUnitDirect(id) {
  state.loading=true;
  try {
    const data=await api(`/api/units/${encodeURIComponent(id)}`); state.currentID=id;
    const m=data.metadata; $("unitID").textContent=m.sourceUnitID; $("sectionTitle").textContent=m.sectionTitle||"Untitled section";
    $("metadata").innerHTML=[["Paper",m.paperID],["Artifact",m.sourceArtifactID],["Role",m.sectionRole],["Characters",m.characterCount.toLocaleString()],["Content",m.contentTypes.join(", ")],["Conversion",m.sourceConversionStatus],["Review required",m.reviewRequired?"yes":"no"],["Review reasons",m.reviewReasons.join(", ")||"none"]].map(([k,v])=>`<div><dt>${escapeHTML(k)}</dt><dd>${escapeHTML(v)}</dd></div>`).join("");
    renderReferences(m); state.currentRevisit=Boolean(data.revisit); updateRevisitControl();
    $("sourceText").textContent=data.text; $("textError").textContent=data.textValidationError||""; $("textError").classList.toggle("hidden",!data.textValidationError); setFormBusy(data.reviewBlocked);
    populateDraft(data.draft); updatePosition();
  } finally { state.loading=false; }
}

function renderReferences(metadata) {
  const host=$("referenceMetadata"); host.replaceChildren();
  const fields=[["Deterministic node refs",metadata.deterministicNodeRefs],["Deterministic edge refs",metadata.deterministicEdgeRefs],["Deferred record refs",metadata.deferredRecordRefs]];
  const present=fields.filter(([,value])=>value);
  if(!present.length){const p=document.createElement("p");p.className="muted";p.textContent="None";host.append(p);return;}
  present.forEach(([label,value])=>{const row=document.createElement("div"),dt=document.createElement("dt"),dd=document.createElement("dd");dt.textContent=label;dd.textContent=value;row.append(dt,dd);host.append(row);});
}

async function persistBoundSnapshot(request) {
  try {
    const result=await api(`/api/units/${encodeURIComponent(request.sourceUnitID)}`,{method:"PUT",body:JSON.stringify({draft:request.draft,markReviewed:request.markReviewed})});
    const unit=state.bootstrap.units.find(x=>x.sourceUnitID===request.sourceUnitID); if(unit)unit.completed=result.draft.completed;
    state.bootstrap.progress=result.progress; state.bootstrap.reviewerLocked=result.reviewerLocked; updateProgress(); updateReviewerControl();
    if(state.currentID===request.sourceUnitID&&state.changeSerial===request.serial){
      state.draft=result.draft; populateDraft(result.draft);
      if(result.clearedExhaustiveEmptyTargetIDs.length) notify(`Cleared incompatible exhaustive-empty target(s): ${result.clearedExhaustiveEmptyTargetIDs.join(", ")}`);
      else if(!request.silent) notify(request.markReviewed?"Unit marked reviewed.":"Draft saved locally.");
    }
    return result;
  } catch(error){ if(state.currentID===request.sourceUnitID)$("saveStatus").textContent="Save failed"; notify(error.message,true); throw error; }
}

function scheduleAutosave() {
  if(!state.currentID||state.loading)return;
  state.changeSerial+=1;
  state.coordinator.schedule({sourceUnitID:state.currentID,draft:collectDraft(),markReviewed:false,silent:true,serial:state.changeSerial});
  $("saveStatus").textContent="Unsaved changes";
}

async function save(markReviewed=false,silent=false) {
  if(!state.currentID)return false;
  const sourceUnitID=state.currentID, request={sourceUnitID,draft:collectDraft(),markReviewed,silent,serial:state.changeSerial};
  try {
    await state.coordinator.saveNow(request);
    if(markReviewed){const target=findNextPending(sourceUnitID);if(target)await navigateSafely(target.sourceUnitID);else notify("All open units are reviewed.");}
    return true;
  } catch(error){return false;}
}

function navigateSafely(sourceUnitID) {
  if(!sourceUnitID)return Promise.resolve();
  state.navigationChain=state.navigationChain.catch(()=>{}).then(async()=>{
    if(sourceUnitID===state.currentID)return;
    setFormBusy(true);
    try {await state.coordinator.navigate(sourceUnitID,loadUnitDirect);}
    catch(error){setFormBusy(false);throw error;}
  }).catch(error=>{notify(`Navigation stopped until the current draft saves: ${error.message}`,true);return false;});
  return state.navigationChain;
}

function updateProgress(){const p=state.bootstrap.progress; $("progressLabel").textContent=`${p.reviewed} / ${p.total} reviewed · ${p.remaining} remaining`;}
function move(delta){const i=state.filtered.findIndex(u=>u.sourceUnitID===state.currentID), target=state.filtered[i+delta]; if(target)navigateSafely(target.sourceUnitID);}
function findNextPending(sourceUnitID=state.currentID){const all=state.bootstrap.units,start=Math.max(0,all.findIndex(u=>u.sourceUnitID===sourceUnitID));return[...all.slice(start+1),...all.slice(0,start+1)].find(u=>!u.completed);}
function nextPending(){const target=findNextPending();if(target)navigateSafely(target.sourceUnitID);else notify("All open units are reviewed.");}

function applyRationaleTemplate() {
  const selector=$("rationaleTemplate"), name=selector.value;
  if(!name)return;
  const rationale=$("screeningRationale"), existing=rationale.value;
  const confirmed=!existing.trim()||confirm("Replace the current non-empty rationale with the selected editable template?");
  const result=ScreeningUIAids.selectRationaleTemplate(existing,name,confirmed); selector.value="";
  if(!result.applied)return;
  rationale.value=result.value; scheduleAutosave(); rationale.focus();
}

function clearSemanticTargetsManually() {
  if(!confirm("Clear all routed node/relation targets, exhaustive-empty selections, and recurring distinctions for this unit?"))return;
  const cleared=ScreeningUIAids.clearSemanticTargets(collectDraft());
  document.querySelectorAll("input[name=nodeTarget],input[name=relationTarget]").forEach(x=>x.checked=false);
  $("recurringDistinctions").querySelectorAll("input").forEach(x=>x.checked=false);
  renderExhaustive(false); scheduleAutosave();
  if(!cleared.screeningRationale.trim()&&confirm("Insert the editable ‘No semantic target’ rationale template?")){
    $("screeningRationale").value=ScreeningUIAids.rationaleTemplates["No semantic target"]; scheduleAutosave();
  }
}

function updateRevisitControl(){$("revisitButton").setAttribute("aria-pressed",String(state.currentRevisit));$("revisitButton").textContent=state.currentRevisit?"Revisit ✓":"Revisit";}
async function toggleRevisit(){
  if(!state.currentID)return;
  const next=!state.currentRevisit;
  try{const result=await api("/api/revisit",{method:"POST",body:JSON.stringify({sourceUnitID:state.currentID,revisit:next})});state.currentRevisit=result.revisit;const unit=state.bootstrap.units.find(x=>x.sourceUnitID===state.currentID);if(unit)unit.revisit=result.revisit;updateRevisitControl();notify(result.revisit?"Marked for local revisit.":"Removed local revisit bookmark.");if($("statusFilter").value==="revisit"&&!result.revisit)applyFilters(false);}catch(error){notify(error.message,true);}
}

function updateReviewerControl(){
  const locked=Boolean(state.bootstrap.reviewerLocked), reviewer=state.bootstrap.reviewerID||"not set";
  $("reviewerLabel").textContent=locked?`${reviewer} (locked)`:reviewer;
  $("reviewerButton").disabled=locked;
  $("reviewerButton").title=locked?"Reviewer identity locked after the first saved revision.":"Set or change reviewer before the first saved revision.";
}

async function setReviewer() {
  const id=$("reviewerInput").value.trim(); if(!id)return;
  try{const result=await api("/api/reviewer",{method:"POST",body:JSON.stringify({reviewerID:id})}); state.bootstrap.reviewerID=result.reviewerID;state.bootstrap.reviewerLocked=result.reviewerLocked;updateReviewerControl();$("reviewerDialog").close();notify("Reviewer identity saved locally.");}catch(error){notify(error.message,true);}
}
async function exportFile(kind){try{const result=await api("/api/export",{method:"POST",body:JSON.stringify({kind})});notify(`Export written to ${result.path}`);}catch(error){notify(error.message,true);}}

async function start() {
  try {
    state.bootstrap=await api("/api/bootstrap"); state.coordinator=new BoundSaveCoordinator(persistBoundSnapshot,650); $("modeBadge").textContent=state.bootstrap.mode; updateReviewerControl(); updateProgress(); initControls();
    $("productionBanner").classList.toggle("hidden",state.bootstrap.mode!=="production"); $("dryRunBanner").classList.toggle("hidden",state.bootstrap.mode!=="dry-run");
    $("resetDryRunButton").classList.toggle("hidden",state.bootstrap.mode!=="dry-run"); $("completeExportButton").disabled=state.bootstrap.mode==="dry-run";
    ["paperFilter","roleFilter","statusFilter"].forEach(id=>$(id).addEventListener("change",()=>applyFilters(false)));
    ["node","relation"].forEach(kind=>$(kind+"Search").addEventListener("input",()=>filterTargets(kind)));
    $("previousButton").onclick=()=>move(-1); $("nextButton").onclick=()=>move(1); $("nextPendingButton").onclick=nextPending; $("saveButton").onclick=()=>save(false); $("saveNextButton").onclick=()=>save(true);
    $("rationaleTemplate").onchange=applyRationaleTemplate; $("noSemanticTargetsButton").onclick=clearSemanticTargetsManually; $("revisitButton").onclick=toggleRevisit;
    $("goButton").onclick=()=>{const id=$("goToID").value.trim(), unit=state.bootstrap.units.find(x=>x.sourceUnitID===id); unit?navigateSafely(id):notify("That sourceUnitID is not an open screening unit.",true);};
    $("reviewerButton").onclick=()=>{$("reviewerInput").value=state.bootstrap.reviewerID;$("reviewerCancel").classList.remove("hidden");$("reviewerDialog").showModal();}; $("reviewerSave").onclick=(event)=>{event.preventDefault();setReviewer();};
    $("reviewerDialog").addEventListener("cancel",event=>{if(!state.bootstrap.reviewerID)event.preventDefault();});
    $("backupButton").onclick=()=>exportFile("partial"); $("completeExportButton").onclick=()=>exportFile("complete");
    $("resetDryRunButton").onclick=async()=>{if(confirm("Delete all dry-run drafts and revisions? Production state will not be touched.")){await api("/api/dry-run/reset",{method:"POST",body:"{}"});location.reload();}};
    window.addEventListener("beforeunload",event=>{if(state.coordinator?.hasUnsavedChanges()){event.preventDefault();event.returnValue="";}});
    applyFilters(false); if(!state.bootstrap.reviewerID){$("reviewerCancel").classList.add("hidden");$("reviewerDialog").showModal();}
  } catch(error){notify(error.message,true);$("sectionTitle").textContent="Application could not start";}
}
start();
