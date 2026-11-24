import { useEffect, useState } from "react"
import { Notice, bytes } from "@/shared/ui"

type Dependency = "ok" | "unavailable"
type Storage = { status: "unavailable" } | { status: "ok" | "low" | "critical"; free_bytes: number; total_bytes: number }
type Budget = { status: "unavailable" } | {
  status: "ok" | "low" | "full" | "unlimited"
  used_bytes: number
  reserved_bytes: number
  available_bytes: number | null
  pool_limit_bytes: number
}

interface Diagnostics {
  database: Dependency
  storage: Storage
  budget: Budget
}

export function AdminStorageCapacity() {
  const [report, setReport] = useState<Diagnostics | "error" | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    void fetch("/admin/diagnostics", { signal: controller.signal, credentials: "same-origin" })
      .then(async response => {
        if (!response.ok) throw new Error("Diagnostics unavailable")
        const result = await response.json() as Diagnostics
        if (!controller.signal.aborted) setReport(result)
      })
      .catch(() => {
        if (!controller.signal.aborted) setReport("error")
      })
    return () => controller.abort()
  }, [])

  if (report === null) return <p role="status" className="text-sm text-muted-foreground">Đang kiểm tra PostgreSQL và lưu trữ…</p>
  if (report === "error") return <Notice kind="error" title="Chưa đọc được tình trạng lưu trữ">Tải lại trang để kiểm tra lại.</Notice>

  const { database, budget, storage } = report
  return (
    <div className="grid min-w-0 gap-4 lg:grid-cols-2">
      <Notice kind={budget.status === "ok" || budget.status === "unlimited" ? "info" : "error"} title="Ngân sách lưu trữ chung">
        {budget.status === "unavailable" ? <p>Chưa đọc được số liệu ngân sách.</p> : <>
          <p>Đã dùng {bytes(budget.used_bytes)} · Đang giữ chỗ {bytes(budget.reserved_bytes)}</p>
          {budget.available_bytes === null ? <p>Chưa đặt giới hạn tổng.</p> : <p>Còn {bytes(budget.available_bytes)} trong tổng {bytes(budget.pool_limit_bytes)}.</p>}
          {budget.status === "low" && <p>Ngân sách gần đầy.</p>}
          {budget.status === "full" && <p>Đã hết ngân sách lưu trữ.</p>}
        </>}
      </Notice>
      <Notice kind={storage.status === "ok" && database === "ok" ? "info" : "error"} title="Ổ lưu trữ Portal">
        <p>PostgreSQL {database === "ok" ? "đang phản hồi." : "chưa phản hồi."}</p>
        {storage.status === "unavailable" ? <p>Portal chưa truy cập được ổ lưu trữ.</p> : <>
          <p>Trống {bytes(storage.free_bytes)} trên {bytes(storage.total_bytes)} trong môi trường chạy Portal.</p>
          {storage.status === "low" && <p>Ổ lưu trữ gần đầy.</p>}
          {storage.status === "critical" && <p>Ổ lưu trữ đã chạm ngưỡng dự phòng tải lên.</p>}
        </>}
      </Notice>
    </div>
  )
}
