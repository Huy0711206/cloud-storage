import {useCallback,useEffect,useRef,useState,type FormEvent} from "react"
import {ArrowLeft,Check,ChevronRight,Copy,Download,File,Folder,FolderPlus,FolderUp,Info,Link2,Loader2,MoreHorizontal,Pencil,RefreshCw,Search,Share2,Trash2,Undo2,Upload,X} from "lucide-react"
import {Button} from "@/components/ui/button"
import {Input} from "@/components/ui/input"
import {Field,FieldGroup,FieldLabel} from "@/components/ui/field"
import {Dialog,DialogContent,DialogDescription,DialogFooter,DialogHeader,DialogTitle} from "@/components/ui/dialog"
import {DropdownMenu,DropdownMenuContent,DropdownMenuGroup,DropdownMenuItem,DropdownMenuSeparator,DropdownMenuTrigger} from "@/components/ui/dropdown-menu"
import {Table,TableBody,TableCell,TableHead,TableHeader,TableRow} from "@/components/ui/table"
import {Progress} from "@/components/ui/progress"
import {Skeleton} from "@/components/ui/skeleton"
import {EmptyState,Notice,PageHeading,bytes,date} from "@/shared/ui"
import type {PageData} from "@/shared/types"
import {usePlanBenefits} from "@/features/billing/benefits"
import {storageApi,jsonBody,publishUsage,type CreatedShare,type FileItem,type FileList,type ShareItem,type StorageUsage} from "./api"

type Mode="storage"|"shared"|"trash"
type Action="new"|"rename"|"move"|"share"|"details"|"trash"|"purge"|"replace"|"version_restore"
type VersionItem={id:string;name:string;size:number;created_at:string;available:boolean;restorable?:boolean;source?:string;expires_at?:string|null}
type UploadState={name:string;percent:number;index:number;count:number}
const when=(value:string)=>new Intl.DateTimeFormat("vi-VN",{dateStyle:"short",timeStyle:"short"}).format(new Date(value))
const message=(error:unknown)=>error instanceof Error?error.message:"Chưa thể hoàn tất thao tác. Hãy thử lại."

export function NativeFilesPage({data:_data,mode="storage"}:{data:PageData;mode?:Mode}) {
  const {current:benefits}=usePlanBenefits()
  const [shareExpiry,setShareExpiry]=useState(""),[sharePassword,setSharePassword]=useState("")
  const [replacement,setReplacement]=useState<File|null>(null),[restoreVersion,setRestoreVersion]=useState<VersionItem|null>(null)
  const [parent,setParent]=useState<string|null>(null),[query,setQuery]=useState(""),[term,setTerm]=useState(""),[sort,setSort]=useState("name")
  const [listing,setListing]=useState<FileList|null>(null),[shares,setShares]=useState<ShareItem[]>([]),[loading,setLoading]=useState(true),[loadingMore,setLoadingMore]=useState(false)
  const [error,setError]=useState(""),[notice,setNotice]=useState(""),[busy,setBusy]=useState(false),[upload,setUpload]=useState<UploadState|null>(null)
  const [dialog,setDialog]=useState<Action|null>(null),[selected,setSelected]=useState<FileItem|null>(null),[name,setName]=useState("")
  const [dialogError,setDialogError]=useState(""),[fileShares,setFileShares]=useState<ShareItem[]>([]),[newLink,setNewLink]=useState("")
  const [copied,setCopied]=useState(false),[sharesLoading,setSharesLoading]=useState(false),[versions,setVersions]=useState<VersionItem[]>([]),[versionsLoading,setVersionsLoading]=useState(false)
  const [moveParent,setMoveParent]=useState<string|null>(null),[moveList,setMoveList]=useState<FileList|null>(null),[moveLoadingMore,setMoveLoadingMore]=useState(false)
  const [dragging,setDragging]=useState(false)
  const fileInput=useRef<HTMLInputElement>(null),folderInput=useRef<HTMLInputElement>(null),uploadControl=useRef<AbortController|null>(null),loadSequence=useRef(0)
  const moveSequence=useRef(0),detailSequence=useRef(0)
  const latestRefresh=useRef<()=>Promise<void>>(async()=>{})
  const writable=mode==="storage",trash=mode==="trash"
  const title=trash?"Thùng rác":mode==="shared"?"Đã chia sẻ":"Tệp của tôi"
  useEffect(()=>{const timer=window.setTimeout(()=>setTerm(query.trim()),250);return()=>window.clearTimeout(timer)},[query])
  useEffect(()=>{setParent(null);setQuery("");setTerm("");setError("");setNotice("")},[mode])

  const refresh=useCallback(async()=>{
    const sequence=++loadSequence.current
    setLoading(true)
    try {
      if(mode==="shared") {
        const result=await storageApi<{items:ShareItem[]}>("/api/shares")
        if(sequence===loadSequence.current)setShares(result.items.filter(item=>!item.revoked))
      } else {
        const params=new URLSearchParams({sort,trash:String(trash)})
        if(parent!==null)params.set("parent",String(parent))
        if(term)params.set("q",term)
        const result=await storageApi<FileList>("/api/files?"+params)
        if(sequence===loadSequence.current){setListing(result);publishUsage(result.usage)}
      }
      if(sequence===loadSequence.current)setError("")
    }catch(cause){if(sequence===loadSequence.current)setError(message(cause))}
    finally{if(sequence===loadSequence.current)setLoading(false)}
  },[mode,parent,term,sort,trash])
  latestRefresh.current=refresh
  async function loadMore() {
    if(!listing?.has_more||listing.next_offset==null||loadingMore)return
    setLoadingMore(true)
    const sequence=loadSequence.current
    const params=new URLSearchParams({sort,trash:String(trash),offset:String(listing.next_offset)})
    if(parent!==null)params.set("parent",parent)
    if(term)params.set("q",term)
    try{const next=await storageApi<FileList>("/api/files?"+params);if(sequence===loadSequence.current)setListing(current=>({...next,items:[...(current?.items??[]),...next.items]}))}catch(cause){setError(message(cause))}finally{setLoadingMore(false)}
  }
  useEffect(()=>{void refresh();return()=>{loadSequence.current++}},[refresh])
  useEffect(()=>()=>uploadControl.current?.abort(),[])

  function closeDialog(){detailSequence.current++;moveSequence.current++;setDialog(null)}
  function open(action:Action,item:FileItem|null=null) {
    const detail=++detailSequence.current
    setSharesLoading(false);setVersionsLoading(false)
    setShareExpiry("");setSharePassword("");setReplacement(null);setRestoreVersion(null)
    setSelected(item);setName(action==="rename"?item?.name??"":"");setDialogError("");setNewLink("");setCopied(false);setDialog(action)
    if(action==="share"&&item) {
      setFileShares([]);setSharesLoading(true)
      storageApi<{items:ShareItem[]}>(`/api/files/${item.id}/shares`).then(result=>{if(detail===detailSequence.current)setFileShares(result.items)}).catch(cause=>{if(detail===detailSequence.current)setDialogError(message(cause))}).finally(()=>{if(detail===detailSequence.current)setSharesLoading(false)})
    }
    if(action==="details") {
      setVersions([])
      if(item&&!item.is_folder&&!item.deleted_at){setVersionsLoading(true);storageApi<{items:VersionItem[]}>(`/api/files/${item.id}/versions`).then(result=>{if(detail===detailSequence.current)setVersions(result.items)}).catch(cause=>{if(detail===detailSequence.current)setDialogError(message(cause))}).finally(()=>{if(detail===detailSequence.current)setVersionsLoading(false)})}
    }
    if(action==="move"){setMoveParent(null);setMoveList(null);void loadMove(null)}
  }
  async function loadMove(id:string|null) {
    const sequence=++moveSequence.current
    setMoveParent(id);setMoveList(null);setMoveLoadingMore(false)
    try{const result=await storageApi<FileList>("/api/files"+(id!==null?"?parent="+id:""));if(sequence===moveSequence.current)setMoveList(result)}catch(cause){if(sequence===moveSequence.current)setDialogError(message(cause))}
  }
  async function moreMoveFolders() {
    if(!moveList?.has_more||moveList.next_offset==null||moveLoadingMore)return
    const sequence=moveSequence.current
    setMoveLoadingMore(true)
    try{const params=new URLSearchParams({offset:String(moveList.next_offset)});if(moveParent!==null)params.set("parent",moveParent);const next=await storageApi<FileList>("/api/files?"+params);if(sequence===moveSequence.current)setMoveList(current=>({...next,items:[...(current?.items??[]),...next.items]}))}catch(cause){if(sequence===moveSequence.current)setDialogError(message(cause))}finally{if(sequence===moveSequence.current)setMoveLoadingMore(false)}
  }
  async function mutate(url:string,options:RequestInit,success:string) {
    setBusy(true);setDialogError("")
    try{await storageApi(url,options);closeDialog();setNotice(success);await latestRefresh.current();await updateUsage()}
    catch(cause){if(dialog)setDialogError(message(cause));else setError(message(cause))}
    finally{setBusy(false)}
  }
  async function updateUsage(){try{const usage=await storageApi<StorageUsage>("/api/storage/usage");publishUsage(usage)}catch{/* The next listing refresh also updates usage. */}}
  function submitName(event:FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if(!name.trim())return
    if(dialog==="new")void mutate("/api/files/folders",{method:"POST",body:jsonBody({name:name.trim(),parent_id:parent})},"Đã tạo thư mục.")
    else if(selected)void mutate(`/api/files/${selected.id}`,{method:"PATCH",body:jsonBody({name:name.trim()})},"Đã đổi tên.")
  }
  async function createShare() {
    if(!selected)return
    setBusy(true);setDialogError("")
    if(shareExpiry&&(!Number.isFinite(new Date(shareExpiry).getTime())||new Date(shareExpiry).getTime()<=Date.now())){setDialogError("Hãy chọn thời điểm hết hạn trong tương lai.");setBusy(false);return}
    if(sharePassword&&sharePassword.length<8){setDialogError("Mật khẩu liên kết cần ít nhất 8 ký tự.");setBusy(false);return}
    try{const result=await storageApi<CreatedShare>(`/api/files/${selected.id}/shares`,{method:"POST",body:jsonBody({expires_at:shareExpiry?new Date(shareExpiry).toISOString():null,password:sharePassword||null})});setNewLink(result.url);setFileShares((await storageApi<{items:ShareItem[]}>(`/api/files/${selected.id}/shares`)).items)}catch(cause){setDialogError(message(cause))}finally{setBusy(false)}
  }
  async function revokeShare(id:string,inDialog=false) {
    setBusy(true)
    try{await storageApi(`/api/shares/${id}`,{method:"DELETE"});setFileShares(current=>current.filter(item=>item.id!==id));setShares(current=>current.filter(item=>item.id!==id));setNewLink("");setNotice("Đã thu hồi liên kết chia sẻ.")}
    catch(cause){inDialog?setDialogError(message(cause)):setError(message(cause))}finally{setBusy(false)}
  }
  async function copyLink(){try{await navigator.clipboard.writeText(newLink);setCopied(true)}catch{setDialogError("Chưa sao chép được. Bạn có thể chọn và sao chép liên kết bên dưới.")}}

  async function uploadFiles(files:File[],replaceItem:FileItem|null=null) {
    if(!files.length||uploadControl.current||upload||!writable)return
    const controller=new AbortController();uploadControl.current=controller
    setError("");setNotice("")
    let activeId:string|number|null=null,completed=0,uploadError=""
    const createdFolders=new Map<string,string|null>([["",parent]])
    try {
      for(let index=0;index<files.length;index++) {
        if(controller.signal.aborted)throw new DOMException("Đã hủy tải lên","AbortError")
        const file=files[index]
        setUpload({name:file.name,percent:0,index:index+1,count:files.length})
        let destination=replaceItem?.parent_id??parent
        const relative=file.webkitRelativePath
        if(relative&&!replaceItem) {
          const parts=relative.split("/").slice(0,-1)
          for(let depth=0;depth<parts.length;depth++) {
            const key=parts.slice(0,depth+1).join("/")
            if(!createdFolders.has(key)) {
              const node=await storageApi<FileItem>("/api/files/folders",{method:"POST",body:jsonBody({name:parts[depth],parent_id:destination}),signal:controller.signal})
              createdFolders.set(key,node.id)
            }
            destination=createdFolders.get(key)??null
          }
        }
        const session=await storageApi<{id:string|number;chunk_size:number;received:number}>("/api/uploads",{method:"POST",body:jsonBody({name:replaceItem?.name??file.name,parent_id:destination,size:file.size,...(replaceItem?{replace_node_id:replaceItem.id}:{})}),signal:controller.signal})
        activeId=session.id
        let offset=session.received
        const chunkSize=Math.min(session.chunk_size,8*1024*1024)
        while(offset<file.size) {
          const chunk=file.slice(offset,Math.min(offset+chunkSize,file.size))
          const result=await storageApi<{received:number}>(`/api/uploads/${session.id}`,{method:"PUT",body:chunk,headers:{"Content-Type":"application/octet-stream","Upload-Offset":String(offset)},signal:controller.signal})
          if(result.received<=offset||result.received>file.size)throw new Error("Tiến trình tải lên không khớp. Hãy tải lại tệp.")
          offset=result.received
          setUpload({name:file.name,percent:Math.round(offset/Math.max(1,file.size)*100),index:index+1,count:files.length})
        }
        await storageApi(`/api/uploads/${session.id}/complete`,{method:"POST",signal:controller.signal});activeId=null;completed++
      }
      setNotice(replaceItem?"Đã cập nhật tệp và lưu phiên bản trước.":`Đã tải lên ${completed} tệp.`)
    }catch(cause){uploadError=controller.signal.aborted?`Đã dừng tải lên. ${completed?`${completed} tệp đã hoàn tất được giữ lại.`:"Bạn có thể chọn tệp để tải lại."}`:message(cause);setError(uploadError)}
    finally {
      if(activeId!==null)await storageApi(`/api/uploads/${activeId}`,{method:"DELETE"}).catch(()=>{})
      uploadControl.current=null;setUpload(null)
      if(fileInput.current)fileInput.current.value=""
      if(folderInput.current)folderInput.current.value=""
      await latestRefresh.current();await updateUsage()
      if(uploadError)setError(uploadError)
    }
  }
  const actions=(item:FileItem)=><DropdownMenu><DropdownMenuTrigger asChild><Button variant="ghost" size="icon" aria-label={`Thao tác với ${item.name}`} disabled={busy}><MoreHorizontal aria-hidden/></Button></DropdownMenuTrigger><DropdownMenuContent align="end"><DropdownMenuGroup>
    {!trash&&!item.is_folder&&<DropdownMenuItem asChild><a href={`/api/files/${item.id}/download`}><Download aria-hidden/>Tải xuống</a></DropdownMenuItem>}
    {!trash&&!item.is_folder&&benefits?.version_days? <DropdownMenuItem onSelect={()=>open("replace",item)}><Upload aria-hidden/>Tải phiên bản mới</DropdownMenuItem>:null}
    {trash?<DropdownMenuItem onSelect={()=>void mutate(`/api/files/${item.id}/restore`,{method:"POST"},"Đã khôi phục tệp hoặc thư mục.")}><Undo2 aria-hidden/>Khôi phục</DropdownMenuItem>:<><DropdownMenuItem onSelect={()=>open("rename",item)}><Pencil aria-hidden/>Đổi tên</DropdownMenuItem><DropdownMenuItem onSelect={()=>open("move",item)}><FolderUp aria-hidden/>Di chuyển</DropdownMenuItem><DropdownMenuItem onSelect={()=>open("share",item)}><Share2 aria-hidden/>Chia sẻ</DropdownMenuItem></>}
    <DropdownMenuItem onSelect={()=>open("details",item)}><Info aria-hidden/>Thông tin</DropdownMenuItem>{trash&&<><DropdownMenuSeparator/><DropdownMenuItem onSelect={()=>open("purge",item)}><Trash2 aria-hidden/>Xóa vĩnh viễn</DropdownMenuItem></>}
    {!trash&&<><DropdownMenuSeparator/><DropdownMenuItem onSelect={()=>open("trash",item)}><Trash2 aria-hidden/>Chuyển vào thùng rác</DropdownMenuItem></>}
  </DropdownMenuGroup></DropdownMenuContent></DropdownMenu>

  return <section className="native-files" aria-label={title}>
    <PageHeading title={title} description={trash?"Khôi phục những tệp và thư mục đã xóa.":mode==="shared"?"Quản lý các liên kết bạn đã chia sẻ.":"Sắp xếp, lưu trữ và chia sẻ ngay trong CloudBox."} action={writable?<div className="files-primary-actions"><Button variant="outline" onClick={()=>open("new")} disabled={!!upload}><FolderPlus data-icon="inline-start" aria-hidden/>Thư mục mới</Button><Button onClick={()=>fileInput.current?.click()} disabled={!!upload}><Upload data-icon="inline-start" aria-hidden/>Tải tệp lên</Button></div>:undefined}/>
    <input ref={fileInput} type="file" multiple className="sr-only" tabIndex={-1} aria-label="Chọn tệp tải lên" onChange={event=>void uploadFiles(Array.from(event.target.files??[]))}/>
    <input ref={element=>{folderInput.current=element;if(element)element.setAttribute("webkitdirectory","")}} type="file" multiple className="sr-only" tabIndex={-1} aria-label="Chọn thư mục tải lên" onChange={event=>void uploadFiles(Array.from(event.target.files??[]))}/>
    {error&&<Notice kind="error" title="Cần kiểm tra lại">{error}</Notice>}{notice&&<Notice kind="ok" title={notice}/>}
    {upload&&<div className="files-upload-status" role="status" aria-live="polite"><div><Upload aria-hidden/><strong>Đang tải {upload.name}</strong><span>{upload.index}/{upload.count} tệp · {upload.percent}%</span><Button variant="ghost" size="icon" aria-label="Dừng tải lên" onClick={()=>uploadControl.current?.abort()}><X aria-hidden/></Button></div><Progress value={upload.percent} aria-label={`Đang tải ${upload.name}: ${upload.percent}%`}/></div>}
    {trash&&<p className="files-policy">Tệp trong thùng rác vẫn được tính vào dung lượng. Xóa vĩnh viễn để giải phóng dung lượng; thao tác này không thể hoàn tác.</p>}
    {mode!=="shared"&&<div className="files-toolbar"><nav className="files-breadcrumb" aria-label="Đường dẫn thư mục"><Button variant="ghost" size="sm" onClick={()=>{setParent(null);setQuery("")}}><Folder data-icon="inline-start" aria-hidden/>{trash?"Thùng rác":"Tệp của tôi"}</Button>{listing?.ancestors.map(part=><span key={part.id}><ChevronRight aria-hidden/><Button variant="ghost" size="sm" onClick={()=>{setParent(part.id);setQuery("")}}>{part.name}</Button></span>)}</nav><div className="files-tools"><div className="files-search"><Search aria-hidden/><Input type="search" aria-label="Tìm tệp hoặc thư mục" placeholder="Tìm tệp hoặc thư mục" value={query} onChange={event=>setQuery(event.target.value)}/></div><label className="sr-only" htmlFor="file-sort">Sắp xếp tệp</label><select id="file-sort" className="files-sort" value={sort} onChange={event=>setSort(event.target.value)}><option value="name">Tên A–Z</option><option value="name_desc">Tên Z–A</option><option value="modified">Mới sửa đổi</option><option value="size">Kích thước</option></select><Button variant="ghost" size="icon" onClick={()=>void refresh()} aria-label="Cập nhật danh sách" disabled={loading}><RefreshCw aria-hidden/></Button></div></div>}
    {writable&&<div className="files-upload-folder"><Button variant="ghost" size="sm" disabled={!!upload} onClick={()=>folderInput.current?.click()}><FolderUp data-icon="inline-start" aria-hidden/>Tải thư mục lên</Button><span>{listing?.usage?`${bytes(listing.usage.used)} / ${bytes(listing.usage.total)}`:""}</span></div>}
    <div className="files-surface" data-dragging={dragging||undefined} onDragOver={event=>{if(writable&&!upload){event.preventDefault();setDragging(true)}}} onDragLeave={event=>{if(!event.currentTarget.contains(event.relatedTarget as Node))setDragging(false)}} onDrop={event=>{event.preventDefault();setDragging(false);if(writable&&!upload)void uploadFiles(Array.from(event.dataTransfer.files))}}>
      {dragging&&<div className="files-drop-overlay"><Upload aria-hidden/><strong>Thả tệp để tải lên thư mục này</strong></div>}
      {loading?<div className="files-loading" role="status"><span className="sr-only">Đang tải danh sách…</span>{[0,1,2,3].map(key=><Skeleton key={key} className="h-14 w-full"/>)}</div>:error&&((mode==="shared"&&shares.length===0)||(mode!=="shared"&&!listing))?<EmptyState title="Chưa tải được danh sách" description="Kiểm tra kết nối rồi thử cập nhật lại."><Button variant="outline" onClick={()=>void refresh()}><RefreshCw data-icon="inline-start" aria-hidden/>Thử lại</Button></EmptyState>:mode==="shared"?<SharedList shares={shares} busy={busy} revoke={id=>void revokeShare(id)}/>:listing?.items.length?<Table><TableHeader><TableRow><TableHead>Tên</TableHead><TableHead className="files-date-column">{trash?"Ngày xóa":"Sửa đổi"}</TableHead><TableHead className="files-size-column">Kích thước</TableHead><TableHead><span className="sr-only">Thao tác</span></TableHead></TableRow></TableHeader><TableBody>{listing.items.map(item=><TableRow key={item.id}><TableCell><button className="file-name" onClick={()=>item.is_folder&&!trash?(setParent(item.id),setQuery("")):open("details",item)}>{item.is_folder?<Folder aria-hidden/>:<File aria-hidden/>}<span>{item.name}</span></button></TableCell><TableCell className="files-date-column">{date(trash?item.deleted_at:item.modified_at)}</TableCell><TableCell className="files-size-column">{item.is_folder?"—":bytes(item.size)}</TableCell><TableCell className="files-row-actions">{actions(item)}</TableCell></TableRow>)}</TableBody></Table>:<EmptyState title={term?"Chưa tìm thấy tệp phù hợp":trash?"Thùng rác đang trống":"Thư mục đang trống"} description={term?"Thử tên khác hoặc xóa nội dung tìm kiếm.":trash?"Các tệp bạn chuyển vào thùng rác sẽ xuất hiện ở đây.":"Tải tệp đầu tiên lên hoặc tạo thư mục để bắt đầu."}>{writable&&!term&&<Button onClick={()=>fileInput.current?.click()} disabled={!!upload}><Upload data-icon="inline-start" aria-hidden/>Tải tệp lên</Button>}</EmptyState>}
    </div>
    {mode!=="shared"&&listing&&<div className="files-pagination"><span>{listing.items.length} / {listing.total_count??listing.items.length} mục</span>{listing.has_more&&<Button variant="outline" disabled={loadingMore} onClick={()=>void loadMore()}>{loadingMore?<Loader2 data-icon="inline-start" className="animate-spin" aria-hidden/>:null}{loadingMore?"Đang tải…":"Tải thêm"}</Button>}</div>}
    <Dialog open={dialog!==null} onOpenChange={isOpen=>{if(!isOpen&&!busy)closeDialog()}}><DialogContent><DialogHeader><DialogTitle>{dialog==="new"?"Tạo thư mục":dialog==="rename"?"Đổi tên":dialog==="move"?"Di chuyển":dialog==="share"?"Chia sẻ bằng liên kết":dialog==="trash"?"Chuyển vào thùng rác?":dialog==="purge"?"Xóa vĩnh viễn?":dialog==="replace"?"Tải phiên bản mới":dialog==="version_restore"?"Khôi phục phiên bản":"Thông tin tệp"}</DialogTitle><DialogDescription>{dialog==="share"?"Người có liên kết cần đáp ứng điều kiện bạn đặt để xem và tải xuống. Bạn có thể thu hồi bất cứ lúc nào.":selected?.name??"Sắp xếp tệp của bạn trong một thư mục mới."}</DialogDescription></DialogHeader>
      {dialogError&&<Notice kind="error" title="Chưa thể hoàn tất">{dialogError}</Notice>}
      {(dialog==="new"||dialog==="rename")&&<form onSubmit={submitName}><FieldGroup><Field><FieldLabel htmlFor="file-name">{dialog==="new"?"Tên thư mục":"Tên mới"}</FieldLabel><Input id="file-name" value={name} onChange={event=>setName(event.target.value)} maxLength={255} required autoFocus disabled={busy}/></Field></FieldGroup><DialogFooter className="mt-6"><Button type="button" variant="outline" onClick={()=>closeDialog()} disabled={busy}>Hủy</Button><Button type="submit" disabled={busy||!name.trim()}>{busy&&<Loader2 data-icon="inline-start" className="animate-spin" aria-hidden/>}{dialog==="new"?"Tạo thư mục":"Lưu tên"}</Button></DialogFooter></form>}
      {dialog==="move"&&<><div className="files-move-picker"><nav aria-label="Thư mục đích"><Button variant="ghost" size="sm" onClick={()=>void loadMove(null)}><Folder data-icon="inline-start" aria-hidden/>Tệp của tôi</Button>{moveList?.ancestors.map(part=><Button key={part.id} variant="ghost" size="sm" onClick={()=>void loadMove(part.id)}><ChevronRight data-icon="inline-start" aria-hidden/>{part.name}</Button>)}</nav>{moveList?moveList.items.filter(item=>item.is_folder&&item.id!==selected?.id).map(item=><Button key={item.id} variant="ghost" onClick={()=>void loadMove(item.id)}><Folder data-icon="inline-start" aria-hidden/>{item.name}<ChevronRight data-icon="inline-end" aria-hidden/></Button>):<Skeleton className="h-12"/>}{moveList&&!moveList.items.some(item=>item.is_folder&&item.id!==selected?.id)&&<p>Không có thư mục con. Có thể chọn vị trí hiện tại.</p>}{moveList?.has_more&&<Button variant="outline" disabled={moveLoadingMore} onClick={()=>void moreMoveFolders()}>{moveLoadingMore?"Đang tải…":"Tải thêm thư mục"}</Button>}</div><DialogFooter><Button variant="outline" onClick={()=>closeDialog()} disabled={busy}>Hủy</Button><Button disabled={busy||!moveList||moveParent===selected?.parent_id} onClick={()=>selected&&void mutate(`/api/files/${selected.id}`,{method:"PATCH",body:jsonBody({parent_id:moveParent})},"Đã di chuyển.")}>Di chuyển đến đây</Button></DialogFooter></>}
      {dialog==="share"&&<div className="files-share-content"><FieldGroup>{benefits?.expiring_links&&<Field><FieldLabel htmlFor="share-expiry">Hết hạn vào (giờ trên thiết bị)</FieldLabel><Input id="share-expiry" type="datetime-local" value={shareExpiry} onChange={event=>setShareExpiry(event.target.value)}/><p className="files-policy">Để trống nếu không đặt thời hạn. Hết hạn áp dụng cả xem và tải xuống.</p></Field>}{benefits?.password_links&&<Field><FieldLabel htmlFor="share-password">Mật khẩu liên kết (không bắt buộc)</FieldLabel><Input id="share-password" type="password" autoComplete="new-password" minLength={8} maxLength={128} value={sharePassword} onChange={event=>setSharePassword(event.target.value)}/><p className="files-policy">Ít nhất 8 ký tự. Gửi mật khẩu cho người nhận qua kênh riêng.</p></Field>}</FieldGroup>{newLink&&<FieldGroup><Field><FieldLabel htmlFor="share-url">Liên kết chỉ đọc</FieldLabel><Input id="share-url" value={newLink} readOnly onFocus={event=>event.currentTarget.select()}/><Button variant="outline" onClick={()=>void copyLink()}>{copied?<Check data-icon="inline-start" aria-hidden/>:<Copy data-icon="inline-start" aria-hidden/>}{copied?"Đã sao chép":"Sao chép liên kết"}</Button></Field></FieldGroup>}<Button onClick={()=>void createShare()} disabled={busy||sharesLoading}><Link2 data-icon="inline-start" aria-hidden/>{newLink?"Tạo liên kết khác":"Tạo liên kết chia sẻ"}</Button>{sharesLoading?<Skeleton className="h-12"/>:fileShares.filter(item=>!item.revoked).map((item,index)=><div className="files-share-row" key={item.id}><span>Liên kết {index+1}<small>Tạo ngày {date(item.created_at)} · Chỉ đọc{item.password_protected?" · Có mật khẩu":""}{item.expires_at?` · Hết hạn ${when(item.expires_at)}`:""}</small>{item.views!==undefined&&<small>{item.views} lượt xem · {item.downloads??0} lượt tải · từ {date(item.stats_since??null)}</small>}</span><Button variant="outline" size="sm" disabled={busy} onClick={()=>void revokeShare(item.id,true)}>Thu hồi</Button></div>)}<p className="files-policy">Liên kết mới chỉ được hiển thị khi tạo. Hãy sao chép trước khi đóng cửa sổ.</p></div>}
      {dialog==="details"&&selected&&<dl className="files-details"><div><dt>Loại</dt><dd>{selected.is_folder?"Thư mục":selected.mime_type||"Tệp"}</dd></div>{!selected.is_folder&&<div><dt>Kích thước</dt><dd>{bytes(selected.size)}</dd></div>}<div><dt>Sửa đổi</dt><dd>{date(selected.modified_at)}</dd></div>{selected.deleted_at&&<div><dt>Ngày xóa</dt><dd>{date(selected.deleted_at)}</dd></div>}{!trash&&!selected.is_folder&&<Button asChild><a href={`/api/files/${selected.id}/download`}><Download data-icon="inline-start" aria-hidden/>Tải xuống</a></Button>}{versionsLoading&&<Skeleton className="h-12"/>}{versions.length>0&&<div className="files-versions"><h3>Phiên bản trước</h3><p className="files-policy">Phiên bản được lưu vẫn tính vào dung lượng. Các bản lịch sử cũ được giữ theo chính sách chuyển đổi.</p>{versions.map(version=><div key={version.id}><span>{date(version.created_at)}<small>{bytes(version.size)}{version.source==="native"?" · Tự động":" · Lịch sử được giữ"}{version.expires_at?` · Khả dụng đến ${date(version.expires_at)}`:""}</small></span>{version.available?<div className="files-version-actions"><Button variant="outline" size="sm" asChild><a href={`/api/files/${selected.id}/versions/${version.id}/download`}><Download data-icon="inline-start" aria-hidden/>Tải xuống</a></Button>{version.restorable&&<Button variant="outline" size="sm" disabled={busy} onClick={()=>{setRestoreVersion(version);setDialog("version_restore");setDialogError("")}}><Undo2 data-icon="inline-start" aria-hidden/>Khôi phục</Button>}</div>:<span>Không khả dụng</span>}</div>)}</div>}</dl>}
      {dialog==="replace"&&selected&&<><p className="files-policy">Cập nhật “{selected.name}” bằng tệp mới. Nội dung hiện tại được giữ trong lịch sử phiên bản. Tệp và các phiên bản đều tính vào dung lượng; không tự xóa dữ liệu cũ để lấy chỗ.</p><FieldGroup><Field><FieldLabel htmlFor="replacement-file">Chọn nội dung mới</FieldLabel><Input id="replacement-file" type="file" onChange={event=>setReplacement(event.target.files?.[0]??null)}/></Field></FieldGroup><DialogFooter><Button variant="outline" disabled={!!upload} onClick={()=>closeDialog()}>Hủy</Button><Button disabled={!replacement||!!upload} onClick={()=>{if(replacement){closeDialog();void uploadFiles([replacement],selected)}}}>Cập nhật và lưu phiên bản</Button></DialogFooter></>}
      {dialog==="version_restore"&&selected&&restoreVersion&&<><p className="files-policy">Khôi phục “{selected.name}” về bản ngày {date(restoreVersion.created_at)}? Nội dung hiện tại sẽ được giữ thành một phiên bản để bạn có thể quay lại. Thao tác cần đủ dung lượng.</p><DialogFooter><Button variant="outline" disabled={busy} onClick={()=>open("details",selected)}>Quay lại</Button><Button disabled={busy} onClick={()=>void mutate(`/api/files/${selected.id}/versions/${restoreVersion.id}/restore`,{method:"POST"},"Đã khôi phục phiên bản và giữ bản trước đó.")}>Khôi phục phiên bản</Button></DialogFooter></>}
      {dialog==="trash"&&selected&&<><p className="files-policy">Bạn có thể khôi phục sau trong Thùng rác. Dung lượng vẫn được tính trong hạn mức.</p><DialogFooter><Button variant="outline" disabled={busy} onClick={()=>closeDialog()}>Hủy</Button><Button disabled={busy} onClick={()=>void mutate(`/api/files/${selected.id}/trash`,{method:"POST"},"Đã chuyển vào thùng rác.")}><Trash2 data-icon="inline-start" aria-hidden/>Chuyển vào thùng rác</Button></DialogFooter></>}
      {dialog==="purge"&&selected&&<><Notice kind="error" title="Không thể khôi phục sau khi xóa">Tệp hoặc thư mục này cùng nội dung bên trong và các phiên bản được lưu sẽ bị xóa vĩnh viễn. Các liên kết chia sẻ liên quan sẽ không còn truy cập được.</Notice><DialogFooter><Button variant="outline" disabled={busy} onClick={()=>closeDialog()}>Hủy</Button><Button variant="destructive" disabled={busy} onClick={()=>void mutate(`/api/files/${selected.id}`,{method:"DELETE",body:jsonBody({confirm_id:selected.id})},"Đã xóa vĩnh viễn và cập nhật dung lượng.")}><Trash2 data-icon="inline-start" aria-hidden/>Xóa vĩnh viễn</Button></DialogFooter></>}
    </DialogContent></Dialog>
  </section>
}

function SharedList({shares,busy,revoke}:{shares:ShareItem[];busy:boolean;revoke:(id:string)=>void}) {
  return shares.length?<><p className="files-policy">Số liệu ghi nhận lượt mở và yêu cầu tải, không phải số người riêng biệt hoặc xác nhận tải xong. Chỉ ghi nhận trong thời gian chủ liên kết có quyền lợi thống kê.</p><Table><TableHeader><TableRow><TableHead>Tệp hoặc thư mục</TableHead><TableHead>Ngày chia sẻ</TableHead><TableHead>Quyền</TableHead><TableHead><span className="sr-only">Thao tác</span></TableHead></TableRow></TableHeader><TableBody>{shares.map(item=><TableRow key={item.id}><TableCell><span className="file-name">{item.is_folder?<Folder aria-hidden/>:<File aria-hidden/>}<span>{item.name??"Liên kết chia sẻ"}</span></span></TableCell><TableCell>{date(item.created_at)}</TableCell><TableCell>Chỉ đọc{item.password_protected&&<small className="block">Có mật khẩu</small>}{item.expires_at&&<small className="block">Hết hạn {when(item.expires_at)}</small>}{item.views!==undefined&&<small className="block">{item.views} lượt xem · {item.downloads??0} lượt yêu cầu tải{item.stats_since?` · Từ ${when(item.stats_since)}`:" · Chưa có dữ liệu"}</small>}</TableCell><TableCell><Button variant="outline" size="sm" disabled={busy} onClick={()=>revoke(item.id)}>Thu hồi</Button></TableCell></TableRow>)}</TableBody></Table></>:<EmptyState title="Chưa có liên kết chia sẻ" description="Mở menu của một tệp hoặc thư mục trong kho để tạo liên kết chia sẻ."><Button variant="outline" asChild><a href="#storage"><ArrowLeft data-icon="inline-start" aria-hidden/>Về tệp của tôi</a></Button></EmptyState>
}
