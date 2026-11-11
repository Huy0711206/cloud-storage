import { useEffect, useId, useRef, useState, type ComponentProps, type ReactNode } from "react"
import { AlertCircle, CheckCircle2, Cloud, Inbox, Loader2, Monitor, Moon, Sun, Eye, EyeOff } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert"
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { InputGroup, InputGroupAddon, InputGroupButton, InputGroupInput } from "@/components/ui/input-group"
import { cn } from "@/lib/utils"

import {csrfToken} from "@/shared/csrf"

export const money = (n:number) => new Intl.NumberFormat("vi-VN", {style:"currency",currency:"VND",maximumFractionDigits:0}).format(n)
export const quota = (n:number) => n >= 1024 && n % 1024 === 0 ? String(n/1024)+" TB" : String(n)+" GB"
export const date = (value:string|null) => value ? new Intl.DateTimeFormat("vi-VN",{day:"2-digit",month:"2-digit",year:"numeric",timeZone:"Asia/Ho_Chi_Minh"}).format(new Date(value)) : "—"
export const bytes = (n:number) => { if(!n) return "0 B"; const units=["B","KB","MB","GB","TB"]; const i=Math.min(Math.floor(Math.log(n)/Math.log(1024)),4); return new Intl.NumberFormat("vi-VN",{maximumFractionDigits:i>0?2:0}).format(n/1024**i)+" "+units[i] }
export function Brand({compact=false}:{compact?:boolean}) { return <a href="/" className={cn("brand",compact&&"brand-compact")} aria-label="CloudBox — Trang chủ"><span className="brand-symbol"><Cloud aria-hidden /></span><span>CloudBox<span className="brand-dot">.</span></span></a> }

export function PageHeading({title,description,action}:{title:string;description?:string;action?:ReactNode}) { return <div className="page-heading"><div><h1>{title}</h1>{description&&<p>{description}</p>}</div>{action&&<div className="page-heading-action">{action}</div>}</div> }

export function Form({children,onSubmit,...props}:ComponentProps<"form">) {
 const [pending,setPending]=useState(false)
 const [offline,setOffline]=useState(false)
 const ref=useRef<HTMLFormElement>(null)
 useEffect(()=>{const reset=()=>setPending(false);window.addEventListener("pageshow",reset);return()=>window.removeEventListener("pageshow",reset)},[])
 useEffect(()=>{ref.current?.querySelectorAll<HTMLButtonElement>('button[type="submit"]').forEach(button=>{button.disabled=pending})},[pending])
 return <form {...props} ref={ref} aria-busy={pending} data-pending={pending||undefined} onSubmit={event=>{
   onSubmit?.(event); if(event.defaultPrevented)return
   if(!navigator.onLine && !["localhost","127.0.0.1","[::1]"].includes(location.hostname)){event.preventDefault();setOffline(true);return}
   setOffline(false);setPending(true)
 }}>{(props.method??"get").toLowerCase()!=="get"&&<input type="hidden" name="csrf_token" value={csrfToken()}/ >}{children}{pending&&<p className="submit-feedback" role="status"><Loader2 className="size-4 animate-spin" aria-hidden/>Đang xử lý…</p>}{offline&&<p className="form-error" role="alert">Chưa có kết nối Internet. Kiểm tra mạng rồi thử lại.</p>}</form>
}

export function StatusBadge({status}:{status:string}) {
 const map:Record<string,[string,string]>={paid:["Đã thanh toán","success"],pending:["Chờ thanh toán","warning"],failed:["Thất bại","danger"],verified:["Đã xác thực","success"],active:["Đang hoạt động","success"],locked:["Đã khóa","danger"]}
 const [label,tone]=map[status]||[status,"neutral"]
 return <Badge variant="outline" data-tone={tone}>{tone==="success"?<CheckCircle2 data-icon="inline-start" aria-hidden/>:tone==="danger"?<AlertCircle data-icon="inline-start" aria-hidden/>:null}{label}</Badge>
}

export function EmptyState({title,description,children}:{title:string;description:string;children?:ReactNode}) {
 return <Empty><EmptyHeader><EmptyMedia variant="icon"><Inbox aria-hidden/></EmptyMedia><EmptyTitle>{title}</EmptyTitle><EmptyDescription>{description}</EmptyDescription></EmptyHeader>{children&&<EmptyContent>{children}</EmptyContent>}</Empty>
}

export function Notice({kind="info",title,children}:{kind?:string;title:string;children?:ReactNode}) {
 return <Alert tabIndex={-1} variant={kind==="error"?"destructive":"default"} data-tone={kind==="ok"?"success":undefined}>{kind==="error"?<AlertCircle aria-hidden/>:<CheckCircle2 aria-hidden/>}<AlertTitle>{title}</AlertTitle>{children&&<AlertDescription>{children}</AlertDescription>}</Alert>
}


export function ThemeMenu() {
 const name=useId()
 const [theme,setTheme]=useState(()=>{try{const value=localStorage.getItem("cloudbox-theme");return ["light","dark","system"].includes(value||"")?value!:"system"}catch{return "system"}})
 useEffect(()=>{
  const media=matchMedia("(prefers-color-scheme: dark)")
  const apply=()=>{const dark=theme==="dark"||(theme==="system"&&media.matches);document.documentElement.classList.toggle("dark",dark);document.documentElement.style.colorScheme=dark?"dark":"light"}
  apply();try{localStorage.setItem("cloudbox-theme",theme)}catch{}
  media.addEventListener("change",apply);return()=>media.removeEventListener("change",apply)
 },[theme])
 const options=[{value:"light",label:"Giao diện sáng",icon:Sun},{value:"dark",label:"Giao diện tối",icon:Moon},{value:"system",label:"Theo thiết bị",icon:Monitor}]
 return <fieldset className="cb-theme"><legend>Giao diện</legend>{options.map(({value,label,icon:Icon})=><label key={value} title={label}><input type="radio" name={name} value={value} checked={theme===value} onChange={()=>setTheme(value)}/><span><Icon aria-hidden/><span className="cb-theme-name">{label}</span></span></label>)}</fieldset>
}

export function PasswordInput({id,name,autoComplete,required=true,minLength,invalid=false,describedBy}:{id:string;name:string;autoComplete?:string;required?:boolean;minLength?:number;invalid?:boolean;describedBy?:string}) {
 const [visible,setVisible]=useState(false)
 return <InputGroup><InputGroupInput id={id} name={name} type={visible?"text":"password"} required={required} minLength={minLength} autoComplete={autoComplete} aria-invalid={invalid||undefined} aria-describedby={describedBy}/><InputGroupAddon align="inline-end"><InputGroupButton type="button" size="icon-sm" aria-label={visible?"Ẩn mật khẩu":"Hiện mật khẩu"} aria-pressed={visible} onClick={()=>setVisible(!visible)}>{visible?<EyeOff aria-hidden/>:<Eye aria-hidden/>}</InputGroupButton></InputGroupAddon></InputGroup>
}
