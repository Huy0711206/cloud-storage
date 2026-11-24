import {useCallback,useEffect,useRef,useState} from "react"
import {Bell,Check} from "lucide-react"
import {Button} from "@/components/ui/button"
import {Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger} from "@/components/ui/dialog"
import {storageApi} from "@/features/storage/api"

type Notification = {id: string; kind: "team_invite"|"file_received"|"plan_expiry"; label: string; read: boolean; created_at: string; expires_at?: string}
type Feed = {items: Notification[]; unread: number}
const dateTime = new Intl.DateTimeFormat("vi-VN",{dateStyle:"short",timeStyle:"short"})

function notificationText(item:Notification) {
  if(item.kind==="team_invite") return "Bạn được mời vào nhóm " + item.label
  if(item.kind==="file_received") return "Bạn vừa nhận tệp " + item.label
  return "Gói " + item.label + " sắp hết hạn"
}

export function Notifications({admin=false}: {admin?:boolean}) {
  const [open,setOpen] = useState(false)
  const [feed,setFeed] = useState<Feed|null>(null)
  const [error,setError] = useState("")
  const [reading,setReading] = useState<string|null>(null)
  const requestId = useRef(0)
  const refresh = useCallback(async(signal:AbortSignal)=>{
    const id = ++requestId.current
    try {
      const next = await storageApi<Feed>("/api/notifications",{signal})
      if (signal.aborted || id!==requestId.current) return
      setFeed(next)
      setError("")
    } catch (cause) {
      if (!signal.aborted && id===requestId.current) setError(cause instanceof Error ? cause.message : "Chưa tải được thông báo.")
    }
  },[])

  useEffect(()=>{
    const controller=new AbortController()
    void refresh(controller.signal)
    const timer=window.setInterval(()=>{
      if(document.visibilityState==="visible") void refresh(controller.signal)
    },60000)
    return ()=>{controller.abort();window.clearInterval(timer)}
  },[open,refresh])

  async function markRead(id:string) {
    setReading(id)
    try {
      await storageApi("/api/notifications/"+encodeURIComponent(id)+"/read",{method:"POST"})
      requestId.current++
      setFeed(previous=>{
        if(!previous?.items.some(item=>item.id===id&&!item.read)) return previous
        return {items:previous.items.map(item=>item.id===id?{...item,read:true}:item),unread:Math.max(0,previous.unread-1)}
      })
    } catch(cause) {
      setError(cause instanceof Error ? cause.message : "Chưa cập nhật được thông báo.")
    } finally {
      setReading(null)
    }
  }

  async function follow(item:Notification) {
    if(!item.read) await markRead(item.id)
    setOpen(false)
    const hash=item.kind==="team_invite"?"teams":item.kind==="file_received"?"requests":"plans"
    const target=admin?"/files":"/dashboard"
    if(location.pathname===target)location.hash=hash
    else location.assign(target+"#"+hash)
  }

  const unread=feed?.unread??0
  return <Dialog open={open} onOpenChange={setOpen}>
    <DialogTrigger asChild>
      <Button size="icon" variant="ghost" className="relative" aria-label={unread?"Thông báo, "+unread+" chưa đọc":"Thông báo"}>
        <Bell aria-hidden/>
        {unread>0&&<span aria-hidden className="absolute end-0 top-0 rounded-full bg-primary px-1 text-[10px] text-primary-foreground">{unread}</span>}
      </Button>
    </DialogTrigger>
    <DialogContent className="max-h-[calc(100dvh-2rem)] overflow-y-auto">
      <DialogHeader><DialogTitle>Thông báo</DialogTitle><DialogDescription>Lời mời nhóm, tệp nhận được và thời hạn gói.</DialogDescription></DialogHeader>
      {error&&<p role="alert" className="text-destructive">{error}</p>}
      {!feed&&!error&&<p role="status">Đang tải thông báo…</p>}
      {feed?.items.length===0&&<p>Bạn chưa có thông báo.</p>}
      <ul className="divide-y">
        {feed?.items.map(item=><li key={item.id} className="flex items-start justify-between gap-2 py-2 text-sm">
          <div className="min-w-0 wrap-anywhere">
            {admin&&item.kind==="plan_expiry"
              ? <p>{notificationText(item)}</p>
              : <button className={"text-left hover:underline "+(item.read?"":"font-semibold")}
                  disabled={reading!==null} onClick={()=>void follow(item)}>{notificationText(item)}</button>}
            <p className="text-xs text-muted-foreground">{item.expires_at?"Hết hạn ":""}
              <time dateTime={item.expires_at??item.created_at}>{dateTime.format(new Date(item.expires_at??item.created_at))}</time>
            </p>
          </div>
          {!item.read&&<Button size="icon" variant="ghost" aria-label="Đánh dấu đã đọc" disabled={reading!==null}
            onClick={()=>void markRead(item.id)}><Check aria-hidden/></Button>}
        </li>)}
      </ul>
    </DialogContent>
  </Dialog>
}
