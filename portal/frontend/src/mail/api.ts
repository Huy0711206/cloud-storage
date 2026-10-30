export class ApiError extends Error {
  readonly status: number
  constructor(message: string, status: number) { super(message); this.name = "ApiError"; this.status = status }
}

export async function apiJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  if (!path.startsWith("/api/v1/")) throw new ApiError("Địa chỉ hộp thư không hợp lệ.", 400)
  const method = (options.method || "GET").toUpperCase()
  const messagesMutation = (method === "PUT" || method === "DELETE") && path.split("?")[0] === "/api/v1/messages"
  const headers = new Headers(options.headers)
  headers.set("Accept", "application/json")
  const controller = new AbortController()
  const external = options.signal
  const abort = () => controller.abort(external?.reason)
  if (external?.aborted) abort()
  else external?.addEventListener("abort", abort, { once: true })
  const timeout = setTimeout(() => controller.abort(new DOMException("Timeout", "TimeoutError")), 15000)
  try {
    const response = await fetch(path, { ...options, credentials: "same-origin", cache: "no-store", redirect: "error", signal: controller.signal, headers })
    if (!response.ok) {
      const message = response.status === 404 ? "Thư này đã bị xóa hoặc không còn tồn tại." : response.status === 400 ? "Yêu cầu chưa hợp lệ. Hãy tải lại rồi thử lại." : "Chưa kết nối được với hộp thư. Hãy thử lại sau ít phút."
      throw new ApiError(message, response.status)
    }
    if (response.status === 204 && messagesMutation) return undefined as T
    const text = await response.text()
    if (messagesMutation && !text.trim()) return undefined as T
    const mime = (response.headers.get("content-type") || "").split(";")[0].trim().toLowerCase()
    if (messagesMutation && mime === "text/plain" && text.trim() === "ok") return undefined as T
    try { return JSON.parse(text) as T } catch { throw new ApiError("Hộp thư trả về dữ liệu chưa hợp lệ. Hãy thử tải lại.", 502) }
  } catch (error) {
    if (error instanceof ApiError || external?.aborted) throw error
    throw new ApiError(controller.signal.aborted ? "Hộp thư phản hồi quá lâu. Hãy thử lại." : "Chưa kết nối được với hộp thư. Hãy kiểm tra kết nối rồi thử lại.", 503)
  } finally {
    clearTimeout(timeout)
    external?.removeEventListener("abort", abort)
  }
}
