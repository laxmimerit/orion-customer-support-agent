"""Validate the portable learner dataset using only Python's standard library."""
from pathlib import Path
import csv,json,datetime as dt,collections,statistics,hashlib
R=Path(__file__).resolve().parents[1]
def read(n):return list(csv.DictReader((R/'data'/f'{n}.csv').open()))
def date(s):return dt.datetime.fromisoformat(s.replace('Z','+00:00'))
t=read('tickets');c=read('customers');a=read('agents');iv=read('invoices');ev=read('evaluation_inputs');lab=read('evaluation_labels');b=read('untriaged_backlog');m=read('messages');snap=date('2026-06-30T23:59:59Z')
assert [len(x) for x in [t,c,a,iv,ev,lab,b]]==[4000,300,9,1800,300,300,500]
ids={x['ticket_id'] for x in t};eids={x['ticket_id'] for x in ev};bids={x['ticket_id'] for x in b};assert len(ids)==4000 and not(ids&eids or ids&bids or eids&bids)
assert eids=={x['ticket_id'] for x in lab};assert set(ev[0])=={'ticket_id','subject','body'}
cs={x['customer_id'] for x in c};ags={x['agent_id'] for x in a}
for x in t:
 assert x['customer_id'] in cs and x['agent_id'] in ags
 assert date('2026-01-01T00:00:00Z')<=date(x['created_at'])<=snap
 for field,hours in [('first_response_at','first_response_hours'),('resolved_at','resolution_hours')]:
  if x[field]:
   assert date(x['created_at'])<=date(x[field])<=snap
   assert abs((date(x[field])-date(x['created_at'])).total_seconds()/3600-float(x[hours]))<1e-6
  else:assert x[hours]==''
 assert (x['status']=='resolved')==bool(x['resolved_at'])
 if x['csat']:assert x['resolved_at'] and 1<=int(x['csat'])<=5
threads=collections.defaultdict(list)
for x in m:
 assert x['ticket_id'] in ids
 threads[x['ticket_id']].append(x)
for x in t:
 thread=threads[x['ticket_id']]
 stamps=[date(v['created_at']) for v in thread]
 assert stamps==sorted(stamps) and stamps[0]==date(x['created_at'])
 assert stamps[-1]<=snap
 replies=[v for v in thread if v['author_role']=='agent']
 assert bool(replies)==bool(x['first_response_at'])
 if replies:assert replies[0]['created_at']==x['first_response_at']
 if x['resolved_at']:assert stamps[-1]<=date(x['resolved_at'])
assert sum(60<=len(v)<=120 for v in threads.values())==10
for name in ['tickets','customers','agents','invoices']:
 assert read(name)==[{k:'' if v is None else str(v) for k,v in row.items()} for row in json.loads((R/'dashboard/data.json').read_text())[name]]
inputs={x['ticket_id']:x for x in ev}
priority_markers={'P1':'entire production team','P2':'Several people','P3':'One person','P4':'non-urgent planning'}
for x in lab:assert priority_markers[x['priority']] in inputs[x['ticket_id']]['body']
assert all(x['region']=={'India':'APAC','Australia':'APAC','United States':'Americas','Canada':'Americas','United Kingdom':'EMEA','Germany':'EMEA'}[x['country']] for x in c)
clusters=read('duplicate_clusters');assert len(clusters)==150 and len({x['cluster_id'] for x in clusters})==30
for group in {x['cluster_id'] for x in clusters}:assert sum(x['cluster_id']==group for x in clusters)==5
for p in (R/'resources/part1/3.2').glob('interview-*.md'):assert 800<=len(p.read_text().split())<=1500

for x in iv:assert x['customer_id'] in cs and int(x['seats'])*int(x['unit_price_usd'])==int(x['total_usd'])
for x in b:assert x['category']==x['priority']==''
assert len({x['created_at'][:7] for x in t})==6
april=[x for x in t if x['created_at'][5:7]=='04'];others=[x for x in t if x['created_at'][5:7]!='04'];assert sum(x['category']=='billing' for x in april)/len(april)>sum(x['category']=='billing' for x in others)/len(others)
assert sum(x['created_at'].startswith('2026-05-14') for x in t)>180
weekend=[x for x in t if date(x['created_at']).weekday()>=5 and x['first_response_hours']];weekday=[x for x in t if date(x['created_at']).weekday()<5 and x['first_response_hours']]
breach=lambda rows:sum(float(x['first_response_hours'])>float(x['sla_response_hours']) for x in rows)/len(rows)
assert breach(weekend)>breach(weekday)
assert all(x['contact_email'].endswith('@example.com') for x in c)
result={'status':'pass','counts':{'tickets':len(t),'customers':len(c),'agents':len(a),'invoices':len(iv),'messages':len(m),'evaluation':len(ev),'backlog':len(b)},'weekend_breach_rate':round(breach(weekend),4),'weekday_breach_rate':round(breach(weekday),4),'april_billing_share':round(sum(x['category']=='billing' for x in april)/len(april),4),'checks':['unique and disjoint pools','foreign keys','timestamps and duration arithmetic','invoice reconciliation','CSAT validity','no labels in evaluation inputs','planted analytics patterns','safe email identifiers','message chronology','ten long threads','dashboard data parity','classification urgency evidence','geographic consistency','duplicate clusters','interview lengths']}
print(json.dumps(result,indent=2))
