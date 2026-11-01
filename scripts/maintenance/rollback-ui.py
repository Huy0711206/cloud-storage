"""Revert or reapply UI images/theme without touching data, domains or published ports.

By default validate and explain. Use --apply to execute; --new re-applies the saved new UI.
"""
from pathlib import Path
import argparse,json,subprocess

ROOT=Path(__file__).resolve().parents[2]
def docker(*args,check=True):
 r=subprocess.run(['docker',*args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
 if check and r.returncode:raise RuntimeError('Docker action failed: '+' '.join(args[:4])+' '+r.stderr[-400:])
 return r.stdout.strip()
def occ(*args):return docker('compose','exec','-u','www-data','-T','nextcloud','php','occ',*args)
def current_brand():
 return {k:occ('config:app:get','theming',k,'--default-value=__CLOUDBOX_MISSING__') for k in ['name','primary_color','background_color','backgroundMime']}
def set_brand(values):
 # Keep current public URL, trusted proxy, user preferences and all other config.
 for key,value in values.items():
  if key=='backgroundMime':
   if value=='__CLOUDBOX_MISSING__':occ('config:app:delete','theming',key)
   else:occ('config:app:set','theming',key,'--value='+value)
  elif value=='__CLOUDBOX_MISSING__':occ('theming:config',key,'--reset')
  else:occ('theming:config',key,value)
def migrate_paths(compose):
 # Adapt old saved Compose only in memory. Original private backups remain immutable.
 for old,new in [('./portal','./apps/portal'),('./mail-ui','./apps/mail'),('./nextcloud/cloudbox_theme','./apps/nextcloud/cloudbox_theme'),('./db-init','./infrastructure/docker/db-init')]:
  compose=compose.replace(old,new)
 return compose


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--apply',action='store_true');parser.add_argument('--new',action='store_true')
 args=parser.parse_args()
 b=Path((ROOT/'.unified-backup/current.txt').read_text(encoding='utf-8').strip())
 assert b.is_relative_to(ROOT/'.unified-backup') and (b/'theming-original.json').exists()
 original=(ROOT/'docker-compose.yml').read_text(encoding='utf-8-sig')
 state=ROOT/'.runtime/ui-rollback';state.mkdir(parents=True,exist_ok=True)
 if args.new:
  saved=state if (state/'unified-final-compose.yml').exists() else b
  candidate=migrate_paths((saved/'unified-final-compose.yml').read_text(encoding='utf-8'))
  brand=json.loads((saved/'theming-unified.json').read_text(encoding='utf-8'))
 else:
  assert '  portal-preview:' not in original,'Finish port consolidation first.'
  assert 'image: cloud-storage-mailpit-unified:1.32.0' in original,'UI is already rolled back or Compose was changed; inspect before proceeding.'
  for image in ['cloud-storage-portal:cloudbox-rollback','axllent/mailpit:cloudbox-base-1.32.0']:docker('image','inspect',image)
  candidate=original.replace('    build: ./apps/portal','    image: cloud-storage-portal:cloudbox-rollback\n    pull_policy: never')
  candidate=candidate.replace('    image: cloud-storage-mailpit-unified:1.32.0','    image: axllent/mailpit:cloudbox-base-1.32.0\n    pull_policy: never').replace('    build: ./apps/mail\n','')
  brand=json.loads((b/'theming-original.json').read_text(encoding='utf-8'))
 temp=state/'rollback-candidate.yml';temp.write_text(candidate,encoding='utf-8')
 docker('compose','--project-directory',str(ROOT),'-f',str(temp),'config','--quiet')
 print(('Reapply the saved new UIs' if args.new else 'Restore the original portal/Mailpit UI images and disable the Nextcloud skin')+'.')
 print('Keep exactly 8000 / 8080 / 8025, current online routing, all database/file/mail volumes and accounts.')
 if not args.apply:
  print('Configuration validated only. Run with --apply to execute. No application changed.');return
 if not args.new:
  (state/'unified-final-compose.yml').write_text(original,encoding='utf-8')
  (state/'theming-unified.json').write_text(json.dumps(current_brand(),indent=2),encoding='utf-8')
 (ROOT/'docker-compose.yml').write_text(candidate,encoding='utf-8')
 set_brand(brand)
 occ('app:enable' if args.new else 'app:disable','cloudbox_theme')
 compose=['compose','-f','docker-compose.yml']
 if (ROOT/'.online/compose.json').exists():compose+=['-f','.online/compose.json']
 docker(*compose,'up','-d','--no-deps','--wait','portal','mailpit')
 print('UI transition complete. No volume deleted and no archived preview port opened.')
if __name__=='__main__':main()
