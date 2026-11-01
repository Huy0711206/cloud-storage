import {useState} from "react"
import {ArrowRight, Check, CheckCircle2, Info, Sparkles} from "lucide-react"
import {Button} from "@/components/ui/button"
import {Badge} from "@/components/ui/badge"
import {Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter} from "@/components/ui/card"
import {Alert, AlertTitle, AlertDescription} from "@/components/ui/alert"
import {ToggleGroup, ToggleGroupItem} from "@/components/ui/toggle-group"
import {Separator} from "@/components/ui/separator"
import {PageHeading, money, date, quota} from "@/shared/ui"
import type {PageData} from "@/shared/types"
import {cn} from "@/lib/utils"

import { CheckoutDialog } from "@/features/payments/CheckoutDialog"
export function CurrentPlan({data}:{data:PageData}) {
 const user=data.user!,plan=user.plan!
 return <Card className="current-plan"><CardHeader><div className="flex items-center gap-2"><span className="plan-icon"><Sparkles aria-hidden/></span><Badge variant="outline">Gói hiện tại</Badge></div><CardTitle>{plan.name}</CardTitle><CardDescription>Thêm không gian khi bạn cần.</CardDescription></CardHeader><CardContent className="flex flex-col gap-5"><p className="plan-capacity">{quota(plan.quota_gb)}<span>cho dữ liệu của bạn</span></p><div className="flex flex-col gap-3"><p className="feature-line"><CheckCircle2 aria-hidden/>Tải lên, tải xuống và chia sẻ</p><p className="feature-line"><CheckCircle2 aria-hidden/>Đồng bộ máy tính và điện thoại</p><p className="feature-line"><CheckCircle2 aria-hidden/>{user.plan_expires_at?"Hết hạn "+date(user.plan_expires_at):"Không giới hạn thời gian"}</p></div></CardContent><CardFooter><Button className="w-full" asChild><a href="#plans">{plan.price_vnd===0?"Nâng cấp dung lượng":"Quản lý gói dịch vụ"}<ArrowRight data-icon="inline-end" aria-hidden/></a></Button></CardFooter></Card>
}

export function PlansPage({data}:{data:PageData}) {
 const [months,setMonths]=useState("1")
 const period=Number(months),billed=period===12?10:period
 return <div className="flex min-w-0 flex-col gap-7"><PageHeading title="Không gian cho mọi nhu cầu" description="Chọn dung lượng phù hợp. Nâng cấp hoặc gia hạn khi bạn cần."/><div className="plan-period"><ToggleGroup type="single" value={months} onValueChange={value=>value&&setMonths(value)} variant="outline" aria-label="Thời hạn gói"><ToggleGroupItem value="1">1 tháng</ToggleGroupItem><ToggleGroupItem value="3">3 tháng</ToggleGroupItem><ToggleGroupItem value="12">12 tháng</ToggleGroupItem></ToggleGroup><Badge variant="secondary">12 tháng chỉ trả 10 tháng</Badge></div><div className="pricing-grid">{data.plans.map(plan=><Card key={plan.id} className={cn("pricing-card",plan.code==="standard"&&"pricing-featured")}><CardHeader><div className="flex flex-wrap items-center justify-between gap-2"><CardTitle>{plan.name}</CardTitle>{plan.id===data.user!.plan_id?<Badge variant="outline">Đang sử dụng</Badge>:plan.code==="standard"?<Badge>Đề xuất</Badge>:null}</div><CardDescription>{plan.price_vnd===0?"Bắt đầu với những điều thiết yếu.":plan.code==="premium"?"Không gian cho những dự án lớn.":"Lưu trữ nhiều hơn, làm việc thoải mái."}</CardDescription></CardHeader><CardContent className="flex flex-col gap-6"><p className="pricing-capacity">{quota(plan.quota_gb)}</p><div><p className="pricing-price">{plan.price_vnd===0?"Miễn phí":money(plan.price_vnd)}{plan.price_vnd>0&&<span>/ tháng</span>}</p><p className="pricing-total">{plan.price_vnd>0?"Tổng "+money(plan.price_vnd*billed)+" cho "+period+" tháng":"Không giới hạn thời gian"}</p></div><Separator/><div className="flex flex-col gap-3">{["Kho lưu trữ riêng","Chia sẻ tệp qua liên kết","Đồng bộ nhiều thiết bị"].map(text=><p className="feature-line" key={text}><Check aria-hidden/>{text}</p>)}</div></CardContent><CardFooter>{plan.price_vnd===0?<Button variant="outline" className="w-full" disabled>{plan.id===data.user!.plan_id?"Gói hiện tại":"Gói miễn phí"}</Button>:<CheckoutDialog plan={plan} data={data} months={period} amount={plan.price_vnd*billed}/>}</CardFooter></Card>)}</div><Alert><Info aria-hidden/><AlertTitle>Thông tin khi đổi gói</AlertTitle><AlertDescription>Gia hạn cùng gói sẽ nối tiếp thời hạn hiện tại. Chuyển sang gói khác áp dụng ngay và tính lại thời hạn từ hôm nay; phần thời gian còn lại chưa được quy đổi.</AlertDescription></Alert></div>
}
