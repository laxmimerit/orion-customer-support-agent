"""Rebuild fictional core datasets with a fixed seed. Standard library; optional pyarrow for Parquet."""
from pathlib import Path
import csv,json,random,datetime as dt
R=Path(__file__).resolve().parents[1]
rng=random.Random(20261030)
def text(p,s):
 p=R/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
def js(p,x):text(p,json.dumps(x,indent=2)+'\n')
def table(p,rows):
 p=R/p;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");w.writeheader();w.writerows(rows)
plans=[{'plan_id':p,'name':n,'monthly_seat_usd':v} for p,n,v in [('starter','Starter',19),('growth','Growth',49),('scale','Scale',99)]]
companies=[]
for i in range(300):
 companies.append(dict(customer_id=f'C{i+1:04}',company=f'{["Aster","Birch","Cedar","Dune","Ember","Fern","Grove","Harbor","Indigo","Juniper"][i%10]} {["Labs","Systems","Works","Cloud","Logic","Studio","Software","Metrics","Platform","Tools"][i//10%10]} {i+1:03}',industry=['SaaS','Retail tech','Education','Finance tools','Healthcare software','Logistics'][i%6],country=['India','United States','United Kingdom','Germany','Australia','Canada'][i%6],region=['APAC','Americas','EMEA'][i%3],company_size=['1-10','11-50','51-200','201-500'][i%4],plan_id=rng.choices(['starter','growth','scale'],[45,38,17])[0],seats=rng.randint(3,24),signup_date=(dt.date(2025,1,1)+dt.timedelta(days=rng.randrange(350))).isoformat(),contact_email=f'contact{i+1:03}@example.com',acquisition_source=['search','social','referral','partner'][i%4]))
# Independent demographic draws avoid accidental perfect segment correlations.
segment_rng=random.Random(731)
regions={'India':'APAC','Australia':'APAC','United States':'Americas','Canada':'Americas','United Kingdom':'EMEA','Germany':'EMEA'}
for c in companies:
 c['country']=segment_rng.choice(list(regions));c['region']=regions[c['country']]
 c['industry']=segment_rng.choice(['SaaS','Retail tech','Education','Finance tools','Healthcare software','Logistics'])
 c['company_size']=segment_rng.choice(['1-10','11-50','51-200','201-500'])
 c['acquisition_source']=segment_rng.choice(['search','social','referral','partner'])
impact={
 'P1':'Our entire production team is blocked right now, with no workaround. We cannot serve customers.',
 'P2':'Several people cannot complete an important workflow today. We have a temporary workaround, but it takes considerable manual work.',
 'P3':'One person is affected. Normal operations continue using a workaround; we can address this in the next few days.',
 'P4':'This is a non-urgent planning question or suggestion for our test workspace. Production is unaffected and there is no deadline.'}
agents=[dict(agent_id=f'A{i+1:02}',name=n,team=['Customer care','Technical support','Customer success'][i%3],shift='weekend' if i==8 else ['APAC','EMEA','Americas'][i%3],skills=['billing;account access','bug;outage','how-to;feature request'][i%3]) for i,n in enumerate(['Asha','Ben','Clara','Dev','Elena','Farah','Gabe','Hana','Ishan'])]
base=dt.datetime(2026,1,1,tzinfo=dt.timezone.utc);snap=dt.datetime(2026,6,30,23,59,59,tzinfo=dt.timezone.utc)
categories=['billing','bug','how-to','account access','feature request','outage']; channels=['email','chat','web','API']
issues={'billing':['Seat count differs from invoice','Proration after plan upgrade','Renewal total changed','Credit missing from next invoice','Tax line needs explanation'], 'bug':['Export stops before completion','Attachment preview is blank','Dashboard filter resets','Webhook delivery is delayed','Saved view loses sorting'], 'how-to':['Configure queue assignment','Export monthly ticket history','Set a reply template','Invite a read-only reviewer','Find archived conversations'], 'account access':['Invite link expired','Password reset email delayed','SSO login loops','Role change not applied','Locked out after device change'], 'feature request':['Add bulk reassignment','Support custom SLA calendars','Add multilingual templates','Allow scheduled exports','Add audit trail download'], 'outage':['Requests time out','Agent workspace unavailable','Messages cannot be sent','Search service unreachable','Queue updates stopped']}
resolutions={'billing':'Checked the invoice line items and seat history, explained the change, and applied the approved correction where needed.','bug':'Reproduced the issue with the supplied steps, linked the engineering case and verified the workaround with the customer.','how-to':'Shared the relevant setup steps and asked the customer to verify the result in their workspace.','account access':'Verified the account through the approved recovery flow and confirmed access was restored without sharing credentials.','feature request':'Recorded the use case and impact for product review; no delivery date was promised.','outage':'Linked the incident, communicated the service status and confirmed recovery with the customer.'}
def iso(x):return x.isoformat().replace('+00:00','Z')
def make_ticket(i,pool):
 cust=companies[rng.randrange(300)];day=rng.randrange(181);created=base+dt.timedelta(days=day,hours=rng.randrange(24),minutes=rng.randrange(60))
 if pool=='backlog':created=base+dt.timedelta(days=rng.randrange(169,181),hours=rng.randrange(24),minutes=rng.randrange(60))
 cat=rng.choices(categories,[22,23,23,16,12,4])[0]
 if created.month==4 and rng.random()<.48:cat='billing'
 if pool=='demo' and i<180:created=dt.datetime(2026,5,14,9,tzinfo=dt.timezone.utc)+dt.timedelta(minutes=i*2);cat='outage'
 priority=rng.choices(['P1','P2','P3','P4'],[5,21,55,19])[0]
 if cat=='outage':priority=rng.choice(['P1','P2'])
 agent=agents[rng.randrange(9)];weekend=created.weekday()>=5
 if agent['shift']=='weekend' and not weekend:agent=agents[rng.randrange(8)]
 target={'P1':1,'P2':4,'P3':12,'P4':24}[priority]*{'starter':1.5,'growth':1,'scale':.75}[cust['plan_id']]
 response=round(rng.lognormvariate(.05,.85)*target*.5*(2.6 if weekend else 1)*(2.7 if agent['agent_id']=='A07' else 1),2)
 resolution=round(response+rng.uniform(2,36)*(1.5 if cat=='bug' else 1),2)
 resolved=created+dt.timedelta(hours=resolution)
 status='resolved' if resolved<=snap and rng.random()>.11 else rng.choice(['open','pending','in progress'])
 first=created+dt.timedelta(hours=response);first_s=iso(first) if first<=snap else ''
 if pool=='backlog':status='open';first_s=''
 subject=rng.choice(issues[cat]);component={'billing':'Billing','bug':rng.choice(['Dashboard','Exports','Integrations']),'how-to':'Workspace','account access':'Identity','feature request':'Product','outage':'Platform'}[cat]
 context=rng.choice(['This affects our morning handoff.','Our administrator can reproduce it in a second browser.','We noticed it after changing the workspace settings.','Only one team is affected so far.','It is blocking our weekly customer review.','We need a clear explanation before making another change.'])
 context=impact[priority]
 body=f'{subject}. We use the {cust["plan_id"]} plan with {cust["seats"]} seats. {context} Workspace reference {cust["customer_id"]}; case {pool}-{i+1:05}. Please explain the next step and any workaround.'
 score=max(1,min(5,round(4.6-(response>target)*1.5-(cat=='outage')*.7+rng.uniform(-1, .7)))) if status=='resolved' and rng.random()<.67 else None
 prefix={'demo':'T','evaluation':'E','backlog':'B'}[pool]
 return dict(ticket_id=f'{prefix}{i+1:05}',customer_id=cust['customer_id'],agent_id=agent['agent_id'] if pool!='backlog' else '',created_at=iso(created),first_response_at=first_s,resolved_at=iso(resolved) if status=='resolved' else '',category=cat if pool!='backlog' else '',priority=priority if pool!='backlog' else '',status=status,channel=rng.choice(channels),component=component,subject=subject,body=body,sla_response_hours=target,sla_resolution_hours=target*8,first_response_hours=response if first_s else None,resolution_hours=resolution if status=='resolved' else None,csat=score,reopened_count=rng.choices([0,1,2],[85,12,3])[0],escalated=rng.random()<(.32 if cat in ['bug','outage'] else .08),sentiment=rng.choice(['neutral','frustrated','urgent','positive']),plan_id=cust['plan_id'],industry=cust['industry'],region=cust['region'],company_size=cust['company_size'])
tickets=[make_ticket(i,'demo') for i in range(4000)];evaluation=[make_ticket(i,'evaluation') for i in range(300)];backlog=[make_ticket(i,'backlog') for i in range(500)]
# Explicitly linked duplicates use distinct wording; no evaluation overlap.
clusters=[]
for g in range(30):
 group=tickets[200+g*5:205+g*5]
 for j,t in enumerate(group):
  t['category']='bug';t['component']='Exports';t['subject']=['CSV download ends early','Only part of the export arrives','Ticket export is truncated','Missing rows in downloaded CSV','Export does not include all tickets'][j];t['body']=f"{t['subject']}. Our saved export for workspace cluster {g+1} stops after page {g+2}. {impact[t['priority']]} Workspace {t['customer_id']}. Please help us retrieve the remaining rows.";clusters.append(dict(cluster_id=f'D{g+1:03}',ticket_id=t['ticket_id']))
messages=[];events=[]
for t in tickets:
 start=dt.datetime.fromisoformat(t['created_at'].replace('Z','+00:00'));end=dt.datetime.fromisoformat(t['resolved_at'].replace('Z','+00:00')) if t['resolved_at'] else min(snap,start+dt.timedelta(hours=48))
 n=rng.randint(3,15)
 if t in tickets[350:360]:n=rng.randint(60,120)
 if not t['first_response_at']:n=1
 first=dt.datetime.fromisoformat(t['first_response_at'].replace('Z','+00:00')) if t['first_response_at'] else start
 end=max(first,end)
 for j in range(n):
  stamp=start if j==0 else first+(end-first)*(j-1)/max(1,n-2)
  msg=t['body'] if j==0 else (resolutions[t['category']] if j%2 else rng.choice(['I tried those steps and have a follow-up about the workspace setting.','Thank you. Please confirm whether this also applies to our other team.','The issue is still reproducible; I have attached more context.','That addresses the immediate issue. How should we avoid it next time?'])+f' Follow-up {j//2+1}.')
  messages.append(dict(message_id=f'M{len(messages)+1:06}',ticket_id=t['ticket_id'],created_at=iso(stamp),author_role='customer' if j%2==0 else 'agent',body=msg))
 events.append(dict(ticket_id=t['ticket_id'],event_at=t['created_at'],event_type='created'))
 if t['resolved_at']:events.append(dict(ticket_id=t['ticket_id'],event_at=t['resolved_at'],event_type='resolved'))
labels=[dict(ticket_id=t['ticket_id'],category=t['category'],priority=t['priority']) for t in evaluation]
eval_inputs=[{k:t[k] for k in ['ticket_id','subject','body']} for t in evaluation]
invoices=[]
for c in companies:
 for m in range(1,7):
  price={'starter':19,'growth':39 if m<4 else 49,'scale':99}[c['plan_id']];amount=price*c['seats'];paid=rng.random()>.07
  invoices.append(dict(invoice_id=f'I{len(invoices)+1:05}',customer_id=c['customer_id'],month=f'2026-{m:02}',plan_id=c['plan_id'],seats=c['seats'],unit_price_usd=price,total_usd=amount,status='paid' if paid else 'overdue'))
for name,rows in [('customers',companies),('agents',agents),('plans',plans),('tickets',tickets),('messages',messages),('ticket_events',events),('invoices',invoices),('duplicate_clusters',clusters),('evaluation_inputs',eval_inputs),('evaluation_labels',labels),('untriaged_backlog',backlog)]:table(f'data/{name}.csv',rows)
js('data/tickets.json',tickets)
js('data/manifest.json',dict(seed=20261030,snapshot=iso(snap),fictional=True,demo_tickets=4000,evaluation_tickets=300,backlog_tickets=500,pools_disjoint=True,embedding_status='Generate after the recorded local Python/model setup; no substitute vectors included.'))
releases=[dict(release_id=f'R{i+1:02}',date=f'2026-{i//2+1:02}-{5 if i%2==0 else 20:02}',version=f'0.{i+1}.0',change=['Queue filters','Export reliability','Role permissions','Search latency'][i%4]) for i in range(12)]
table('data/releases.csv',releases);table('data/incidents.csv',[dict(incident_id='INC001',start='2026-05-14T09:00:00Z',end='2026-05-14T15:00:00Z',service='Platform',description='Synthetic queue-service outage')])

try:
 import pyarrow as pa,pyarrow.parquet as pq
 for name,rows in [('tickets',tickets),('invoices',invoices),('customers',companies),('messages',messages)]:pq.write_table(pa.Table.from_pylist(rows),R/f'data/{name}.parquet',compression='snappy')
except ImportError:
 print('CSV/JSON generated. Install pyarrow during the data lesson to refresh Parquet exports.')
view=dict(tickets=tickets,agents=agents,customers=companies,invoices=invoices,snapshot=iso(snap))
js('dashboard/data.json',view)
text('dashboard/data.js','const DATA = '+json.dumps(view,separators=(',',':'))+';\n')
print(json.dumps({'tickets':len(tickets),'messages':len(messages),'invoices':len(invoices)}))
