#!/usr/bin/env python3
"""Pinned, reversible Viewer 8.0.0 close guard. Default is read-only dry-run."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PATCHDIR = ROOT / 'apps' / 'nextcloud' / 'patches' / 'viewer-close'
ORIGINAL = {
    'js/viewer-main.mjs': '097a4ad44b6a50174f0f03d3ac71b9dc5dd5f3d957f4753692d32054e1bed890',
    'js/viewer-main.mjs.map': 'a09e70e305b55b2ffc65222669dedaa4219fc46cf794807efd42f2d2d4141446',
    'lib/Listener/LoadViewerScript.php': 'a2aab6c4fbb6f40fb33075f151522181c4989e4c078e3bc41609837f12711290',
    'appinfo/info.xml': '179bad2743af840e18606f5bc0ff839f75bb7c023fcf82b549bbeb031d76f6bb',
}
OLD = b'OCA?.Files?.Sidebar&&OCA.Files.Sidebar.setFullScreenMode(!1)'
NEW = b'typeof OCA?.Files?.Sidebar?.setFullScreenMode==="function"&&OCA.Files.Sidebar.setFullScreenMode(!1)'
OLD_OPEN = b'OCA?.Files?.Sidebar&&await OCA.Files.Sidebar.open(this.sidebarOpenFilePath)'
NEW_OPEN = b'typeof OCA?.Files?.Sidebar?.open==="function"&&await OCA.Files.Sidebar.open(this.sidebarOpenFilePath)'
LOAD = b"Util::addScript(Application::APP_ID, 'viewer-main', 'files');"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def docker(*args, data=None):
    return subprocess.run(['docker', 'compose', 'exec', '-T', '-u', 'root', 'nextcloud', *args],
                          cwd=ROOT, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout


def read(rel):
    return docker('cat', '/var/www/html/apps/viewer/' + rel)


def transform(module, loader):
    if module.count(OLD) != 1 or module.count(OLD_OPEN) != 1 or loader.count(LOAD) != 1:
        raise RuntimeError('Expected exact close guard and loader once; refusing patch')
    patched = module.replace(OLD, NEW).replace(OLD_OPEN, NEW_OPEN)
    # Do not attach the original map to changed columns. Original module/map stay intact.
    patched = b'\n'.join(line for line in patched.split(b'\n') if b'//# sourceMappingURL=' not in line)
    stem = 'viewer-main-cloudbox-' + sha(patched)[:12]
    return patched, loader.replace(LOAD, LOAD.replace(b"'viewer-main'", ("'" + stem + "'").encode())), stem


def mutate(rel, data=None):
    # No arbitrary shell command/path input. Writes atomically under the app only.
    if rel not in {'lib/Listener/LoadViewerScript.php'} and not (
        rel.startswith('js/viewer-main-cloudbox-') and rel.endswith('.mjs') and '/' not in rel[3:]
    ):
        raise RuntimeError('Unexpected target')
    payload = json.dumps({'path': '/var/www/html/apps/viewer/' + rel,
                          'data': base64.b64encode(data).decode() if data is not None else None}).encode()
    code = '''$x=json_decode(stream_get_contents(STDIN),true,512,JSON_THROW_ON_ERROR);$p=$x['path'];
if($x['data']===null){if(is_file($p)&&!unlink($p)){throw new Exception('unlink failed');}}
else{$t=$p.'.cloudbox-tmp';if(file_put_contents($t,base64_decode($x['data'],true))===false){throw new Exception('write failed');}chmod($t,0644);chown($t,'www-data');chgrp($t,'www-data');if(!rename($t,$p)){throw new Exception('rename failed');}}'''
    docker('php', '-r', code, data=payload)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--apply', action='store_true')
    g.add_argument('--restore', action='store_true')
    args = ap.parse_args()
    original = {}
    for rel, digest in ORIGINAL.items():
        if rel == 'lib/Listener/LoadViewerScript.php':
            continue
        original[rel] = read(rel)
        if sha(original[rel]) != digest:
            raise RuntimeError('Upstream changed; refusing operation: ' + rel)
    loader = read('lib/Listener/LoadViewerScript.php')
    saved_loader = PATCHDIR / 'backup' / 'LoadViewerScript.php'
    if sha(loader) == ORIGINAL['lib/Listener/LoadViewerScript.php']:
        base_loader = loader
    else:
        if not saved_loader.is_file():
            raise RuntimeError('Unknown loader and no verified backup; refusing')
        base_loader = saved_loader.read_bytes()
        if sha(base_loader) != ORIGINAL['lib/Listener/LoadViewerScript.php']:
            raise RuntimeError('Backup loader hash mismatch')
    module, patched_loader, stem = transform(original['js/viewer-main.mjs'], base_loader)
    target = 'js/' + stem + '.mjs'
    state = 'original' if loader == base_loader else 'patched' if loader == patched_loader else 'unknown'
    if state == 'unknown':
        raise RuntimeError('Loader has other changes; refusing overwrite')
    if state == 'patched' and read(target) != module:
        raise RuntimeError('Patched module hash mismatch')
    if args.apply and state == 'original':
        exists = docker('php', '-r', "echo is_file('/var/www/html/apps/viewer/" + target + "') ? '1' : '0';")
        if exists == b'1' and read(target) != module:
            raise RuntimeError('Target already contains unrelated bytes; refusing overwrite')
        backup = PATCHDIR / 'backup'
        backup.mkdir(parents=True, exist_ok=True)
        for rel, data in {**original, 'lib/Listener/LoadViewerScript.php': base_loader}.items():
            dest = backup / Path(rel).name
            if dest.exists() and dest.read_bytes() != data:
                raise RuntimeError('Backup collision: ' + str(dest))
            dest.write_bytes(data)
        source_map = json.loads(original['js/viewer-main.mjs.map'])
        source = next(c for s, c in zip(source_map['sources'], source_map['sourcesContent']) if s.endswith('/src/views/Viewer.vue'))
        (backup / 'Viewer.vue.original').write_text(source, encoding='utf8')
        mutate(target, module)
        mutate('lib/Listener/LoadViewerScript.php', patched_loader)
        if read(target) != module or read('lib/Listener/LoadViewerScript.php') != patched_loader:
            raise RuntimeError('Post-write verification failed')
        state = 'patched'
    elif args.restore and state == 'patched':
        mutate('lib/Listener/LoadViewerScript.php', base_loader)
        mutate(target)
        if read('lib/Listener/LoadViewerScript.php') != base_loader:
            raise RuntimeError('Restore verification failed')
        state = 'original'
    report = {'state': state, 'mode': 'apply' if args.apply else 'restore' if args.restore else 'dry-run',
              'original_sha256': ORIGINAL, 'module': target, 'module_sha256': sha(module),
              'loader_sha256': sha(patched_loader), 'stale_sourcemap_attached': False,
              'expected_integrity': 'Viewer app: modified lib/Listener/LoadViewerScript.php and extra hashed mjs. Core unchanged. Do not disable integrity checks.'}
    if args.apply or args.restore:
        PATCHDIR.mkdir(parents=True, exist_ok=True)
        (PATCHDIR / 'state.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
