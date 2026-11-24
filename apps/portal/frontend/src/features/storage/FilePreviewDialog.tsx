import {useEffect, useState} from "react"
import {Download} from "lucide-react"
import {Button} from "@/components/ui/button"
import {Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle} from "@/components/ui/dialog"
import type {FileItem} from "./api"

const previewTypes = ["image/png", "image/jpeg", "image/gif", "image/webp", "application/pdf"]

export function canOfferFilePreview(file: FileItem) {
  return !file.is_folder && !file.deleted_at &&
    (previewTypes.includes(file.mime_type ?? "") || /\.(png|jpe?g|gif|webp|pdf|txt|md|csv|log|json)$/i.test(file.name))
}

type PreviewState =
  | {status: "loading"}
  | {status: "ready"; mediaType: string}
  | {status: "text"; content: string}
  | {status: "error"; message: string}

function previewMediaType(response: Response) {
  if (response.status === 413) {
    throw new Error("Tệp văn bản vượt giới hạn xem trước 256 KiB. Hãy tải xuống để đọc.")
  }
  if (!response.ok) {
    throw new Error("Tệp không khả dụng để xem trước. Bạn có thể thử tải xuống.")
  }
  return response.headers.get("content-type")?.split(";", 1)[0].trim().toLowerCase() ?? ""
}

function PreviewContent({url, fileName}: {url: string; fileName: string}) {
  const [state, setState] = useState<PreviewState>({status: "loading"})
  const [loadingFrame, setLoadingFrame] = useState(true)

  useEffect(() => {
    const controller = new AbortController()

    async function load() {
      try {
        const options: RequestInit = {
          credentials: "same-origin",
          signal: controller.signal,
        }
        const mediaType = previewMediaType(await fetch(url, {...options, method: "HEAD"}))
        if (mediaType === "text/plain") {
          const body = await fetch(url, options)
          if (previewMediaType(body) !== "text/plain") {
            throw new Error("Tệp đã thay đổi. Hãy đóng rồi mở lại bản xem trước.")
          }
          const content = await body.text()
          if (!controller.signal.aborted) setState({status: "text", content})
          return
        }
        if (!previewTypes.includes(mediaType)) {
          throw new Error("Tệp không khả dụng để xem trước. Bạn có thể thử tải xuống.")
        }
        if (mediaType === "application/pdf" && navigator.pdfViewerEnabled === false) {
          throw new Error("Trình duyệt này không hỗ trợ xem trước PDF. Hãy tải xuống để mở tệp.")
        }
        if (!controller.signal.aborted) setState({status: "ready", mediaType})
      } catch (cause) {
        if (!controller.signal.aborted) {
          const message = cause instanceof TypeError
            ? "Chưa kết nối được với CloudBox. Hãy kiểm tra mạng rồi mở lại tệp."
            : cause instanceof Error ? cause.message : "Chưa thể mở bản xem trước."
          setState({status: "error", message})
        }
      }
    }

    void load()
    return () => controller.abort()
  }, [url])

  function showMediaError() {
    setState({status: "error", message: "Chưa thể hiển thị tệp này. Hãy tải xuống để mở tệp."})
  }

  if (state.status === "error") return <p role="alert" className="text-destructive">{state.message}</p>
  if (state.status === "text") {
    return state.content ? (
      <pre
        aria-label="Nội dung tệp"
        tabIndex={0}
        className="max-h-[min(60dvh,42rem)] min-w-0 overflow-auto whitespace-pre-wrap wrap-anywhere rounded-md border bg-muted p-3 font-mono text-sm"
      >{state.content}</pre>
    ) : <p>Tệp này chưa có nội dung.</p>
  }

  return (
    <div className="min-w-0">
      {(state.status === "loading" || loadingFrame) && <p role="status">Đang tải bản xem trước…</p>}
      {state.status === "ready" && (state.mediaType === "application/pdf" ? (
        <>
          <iframe
            title={fileName}
            src={url}
            className="h-[min(60dvh,42rem)] w-full rounded-md border"
            onLoad={() => setLoadingFrame(false)}
            onError={showMediaError}
          />
          <p className="mt-2 text-muted-foreground">Nếu PDF không hiển thị, hãy tải xuống để mở tệp.</p>
        </>
      ) : (
        <img
          src={url}
          alt={fileName}
          className="mx-auto max-h-[min(60dvh,42rem)] max-w-full rounded-md object-contain"
          onLoad={() => setLoadingFrame(false)}
          onError={showMediaError}
        />
      ))}
    </div>
  )
}

export function FilePreviewDialog({file, teamId, onClose, onRestoreFocus}: {
  file: FileItem
  teamId?: string
  onClose: () => void
  onRestoreFocus?: () => void
}) {
  const scope = teamId ? "/api/teams/" + encodeURIComponent(teamId) : "/api"
  const fileUrl = scope + "/files/" + encodeURIComponent(file.id)
  return (
    <Dialog open onOpenChange={open => {if (!open) onClose()}}>
      <DialogContent
        className="max-h-[calc(100dvh-2rem)] overflow-y-auto sm:max-w-3xl"
        onCloseAutoFocus={onRestoreFocus ? event => {
          event.preventDefault()
          onRestoreFocus()
        } : undefined}
      >
        <DialogHeader className="min-w-0 pr-6">
          <DialogTitle>Xem trước</DialogTitle>
          <DialogDescription className="break-all">{file.name}</DialogDescription>
        </DialogHeader>
        <PreviewContent key={file.id} url={fileUrl + "/preview"} fileName={file.name}/>
        <DialogFooter showCloseButton>
          <Button variant="outline" asChild>
            <a href={fileUrl + "/download"}><Download data-icon="inline-start" aria-hidden/>Tải xuống</a>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
