import {ArrowRight, Check, Cloud, Folder, HardDrive, Link2} from "lucide-react"

import {Badge} from "@/components/ui/badge"
import {Button} from "@/components/ui/button"
import {Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle} from "@/components/ui/card"
import {Notice, money, quota} from "@/shared/ui"
import type {PageData, Plan} from "@/shared/types"

import { LoginPage, RegisterPage, MessagePage, VerifyPage, ForgotPasswordPage, ResetPasswordPage } from "@/features/authentication/AuthPages"
import {usePlanBenefits,benefitsFor,planDescription,PlanFeatureList,PlanComparison,PlanCapacityNotice} from "@/features/billing/benefits"
import { StorageIllustration } from "@/shared/StorageIllustration"
export function PublicPage({ data }: { data: PageData }) {
  if (data.page === "login") return <LoginPage data={data} />
  if (data.page === "register") return <RegisterPage data={data} />
  if (data.page === "verify") return <VerifyPage data={data} />
  if (data.page === "forgot") return <ForgotPasswordPage data={data} />
  if (data.page === "reset") return <ResetPasswordPage data={data} />
  if (data.page === "message") return <MessagePage data={data} />
  return <HomePage data={data} />
}

function HomePage({ data }: { data: PageData }) {
  const {plans:benefits}=usePlanBenefits()
  const freePlan = data.plans.find((plan) => plan.price_vnd === 0)
  const workspaceUrl = data.user?.role === "admin" ? "/admin" : "/dashboard"

  return (
    <div className="public-home">
      <section className="public-hero" aria-labelledby="hero-title">
        <div className="public-hero-copy">
          <Badge variant="outline"><Cloud data-icon="inline-start" aria-hidden />Không gian lưu trữ của bạn</Badge>
          <h1 id="hero-title">Mọi tệp của bạn.<br /><span>Một nơi gọn gàng.</span></h1>
          <p>Lưu trữ, truy cập và chia sẻ tệp với CloudBox. Quản lý dung lượng và gói dịch vụ trong một không gian đơn giản, rõ ràng.</p>
          <div className="flex flex-wrap items-center gap-3">
            <Button size="lg" asChild>
              <a href={data.user ? workspaceUrl : "/register"}>
                {data.user ? "Vào không gian của tôi" : freePlan ? "Bắt đầu miễn phí" : "Tạo tài khoản"}
                <ArrowRight data-icon="inline-end" aria-hidden />
              </a>
            </Button>
            <Button variant="outline" size="lg" asChild><a href="#plans">Khám phá các gói</a></Button>
          </div>
          {freePlan && <p className="hero-footnote"><Check className="size-4" aria-hidden /><span>Bắt đầu với {quota(freePlan.quota_gb)} miễn phí. Nâng cấp khi bạn cần.</span></p>}
        </div>
        <StorageIllustration />
      </section>

      <section className="public-features" aria-label="Tính năng CloudBox">
        <div className="public-feature">
          <div className="feature-icon"><Folder aria-hidden /></div>
          <div><h2>Tệp được sắp xếp</h2><p>Tải lên, tải xuống và quản lý thư mục trong CloudBox của bạn.</p></div>
        </div>
        <div className="public-feature">
          <div className="feature-icon"><Link2 aria-hidden /></div>
          <div><h2>Chia sẻ thuận tiện</h2><p>Truy cập trên nhiều thiết bị và chia sẻ tệp bằng liên kết.</p></div>
        </div>
        <div className="public-feature">
          <div className="feature-icon"><HardDrive aria-hidden /></div>
          <div><h2>Dung lượng linh hoạt</h2><p>Theo dõi hạn mức, chọn gói phù hợp và thanh toán qua VNPay.</p></div>
        </div>
      </section>

      <section id="plans" className="public-pricing scroll-mt-24" aria-labelledby="pricing-title">
        <div className="pricing-heading">
          <p className="eyebrow">Gói lưu trữ</p>
          <h2 id="pricing-title">Thêm không gian cho điều bạn cần.</h2>
          <p>Bắt đầu miễn phí, chọn thêm dung lượng khi nhu cầu lớn hơn.</p>
        </div>
        {data.plans.length ? (
          <div className="grid items-stretch gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {data.plans.map((plan) => <PricingCard key={plan.id} plan={plan} data={data} />)}
          </div>
        ) : (
          <Notice title="Chưa có gói dịch vụ">Bảng giá hiện chưa được cập nhật. Vui lòng quay lại sau.</Notice>
        )}
        <PlanCapacityNotice/><PlanComparison plans={data.plans} benefits={benefits}/>
        <p className="pricing-footnote">Mua 12 tháng, thanh toán 10 tháng. Đăng ký tài khoản miễn phí trước khi nâng cấp.</p>
      </section>

      <section className="public-bottom-note">
        <Cloud className="size-7 shrink-0" aria-hidden />
        <div><h2>Không gian của bạn, theo cách của bạn.</h2><p>Tạo tài khoản, xác thực email và bắt đầu sử dụng kho lưu trữ.</p></div>
        <Button variant="outline" asChild><a href={data.user ? workspaceUrl : "/register"}>{data.user ? "Mở trang của tôi" : "Tạo tài khoản"}<ArrowRight data-icon="inline-end" aria-hidden /></a></Button>
      </section>
    </div>
  )
}

function PricingCard({ plan, data }: { plan: Plan; data: PageData }) {
  const {plans:benefits}=usePlanBenefits()
  const benefit=benefitsFor(benefits,plan.code)
  const isFree = plan.price_vnd === 0
  const featured = plan.code === "standard"
  const currentPlan = data.user?.plan_id === plan.id
  const destination = !data.user ? "/register" : data.user.role === "admin" ? "/admin/plans" : "/dashboard#plans"
  const label = !data.user ? isFree ? "Bắt đầu miễn phí" : "Tạo tài khoản" : currentPlan || data.user.role === "admin" ? "Quản lý gói" : "Xem gói dịch vụ"

  return (
    <Card className="plan-card plan-border" data-featured={featured || undefined}>
      <CardHeader>
        <div className="flex min-h-6 flex-wrap items-center justify-between gap-2">
          <CardTitle>{plan.name}</CardTitle>
          <span className="flex flex-wrap gap-2">{currentPlan&&<Badge variant="secondary">Gói hiện tại</Badge>}{featured&&<Badge>Đề xuất</Badge>}</span>
        </div>
        <CardDescription>{planDescription(plan.code,benefit)}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-6">
        <div>
          <p className="plan-capacity">{quota(plan.quota_gb)}</p>
          <p className="plan-price">{isFree ? "Miễn phí" : money(plan.price_vnd)}{!isFree && <span>/tháng</span>}</p>
        </div>
        <PlanFeatureList code={plan.code} benefits={benefit}/>
      </CardContent>
      <CardFooter><Button variant="plan-outline" className="w-full" asChild><a href={destination}>{label}<ArrowRight data-icon="inline-end" aria-hidden /></a></Button></CardFooter>
    </Card>
  )
}

