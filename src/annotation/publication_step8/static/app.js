'use strict';
let state, csrf, unit, position = 0, busy = false;
const q = id => document.getElementById(id);
function el(tag, text, className) { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (className) n.className = className; return n; }
function button(text, action, disabled = false) { const n = el('button', text); n.disabled = disabled || busy; n.onclick = action; return n; }
async function api(path, body) {
  const r = await fetch(path, body ? {method:'POST', headers:{'Content-Type':'application/json','X-Review-Token':csrf}, body:JSON.stringify(body)} : {});
  const result = await r.json(); if (!r.ok) throw Error(result.error || 'Request failed'); return result;
}
async function act(action, id, value) {
  if (busy) return; busy = true; q('save').textContent = 'Saving…'; render();
  try { state = await api('/api/action', {expectedRevision:state.revision, action, id, value}); q('save').textContent = 'Saved ✓'; q('error').textContent = ''; }
  catch(e) { q('save').textContent = 'Not saved'; q('error').textContent = e.message + '. Your last confirmed state is shown. Reload to recover from a stale revision.'; }
  finally { busy = false; render(); }
}
async function openUnit(id) {
  if (busy) return;
  try { unit = await api('/api/unit/' + encodeURIComponent(id)); position = 0; render(); }
  catch(e) { q('error').textContent = e.message; }
}
function sourcePanel(parent, source, title) { const d = el('details'), s = el('summary', title); d.append(s, el('div',source.text,'source')); parent.append(d); }
function choices(parent, id, values, action) {
  const box = el('fieldset'); box.append(el('legend', action === 'judgment' ? 'Judgment as proposed' : 'Duplicate decision'));
  const options = el('div', undefined, 'judgments');
  values.forEach(value => { const label = el('label'); const input = el('input'); input.type = 'radio'; input.name = id; input.value = value;
    input.checked = state.decisions[id] === value; input.disabled = busy;
    input.onchange = () => act(action,id,value); label.append(input, document.createTextNode(' '+value.replaceAll('_',' '))); options.append(label); });
  box.append(options); parent.append(box);
}
function endpoint(parent, value) { const box=el('div',undefined,'endpoint'); box.append(el('strong',value.label || value.exactNodeID || 'Endpoint')); if(value.className) box.append(el('div',value.className)); parent.append(box); }
function render() {
  if (!state) return;
  q('session').textContent = `${state.mode} · ${state.reviewRole} · ${state.reviewerID} · Session: ${state.answered} / ${state.total} reviewed`;
  const nav=q('units'); nav.replaceChildren(); state.units.forEach((u,i)=>{const b=button(`${i+1}. ${u.primarySourceUnitID} — ${u.phase}`,()=>openUnit(u.primarySourceUnitID)); if(unit && u.primarySourceUnitID===unit.primarySourceUnitID)b.className='current';nav.append(b);});
  const root=q('review');root.replaceChildren();if(!unit)return;
  const current=state.units.find(u=>u.primarySourceUnitID===unit.primarySourceUnitID);
  root.append(el('h2',unit.source.sectionTitle),el('p',`Nodes: ${current.nodesAnswered} / ${current.nodesTotal} · Relations: ${current.relationsAnswered} / ${current.relationsTotal}`,'progress'));
  if(current.phase==='orientation') {root.append(el('p','Source orientation: read the authorized primary unit, then begin candidate review.'),el('div',unit.source.text,'source'),button('Begin candidate review',()=>act('phase',unit.primarySourceUnitID,'nodes')));return;}
  sourcePanel(root,unit.source,'Complete authorized primary source text');
  unit.authorizedContext.forEach(source=>sourcePanel(root,source,'Show authorized context: '+source.sectionTitle));
  if(current.phase==='complete') {root.append(el('h3','Unit complete'));const i=state.units.findIndex(u=>u.primarySourceUnitID===unit.primarySourceUnitID);if(i+1<state.units.length)root.append(button('Next unit',()=>openUnit(state.units[i+1].primarySourceUnitID)));return;}
  const kind=current.phase==='nodes'?'node':'relation';const items=unit.items.filter(x=>x.recordKind===kind);
  position=Math.max(0,Math.min(position,items.length-1));
  root.append(el('h3',current.phase==='nodes'?'Node review':'Relation review'));
  const navigator=el('div',undefined,'navigator');items.forEach((item,i)=>{const answered=Object.hasOwn(state.decisions,item.judgmentItemID);const b=button(`${i+1} ${answered?'✓':'○'}`,()=>{position=i;render();});b.title=answered?'Answered':'Pending';if(i===position)b.className='current';navigator.append(b);});root.append(navigator);
  if(items.length) {
    const item=items[position], assertion=item.assertion;
    root.append(el('p',`${item.judgmentItemID} · ${position+1} / ${items.length}`),el('h3',item.operationalTarget.name));
    if(kind==='node') {root.append(el('p',assertion.label),el('p','Identity action: '+assertion.action));if(assertion.exactExistingNodeID)root.append(el('p',assertion.exactExistingNodeID));assertion.attributes.forEach(a=>root.append(el('p',a.attributeName+': '+String(a.value))));}
    else {const r=el('div',undefined,'relation');endpoint(r,assertion.sourceEndpoint);r.append(el('strong','→ '+assertion.relationName+' →'));endpoint(r,assertion.targetEndpoint);root.append(r,el('p','Scope: '+assertion.relationScope));}
    choices(root,item.judgmentItemID,state.judgments,'judgment');
    item.paragraphContexts.forEach((context,i)=>{root.append(el('small',`Evidence context ${i+1} of ${item.paragraphContexts.length} · ${context.sourceUnitID}`));const p=el('div',undefined,'paragraph');context.segments.forEach(segment=>{const s=el('span',segment.text);s.className=segment.highlights.map(k=>k==='source'?'sourceMention':k==='target'?'targetMention':k).join(' ');p.append(s);});root.append(p);});
    root.append(button('Previous',()=>{position--;render();},position===0),button('Next',()=>{position++;render();},position>=items.length-1));
  }
  if(kind==='node')root.append(button('Continue to relations',()=>{position=0;act('phase',unit.primarySourceUnitID,'relations');},current.nodesAnswered!==current.nodesTotal));
  else {unit.duplicateReviewGroups.forEach(group=>{root.append(el('h3',group.duplicateReviewGroupID),el('p',group.instruction),el('p',group.judgmentItemIDs.join(', ')));choices(root,group.duplicateReviewGroupID,state.duplicateDecisions,'duplicate');});root.append(button('Return to nodes',()=>{position=0;act('phase',unit.primarySourceUnitID,'nodes');}),button('Complete unit',()=>act('phase',unit.primarySourceUnitID,'complete'),current.relationsAnswered!==current.relationsTotal || unit.duplicateReviewGroups.some(g=>!state.decisions[g.duplicateReviewGroupID])));}
}
async function start() {try {state=await api('/api/state');csrf=state.csrfToken;const next=state.units.find(u=>u.phase!=='complete') || state.units[0];await openUnit(next.primarySourceUnitID);}catch(e){q('error').textContent=e.message;}}
start();
