import type {storageApi} from "./api"

interface PersonalUploadSession {
  id: string | number
  chunk_size: number
  received: number
}

interface UploadOptions {
  signal: AbortSignal
  onProgress: (percent: number) => void
  request: typeof storageApi
}

interface UploadProgress {
  received: number
  size: number
}

const retryDelays = [250, 500, 1000]
const chunkLimit = 8 * 1024 * 1024

export function isTransientUploadError(cause: unknown): boolean {
  if (!(cause instanceof Error) || !("status" in cause)) return false
  const status = cause.status
  return status === null || status === 408 || status === 500 || status === 502 || status === 503 || status === 504
}

function waitForRetry(ms: number, signal: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    signal.throwIfAborted()
    const timer = setTimeout(() => {
      signal.removeEventListener("abort", cancel)
      resolve()
    }, ms)
    function cancel() {
      clearTimeout(timer)
      reject(signal.reason)
    }
    signal.addEventListener("abort", cancel, {once: true})
  })
}

async function retryStep<T>(signal: AbortSignal, action: (recovering: boolean) => Promise<T>): Promise<T> {
  for (let attempt = 0; ; attempt++) {
    signal.throwIfAborted()
    try {
      return await action(attempt > 0)
    } catch (cause) {
      if (signal.aborted || !isTransientUploadError(cause) || attempt >= retryDelays.length) throw cause
      await waitForRetry(retryDelays[attempt], signal)
    }
  }
}

export async function transferPersonalUpload(file: Blob, session: PersonalUploadSession, {signal, onProgress, request}: UploadOptions) {
  const url = `/api/uploads/${session.id}`
  const chunkSize = Math.min(session.chunk_size, chunkLimit)
  let offset = session.received
  const invalidProgress = "Tiến trình tải lên không khớp. Hãy tải lại tệp."
  if (!Number.isSafeInteger(chunkSize) || chunkSize <= 0 || !Number.isSafeInteger(offset) || offset < 0 || offset > file.size) {
    throw new Error(invalidProgress)
  }

  while (offset < file.size) {
    const end = Math.min(offset + chunkSize, file.size)
    const chunk = file.slice(offset, end)
    async function readOffset() {
      const progress = await request<UploadProgress>(url, {signal, cache: "no-store"})
      if (progress.size !== file.size || (progress.received !== offset && progress.received !== end)) {
        throw new Error(invalidProgress)
      }
      return progress.received
    }

    offset = await retryStep(signal, async recovering => {
      // Reconcile before repeating an operation whose response may have been lost.
      if (recovering && await readOffset() === end) return end
      try {
        const result = await request<UploadProgress>(url, {
          method: "PUT", body: chunk, signal,
          headers: {"Content-Type": "application/octet-stream", "Upload-Offset": String(offset)},
        })
        if (result.size !== file.size || result.received !== end) throw new Error(invalidProgress)
        return result.received
      } catch (cause) {
        // A prior request could finish between the progress check and the repeated PUT.
        if (recovering && cause instanceof Error && "status" in cause && cause.status === 409 && await readOffset() === end) return end
        throw cause
      }
    })
    onProgress(Math.round(offset / file.size * 100))
  }

  await retryStep(signal, () => request(`${url}/complete`, {method: "POST", signal}))
}
