"""Read-only source ZIP/current AST equivalence check for the reviewed backend relocation.

No app imports, database, configuration values, or network access. The original ZIP
is never rewritten. Source SHA checks cover imports/path anchors outside functions.
"""
from pathlib import Path
import ast,hashlib,json,zipfile

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'apps/portal/backend'
report=json.loads((ROOT/'artifacts/qa/refactor-backend-semantics.json').read_text(encoding='utf-8'))
archive=zipfile.ZipFile(ROOT/report['baseline_zip'])

def extract(source,name):
 node=next(n for n in ast.parse(source).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and n.name==name)
 first=min([node.lineno]+[d.lineno for d in getattr(node,'decorator_list',[])])-1
 return ''.join(source.splitlines(True)[first:node.end_lineno])

def dump(source):
 return ast.dump(ast.parse(source),include_attributes=False)

def routes(source):
 tree=ast.parse(source);prefix='';result=[]
 for n in tree.body:
  if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='APIRouter':
   prefix=next((ast.literal_eval(k.value)for k in n.value.keywords if k.arg=='prefix'),'')
 for n in tree.body:
  if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
  for d in n.decorator_list:
   if isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute) and isinstance(d.func.value,ast.Name) and d.func.value.id in ('router','app') and d.func.attr in ('get','post','put','patch','delete','head','options'):
    result.append((d.func.attr,prefix+ast.literal_eval(d.args[0])))
 return result

count=0;before_routes=[];after_routes=[]
seen_old=set();seen_new=set()
for item in report['module_map']:
 oldbytes=archive.read(item['old']);newbytes=(BASE/item['new']).read_bytes()
 assert hashlib.sha256(oldbytes).hexdigest()==report['original_module_sha256'][item['old']], 'Original ZIP bytes changed: '+item['old']
 assert hashlib.sha256(newbytes).hexdigest()==report['reviewed_new_module_sha256'][item['new']], 'Reviewed new source changed; inspect before accepting: '+item['new']
 before=oldbytes.decode('utf-8-sig');after=newbytes.decode('utf-8-sig')
 for name in item['definitions']:
  a=extract(before,name);b=extract(after,name)
  for oldref,newref in item['reference_renames'].items():b=b.replace(newref,oldref)
  assert dump(a)==dump(b), 'Function/class AST differs: '+name
  count+=1
 if item['old'] not in seen_old:before_routes.extend(routes(before));seen_old.add(item['old'])
 if item['new'] not in seen_new:after_routes.extend(routes(after));seen_new.add(item['new'])
assert sorted(before_routes)==sorted(after_routes),'HTTP route method/path contract changed'
assert len(before_routes)==len(set(before_routes)),'Duplicate original route'
assert len(after_routes)==len(set(after_routes)),'Duplicate new route'

def assignment(source,name):
 for node in ast.parse(source).body:
  if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name)and t.id==name for t in node.targets):
   return ast.dump(node,include_attributes=False)
 raise AssertionError('Missing original module binding: '+name)

assignment_count=0
for item in report['module_assignment_map']:
 before=archive.read(item['old']).decode('utf-8-sig');after=(BASE/item['new']).read_text(encoding='utf-8-sig')
 for name in item['names']:
  assert assignment(before,name)==assignment(after,name),'Module assignment AST changed: '+name
  assignment_count+=1

# A function body can be unchanged while a split drops its global constant/import.
# Check symbol bindings without importing application code/configuration.
import builtins,symtable
for path in (BASE/'app').rglob('*.py'):
 source=path.read_text(encoding='utf-8-sig');top=symtable.symtable(source,str(path),'exec')
 known={s.get_name()for s in top.get_symbols()if s.is_assigned()or s.is_imported()or s.is_namespace()}|set(dir(builtins))|{'__file__','__name__','__package__','__annotations__'}
 def check_symbols(table):
  missing=[s.get_name()for s in table.get_symbols()if s.is_referenced()and s.is_global()and s.get_name()not in known]
  assert not missing,'Unbound global references in '+str(path.relative_to(BASE))+': '+str(missing)
  for child in table.get_children():check_symbols(child)
 check_symbols(top)
print('PASS '+str(assignment_count)+' original module-level assignments preserve AST; production modules have no unbound global references.')

print('PASS '+str(count)+' original functions/classes preserve AST after declared reference relocation; '+str(len(before_routes))+' exact HTTP method/path pairs preserved; original ZIP and reviewed source hashes match. No application imports or database writes.')
