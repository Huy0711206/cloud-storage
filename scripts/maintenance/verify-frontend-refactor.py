"""Exact declaration/CSS proof against immutable pre-refactor ZIP; no app execution."""
from pathlib import Path
import re,json,zipfile,hashlib
ROOT=Path(__file__).resolve().parents[2]
FRONT=ROOT/'apps/portal/frontend'
mapping=json.loads((ROOT/'artifacts/qa/refactor-frontend-map.json').read_text(encoding='utf-8'))
archive=zipfile.ZipFile(ROOT/'.unified-backup/refactor-20261101/source.zip')
def norm(s):return s.replace('\r\n','\n').strip()
def original(rel):return archive.read('portal/frontend/'+rel).decode('utf-8-sig')
def current(rel):return (FRONT/rel).read_text(encoding='utf-8-sig')
def funcs(text):
 matches=list(re.finditer(r'^(?:export(?: default)? )?function (\w+)\(',text,re.M))
 return {m.group(1):text[m.start():matches[i+1].start()if i+1<len(matches)else len(text)]for i,m in enumerate(matches)}
def decl(s):return norm(re.sub(r'^export(?: default)? ','',s))
checks=[]
for split in mapping['function_splits']:
 before=funcs(original(split['old']));after=funcs(current(split['new']))
 for name in split['functions']:
  assert decl(before[name])==decl(after[name]),'Split declaration differs: '+name
  checks.append({'kind':'exact-function-declaration','function':name,'old':split['old'],'new':split['new'],'same_except_export':True})
for move in mapping['moves']:
 old,new=move['old'],move['new']
 if old.endswith('.css'):
  assert norm(original(old))==norm(current(new)),'CSS changed: '+old
  checks.append({'kind':'exact-css-declarations','old':old,'new':new,'same':True})
 if '/fonts/' in old:
  assert archive.read('portal/frontend/'+old)==(FRONT/new).read_bytes()
  checks.append({'kind':'exact-font-bytes','old':old,'new':new,'same':True})
locks={}
for name in ['package.json','pnpm-lock.yaml']:
 before=archive.read('portal/frontend/'+name);after=(FRONT/name).read_bytes();assert before==after
 locks[name]=hashlib.sha256(after).hexdigest()
out={'comparison':'Exact function declarations including JSX/form/action literals after normalizing CRLF and only adding export; exact CSS contents/font bytes. Imports and moved module composition are typechecked/built separately. This is not proof of all runtime behavior.','checks':checks,'function_declarations_equal':sum(c['kind']=='exact-function-declaration'for c in checks),'css_files_equal':sum(c['kind']=='exact-css-declarations'for c in checks),'font_files_equal':sum(c['kind']=='exact-font-bytes'for c in checks),'dependency_files_byte_identical':locks,'manifest_entry':'src/main.tsx'}
(ROOT/'artifacts/qa/refactor-frontend-source.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in out.items()if k!='checks'},indent=2))
