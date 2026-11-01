import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
const original = fs.readFileSync(process.argv[2] || new URL('./fixture/viewer-main.mjs', import.meta.url), 'utf8');
const oldGuard = 'OCA?.Files?.Sidebar&&OCA.Files.Sidebar.setFullScreenMode(!1)';
const newGuard = 'typeof OCA?.Files?.Sidebar?.setFullScreenMode==="function"&&OCA.Files.Sidebar.setFullScreenMode(!1)';
const oldOpen = 'OCA?.Files?.Sidebar&&await OCA.Files.Sidebar.open(this.sidebarOpenFilePath)';
const newOpen = 'typeof OCA?.Files?.Sidebar?.open==="function"&&await OCA.Files.Sidebar.open(this.sidebarOpenFilePath)';
assert.equal(original.split(oldGuard).length, 2);
const body = original.replace(oldGuard, newGuard).match(/close\(\)\{(OCA\.Viewer\.close\(\)[\s\S]*?)\},keyboardDeleteFile/)[1];
const close = new Function('OCA', body);
for (const [name, sidebar, expected] of [
  ['missing Files', undefined, []],
  ['missing Sidebar', null, []],
  ['missing method', {}, []],
  ['non-callable method', { setFullScreenMode: true }, []],
  ['callable method', 'callable', ['sidebar:false']],
]) {
  for (const fullscreen of [false, true]) {
    test(`${name}; fullscreen=${fullscreen}`, () => {
      const calls = [];
      const Sidebar = sidebar === 'callable' ? { setFullScreenMode(value) { assert.equal(this, Sidebar); calls.push(`sidebar:${value}`); } } : sidebar;
      const OCA = { Viewer: { close() { calls.push('viewer'); } }, ...(sidebar !== undefined ? { Files: { Sidebar } } : {}) };
      close.call({ isFullscreenMode: fullscreen, exitFullscreen() { calls.push('exit'); } }, OCA);
      assert.deepEqual(calls, ['viewer', ...expected, ...(fullscreen ? ['exit'] : [])]);
    });
  }
}
test('original reproduces exception after viewer.close and prevents fullscreen exit', () => {
  const oldBody = original.match(/close\(\)\{(OCA\.Viewer\.close\(\)[\s\S]*?)\},keyboardDeleteFile/)[1];
  let viewerClosed = false, fullscreenExited = false;
  assert.throws(() => new Function('OCA', oldBody).call({ isFullscreenMode: true, exitFullscreen() { fullscreenExited = true; } }, { Viewer: { close() { viewerClosed = true; } }, Files: { Sidebar: {} } }), TypeError);
  assert.equal(viewerClosed, true);
  assert.equal(fullscreenExited, false);
});
const AsyncFunction = Object.getPrototypeOf(async function() {}).constructor;
const showBody = original.replace(oldOpen, newOpen).match(/async showSidebar\(\)\{([\s\S]*?)\},handleAppSidebarOpen/)[1];
const showSidebar = new AsyncFunction('OCA', 'L', 'C', 'f', 'V', showBody);
for (const [name, sidebar] of [['missing Files', undefined], ['missing Sidebar', null], ['missing method', {}], ['non-callable method', { open: true }], ['legacy callable', 'callable']]) {
  test(`showSidebar ${name}: real node event retained before legacy fallback`, async () => {
    const calls = [];
    const Sidebar = sidebar === 'callable' ? { async open(path) { assert.equal(this, Sidebar); calls.push(['legacy', path]); } } : sidebar;
    const OCA = sidebar === undefined ? {} : { Files: { Sidebar } };
    const context = { enableSidebar: true, sidebarOpenFilePath: '/QA.txt', currentFile: { filename: '/QA.txt', fileid: 44, displayname: 'QA.txt', mime: 'text/plain', lastmod: '2026-11-01', ownerId: 'qa' } };
    await showSidebar.call(context, OCA, class Node { constructor(data) { Object.assign(this, data); } }, 'http://nextcloud/remote.php/dav', () => '/files/qa', (name, node) => { assert.equal(name, 'viewer:sidebar:open'); assert.equal(node.id, 44); assert.equal(node.source, 'http://nextcloud/remote.php/dav/files/qa/QA.txt'); calls.push(['event']); });
    assert.deepEqual(calls, sidebar === 'callable' ? [['event'], ['legacy', '/QA.txt']] : [['event']]);
  });
}
test('showSidebar disabled does not open sidebar', async () => {
  await showSidebar.call({ enableSidebar: false }, {}, null, '', null, () => assert.fail('event should not emit'));
});
