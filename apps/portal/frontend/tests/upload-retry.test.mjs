import assert from "node:assert/strict"
import test from "node:test"
import {isTransientUploadError, transferPersonalUpload} from "../src/features/storage/uploadRetry.ts"

const error = (status) => Object.assign(new Error("test failure"), {status})
const file = new Blob(["abcdef"])
const session = {id: "test-id", chunk_size: 3, received: 0}

for (const firstChunkReachedServer of [false, true]) {
  test(`recovers a lost response when the chunk ${firstChunkReachedServer ? "arrived" : "never arrived"}`, async () => {
    const segments = []
    const progress = []
    let offset = 0
    let sent = 0
    let reads = 0
    let completions = 0

    await transferPersonalUpload(file, session, {
      signal: new AbortController().signal,
      onProgress: (percent) => progress.push(percent),
      request: async (url, options) => {
        if (options.method === "POST") {
          assert.match(url, /\/complete$/)
          completions++
          return {}
        }
        if (options.method !== "PUT") {
          reads++
          return {received: offset, size: file.size}
        }
        assert.equal(options.headers["Upload-Offset"], String(offset))
        sent++
        if (sent === 1 && !firstChunkReachedServer) throw error(null)
        segments.push(await options.body.text())
        offset += options.body.size
        if (sent === 1) throw error(null)
        return {received: offset, size: file.size}
      },
    })

    assert.equal(segments.join(""), "abcdef")
    assert.equal(sent, firstChunkReachedServer ? 2 : 3)
    assert.equal(reads, 1)
    assert.equal(completions, 1)
    assert.deepEqual(progress, [50, 100])
  })
}

test("retries completion on the same session after a lost response", async () => {
  const paths = []
  await transferPersonalUpload(file, {...session, received: file.size}, {
    signal: new AbortController().signal,
    onProgress: assert.fail,
    request: async (url, options) => {
      assert.equal(options.method, "POST")
      paths.push(url)
      if (paths.length === 1) throw error(503)
    },
  })
  assert.deepEqual(paths, ["/api/uploads/test-id/complete", "/api/uploads/test-id/complete"])
})

test("reconciles a prior write that completes between reading progress and repeating PUT", async () => {
  const calls = []
  const progress = []
  let offset = 0
  const smallFile = file.slice(0, 3)
  await transferPersonalUpload(smallFile, session, {
    signal: new AbortController().signal,
    onProgress: percent => progress.push(percent),
    request: async (_url, options) => {
      calls.push(options.method ?? "GET")
      if (calls.length === 1) throw error(null)
      if (calls.length === 3) {
        offset = 3
        throw error(409)
      }
      return {received: offset, size: smallFile.size}
    },
  })
  assert.deepEqual(calls, ["PUT", "GET", "PUT", "GET", "POST"])
  assert.deepEqual(progress, [100])
})

test("preserves the transient failure after the bounded retries", async () => {
  const methods = []
  const failure = error(503)
  await assert.rejects(transferPersonalUpload(file, session, {
    signal: new AbortController().signal,
    onProgress: assert.fail,
    request: async (_url, options) => {
      methods.push(options.method ?? "GET")
      throw failure
    },
  }), failure)
  assert.deepEqual(methods, ["PUT", "GET", "GET", "GET"])
  assert.equal(isTransientUploadError(failure), true)
})

test("does not retry permanent errors", async () => {
  for (const status of [401, 403, 404, 409, 413, 507]) {
    let requests = 0
    const failure = error(status)
    assert.equal(isTransientUploadError(failure), false)
    await assert.rejects(transferPersonalUpload(file, session, {
      signal: new AbortController().signal,
      onProgress: assert.fail,
      request: async () => {
        requests++
        throw failure
      },
    }), failure)
    assert.equal(requests, 1)
  }
})

test("stops the retry delay when the user cancels", async () => {
  const controller = new AbortController()
  let requests = 0
  await assert.rejects(transferPersonalUpload(file, session, {
    signal: controller.signal,
    onProgress: assert.fail,
    request: async () => {
      requests++
      setTimeout(() => controller.abort(), 5)
      throw error(null)
    },
  }), {name: "AbortError"})
  assert.equal(requests, 1)
})
