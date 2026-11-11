import {ArrowRight, CreditCard} from "lucide-react"
import {Button} from "@/components/ui/button"
import {Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose} from "@/components/ui/dialog"
import {Separator} from "@/components/ui/separator"
import {Form, money, quota} from "@/shared/ui"
import {usePlanBenefits,benefitsFor,PlanFeatureList} from "@/features/billing/benefits"
import type {PageData, Plan} from "@/shared/types"


export function CheckoutDialog({plan,data,months,amount}:{plan:Plan;data:PageData;months:number;amount:number}) {
 const {plans:benefits}=usePlanBenefits()
 const same=plan.id===data.user!.plan_id
 return <Dialog><DialogTrigger asChild><Button className="w-full" variant="plan-outline">{same?"Gia hạn gói":"Chọn gói"}<ArrowRight data-icon="inline-end" aria-hidden/></Button></DialogTrigger><DialogContent><DialogHeader><DialogTitle>{same?"Gia hạn":"Nâng cấp"} gói {plan.name}</DialogTitle><DialogDescription>Kiểm tra thông tin trước khi chuyển đến VNPay.</DialogDescription></DialogHeader><div className="checkout-summary"><div><span>Gói dịch vụ</span><strong>{plan.name} · {quota(plan.quota_gb)}</strong></div><div><span>Thời hạn</span><strong>{months} tháng</strong></div>{months===12&&<p className="text-sm text-success">Đã áp dụng ưu đãi tặng 2 tháng.</p>}<Separator/><div><span>Tổng thanh toán</span><strong className="text-xl">{money(amount)}</strong></div></div><PlanFeatureList code={plan.code} benefits={benefitsFor(benefits,plan.code)}/><p className="text-sm text-muted-foreground">Quyền lợi không thay đổi theo kỳ thanh toán. Tệp và phiên bản đang lưu tiếp tục tính vào dung lượng.</p><Form method="post" action="/billing/checkout"><input type="hidden" name="plan_code" value={plan.code}/><input type="hidden" name="months" value={months}/><DialogFooter><DialogClose asChild><Button type="button" variant="outline">Quay lại</Button></DialogClose><Button type="submit"><CreditCard data-icon="inline-start" aria-hidden/>Tiếp tục với VNPay</Button></DialogFooter></Form></DialogContent></Dialog>
}

