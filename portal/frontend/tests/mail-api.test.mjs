import assert from "node:assert/strict"
import test from "node:test"
import { apiJson, ApiError } from "../src/mail/api.ts"

// Node 24+ strips TypeScript for this import. All requests are mocked: these tests
// never contact Mailpit, mark a real message as read, or delete email.
function reply(t, body, contentType = "text/plain", status = 200) {
  t.mock.method(globalThis, "fetch", async () => new Response(body, {
    status,
    headers: { "content-type": contentType },
  }))
}

const invalidResponse = error => error instanceof ApiError && error.status === 502

test("PUT messages accepts the Mailpit plain-text acknowledgement", async t => {
  reply(t, "ok")
  assert.equal(await apiJson("/api/v1/messages", { method: "PUT" }), undefined)
})

test("DELETE messages accepts acknowledgement with a charset and newline", async t => {
  reply(t, "ok\n", "text/plain; charset=utf-8")
  assert.equal(await apiJson("/api/v1/messages", { method: "DELETE" }), undefined)
})

test("GET messages rejects a plain-text acknowledgement instead of JSON", async t => {
  reply(t, "ok")
  await assert.rejects(apiJson("/api/v1/messages"), invalidResponse)
})

test("acknowledgements are not accepted for other resource paths", async t => {
  reply(t, "ok")
  await assert.rejects(apiJson("/api/v1/message/example", { method: "PUT" }), invalidResponse)
})

test("DELETE rejects unexpected plain-text responses", async t => {
  reply(t, "not-ok")
  await assert.rejects(apiJson("/api/v1/messages", { method: "DELETE" }), invalidResponse)
})

test("GET messages rejects an empty response body", async t => {
  reply(t, "")
  await assert.rejects(apiJson("/api/v1/messages"), invalidResponse)
})

test("GET messages returns parsed JSON", async t => {
  reply(t, '{"messages":[]}', "application/json")
  assert.deepEqual(await apiJson("/api/v1/messages"), { messages: [] })
})

test("mutations continue to accept valid JSON responses", async t => {
  reply(t, "true", "application/json")
  assert.equal(await apiJson("/api/v1/messages", { method: "PUT" }), true)
})

test("the acknowledgement exception requires the text/plain media type", async t => {
  reply(t, "ok", "application/json")
  await assert.rejects(apiJson("/api/v1/messages", { method: "PUT" }), invalidResponse)
})

test("Headers instances preserve the mutation Content-Type", async t => {
  t.mock.method(globalThis, "fetch", async (_url, options) => {
    assert.equal(options.headers.get("Content-Type"), "application/json")
    assert.equal(options.headers.get("Accept"), "application/json")
    return new Response("ok", { headers: { "content-type": "text/plain" } })
  })
  assert.equal(await apiJson("/api/v1/messages", {
    method: "PUT",
    headers: new Headers({ "Content-Type": "application/json" }),
  }), undefined)
})
