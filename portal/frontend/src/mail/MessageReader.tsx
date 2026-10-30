import { useEffect, useMemo, useRef, useState } from "react"
import { ArrowLeft, ChevronDown, Download, FileText, Mail, MailOpen, Paperclip, RefreshCw, ShieldCheck, Trash2 } from "lucide-react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Skeleton } from "@/components/ui/skeleton"
import { Empty, EmptyHeader, EmptyDescription, EmptyTitle } from "@/components/ui/empty"
import { apiJson, ApiError } from "./api"
import { buildEmailDocument, normalizeContentId, referencedContentIds } from "./email-frame"
import type { MailAddress, MailDetail } from "./types"
import "./reader.css"

export interface MessageReaderProps {
  message: MailDetail; read: boolean; busy: boolean
  onBack: () => void; onToggleRead: () => void; onDelete: () => void
}
type ReaderView = "html" | "text" | "headers" | "source"

export const addressText = (address?: MailAddress) => address ? address.Name ? `${address.Name} <${address.Address}>` : address.Address : "Không rõ người gửi"
function fileSize(bytes: number) { return bytes < 1024 ? `${bytes} B` : bytes < 1024 ** 2 ? `${new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 1 }).format(bytes / 1024)} KB` : `${new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 1 }).format(bytes / 1024 ** 2)} MB` }
function messageDate(value: string) { const date = new Date(value); return Number.isNaN(date.getTime()) ? "Chưa có thời gian" : new Intl.DateTimeFormat("vi-VN", { dateStyle: "long", timeStyle: "short" }).format(date) }

export function MessageReader(props: MessageReaderProps) { return <ReaderContent key={props.message.ID} {...props} /> }

function ReaderContent({ message, read, busy, onBack, onToggleRead, onDelete }: MessageReaderProps) {
  const [view, setView] = useState<ReaderView>(message.HTML ? "html" : "text")
  const [headers, setHeaders] = useState<Record<string, string[]> | null>(null)
  const [source, setSource] = useState<string | null>(null)
  const [resourceLoading, setResourceLoading] = useState(false)
  const [resourceError, setResourceError] = useState("")
  const [retry, setRetry] = useState(0)
  const [cidSources, setCidSources] = useState<Record<string, string>>({})
  const title = useRef<HTMLHeadingElement>(null)
  const base = `/api/v1/message/${encodeURIComponent(message.ID)}`

  useEffect(() => { title.current?.focus({ preventScroll: true }) }, [message.ID])

  useEffect(() => {
    setResourceLoading(false); setResourceError("")
    if (view !== "headers" && view !== "source") return
    if ((view === "headers" && headers !== null) || (view === "source" && source !== null)) return
    const controller = new AbortController()
    let timedOut = false
    const timeout = setTimeout(() => { timedOut = true; controller.abort() }, 15000)
    setResourceLoading(true); setResourceError("")
    const request = async () => {
      try {
        if (view === "headers") setHeaders(await apiJson<Record<string, string[]>>(`${base}/headers`, { signal: controller.signal }))
        else {
          const response = await fetch(`${base}/raw`, { credentials: "same-origin", cache: "no-store", redirect: "error", signal: controller.signal })
          if (!response.ok) throw new ApiError(response.status === 404 ? "Thư này không còn tồn tại." : "Chưa tải được nguồn thư.", response.status)
          setSource(await response.text())
        }
      } catch (error) {
        if (!controller.signal.aborted || timedOut) setResourceError(timedOut ? "Hộp thư phản hồi quá lâu. Hãy thử lại." : error instanceof Error ? error.message : "Chưa tải được nội dung. Hãy thử lại.")
      } finally {
        clearTimeout(timeout)
        if (!controller.signal.aborted || timedOut) setResourceLoading(false)
      }
    }
    void request()
    return () => { clearTimeout(timeout); controller.abort() }
    // Cached resources are scoped to this message; entering another view cancels in-flight work.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, base, retry])

  useEffect(() => {
    const controller = new AbortController()
    let disposed = false
    const timeout = setTimeout(() => controller.abort(), 15000)
    const ids = referencedContentIds(message.HTML || "")
    const parts = [...new Map([...(message.Inline || []), ...(message.Attachments || [])].map(part => [part.PartID, part])).values()]
    const inline = parts.filter(part => ids.has(normalizeContentId(part.ContentID)) && /^image\/(png|jpeg|gif|webp|avif)$/i.test(part.ContentType.split(";")[0].trim()) && part.Size <= 10 * 1024 * 1024)
    void Promise.allSettled(inline.map(async part => {
      const response = await fetch(`${base}/part/${encodeURIComponent(part.PartID)}`, { credentials: "same-origin", cache: "no-store", redirect: "error", signal: controller.signal })
      if (!response.ok) return null
      const length = Number(response.headers.get("content-length") || 0)
      if (length > 10 * 1024 * 1024) return null
      const content = await response.arrayBuffer()
      if (controller.signal.aborted || content.byteLength > 10 * 1024 * 1024) return null
      const mime = part.ContentType.split(";")[0].trim().toLowerCase()
      // Data URLs remain readable inside an opaque-origin sandbox without granting same-origin access.
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader()
        const abort = () => reader.abort()
        const cleanup = () => controller.signal.removeEventListener("abort", abort)
        reader.onload = () => { cleanup(); typeof reader.result === "string" ? resolve(reader.result) : reject(new Error("Invalid inline image")) }
        reader.onerror = () => { cleanup(); reject(reader.error || new Error("Inline image could not be read")) }
        reader.onabort = () => { cleanup(); reject(new DOMException("Aborted", "AbortError")) }
        controller.signal.addEventListener("abort", abort, { once: true })
        reader.readAsDataURL(new Blob([content], { type: mime }))
      })
      return [normalizeContentId(part.ContentID), dataUrl] as const
    })).then(results => {
      clearTimeout(timeout)
      if (disposed) return
      const sources: Record<string, string> = {}
      for (const result of results) if (result.status === "fulfilled" && result.value) sources[result.value[0]] = result.value[1]
      setCidSources(sources)
    })
    return () => { disposed = true; clearTimeout(timeout); controller.abort() }
  }, [message.HTML, message.Inline, message.Attachments, base])

  const htmlDocument = useMemo(() => buildEmailDocument(message.HTML || "", cidSources), [message.HTML, cidSources])
  const sender = message.From?.Name || message.From?.Address || "?"
  const initials = sender.split(/\s+/).filter(Boolean).slice(0, 2).map(word => word[0]).join("").toUpperCase()

  return <article className="mail-reader" aria-labelledby="mail-reader-subject">
    <div className="mail-reader-toolbar">
      <Button className="mail-reader-back" variant="ghost" onClick={onBack}><ArrowLeft data-icon="inline-start" aria-hidden />Hộp thư</Button>
      <div className="mail-reader-actions">
        <Button variant="ghost" size="icon" disabled={busy} onClick={onToggleRead} aria-label={read ? "Đánh dấu thư chưa đọc" : "Đánh dấu thư đã đọc"} title={read ? "Đánh dấu chưa đọc" : "Đánh dấu đã đọc"}>{read ? <Mail aria-hidden /> : <MailOpen aria-hidden />}</Button>
        <Button variant="ghost" size="icon" asChild><a href={`${base}/raw?dl=1`} download aria-label="Tải thư gốc định dạng EML" title="Tải thư gốc"><Download aria-hidden /></a></Button>
        <Button variant="destructive" size="icon" disabled={busy} onClick={onDelete} aria-label="Xóa thư đang xem" title="Xóa thư"><Trash2 aria-hidden /></Button>
      </div>
    </div>
    <header className="mail-reader-heading">
      <div className="mail-reader-tags">{(message.Tags || []).map(tag => <Badge key={tag} variant="secondary">{tag}</Badge>)}</div>
      <h2 ref={title} id="mail-reader-subject" tabIndex={-1}>{message.Subject || "(Không có tiêu đề)"}</h2>
      <div className="mail-reader-sender"><Avatar><AvatarFallback>{initials}</AvatarFallback></Avatar><div><strong>{message.From?.Name || message.From?.Address || "Không rõ người gửi"}</strong>{message.From?.Name && <span>{message.From.Address}</span>}</div><Badge variant="outline">{read ? "Đã đọc" : "Chưa đọc"}</Badge></div>
      <details className="mail-reader-addresses"><summary><span>Tới {(message.To || []).map(address => address.Name || address.Address).join(", ") || "Không rõ người nhận"}</span><ChevronDown aria-hidden /></summary><dl><div><dt>Từ</dt><dd>{addressText(message.From)}</dd></div><div><dt>Tới</dt><dd>{(message.To || []).map(addressText).join(", ") || "—"}</dd></div>{!!message.Cc?.length && <div><dt>Cc</dt><dd>{message.Cc.map(addressText).join(", ")}</dd></div>}{!!message.Bcc?.length && <div><dt>Bcc</dt><dd>{message.Bcc.map(addressText).join(", ")}</dd></div>}{!!message.ReplyTo?.length && <div><dt>Trả lời tới</dt><dd>{message.ReplyTo.map(addressText).join(", ")}</dd></div>}<div><dt>Thời gian</dt><dd>{messageDate(message.Date)}</dd></div><div><dt>Kích thước</dt><dd>{fileSize(message.Size)}</dd></div></dl></details>
      <time className="mail-reader-date" dateTime={message.Date}>{messageDate(message.Date)}</time>
    </header>
    <div className="mail-reader-views"><ToggleGroup type="single" value={view} onValueChange={value => { if (value) setView(value as ReaderView) }} variant="outline" aria-label="Định dạng xem thư"><ToggleGroupItem value="html" disabled={!message.HTML}>HTML</ToggleGroupItem><ToggleGroupItem value="text">Văn bản</ToggleGroupItem><ToggleGroupItem value="headers">Headers</ToggleGroupItem><ToggleGroupItem value="source">Nguồn</ToggleGroupItem></ToggleGroup></div>
    <div className="mail-reader-content" aria-busy={resourceLoading}>
      {view === "html" && <><p className="mail-reader-protection"><ShieldCheck aria-hidden /><span>Script, ảnh bên ngoài và liên kết bị chặn trong bản xem trước.</span></p><iframe className="mail-reader-frame" title="Nội dung HTML của email" sandbox="" referrerPolicy="no-referrer" srcDoc={htmlDocument} /></>}
      {view === "text" && (message.Text ? <pre className="mail-reader-text">{message.Text}</pre> : <Empty><EmptyHeader><EmptyTitle>Thư không có bản văn bản thuần</EmptyTitle><EmptyDescription>Chọn HTML để xem nội dung của thư này.</EmptyDescription></EmptyHeader></Empty>)}
      {(view === "headers" || view === "source") && (resourceLoading ? <div className="mail-reader-resource-loading" role="status" aria-label="Đang tải nội dung thư"><Skeleton className="h-5 w-3/4" /><Skeleton className="h-5 w-full" /><Skeleton className="h-5 w-2/3" /><span className="sr-only">Đang tải…</span></div> : resourceError ? <Alert variant="destructive"><AlertTitle>Chưa tải được nội dung</AlertTitle><AlertDescription>{resourceError}</AlertDescription><Button variant="outline" onClick={() => setRetry(value => value + 1)}><RefreshCw data-icon="inline-start" aria-hidden />Thử lại</Button></Alert> : view === "source" ? <pre className="mail-reader-source">{source}</pre> : <dl className="mail-reader-headers">{Object.entries(headers || {}).map(([name, values]) => <div key={name}><dt>{name}</dt><dd>{Array.isArray(values) ? values.join("\n") : String(values)}</dd></div>)}</dl>)}
    </div>
    {!!message.Attachments?.length && <section className="mail-reader-attachments" aria-labelledby="mail-attachments-title"><h3 id="mail-attachments-title"><Paperclip aria-hidden />{message.Attachments.length} tệp đính kèm</h3><div>{message.Attachments.map(part => <a className="mail-reader-attachment" key={part.PartID} href={`${base}/part/${encodeURIComponent(part.PartID)}`} download={part.FileName || "tep-dinh-kem"}><FileText aria-hidden /><span><strong>{part.FileName || "Tệp không tên"}</strong><small>{fileSize(part.Size)} · {part.ContentType}</small></span><Download aria-hidden /><span className="sr-only">Tải xuống</span></a>)}</div></section>}
  </article>
}
