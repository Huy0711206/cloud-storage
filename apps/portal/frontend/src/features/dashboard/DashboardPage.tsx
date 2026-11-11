import {FileRequestsPage,TeamsPage} from "@/features/storage/CollaborationPages"
import {ArrowRight, HardDrive, Sparkles, CalendarDays} from "lucide-react"
import {Button} from "@/components/ui/button"
import {Card, CardHeader, CardTitle, CardDescription, CardContent} from "@/components/ui/card"
import {EmptyState, PageHeading, Notice, bytes, date, quota} from "@/shared/ui"
import type {PageData} from "@/shared/types"

import { StorageButton, UsageCard, StoragePage } from "@/features/storage/StoragePage"
import { CurrentPlan, PlansPage } from "@/features/billing/PlansPage"
import { OrdersPage, OrdersTable } from "@/features/billing/OrdersPage"
import { SettingsPage } from "@/features/accounts/SettingsPage"
export function DashboardPage({data,section}:{data:PageData;section:string}) {
 if(section==="requests")return <FileRequestsPage/>
 if(section==="teams")return <TeamsPage/>
 if(data.user?.role==="admin"||!data.user?.plan)return <StoragePage data={data} mode={(["storage","shared","trash"].includes(section)?section:"storage") as "storage"|"shared"|"trash"}/>
 if(section==="plans") return <PlansPage data={data}/>
 if(section==="orders") return <OrdersPage orders={data.orders}/>
 if(section==="settings") return <SettingsPage data={data}/>
 if(["storage","shared","trash"].includes(section)) return <StoragePage data={data} mode={section as "storage"|"shared"|"trash"}/>
 const user=data.user!, plan=user.plan!
 return <div className="flex min-w-0 flex-col gap-7">
  <PageHeading title={"Chào "+user.full_name.split(" ").filter(Boolean).at(-1)+","} description="Một nơi cho dữ liệu. Nhiều không gian cho ý tưởng." action={<StorageButton data={data}/>}/>
  <div className="summary-grid">
   <Summary icon={HardDrive} label="Dung lượng đã dùng" value={data.usage?bytes(data.usage.used):"Chưa cập nhật"} detail={data.usage?"trên "+bytes(data.usage.total)+" khả dụng":"Hãy thử tải lại sau ít phút"}/>
   <Summary icon={Sparkles} label="Gói đang sử dụng" value={plan.name} detail={quota(plan.quota_gb)+" dung lượng lưu trữ"}/>
   <Summary icon={CalendarDays} label={user.plan_expires_at?"Ngày hết hạn":"Thời hạn sử dụng"} value={user.plan_expires_at?date(user.plan_expires_at):"Không giới hạn"} detail={user.plan_expires_at?"Gia hạn để tiếp tục sử dụng gói":"Miễn phí, không cần thẻ thanh toán"}/>
  </div>
  {!user.quota_synced&&<Notice title="Hạn mức đang chờ đồng bộ">Dung lượng mới sẽ được cập nhật vào kho lưu trữ. Bạn có thể tải lại trang sau ít phút.</Notice>}
  <div className="dashboard-grid"><UsageCard data={data}/><CurrentPlan data={data}/></div>
  <Card className="min-w-0"><CardHeader className="flex flex-row items-center justify-between gap-3"><div><CardTitle>Đơn hàng gần đây</CardTitle><CardDescription>Theo dõi thanh toán và các gói đã chọn.</CardDescription></div><Button variant="ghost" asChild><a href="#orders">Xem tất cả<ArrowRight data-icon="inline-end" aria-hidden/></a></Button></CardHeader><CardContent>{data.orders.length?<OrdersTable orders={data.orders.slice(0,4)}/>:<EmptyState title="Chưa có đơn hàng" description="Gói miễn phí đã sẵn sàng. Khi cần thêm dung lượng, bạn có thể chọn một gói phù hợp."><Button variant="outline" asChild><a href="#plans">Khám phá các gói<ArrowRight data-icon="inline-end" aria-hidden/></a></Button></EmptyState>}</CardContent></Card>
 </div>
}
function Summary({icon:Icon,label,value,detail}:{icon:typeof HardDrive;label:string;value:string;detail:string}) { return <div className="summary-item"><span className="summary-icon"><Icon aria-hidden/></span><p className="summary-label">{label}</p><p className="summary-value">{value}</p><p className="summary-detail">{detail}</p></div> }
