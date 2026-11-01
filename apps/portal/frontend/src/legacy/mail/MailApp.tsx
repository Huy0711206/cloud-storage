import { lazy, Suspense, useCallback, useEffect, useRef, useState, type ReactNode } from "react"
import LiquidGlass from "liquid-glass-react"
import { ArrowLeft, ArrowUpRight, Check, ChevronLeft, ChevronRight, Cloud, Inbox, Info, Loader2, Mail, MailOpen, Menu, Paperclip, RefreshCw, Search, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert"
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { InputGroup, InputGroupAddon, InputGroupButton, InputGroupInput } from "@/components/ui/input-group"
import { Field, FieldLabel } from "@/components/ui/field"
import { Skeleton } from "@/components/ui/skeleton"
import { Separator } from "@/components/ui/separator"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetTrigger } from "@/components/ui/sheet"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from "@/components/ui/dialog"
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog"
import { ThemeMenu } from "@/shared/ui"
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import { apiJson, ApiError } from "@/legacy/mail/api"
import type { MailDetail, MailList, MailSummary } from "@/legacy/mail/types"
const MessageReader=lazy(()=>import("@/legacy/mail/MessageReader").then(m=>({default:m.MessageReader})))

type Filter = "all" | "unread" | "attachments"
const PAGE_SIZE=20
const validFilter=(v:string|null):Filter=>v==="unread"||v==="attachments"?v:"all"
const initial=new URLSearchParams(location.search)
const dateFormat=new Intl.DateTimeFormat("vi-VN",{day:"2-digit",month:"2-digit",hour:"2-digit",minute:"2-digit"})
function shortDate(value:string){const d=new Date(value);return Number.isNaN(d.getTime())?"—":dateFormat.format(d)}
function initials(name:string){return name.split(/[\s@._-]+/).filter(Boolean).slice(0,2).map(x=>x[0]).join("").toUpperCase()||"M"}

function ToolSurface({children,dark}:{children:ReactNode;dark:boolean}) {
 const query="(min-width: 1024px) and (pointer: fine) and (prefers-reduced-motion: no-preference)"
 const supported=/Chrome|Chromium|Edg\//.test(navigator.userAgent)
 const [glass,setGlass]=useState(()=>supported&&matchMedia(query).matches)
 useEffect(()=>{const m=matchMedia(query),update=()=>setGlass(supported&&m.matches);m.addEventListener("change",update);return()=>m.removeEventListener("change",update)},[supported])
 if(!glass)return <div className="mail-tool-fallback">{children}</div>
 return <div className="mail-glass-host" data-glass="active"><LiquidGlass mode="standard" displacementScale={12} blurAmount={0.03} saturation={110} aberrationIntensity={0.3} elasticity={0} cornerRadius={15} padding="3px 5px" overLight={!dark} style={{position:"absolute",top:"50%",left:"50%"}} className="mail-glass"><div className="mail-tool-content">{children}</div></LiquidGlass></div>
}

export function MailApp() {
 const [filter,setFilter]=useState<Filter>(()=>validFilter(initial.get("view")))
 const [query,setQuery]=useState(initial.get("q")||"")
 const [search,setSearch]=useState(query.trim())
 const [page,setPage]=useState(0)
 const [selected,setSelected]=useState<string|null>(initial.get("message"))
 const [list,setList]=useState<MailList|null>(null)
 const [loading,setLoading]=useState(true),[refreshing,setRefreshing]=useState(false),[error,setError]=useState("")
 const [message,setMessage]=useState<MailDetail|null>(null),[detailLoading,setDetailLoading]=useState(false),[detailError,setDetailError]=useState("")
 const [missing,setMissing]=useState(false),[read,setRead]=useState(true),[busy,setBusy]=useState(false),[deleteOpen,setDeleteOpen]=useState(false)
 const [deleteTarget,setDeleteTarget]=useState<{id:string;subject:string}|null>(null)
 const [menuOpen,setMenuOpen]=useState(false),[detailRetry,setDetailRetry]=useState(0)
 const [lastUpdate,setLastUpdate]=useState<Date|null>(null),[online,setOnline]=useState(navigator.onLine)
 const [dark,setDark]=useState(document.documentElement.classList.contains("dark"))
 const listAbort=useRef<AbortController|null>(null),requestSerial=useRef(0)
 const readerRef=useRef<HTMLElement|null>(null),listHeading=useRef<HTMLHeadingElement|null>(null),deleteOrigin=useRef<HTMLElement|null>(null)
 const selectedRef=useRef(selected);selectedRef.current=selected

 const updateUrl=useCallback((id:string|null,replace=false)=>{const u=new URL(location.href);if(id)u.searchParams.set("message",id);else u.searchParams.delete("message");(replace?history.replaceState:history.pushState).call(history,null,"",u)},[])
 const selectMessage=(id:string)=>{setSelected(id);updateUrl(id)}
 const closeMessage=()=>{setSelected(null);updateUrl(null);requestAnimationFrame(()=>listHeading.current?.focus())}
 useEffect(()=>{const back=()=>{const p=new URLSearchParams(location.search);setSelected(p.get("message"));setFilter(validFilter(p.get("view")));setQuery(p.get("q")||"")};window.addEventListener("popstate",back);return()=>window.removeEventListener("popstate",back)},[])
 useEffect(()=>{const t=setTimeout(()=>{setSearch(query.trim());setPage(0)},350);return()=>clearTimeout(t)},[query])
 useEffect(()=>{const u=new URL(location.href);if(search)u.searchParams.set("q",search);else u.searchParams.delete("q");if(filter!=="all")u.searchParams.set("view",filter);else u.searchParams.delete("view");history.replaceState(null,"",u)},[search,filter])
 useEffect(()=>{const update=()=>setOnline(navigator.onLine);window.addEventListener("online",update);window.addEventListener("offline",update);const observer=new MutationObserver(()=>setDark(document.documentElement.classList.contains("dark")));observer.observe(document.documentElement,{attributes:true,attributeFilter:["class"]});return()=>{window.removeEventListener("online",update);window.removeEventListener("offline",update);observer.disconnect()}},[])

 const loadList=useCallback(async(silent=false)=>{
  if(silent&&listAbort.current&&!listAbort.current.signal.aborted)return
  listAbort.current?.abort();const controller=new AbortController();listAbort.current=controller;const serial=++requestSerial.current
  if(!silent)setLoading(true);setRefreshing(true)
  const terms=[search,filter==="unread"?"is:unread":filter==="attachments"?"has:attachment":""].filter(Boolean).join(" ")
  const params=new URLSearchParams({start:String(page*PAGE_SIZE),limit:String(PAGE_SIZE)});if(terms)params.set("query",terms)
  try{const result=await apiJson<MailList>("/api/v1/"+(terms?"search":"messages")+"?"+params,{signal:controller.signal});if(serial!==requestSerial.current)return;setList(result);setError("");setLastUpdate(new Date());if(page>0&&result.messages.length===0){setPage(p=>p-1)}}
  catch(e){if(controller.signal.aborted)return;setError(e instanceof Error?e.message:"Chưa kết nối được hộp thư. Hãy thử lại.")}
  finally{if(serial===requestSerial.current){listAbort.current=null;setLoading(false);setRefreshing(false)}}
 },[search,filter,page])
 useEffect(()=>{void loadList();return()=>listAbort.current?.abort()},[loadList])
 useEffect(()=>{const t=setInterval(()=>{if(!document.hidden)void loadList(true)},10000);const visible=()=>{if(!document.hidden)void loadList(true)};document.addEventListener("visibilitychange",visible);return()=>{clearInterval(t);document.removeEventListener("visibilitychange",visible)}},[loadList])

 useEffect(()=>{
  if(!selected){setMessage(null);setDetailError("");setMissing(false);return}
  const controller=new AbortController();setDetailLoading(true);setDetailError("");setMissing(false);setMessage(null)
  apiJson<MailDetail>("/api/v1/message/"+encodeURIComponent(selected),{signal:controller.signal}).then(data=>{if(controller.signal.aborted)return;setMessage(data);setRead(true);void loadList(true);requestAnimationFrame(()=>readerRef.current?.focus())}).catch(e=>{if(controller.signal.aborted)return;setMissing(e instanceof ApiError&&e.status===404);setDetailError(e instanceof Error?e.message:"Chưa tải được thư.")}).finally(()=>{if(!controller.signal.aborted)setDetailLoading(false)})
  return()=>controller.abort()
  // Opening a message marks it read. Polling the list must never re-open it.
  // eslint-disable-next-line react-hooks/exhaustive-deps
 },[selected,detailRetry])

 async function toggleRead(){if(!selected||busy)return;const id=selected,nextRead=!read;setBusy(true);try{await apiJson("/api/v1/messages",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({IDs:[id],Read:nextRead})});if(selectedRef.current===id)setRead(nextRead);void loadList(true);toast.success(nextRead?"Đã đánh dấu đã đọc":"Đã đánh dấu chưa đọc")}catch(e){toast.error(e instanceof Error?e.message:"Chưa cập nhật được trạng thái thư.")}finally{setBusy(false)}}
 function askDelete(){if(!selected)return;deleteOrigin.current=document.activeElement as HTMLElement;setDeleteTarget({id:selected,subject:message?.Subject||"(Không có tiêu đề)"});setDeleteOpen(true)}
 async function deleteMessage(){if(!deleteTarget||busy)return;const id=deleteTarget.id;setBusy(true);try{await apiJson("/api/v1/messages",{method:"DELETE",headers:{"Content-Type":"application/json"},body:JSON.stringify({IDs:[id]})});if(selectedRef.current===id){setSelected(null);updateUrl(null,true)}setDeleteOpen(false);void loadList(true);toast.success("Đã xóa thư");requestAnimationFrame(()=>listHeading.current?.focus())}catch(e){toast.error(e instanceof Error?e.message:"Chưa xóa được thư. Hãy thử lại.")}finally{setBusy(false)}}
 const changeFilter=(next:Filter)=>{setFilter(next);setPage(0);setMenuOpen(false);setSelected(null);updateUrl(null,true)}
 const total=list?.messages_count??0,unread=list?.unread??0
 const name=filter==="unread"?"Chưa đọc":filter==="attachments"?"Có tệp đính kèm":"Hộp thư đến"
 const filtered=!!search||filter!=="all"
 const navigation=<><div className="mail-space-label">Hộp thư của dự án</div><nav aria-label="Thư mục hộp thư" className="mail-navigation">{([{id:"all",label:"Hộp thư đến",icon:Inbox},{id:"unread",label:"Chưa đọc",icon:Mail},{id:"attachments",label:"Có tệp đính kèm",icon:Paperclip}] as const).map(item=><Button key={item.id} variant="ghost" className="mail-nav-item" data-active={filter===item.id||undefined} aria-current={filter===item.id?"page":undefined} onClick={()=>changeFilter(item.id)}><item.icon data-icon="inline-start" aria-hidden/><span>{item.label}</span>{item.id==="all"&&<Badge variant="secondary">{list?.total??0}</Badge>}{item.id==="unread"&&unread>0&&<Badge variant="secondary">{unread}</Badge>}</Button>)}</nav><div className="mail-sidebar-bottom"><Separator/><a href="http://localhost:8001/dashboard" target="_blank" rel="noopener noreferrer"><Cloud aria-hidden/>Về CloudBox<ArrowUpRight aria-hidden/><span className="sr-only"> (mở tab mới)</span></a><a href="http://localhost:8025/" target="_blank" rel="noopener noreferrer"><ArrowUpRight aria-hidden/>Mở Mailpit gốc<span className="sr-only"> (mở tab mới)</span></a><div className="mail-local-note"><span aria-hidden/><p>Hộp thư thử nghiệm<span>Dữ liệu dùng chung với cổng 8025.</span></p></div></div></>

 return <div className="mail-shell"><a href="#mail-main" className="mail-skip" onClick={e=>{e.preventDefault();document.getElementById("mail-main")?.focus()}}>Chuyển đến nội dung chính</a>
  <aside className="mail-sidebar"><a href="/" className="mail-brand" aria-label="CloudBox Mail — Hộp thư"><span><Cloud aria-hidden/></span><div>CloudBox<span>Mail</span></div></a>{navigation}</aside>
  <div className="mail-workspace"><header className="mail-topbar"><div className="mail-topbar-title"><Sheet open={menuOpen} onOpenChange={setMenuOpen}><SheetTrigger asChild><Button variant="ghost" size="icon" className="mail-nav-trigger" aria-label="Mở điều hướng hộp thư"><Menu aria-hidden/></Button></SheetTrigger><SheetContent side="left" className="mail-mobile-menu"><SheetHeader><SheetTitle>CloudBox Mail</SheetTitle><SheetDescription>Hộp thư thử nghiệm của dự án.</SheetDescription></SheetHeader>{navigation}</SheetContent></Sheet><div><strong>Không gian email</strong><span>Hộp thư thử nghiệm CloudBox</span></div></div><div className="mail-topbar-right"><span className="mail-live-indicator" data-error={!!error||!online||undefined}><span aria-hidden/>{error?"Chưa kết nối":!online?"Ngoại tuyến":"Tự cập nhật 10 giây"}</span><ToolSurface dark={dark}><ThemeMenu/><Dialog><DialogTrigger asChild><Button variant="ghost" size="icon" aria-label="Thông tin hộp thư"><Info aria-hidden/></Button></DialogTrigger><DialogContent><DialogHeader><DialogTitle>Hộp thư thử nghiệm</DialogTitle><DialogDescription>Kiểm tra các email CloudBox gửi trong lúc phát triển.</DialogDescription></DialogHeader><div className="mail-help"><p>Giao diện này và Mailpit ở cổng 8025 dùng chung thư. Mở thư sẽ đánh dấu đã đọc; xóa thư sẽ xóa ở cả hai nơi.</p><p>Nội dung HTML được cô lập. Script, liên kết và tài nguyên bên ngoài bị chặn trong bản xem trước. Bạn có thể xem nội dung gốc hoặc tải thư về để kiểm tra.</p><p>Danh sách tự cập nhật mỗi 10 giây khi tab đang hiển thị. Dùng nút làm mới để kiểm tra ngay.</p></div></DialogContent></Dialog></ToolSurface></div></header>
   <main id="mail-main" className={cn("mail-panels",selected&&"mail-has-selection")} tabIndex={-1}>
    <section className="mail-list-panel" aria-label="Danh sách email"><div className="mail-list-heading"><div><h1 ref={listHeading} tabIndex={-1}>{name}</h1><p>{loading&&!list?"Đang kết nối hộp thư…":`${total} thư${filtered?" phù hợp":" trong hộp thư"}`}</p></div><Button variant="outline" size="icon" aria-label="Làm mới hộp thư" disabled={refreshing} onClick={()=>{void loadList();if(selected)setDetailRetry(x=>x+1)}}>{refreshing?<Loader2 className="animate-spin" aria-hidden/>:<RefreshCw aria-hidden/>}</Button></div>
     <div className="mail-search"><Field><FieldLabel htmlFor="mail-search" className="sr-only">Tìm email</FieldLabel><InputGroup><InputGroupAddon><Search aria-hidden/></InputGroupAddon><InputGroupInput id="mail-search" type="search" autoComplete="off" placeholder="Tìm tiêu đề, người gửi…" value={query} maxLength={500} onChange={e=>setQuery(e.target.value)}/>{query&&<InputGroupAddon align="inline-end"><InputGroupButton size="icon-sm" aria-label="Xóa tìm kiếm" onClick={()=>setQuery("")}><X aria-hidden/></InputGroupButton></InputGroupAddon>}</InputGroup></Field>{search&&<p className="mail-search-caption">Kết quả cho “{search}”</p>}</div>
     {!online&&<Alert data-tone="warning"><Info aria-hidden/><AlertTitle>Đang ngoại tuyến</AlertTitle><AlertDescription>Kiểm tra kết nối rồi thử làm mới hộp thư.</AlertDescription></Alert>}
     {error&&<div className="mail-list-error"><Alert variant="destructive"><Info aria-hidden/><AlertTitle>Chưa tải được hộp thư</AlertTitle><AlertDescription>{error}</AlertDescription></Alert><Button variant="outline" onClick={()=>void loadList()}>Thử kết nối lại</Button></div>}
     <div className="mail-list-scroll" aria-busy={loading}>
      {loading?<div className="mail-list-skeleton" role="status" aria-label="Đang tải email">{Array.from({length:6},(_,i)=><div className="mail-skeleton-row" key={i}><Skeleton className="size-9 rounded-xl"/><div className="flex min-w-0 flex-1 flex-col gap-3"><Skeleton className="h-3 w-3/4"/><Skeleton className="h-3 w-full"/><Skeleton className="h-3 w-2/3"/></div></div>)}</div>:!error||list?list?.messages.length?<ul className="mail-message-list">{list.messages.map((m:MailSummary)=><li key={m.ID}><button className="mail-message-row" data-selected={selected===m.ID||undefined} data-unread={!m.Read||undefined} aria-current={selected===m.ID?"true":undefined} onClick={()=>selectMessage(m.ID)}><Avatar><AvatarFallback>{initials(m.From.Name||m.From.Address)}</AvatarFallback></Avatar><div className="mail-message-copy"><div className="mail-message-sender"><strong title={m.From.Address}>{m.From.Name||m.From.Address||"Không rõ người gửi"}</strong><time dateTime={m.Created}>{shortDate(m.Created)}</time></div><div className="mail-message-subject"><span>{m.Subject||"(Không có tiêu đề)"}</span>{!m.Read&&<i aria-label="Chưa đọc"/>}</div><p>{m.Snippet||"Mở thư để xem nội dung."}</p><div className="mail-message-meta"><span title={m.To?.map(x=>x.Address).join(", ")}>Đến: {m.To?.map(x=>x.Name||x.Address).join(", ")||"Không có người nhận"}</span>{m.Attachments>0&&<span><Paperclip aria-hidden/>{m.Attachments}</span>}</div></div></button></li>)}</ul>:<Empty className="mail-empty-list"><EmptyHeader><EmptyMedia variant="icon">{filtered?<Search aria-hidden/>:<Inbox aria-hidden/>}</EmptyMedia><EmptyTitle>{filtered?"Không tìm thấy thư":"Chưa có thư nào"}</EmptyTitle><EmptyDescription>{filtered?"Thử từ khóa khác hoặc xem tất cả thư trong hộp thư.":"Email thử nghiệm sẽ xuất hiện tại đây khi CloudBox gửi thư."}</EmptyDescription></EmptyHeader><EmptyContent><Button variant="outline" onClick={()=>{if(filtered){setQuery("");changeFilter("all")}else void loadList()}}>{filtered?"Xem tất cả thư":"Làm mới hộp thư"}</Button></EmptyContent></Empty>:null}
     </div>
     <footer className="mail-list-footer"><span>{total?`${page*PAGE_SIZE+1}–${Math.min((page+1)*PAGE_SIZE,total)} / ${total}`:"0 thư"}</span><div><Button variant="ghost" size="icon" aria-label="Trang thư trước" disabled={!page||loading} onClick={()=>setPage(p=>p-1)}><ChevronLeft aria-hidden/></Button><Button variant="ghost" size="icon" aria-label="Trang thư sau" disabled={(page+1)*PAGE_SIZE>=total||loading} onClick={()=>setPage(p=>p+1)}><ChevronRight aria-hidden/></Button></div></footer>
    </section>
    <section ref={readerRef} className="mail-reader-panel" tabIndex={-1} aria-label="Nội dung email">
     {!selected?<div className="mail-reader-placeholder"><div className="mail-envelope-art" aria-hidden><div/><MailOpen/></div><h2>Chọn một email</h2><p>Chọn một email để xem nội dung,<br/>thông tin gửi và tệp đính kèm.</p><span><Check aria-hidden/>Nội dung thư được cô lập khi xem</span></div>:detailLoading?<div className="mail-detail-skeleton" role="status" aria-label="Đang mở email"><Skeleton className="h-6 w-4/5"/><Skeleton className="h-4 w-1/2"/><Separator/><Skeleton className="h-40 w-full"/><Skeleton className="h-4 w-3/4"/><Skeleton className="h-4 w-2/3"/></div>:detailError?<Empty className="mail-reader-error"><EmptyHeader><EmptyMedia variant="icon"><Mail aria-hidden/></EmptyMedia><EmptyTitle>{missing?"Thư không còn tồn tại":"Chưa mở được email"}</EmptyTitle><EmptyDescription>{missing?"Thư có thể đã được xóa từ giao diện khác. Hãy quay lại và làm mới danh sách.":detailError}</EmptyDescription></EmptyHeader><EmptyContent><Button variant="outline" onClick={closeMessage}><ArrowLeft data-icon="inline-start" aria-hidden/>Về danh sách</Button>{!missing&&<Button onClick={()=>setDetailRetry(x=>x+1)}>Thử tải lại thư</Button>}</EmptyContent></Empty>:message?<Suspense fallback={<div className="mail-detail-skeleton" role="status">Đang mở khung đọc thư…</div>}><MessageReader message={message} read={read} busy={busy} onBack={closeMessage} onToggleRead={()=>void toggleRead()} onDelete={askDelete}/></Suspense>:null}
    </section>
   </main><div className="sr-only" role="status" aria-live="polite">{!loading&&!error?`${total} thư${filtered?" phù hợp":" trong hộp thư"}. ${unread} thư chưa đọc.`:""}</div><div className="mail-updated-at sr-only">{lastUpdate?`Cập nhật lúc ${lastUpdate.toLocaleTimeString("vi-VN")}`:""}</div>
  </div>
  <AlertDialog open={deleteOpen} onOpenChange={v=>{if(!busy)setDeleteOpen(v)}}><AlertDialogContent onCloseAutoFocus={e=>{e.preventDefault();if(deleteOrigin.current?.isConnected)deleteOrigin.current.focus();else listHeading.current?.focus()}}><AlertDialogHeader><AlertDialogTitle>Xóa email này?</AlertDialogTitle><AlertDialogDescription>Thư sẽ bị xóa khỏi Mailpit và cả hai giao diện 8025/8026. Không thể hoàn tác thao tác này.</AlertDialogDescription></AlertDialogHeader><p className="mail-delete-subject">{deleteTarget?.subject}</p><AlertDialogFooter><AlertDialogCancel disabled={busy}>Giữ lại thư</AlertDialogCancel><AlertDialogAction variant="destructive" disabled={busy} onClick={e=>{e.preventDefault();void deleteMessage()}}>{busy?<Loader2 data-icon="inline-start" className="animate-spin" aria-hidden/>:null}{busy?"Đang xóa…":"Xóa email"}</AlertDialogAction></AlertDialogFooter></AlertDialogContent></AlertDialog>
  <Toaster theme={dark?"dark":"light"}/>
 </div>
}
