/* Focused client execution with a minimal DOM: no browser or real judgments. */
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.textContent = ''; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  set innerHTML(_) { throw Error('Source content must be rendered as text'); }
}
function descendants(element) {
  return [element, ...element.children.filter(x => x instanceof Element).flatMap(descendants)];
}

test('orientation, unselected controls, autosave, and literal-only rendering', async () => {
  const elements = Object.fromEntries(['session','save','error','units','review'].map(id => [id,new Element('div')]));
  const values = ['supported_as_proposed','not_supported_as_proposed','insufficient_evidence_to_decide'];
  const state = {mode:'dry-run', reviewRole:'second', reviewerID:'synthetic', total:1, answered:0, revision:0,
    csrfToken:'synthetic-token', decisions:{}, judgments:values, duplicateDecisions:[],
    units:[{primarySourceUnitID:'synthetic-unit', phase:'orientation', nodesTotal:1,nodesAnswered:0,relationsTotal:0,relationsAnswered:0}]};
  const unit = {primarySourceUnitID:'synthetic-unit', source:{sectionTitle:'Synthetic source',text:'A 😀 <script> is literal.'},authorizedContext:[],duplicateReviewGroups:[],
    items:[{judgmentItemID:'opaque',recordKind:'node',operationalTarget:{name:'Finding'},assertion:{label:'😀',action:'propose_new',attributes:[]},
      paragraphContexts:[{sourceUnitID:'synthetic-unit',segments:[{text:'A ',highlights:[]},{text:'😀',highlights:['evidence','label']},{text:' <script> is literal.',highlights:[]}]}]}]};
  const actions = [];
  const context = vm.createContext({document:{getElementById:id=>elements[id],createElement:tag=>new Element(tag),createTextNode:text=>text},
    fetch:async (url,init) => {
      if(init && init.method === 'POST') {
        assert.equal(init.headers['X-Review-Token'],'synthetic-token');
        const action=JSON.parse(init.body);actions.push(action);assert.equal(action.expectedRevision,state.revision);
        if(action.action==='phase') state.units[0].phase=action.value;
        if(action.action==='judgment'){state.decisions[action.id]=action.value;state.answered=1;state.units[0].nodesAnswered=1;}
        state.revision++;
      }
      return {ok:true,json:async()=>structuredClone(url.startsWith('/api/unit/')?unit:state)};
    }});
  const code = fs.readFileSync(path.join(__dirname,'../src/annotation/publication_step8/static/app.js'),'utf8');
  await vm.runInContext(code,context);
  assert.equal(elements.error.textContent,'');
  assert.equal(descendants(elements.review).filter(x=>x.tag==='input').length,0);
  const begin=descendants(elements.review).find(x=>x.textContent==='Begin candidate review');
  await begin.onclick();
  const radios=descendants(elements.review).filter(x=>x.tag==='input');
  assert.equal(radios.length,3);assert.ok(radios.every(x=>x.checked===false));
  assert.ok(!descendants(elements.review).some(x=>x.textContent.startsWith('Show authorized context')));
  assert.ok(descendants(elements.review).some(x=>x.textContent===' <script> is literal.'));
  await radios[1].onchange();
  assert.equal(elements.save.textContent,'Saved ✓');
  assert.equal(actions.length,2);assert.equal(actions[1].value,'not_supported_as_proposed');
  const saved=descendants(elements.review).filter(x=>x.tag==='input');
  assert.equal(saved.filter(x=>x.checked).length,1);assert.equal(saved.find(x=>x.checked).value,'not_supported_as_proposed');
});
