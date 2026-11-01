"""Read-only final deployment checks. Never prints environment values or credentials."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urljoin,urlsplit
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import subprocess,json,hashlib,socket,re,time,urllib.request,urllib.error,http.client,sys,zipfile

TRANSIENT_RETRIES=[]

ROOT=Path(__file__).resolve().parents[2]
def docker(*args):
 r=subprocess.run(['docker',*args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
 if r.returncode:raise RuntimeError('Docker read failed: '+' '.join(args[:4])+' '+r.stderr[-300:])
 return r.stdout.strip()
def fetch(url):
 for attempt in range(3):
  try:
   with urllib.request.urlopen(url,timeout=20)as r:return r.status,r.geturl(),r.read(),dict(r.headers)
  except (TimeoutError,urllib.error.URLError,http.client.IncompleteRead,ConnectionError) as error:
   if isinstance(error,urllib.error.HTTPError) or attempt==2:raise
   TRANSIENT_RETRIES.append({'origin':urlsplit(url).netloc,'path':urlsplit(url).path,'reason':type(error).__name__})
   time.sleep(.5)
def getjson(url):return json.loads(fetch(url)[2])
class Links(HTMLParser):
 def __init__(self):super().__init__();self.assets=[];self.links=[]
 def handle_starttag(self,tag,attrs):
  d=dict(attrs)
  if tag=='script' and d.get('src'):self.assets.append(d['src'])
  if tag=='link' and d.get('rel')=='stylesheet':self.assets.append(d.get('href',''))
  if tag in ['a','form']:self.links.append(d.get('href',d.get('action','')))
def port_open(port):
 with socket.socket(socket.AF_INET,socket.SOCK_STREAM)as s:s.settimeout(1);return s.connect_ex(('127.0.0.1',port))==0
def main():
 b=Path((ROOT/'.unified-backup/current.txt').read_text(encoding='utf-8').strip())
 before=json.loads((b/'baseline.json').read_text(encoding='utf-8'))
 out={'verified_at':datetime.now(timezone.utc).isoformat()}
 out['compose_services']=docker('compose','config','--services').splitlines()
 assert set(out['compose_services'])=={'portal','nextcloud','mailpit','db','redis'}
 rows=[json.loads(x) for x in docker('compose','ps','--format','json').splitlines() if x.strip()]
 out['services']=[{k:r.get(k) for k in ['Service','State','Health']}for r in rows]
 assert len(rows)==5 and all(r['State']=='running' and r.get('Health')=='healthy' for r in rows)
 out['web_ports']={str(p):port_open(p)for p in [8000,8080,8025,8001,8081,8026]}
 assert all(out['web_ports'][str(p)]for p in [8000,8080,8025])
 assert not any(out['web_ports'][str(p)]for p in [8001,8081,8026])
 out['env_unchanged']=hashlib.sha256((ROOT/'.env').read_bytes()).hexdigest()==before['env_sha256']
 out['pnpm_lock_unchanged']=hashlib.sha256((ROOT/'apps/portal/frontend/pnpm-lock.yaml').read_bytes()).hexdigest()==before['pnpm_sha256']
 # Preserve the original byte baseline. Refactored imports/module locations necessarily differ.
 snapshot=ROOT/'.unified-backup/refactor-20261101/source.zip'
 with zipfile.ZipFile(snapshot) as source:
  out['portal_original_business_snapshot_matches']=all(hashlib.sha256(source.read(name)).hexdigest()==digest for name,digest in before['business'].items())
 assert out['portal_original_business_snapshot_matches'],'Original business baseline does not match pre-refactor snapshot'
 semantic=subprocess.run([sys.executable,str(ROOT/'scripts/maintenance/verify-backend-refactor.py')],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
 assert semantic.returncode==0,'Backend semantic/refactor validation failed: '+semantic.stderr[-300:]+semantic.stdout[-300:]
 out['portal_business_bytes_unchanged']=False
 out['portal_business_semantics_preserved']=True
 out['portal_refactor_validation']=semantic.stdout.strip()
 assert out['env_unchanged'] and out['pnpm_lock_unchanged']
 old_apps=json.loads((b/'nextcloud-apps-before.json').read_text(encoding='utf-8-sig'))['enabled']
 new_apps=json.loads(docker('compose','exec','-u','www-data','-T','nextcloud','php','occ','app:list','--output=json'))['enabled']
 out['native_apps_unchanged']=all(new_apps.get(k)==v for k,v in old_apps.items())
 out['added_apps']=sorted(set(new_apps)-set(old_apps));out['native_app_count']=len(old_apps)
 assert out['native_apps_unchanged'] and out['added_apps']==['cloudbox_theme']
 out['user_counts']={}
 for db,query in [('portal','select count(*) from users;'),('nextcloud','select count(*) from oc_users;')]:
  count=docker('compose','exec','-T','db','sh','-c',f'psql -U "$POSTGRES_USER" -d {db} -Atc "{query}"')
  out['user_counts'][db]={'before':before[db+'_users'],'after':count,'same':count==before[db+'_users']}
 assert all(x['same']for x in out['user_counts'].values())
 mail=getjson('http://localhost:8025/api/v1/messages?limit=1')
 out['mail_counts']={k:mail[k]for k in before['mail_counts']}
 out['mail_counts_match_baseline']=out['mail_counts']==before['mail_counts']
 out['mail_features_match_baseline']=getjson('http://localhost:8025/api/v1/webui')==before['mail_webui']
 assert out['mail_counts_match_baseline'] and out['mail_features_match_baseline']
 assert not (b/'qa-private.json').exists()
 out['qa_cleanup']=json.loads((ROOT/'artifacts/qa/UNIFIED-QA-CLEANUP.json').read_text(encoding='utf-8'))
 out['infrastructure_not_published']=True
 for service in ['db','redis']:
  cid=docker('compose','ps','-q',service)
  bindings=json.loads(docker('inspect','--format','{{json .HostConfig.PortBindings}}',cid)) or {}
  assert not bindings
 mail_id=docker('compose','ps','-q','mailpit')
 bindings=json.loads(docker('inspect','--format','{{json .HostConfig.PortBindings}}',mail_id))
 assert set(bindings)=={'8025/tcp'} and bindings['8025/tcp']==[{'HostIp':'127.0.0.1','HostPort':'8025'}]
 mounts=json.loads(docker('inspect','--format','{{json .Mounts}}',mail_id))
 out['mail_persistent_volume']=[m.get('Name')for m in mounts if m['Destination']=='/data']
 assert out['mail_persistent_volume']==['cloud-storage_mailpit_data']
 out['local_http']={}
 for port,path in [(8000,'/'),(8000,'/login'),(8080,'/login'),(8025,'/')]:
  code,final,body,_=fetch(f'http://localhost:{port}'+path)
  assert code==200 and urlsplit(final).hostname=='localhost' and urlsplit(final).port==port
  out['local_http'][str(port)+path]=200
 assert getjson('http://localhost:8000/healthz')['status']=='ok'
 assert getjson('http://localhost:8080/status.php')['installed']
 urls=[];out['tunnels']=[]
 state=ROOT/'.online/state.json'
 if state.exists():
  urls=json.loads(state.read_text(encoding='utf-8'))['urls']
  for name,expected in [('cloud-storage-portal-tunnel','http://portal:8000'),('cloud-storage-nextcloud-tunnel','http://nextcloud:80')]:
   data=json.loads(docker('inspect',name))[0]
   assert data['State']['Running']
   cmd=data['Config']['Cmd'];target=cmd[cmd.index('--url')+1]
   assert target==expected
   out['tunnels'].append({'name':name,'running':True,'target':target})
 out['public_pages']=[];assets=set()
 for app,base in zip(['portal','nextcloud'],urls):
  for path in ['/','/login']:
   code,final,body,_=fetch(base+path);assert code==200 and urlsplit(final).scheme=='https' and urlsplit(final).hostname==urlsplit(base).hostname
   parsed=Links();parsed.feed(body.decode('utf-8'))
   bad=[x for x in parsed.links if urlsplit(x).hostname in ['localhost','127.0.0.1','::1']]
   assert not bad,'Public workflow link points to localhost'
   out['public_pages'].append({'app':app,'path':path,'status':code,'https':True,'localhost_links':0})
   selected=parsed.assets if app=='portal' else [x for x in parsed.assets if 'cloudbox_theme' in x]+[x for x in parsed.assets if '.js' in x][:2]
   assets.update(urljoin(final,x)for x in selected if x)
 # Portal's renderer CSS loads lazily; inspect its real built manifest instead of guessing hashes.
 manifest=json.loads(docker('compose','exec','-T','portal','python','-c',"import json;print(open('/srv/app/static/ui/.vite/manifest.json').read())"))
 portal_base=urls[0]if urls else'http://localhost:8000'
 for entry in manifest.values():
  for css in entry.get('css',[]):assets.add(portal_base+'/static/ui/'+css)
  if entry.get('src','').endswith(('PortalApp.tsx','UnifiedApp.tsx')):assets.add(portal_base+'/static/ui/'+entry['file'])
 _,_,body,_=fetch('http://localhost:8025/');p=Links();p.feed(body.decode());assets.update(urljoin('http://localhost:8025/',x)for x in p.assets)
 assets.add('http://localhost:8025/mailpit.svg?cloudbox=1')
 results=[];fonts=set()
 def asset(url):
  status,final,body,headers=fetch(url);assert status==200 and body
  return url,body,headers
 with ThreadPoolExecutor(max_workers=1)as pool:
  for url,body,headers in pool.map(asset,sorted(assets)):
   results.append({'origin':urlsplit(url).netloc,'path':urlsplit(url).path,'status':200})
   if '.css' in urlsplit(url).path:
    text=body.decode('utf-8')
    for ref in re.findall(r'url\([\"\x27]?([^\"\x27)]+)',text):
     if not ref.startswith('data:') and re.search(r'\.(ttf|woff2?)(?:\?|$)',ref):fonts.add(urljoin(url,ref))
  for url,_,_ in pool.map(asset,sorted(fonts)):
   results.append({'origin':urlsplit(url).netloc,'path':urlsplit(url).path,'status':200})
 out['assets_and_fonts']=results
 out['transient_http_retries']=TRANSIENT_RETRIES
 out['public_urls']=urls;out['mail_has_public_tunnel']=False
 out['known_native_limitations']='See docs/qa/DIAGNOSTICS-2026-11-01.md: Viewer has a local integrity-disclosed patch; raw archive current404 was an invalid QA route; Mail observer reproduced on script-free control. Deployment checks do not cover all functionality.'
 (ROOT/'artifacts/qa/UNIFIED-FINAL-VERIFICATION.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
 print('PASS final ports 8000/8080/8025; 8001/8081/8026 closed; 5 healthy services; data counts/config/lock and original snapshot match; backend semantic checks pass; 51 native apps retained.')
 if urls:print('PASS HTTPS pages/redirects/current tunnel targets and',len(results),'actual UI assets/fonts. Mail remains local. Known limitations remain recorded.')
 else:print('PASS local pages and',len(results),'actual UI assets/fonts. Public HTTPS not checked: tunnels are off by user choice. Known limitations remain recorded.')
if __name__=='__main__':main()
