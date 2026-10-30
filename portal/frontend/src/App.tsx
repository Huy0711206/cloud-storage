import { lazy, Suspense, useEffect, useState, type CSSProperties, type ReactNode, type ComponentType } from "react"
import { ArrowUpRight, ChevronDown, CircleHelp, Cloud, CreditCard, FolderOpen, HardDrive, LayoutDashboard, LogOut, PanelLeftClose, Settings2, ShieldCheck, SlidersHorizontal, Sparkles, Users, WifiOff, ReceiptText } from "lucide-react"
import { Sidebar, SidebarContent, SidebarFooter, SidebarGroup, SidebarGroupContent, SidebarGroupLabel, SidebarHeader, SidebarInset, SidebarMenu, SidebarMenuButton, SidebarMenuItem, SidebarProvider, SidebarTrigger, useSidebar } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Progress } from "@/components/ui/progress"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { DropdownMenu, DropdownMenuContent, DropdownMenuGroup, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert"
import { Brand, Form, Notice, ThemeMenu, bytes } from "./shared"
import { Skeleton } from "@/components/ui/skeleton"
const DashboardPage=lazy(()=>import("./dashboard-pages").then(module=>({default:module.DashboardPage})))
const AdminPage=lazy(()=>import("./admin-pages").then(module=>({default:module.AdminPage})))
const PublicPage=lazy(()=>import("./public-pages").then(module=>({default:module.PublicPage})))
import type { PageData } from "./types"

const sections=[{id:"overview",label:"Tổng quan",icon:LayoutDashboard},{id:"storage",label:"Kho lưu trữ",icon:FolderOpen},{id:"plans",label:"Gói dịch vụ",icon:Sparkles},{id:"orders",label:"Đơn hàng",icon:ReceiptText},{id:"settings",label:"Tài khoản & bảo mật",icon:Settings2}]
const adminSections=[{id:"admin_overview",href:"/admin",label:"Tổng quan",icon:LayoutDashboard},{id:"admin_users",href:"/admin/users",label:"Người dùng",icon:Users},{id:"admin_orders",href:"/admin/orders",label:"Đơn hàng",icon:CreditCard},{id:"admin_plans",href:"/admin/plans",label:"Gói dịch vụ",icon:SlidersHorizontal}]

type DashboardRenderer=ComponentType<{data:PageData;section:string}>
type PublicRenderer=ComponentType<{data:PageData}>
type ToolbarRenderer=ComponentType<{children:ReactNode}>
function DefaultToolbar({children}:{children:ReactNode}){return <div className="flex shrink-0 items-center gap-1">{children}</div>}
export function App({data,DashboardComponent=DashboardPage,PublicComponent=PublicPage,ToolbarSurface=DefaultToolbar}:{data:PageData;DashboardComponent?:DashboardRenderer;PublicComponent?:PublicRenderer;ToolbarSurface?:ToolbarRenderer}) {
 useEffect(()=>{if(data.error||data.flashes.some(([kind])=>kind==="error")){document.querySelector<HTMLElement>("[role=alert]")?.focus()}},[data])
 useEffect(()=>{if(data.page!=="dashboard"&&!data.page.startsWith("admin_")){const titles:Record<string,string>={home:"Lưu trữ đám mây",login:"Đăng nhập",register:"Tạo tài khoản"};document.title=(data.title||titles[data.page]||"CloudBox")+" · CloudBox"}},[data.page,data.title])
 const isWorkspace=data.page==="dashboard"||data.page.startsWith("admin_")
 return <Suspense fallback={<PageSkeleton/>}><a className="skip-link" href="#main-content" onClick={event=>{event.preventDefault();document.getElementById("main-content")?.focus()}}>Chuyển đến nội dung chính</a>{isWorkspace?<Workspace data={data} DashboardComponent={DashboardComponent} ToolbarSurface={ToolbarSurface}/>:<PublicLayout data={data}><PublicComponent data={data}/></PublicLayout>}</Suspense>
}
function OfflineBanner() {
 const [online,setOnline]=useState(navigator.onLine)
 useEffect(()=>{const update=()=>setOnline(navigator.onLine);window.addEventListener("online",update);window.addEventListener("offline",update);return()=>{window.removeEventListener("online",update);window.removeEventListener("offline",update)}},[])
 return online?null:<Alert data-tone="warning"><WifiOff aria-hidden/><AlertTitle>Đang ngoại tuyến</AlertTitle><AlertDescription>Kiểm tra kết nối mạng trước khi thực hiện thay đổi.</AlertDescription></Alert>
}
function Flashes({data}:{data:PageData}) { return <>{data.flashes.map(([kind,message],i)=><Notice key={i} kind={kind} title={message}/>)}</> }
function useSection() {
 const get=()=>sections.some(s=>s.id===window.location.hash.slice(1))?window.location.hash.slice(1):"overview"
 const [section,setSection]=useState(get)
 useEffect(()=>{const update=()=>{setSection(get());window.scrollTo({top:0,behavior:"instant"})};window.addEventListener("hashchange",update);return()=>window.removeEventListener("hashchange",update)},[])
 return section
}
function Workspace({data,DashboardComponent,ToolbarSurface}:{data:PageData;DashboardComponent:DashboardRenderer;ToolbarSurface:ToolbarRenderer}) {
 const section=useSection(),admin=data.user!.role==="admin"
 const label=admin?adminSections.find(s=>s.id===data.page)?.label:sections.find(s=>s.id===section)?.label
 useEffect(()=>{document.title=(label||"Tổng quan")+" · CloudBox"},[label])
 return <SidebarProvider style={{"--sidebar-width":"15.5rem"} as CSSProperties}><CloudSidebar data={data} section={section}/><SidebarInset className="workspace-inset"><header className="workspace-header"><div className="flex min-w-0 items-center gap-3"><SidebarTrigger aria-label="Mở hoặc đóng thanh điều hướng"/><Separator orientation="vertical" className="h-5"/><div className="breadcrumb"><span>{admin?"Quản trị":"Không gian của tôi"}</span><span aria-hidden>/</span><strong>{label}</strong></div></div><ToolbarSurface><ThemeMenu/><HelpDialog/><Separator orientation="vertical" className="mx-2 h-6"/><AccountMenu data={data}/></ToolbarSurface></header><main id="main-content" className="workspace-main" tabIndex={-1}><OfflineBanner/><Flashes data={data}/>{admin?<AdminPage data={data}/>:<DashboardComponent data={data} section={section}/>}<footer className="workspace-footer"><span>CloudBox — Không gian cho dữ liệu của bạn.</span><span className="flex items-center gap-1.5"><ShieldCheck className="size-3.5" aria-hidden/>Kho lưu trữ riêng</span></footer></main></SidebarInset></SidebarProvider>
}
function CloudSidebar({data,section}:{data:PageData;section:string}) {
 const {setOpenMobile,isMobile}=useSidebar(),admin=data.user!.role==="admin"
 const items=admin?adminSections:sections.map(item=>({...item,href:"#"+item.id}))
 return <Sidebar collapsible="offcanvas"><SidebarHeader className="sidebar-brand-area"><Brand/><div className="workspace-selector"><span className="workspace-selector-icon"><Cloud aria-hidden/></span><div><strong>{admin?"CloudBox Admin":"Không gian cá nhân"}</strong><span>{admin?"Quản trị hệ thống":"Tài khoản của bạn"}</span></div></div>{isMobile&&<Button size="icon" variant="ghost" className="absolute right-2 top-4" aria-label="Đóng menu" onClick={()=>setOpenMobile(false)}><PanelLeftClose aria-hidden/></Button>}</SidebarHeader><SidebarContent><SidebarGroup><SidebarGroupLabel>{admin?"Quản trị":"Không gian làm việc"}</SidebarGroupLabel><SidebarGroupContent><SidebarMenu>{items.map(item=><SidebarMenuItem key={item.id}><SidebarMenuButton asChild isActive={admin?data.page===item.id:section===item.id} tooltip={item.label}><a href={item.href} aria-current={(admin?data.page===item.id:section===item.id)?"page":undefined} onClick={()=>setOpenMobile(false)}><item.icon aria-hidden/><span>{item.label}</span></a></SidebarMenuButton></SidebarMenuItem>)}</SidebarMenu></SidebarGroupContent></SidebarGroup><SidebarGroup><SidebarGroupLabel>Truy cập nhanh</SidebarGroupLabel><SidebarMenu><SidebarMenuItem><SidebarMenuButton asChild><a href={data.settings.nc_public_url} target="_blank" rel="noopener noreferrer"><ArrowUpRight aria-hidden/><span>Mở kho lưu trữ</span><span className="sr-only"> (tab mới)</span></a></SidebarMenuButton></SidebarMenuItem><SidebarMenuItem><SidebarMenuButton asChild><a href="/#plans"><CreditCard aria-hidden/><span>Bảng giá CloudBox</span></a></SidebarMenuButton></SidebarMenuItem></SidebarMenu></SidebarGroup></SidebarContent><SidebarFooter className="sidebar-bottom">{!admin&&<div className="sidebar-storage"><div className="flex items-center gap-2"><HardDrive className="size-4" aria-hidden/><strong>Dung lượng lưu trữ</strong></div>{data.usage?<><Progress value={data.usage.percent} aria-label="Dung lượng đã sử dụng"/><p>{bytes(data.usage.used)} <span>/ {bytes(data.usage.total)}</span></p></>:<p>Chưa cập nhật dung lượng</p>}<Button variant="outline" className="w-full" asChild><a href="#plans" onClick={()=>setOpenMobile(false)}>Nâng cấp gói<Sparkles data-icon="inline-end" aria-hidden/></a></Button></div>}<Separator/><div className="sidebar-profile"><Avatar><AvatarFallback>{initials(data.user!.full_name)}</AvatarFallback></Avatar><div><strong>{data.user!.full_name}</strong><span title={data.user!.email}>{data.user!.email}</span></div><Form action="/logout" method="post"><Button type="submit" variant="ghost" size="icon" aria-label="Đăng xuất"><LogOut aria-hidden/></Button></Form></div></SidebarFooter></Sidebar>
}
function initials(name:string) { return name.split(" ").filter(Boolean).map(s=>s[0]).slice(-2).join("").toUpperCase() }
function AccountMenu({data}:{data:PageData}) {
 const admin=data.user!.role==="admin"
 return <><DropdownMenu><DropdownMenuTrigger asChild><Button variant="ghost" className="account-trigger" aria-label="Menu tài khoản"><Avatar><AvatarFallback>{initials(data.user!.full_name)}</AvatarFallback></Avatar><span className="hidden sm:inline">{data.user!.full_name}</span><ChevronDown aria-hidden/></Button></DropdownMenuTrigger><DropdownMenuContent align="end" className="w-64"><DropdownMenuGroup><DropdownMenuLabel><p className="font-medium">{data.user!.full_name}</p><p className="mt-1 truncate text-xs font-normal text-muted-foreground">{data.user!.email}</p></DropdownMenuLabel><DropdownMenuSeparator/><DropdownMenuItem asChild><a href={admin?"/admin":"/dashboard#settings"}><Settings2 aria-hidden/>{admin?"Trang quản trị":"Tài khoản & bảo mật"}</a></DropdownMenuItem><DropdownMenuItem onSelect={()=>(document.getElementById("account-logout") as HTMLFormElement)?.requestSubmit()}><LogOut aria-hidden/>Đăng xuất</DropdownMenuItem></DropdownMenuGroup></DropdownMenuContent></DropdownMenu><Form id="account-logout" action="/logout" method="post" className="hidden"><button type="submit">Đăng xuất</button></Form></>
}
function HelpDialog() { return <Dialog><DialogTrigger asChild><Button variant="ghost" size="icon" aria-label="Trợ giúp CloudBox"><CircleHelp aria-hidden/></Button></DialogTrigger><DialogContent><DialogHeader><DialogTitle>Sử dụng CloudBox</DialogTitle><DialogDescription>Những điều cần biết để bắt đầu.</DialogDescription></DialogHeader><div className="help-topics"><section><FolderOpen aria-hidden/><div><h2>Mở kho lưu trữ</h2><p>Dùng nút “Mở kho lưu trữ”, rồi đăng nhập bằng cùng email và mật khẩu CloudBox.</p></div></section><section><CreditCard aria-hidden/><div><h2>Gói dịch vụ & thanh toán</h2><p>Chọn gói và thời hạn, kiểm tra số tiền rồi tiếp tục qua VNPay. Đơn hàng được lưu trong mục Đơn hàng.</p></div></section><section><ShieldCheck aria-hidden/><div><h2>Bảo vệ tài khoản</h2><p>Xác thực email để kích hoạt kho. Bạn có thể đổi mật khẩu trong mục Tài khoản & bảo mật.</p></div></section></div></DialogContent></Dialog> }
function PublicLayout({data,children}:{data:PageData;children:ReactNode}) {
 return <div className="public-shell"><header className="public-header"><Brand/><nav aria-label="Điều hướng chính"><a href="/#plans" className="public-price-link">Bảng giá</a><ThemeMenu/>{data.user?<Button asChild><a href={data.user.role==="admin"?"/admin":"/dashboard"}>Trang của tôi<ArrowUpRight data-icon="inline-end" aria-hidden/></a></Button>:<><Button variant="ghost" asChild><a href="/login">Đăng nhập</a></Button><Button asChild><a href="/register">Bắt đầu miễn phí</a></Button></>}</nav></header><main id="main-content" className="public-main" tabIndex={-1}><OfflineBanner/><Flashes data={data}/>{children}</main><footer className="public-footer"><Brand compact/><p>Không gian cho dữ liệu của bạn.</p><span>Được xây dựng cùng Nextcloud</span></footer></div>
}

function PageSkeleton(){return <main className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-8" role="status" aria-label="Đang tải giao diện"><span className="sr-only">Đang tải giao diện…</span><Skeleton className="h-9 w-64"/><Skeleton className="h-4 w-80 max-w-full"/><div className="grid gap-6 sm:grid-cols-2"><Skeleton className="h-64"/><Skeleton className="h-64"/></div></main>}
