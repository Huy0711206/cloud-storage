import {useState} from "react"
import {FileText} from "lucide-react"
import {Button} from "@/components/ui/button"
import {Card, CardHeader, CardTitle, CardDescription, CardContent} from "@/components/ui/card"
import {Field, FieldLabel} from "@/components/ui/field"
import {Input} from "@/components/ui/input"
import {Table, TableHeader, TableBody, TableHead, TableRow, TableCell, TableCaption} from "@/components/ui/table"
import {ToggleGroup, ToggleGroupItem} from "@/components/ui/toggle-group"
import {NativeSelect, NativeSelectOption} from "@/components/ui/native-select"
import {EmptyState, PageHeading, StatusBadge, money, date, quota} from "@/shared/ui"
import type {Order} from "@/shared/types"


export function OrdersPage({orders}:{orders:Order[]}) {
 const [query,setQuery]=useState(""),[filter,setFilter]=useState("all")
 const visible=orders.filter(o=>(filter==="all"||o.status===filter)&&(o.txn_ref+" "+o.plan.name).toLowerCase().includes(query.toLowerCase()))
 const exportCsv=()=>{
  const rows=[["Mã đơn","Gói","Thời hạn","Số tiền VND","Trạng thái","Ngày tạo"],...visible.map(o=>[o.txn_ref,o.plan.name,o.months,o.amount_vnd,o.status,date(o.created_at)])]
  const quote=(v:unknown)=>'"'+String(v).replace(/"/g,'""')+'"'
  const blob=new Blob(["\uFEFF"+rows.map(r=>r.map(quote).join(",")).join("\r\n")],{type:"text/csv;charset=utf-8"})
  const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download="cloudbox-don-hang.csv";a.click();URL.revokeObjectURL(url)
 }
 return <div className="flex min-w-0 flex-col gap-7"><PageHeading title="Lịch sử đơn hàng" description="Theo dõi các giao dịch và gói dịch vụ của bạn." action={<Button variant="outline" disabled={!visible.length} onClick={exportCsv}><FileText data-icon="inline-start" aria-hidden/>Xuất CSV</Button>}/><Card className="min-w-0"><CardHeader><CardTitle>Đơn hàng của bạn</CardTitle><CardDescription>Hiển thị tối đa 20 đơn gần nhất.</CardDescription></CardHeader><CardContent className="flex min-w-0 flex-col gap-5"><div className="order-filters"><Field><FieldLabel htmlFor="order-search">Tìm đơn hàng</FieldLabel><Input id="order-search" type="search" placeholder="Mã đơn hoặc tên gói…" value={query} onChange={e=>setQuery(e.target.value)}/></Field><Field className="order-filter-mobile"><FieldLabel htmlFor="order-status">Trạng thái đơn hàng</FieldLabel><NativeSelect id="order-status" value={filter} onChange={e=>setFilter(e.target.value)}><NativeSelectOption value="all">Tất cả trạng thái</NativeSelectOption><NativeSelectOption value="paid">Đã thanh toán</NativeSelectOption><NativeSelectOption value="pending">Đang chờ</NativeSelectOption><NativeSelectOption value="failed">Thất bại</NativeSelectOption></NativeSelect></Field><ToggleGroup className="order-filter-desktop" type="single" value={filter} onValueChange={v=>v&&setFilter(v)} variant="outline" aria-label="Lọc trạng thái đơn hàng"><ToggleGroupItem value="all">Tất cả</ToggleGroupItem><ToggleGroupItem value="paid">Đã thanh toán</ToggleGroupItem><ToggleGroupItem value="pending">Đang chờ</ToggleGroupItem><ToggleGroupItem value="failed">Thất bại</ToggleGroupItem></ToggleGroup></div>{visible.length?<OrdersTable orders={visible}/>:<EmptyState title={orders.length?"Không tìm thấy đơn hàng":"Chưa có đơn hàng"} description={orders.length?"Thử tìm bằng mã đơn hoặc chọn trạng thái khác.":"Các giao dịch sẽ xuất hiện tại đây khi bạn chọn một gói trả phí."}>{orders.length?<Button variant="outline" onClick={()=>{setQuery("");setFilter("all")}}>Xóa bộ lọc</Button>:<Button variant="outline" asChild><a href="#plans">Xem các gói dịch vụ</a></Button>}</EmptyState>}<p className="sr-only" role="status">{visible.length} đơn hàng phù hợp</p></CardContent></Card></div>
}
export function OrdersTable({orders}:{orders:Order[]}) { return <Table><TableCaption className="sr-only">Chi tiết đơn hàng CloudBox</TableCaption><TableHeader><TableRow><TableHead>Mã đơn hàng</TableHead><TableHead>Gói dịch vụ</TableHead><TableHead>Ngày tạo</TableHead><TableHead>Trạng thái</TableHead><TableHead className="text-right">Số tiền</TableHead></TableRow></TableHeader><TableBody>{orders.map(o=><TableRow key={o.id}><TableCell className="whitespace-nowrap font-medium">{o.txn_ref}</TableCell><TableCell><p className="font-medium">{o.plan.name}</p><p className="mt-1 text-xs text-muted-foreground">{o.months} tháng · {quota(o.plan.quota_gb)}</p></TableCell><TableCell className="whitespace-nowrap">{date(o.created_at)}</TableCell><TableCell><StatusBadge status={o.status}/></TableCell><TableCell className="whitespace-nowrap text-right font-medium tabular-nums">{money(o.amount_vnd)}</TableCell></TableRow>)}</TableBody></Table> }

