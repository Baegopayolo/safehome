const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('static/js/index.js','utf8');
class Element {
    constructor(){this.textContent='';this.hidden=false;this.children=[];this.style={};this.dataset={};}
    replaceChildren(){this.children=[];}
    append(...nodes){this.children.push(...nodes);}
    setAttribute(){}
    addEventListener(){}
}
const valid = () => ({status:'complete',summary:{region_count:25,transaction_count:300},
    coverage:{completed:300,expected:300,stale:[],failures:[]},
    period:{from:'2025-12-01',to:'2026-11-05'},
    last_updated:'2026-11-05T10:00:00+09:00',oldest_updated:'2026-11-04T10:00:00+09:00',
    regions:Array.from({length:25},(_,i)=>({name:'지역'+i,transaction_count:12,completed_months:12})),
    trends:Array.from({length:12},(_,i)=>({month:'2025'+String(i+1).padStart(2,'0'),transaction_count:25,completed_regions:25}))});
async function render(data,ok=true){
    const ids=['data-status','data-period','retry-stats','region-count','transaction-count','last-updated',
        'region-chart','trend-chart','region-chart-note','trend-chart-note'];
    const nodes=Object.fromEntries(ids.map(id=>[id,new Element()]));
    const root=new Element();root.dataset.dashboardUrl='/api/dashboard/summary';
    let calls=0;
    const context=vm.createContext({document:{querySelector:()=>root,getElementById:id=>nodes[id],
        createElement:()=>new Element(),addEventListener(){}},
        fetch:async()=>{calls++;if(data instanceof Error)throw data;return{ok,json:async()=>data};},
        AbortController,setTimeout,clearTimeout,Intl});
    vm.runInContext(script,context);await vm.runInContext('loadDashboardStats()',context);
    return {nodes,root,calls};
}
test('one coherent response renders summary and both charts',async()=>{
    const {nodes:n,calls}=await render(valid());
    assert.equal(calls,1);assert.equal(n['transaction-count'].textContent,'300건');
    assert.equal(n['region-chart'].children.length,25);assert.equal(n['trend-chart'].children.length,12);
    assert.match(n['last-updated'].textContent,/10:00/);assert.equal(n['retry-stats'].hidden,true);
});
test('partial and stale states are explicit',async()=>{
    for(const status of ['partial','stale']){
        const d=valid();d.status=status;
        if(status==='partial'){d.coverage.completed=299;d.regions[0].completed_months=11;}
        else d.coverage.stale=[{cadence:'daily'}];
        const {nodes:n,root}=await render(d);
        assert.equal(root.dataset.state,status);
        assert.match(n['data-status'].textContent,status==='partial'?/일부 수집/:/갱신 지연/);
        if(status==='partial')assert.match(n['region-chart'].children[0].children[2].textContent,/일부 11\/12/);
        else assert.match(n['data-status'].textContent,/최근 3개월 1개/);
    }
});
test('uncollected is not zero',async()=>{
    const d=valid();d.status='unavailable';d.coverage.completed=0;d.summary={transaction_count:null,region_count:null};
    d.last_updated=null;d.oldest_updated=null;
    d.regions.forEach(r=>{r.transaction_count=null;r.completed_months=0;});
    d.trends.forEach(r=>{r.transaction_count=null;r.completed_regions=0;});
    const {nodes:n}=await render(d);assert.equal(n['transaction-count'].textContent,'—');
    assert.equal(n['last-updated'].textContent,'수집 전');assert.equal(n['region-chart'].children.length,0);
});
test('successful empty collection shows zero and explains it',async()=>{
    const d=valid();d.summary={transaction_count:0,region_count:0};
    d.regions.forEach(r=>r.transaction_count=0);d.trends.forEach(r=>r.transaction_count=0);
    const {nodes:n}=await render(d);assert.equal(n['transaction-count'].textContent,'0건');
    assert.match(n['trend-chart-note'].textContent,/0건/);
});
test('HTTP/network and inconsistent totals show retry without fabricated zero',async()=>{
    const broken=valid();broken.summary.transaction_count=999;
    for(const [data,ok]of [[valid(),false],[new Error('timeout'),true],[broken,true],[{},true]]){
        const {nodes:n,root}=await render(data,ok);assert.equal(root.dataset.state,'error');
        assert.equal(n['transaction-count'].textContent,'—');assert.equal(n['retry-stats'].hidden,false);
    }
});
test('unknown region has no fabricated bar and text remains text',async()=>{
    const d=valid();d.status='partial';d.summary.transaction_count=288;
    d.regions[0]={name:'<img src=x onerror=alert(1)>',transaction_count:null,completed_months:0};
    d.trends.forEach(r=>r.transaction_count=24);
    const {nodes:n}=await render(d);const row=n['region-chart'].children[0];
    assert.equal(row.children[0].textContent,'<img src=x onerror=alert(1)>');
    assert.equal(row.children[2].textContent,'미수집');assert.equal(row.children[1].children[0].style.width,'0%');
});
