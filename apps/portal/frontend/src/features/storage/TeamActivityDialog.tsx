import {useState} from "react"
import {History} from "lucide-react"
import {Button} from "@/components/ui/button"
import {Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger} from "@/components/ui/dialog"
import {storageApi} from "./api"

type Entry = {id: number; actor: string; action: string; name: string; created_at: string}
type Feed = {items: Entry[]; next_before: number|null}
const labels: Record<string, string> = {
  folder: "đã tạo thư mục", rename: "đã đổi tên thành", move: "đã di chuyển",
  upload: "đã tải lên", replace: "đã cập nhật", restore: "đã khôi phục",
  trash: "đã chuyển vào thùng rác", restore_version: "đã khôi phục phiên bản của",
}
const dateTime = new Intl.DateTimeFormat("vi-VN", {dateStyle:"short",timeStyle:"short"})

export function TeamActivityDialog({teamId}: {teamId: string}) {
  const [feed,setFeed] = useState<Feed|null>(null)
  const [loading,setLoading] = useState(false)
  const [error,setError] = useState("")

  async function load(before?:number) {
    setLoading(true)
    setError("")
    try {
      const path = "/api/teams/" + encodeURIComponent(teamId) + "/activity"
      const next = await storageApi<Feed>(path + (before ? "?before="+before : ""))
      setFeed(previous=>({...next,items:before ? [...(previous?.items??[]),...next.items] : next.items}))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Chưa tải được nhật ký hoạt động.")
    } finally {
      setLoading(false)
    }
  }

  return <Dialog onOpenChange={open=>{if(open){setFeed(null);void load()}}}>
    <DialogTrigger asChild>
      <Button variant="outline"><History data-icon="inline-start" aria-hidden/>Hoạt động nhóm</Button>
    </DialogTrigger>
    <DialogContent className="max-h-[calc(100dvh-2rem)] overflow-y-auto">
      <DialogHeader>
        <DialogTitle>Nhật ký hoạt động nhóm</DialogTitle>
        <DialogDescription>Những thay đổi gần đây trong kho nhóm.</DialogDescription>
      </DialogHeader>
      {error && <p role="alert" className="text-destructive">{error}</p>}
      {loading && <p role="status">Đang tải hoạt động…</p>}
      {!loading && feed?.items.length===0 && <p>Chưa có hoạt động được ghi nhận.</p>}
      <ul className="divide-y">
        {feed?.items.map(entry=><li key={entry.id} className="space-y-1 py-2 text-sm wrap-anywhere">
          <p><strong>{entry.actor}</strong> {labels[entry.action]??"đã thay đổi"} <strong>{entry.name}</strong></p>
          <time className="text-xs text-muted-foreground" dateTime={entry.created_at}>{dateTime.format(new Date(entry.created_at))}</time>
        </li>)}
      </ul>
      {feed?.next_before!=null&&<Button variant="outline" disabled={loading} onClick={()=>void load(feed.next_before!)}>Xem thêm</Button>}
    </DialogContent>
  </Dialog>
}
