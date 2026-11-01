"""Temporary public access for the existing local project. No credentials in state."""
import hashlib,json,re,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
STATE=ROOT/'.online/state.json'
KEYS=['trusted_domains','trusted_proxies','overwritehost','overwriteprotocol','overwrite.cli.url','overwritecondaddr']
NAMES=['cloud-storage-portal-tunnel','cloud-storage-nextcloud-tunnel']
def run(args,check=True):
    p=subprocess.run(['docker',*args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
    if check and p.returncode:raise RuntimeError('Docker command failed: '+' '.join(args[:5])+'; '+p.stderr[-600:])
    return p.stdout.strip()
def compose(*args):return run(['compose',*args])
def save(s):STATE.parent.mkdir(exist_ok=True);STATE.write_text(json.dumps(s,indent=2),encoding='utf-8')
def occ(*args):return compose('exec','-T','-u','www-data','nextcloud','php','occ',*args)
def setkey(key,value):
    if value is None:occ('config:system:delete',key)
    else:occ('config:system:set',key,'--type=json','--value='+json.dumps(value))
def url(name):
    for _ in range(25):
        p=subprocess.run(['docker','logs','--tail','150',name],capture_output=True,text=True)
        found=re.findall(r'https://[a-z0-9-]+\.trycloudflare\.com',p.stdout+p.stderr)
        if found:return found[-1]
        time.sleep(2)
    raise RuntimeError('No Quick Tunnel URL for '+name)
def inspect(name):
    raw=run(['inspect',name],False)
    items=json.loads(raw) if raw else []
    return items[0] if items else None
def stop():
    if not STATE.exists():print('No saved online session. Nothing changed.');return
    s=json.loads(STATE.read_text())
    for name in NAMES:
        info=inspect(name)
        if info:
            if info['Config']['Labels'].get('cloudbox.quick')!='managed':raise RuntimeError('Refusing to stop unrelated container '+name)
            logs=subprocess.run(['docker','logs',name],capture_output=True,text=True)
            (ROOT/'.online'/f'{name}.log').write_text(logs.stdout+logs.stderr,encoding='utf-8')
            run(['rm','-f',name])
    for k,v in s['nextcloud_before'].items():setkey(k,v)
    compose('up','-d','--no-deps','--wait','portal')
    override=ROOT/'.online/compose.json'
    if override.exists():override.replace(override.with_name('last-compose.json'))
    STATE.replace(STATE.with_name('last-session.json'))
    print('Stopped both tunnels. Restored original Nextcloud and local portal configuration. Data/volumes unchanged.')
def start():
    running=compose('ps','--status','running','--services').splitlines()
    if not {'portal','nextcloud'}.issubset(running):raise RuntimeError('Start the local application with start-local.cmd before enabling online mode.')
    if STATE.exists():
        s=json.loads(STATE.read_text())
        infos=[inspect(n) for n in NAMES]
        if all(x and x['State']['Running'] for x in infos):
            if [url(n) for n in NAMES]==s['urls']:
                print('Existing session reused.\nCloudBox: '+s['urls'][0]+'\nNextcloud: '+s['urls'][1]);return
        stop()
    for n in NAMES:
        if inspect(n):raise RuntimeError('Container name already used; not replacing '+n)
    config=json.loads(occ('config:list','system','--output=json'))['system']
    networks=inspect('cloud-storage-nextcloud-1')['NetworkSettings']['Networks']
    network=next(k for k in networks if k.endswith('_default'))
    image=run(['image','inspect','cloudflare/cloudflared:latest','--format','{{.Id}}'])
    s={'nextcloud_before':{k:config.get(k) for k in KEYS},'env_sha256':hashlib.sha256((ROOT/'.env').read_bytes()).hexdigest(),'urls':[]}
    save(s)
    try:
        for n,service in zip(NAMES,['portal:8000','nextcloud:80']):
            run(['run','-d','--pull=never','--name',n,'--label','cloudbox.quick=managed','--network',network,'--restart=no',image,'tunnel','--no-autoupdate','--protocol','http2','--url','http://'+service])
        s['urls']=[url(n) for n in NAMES];save(s)
        for name in NAMES:
            logs=subprocess.run(['docker','logs',name],capture_output=True,text=True)
            (ROOT/'.online'/f'{name}.log').write_text(logs.stdout+logs.stderr,encoding='utf-8')
        ips=[inspect(n)['NetworkSettings']['Networks'][network]['IPAddress'] for n in NAMES]
        host=s['urls'][1].split('://')[1]
        domains=config.get('trusted_domains',[])
        if isinstance(domains,dict):domains=list(domains.values())
        setkey('trusted_domains',list(dict.fromkeys([*domains,host])))
        setkey('trusted_proxies',[*(config.get('trusted_proxies') or []),ips[1]])
        setkey('overwritehost',host);setkey('overwriteprotocol','https')
        setkey('overwritecondaddr','^'+re.escape(ips[1])+'$')
        setkey('overwrite.cli.url',s['urls'][1])
        override={'services':{'portal':{'environment':{'BASE_URL':s['urls'][0],'NEXTCLOUD_PUBLIC_URL':s['urls'][1]},'command':['uvicorn','app.main:app','--host','0.0.0.0','--port','8000','--proxy-headers','--forwarded-allow-ips','127.0.0.1,'+ips[0]]}}}
        (ROOT/'.online/compose.json').write_text(json.dumps(override,indent=2))
        run(['compose','-f','docker-compose.yml','-f','.online/compose.json','up','-d','--no-deps','--wait','portal'])
        assert hashlib.sha256((ROOT/'.env').read_bytes()).hexdigest()==s['env_sha256']
        print('CloudBox: '+s['urls'][0]+'\nNextcloud: '+s['urls'][1])
        print('Only portal 8000 and Nextcloud 8080 are published. Keep laptop, Docker and both tunnel containers running.')
    except Exception:
        stop();raise
if __name__=='__main__':
    try:
        mode=sys.argv[1] if len(sys.argv)>1 else 'status'
        if mode=='start':start()
        elif mode=='stop':stop()
        elif mode=='status':
            if STATE.exists():
                s=json.loads(STATE.read_text());print(json.dumps({'urls':s['urls'],'running':{n:bool((inspect(n) or {}).get('State',{}).get('Running')) for n in NAMES}},indent=2))
            else:print('No active saved session.')
        else:raise RuntimeError('Expected start, stop or status')
    except Exception as e:print(str(e),file=sys.stderr);sys.exit(1)
