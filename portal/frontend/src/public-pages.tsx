import { useState, type FormEvent } from "react"
import {
  ArrowRight,
  Check,
  CheckCircle2,
  CircleAlert,
  Cloud,
  File,
  FileImage,
  FileText,
  Folder,
  HardDrive,
  Layers3,
  Link2,
  Mail,
  RefreshCw,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import { Form, Notice, PasswordInput, money, quota } from "./shared"
import type { PageData, Plan } from "./types"

export function PublicPage({ data }: { data: PageData }) {
  if (data.page === "login") return <LoginPage data={data} />
  if (data.page === "register") return <RegisterPage data={data} />
  if (data.page === "message") return <MessagePage data={data} />
  return <HomePage data={data} />
}

function StorageIllustration({ compact = false }: { compact?: boolean }) {
  return (
    <div className={cn("storage-illustration", compact && "storage-illustration-compact")} aria-hidden="true">
      <div className="storage-illustration-orbit" />
      <div className="storage-illustration-window">
        <div className="storage-window-toolbar">
          <span /><span /><span />
          <Cloud className="ml-auto size-4" />
        </div>
        <div className="storage-window-content">
          <div className="storage-folder"><Folder strokeWidth={1.25} /></div>
          <div className="storage-file-grid">
            <div className="storage-file"><FileText strokeWidth={1.5} /><span>Tài liệu</span></div>
            <div className="storage-file"><FileImage strokeWidth={1.5} /><span>Hình ảnh</span></div>
            <div className="storage-file"><File strokeWidth={1.5} /><span>Tệp khác</span></div>
          </div>
          <div className="storage-window-line" /><div className="storage-window-line storage-window-line-short" />
        </div>
      </div>
      <div className="storage-floating-label"><Cloud /><span>Một nơi cho mọi tệp</span></div>
      <div className="storage-floating-icon"><Layers3 strokeWidth={1.5} /></div>
    </div>
  )
}

function HomePage({ data }: { data: PageData }) {
  const freePlan = data.plans.find((plan) => plan.price_vnd === 0)
  const workspaceUrl = data.user?.role === "admin" ? "/admin" : "/dashboard"

  return (
    <div className="public-home">
      <section className="public-hero" aria-labelledby="hero-title">
        <div className="public-hero-copy">
          <Badge variant="outline"><Cloud data-icon="inline-start" aria-hidden />Không gian lưu trữ của bạn</Badge>
          <h1 id="hero-title">Mọi tệp của bạn.<br /><span>Một nơi gọn gàng.</span></h1>
          <p>Lưu trữ, đồng bộ và chia sẻ tệp với CloudBox. Quản lý dung lượng và gói dịch vụ trong một không gian đơn giản, rõ ràng.</p>
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
          <div><h2>Tệp được sắp xếp</h2><p>Tải lên, tải xuống và quản lý thư mục trong kho lưu trữ Nextcloud của bạn.</p></div>
        </div>
        <div className="public-feature">
          <div className="feature-icon"><Link2 aria-hidden /></div>
          <div><h2>Chia sẻ thuận tiện</h2><p>Đồng bộ giữa các thiết bị và chia sẻ tệp bằng liên kết.</p></div>
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
  const isFree = plan.price_vnd === 0
  const featured = plan.code === "standard"
  const currentPlan = data.user?.plan_id === plan.id
  const destination = !data.user ? "/register" : data.user.role === "admin" ? "/admin/plans" : "/dashboard#plans"
  const label = !data.user ? isFree ? "Bắt đầu miễn phí" : "Tạo tài khoản" : currentPlan || data.user.role === "admin" ? "Quản lý gói" : "Xem gói dịch vụ"

  return (
    <Card className={cn("plan-card", featured && "plan-featured")}>
      <CardHeader>
        <div className="flex min-h-6 flex-wrap items-center justify-between gap-2">
          <CardTitle>{plan.name}</CardTitle>
          {currentPlan ? <Badge variant="secondary">Gói hiện tại</Badge> : featured ? <Badge>Đề xuất</Badge> : null}
        </div>
        <CardDescription>{isFree ? "Cho những tệp đầu tiên của bạn." : plan.quota_gb >= 1024 ? "Không gian cho nhiều dự án hơn." : plan.quota_gb >= 500 ? "Thoải mái cho nhu cầu mỗi ngày." : "Thêm chỗ cho tệp và tài liệu."}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-6">
        <div>
          <p className="plan-capacity">{quota(plan.quota_gb)}</p>
          <p className="plan-price">{isFree ? "Miễn phí" : money(plan.price_vnd)}{!isFree && <span>/tháng</span>}</p>
        </div>
        <ul className="flex flex-col gap-3 text-sm text-muted-foreground">
          <li className="flex items-start gap-2"><Check className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />Kho lưu trữ riêng</li>
          <li className="flex items-start gap-2"><Check className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />Đồng bộ tệp và thư mục</li>
          <li className="flex items-start gap-2"><Check className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />Chia sẻ bằng liên kết</li>
        </ul>
      </CardContent>
      <CardFooter><Button variant={featured ? "default" : "outline"} className="w-full" asChild><a href={destination}>{label}<ArrowRight data-icon="inline-end" aria-hidden /></a></Button></CardFooter>
    </Card>
  )
}

function AuthStory({ register, freePlan }: { register?: boolean; freePlan?: Plan }) {
  return (
    <aside className="auth-story" aria-label="Về CloudBox">
      <div>
        <p className="eyebrow">Không gian của bạn</p>
        <h2>{register ? <>Thêm không gian.<br />Thêm cảm hứng.</> : <>Tệp quan trọng.<br />Luôn gọn một nơi.</>}</h2>
        <p>{register ? "Bắt đầu sắp xếp tệp, đồng bộ giữa các thiết bị và chia sẻ điều bạn cần." : "Đăng nhập để theo dõi dung lượng, quản lý gói dịch vụ và tiếp tục công việc của bạn."}</p>
      </div>
      <StorageIllustration compact />
      <div className="auth-story-note">
        <span className="auth-note-icon"><HardDrive aria-hidden /></span>
        <div><strong>{freePlan ? `${quota(freePlan.quota_gb)} để bắt đầu` : "Không gian riêng cho tệp của bạn"}</strong><p>{freePlan ? "Gói miễn phí không giới hạn thời gian." : "Quản lý dung lượng trong tài khoản CloudBox."}</p></div>
      </div>
    </aside>
  )
}

function LoginPage({ data }: { data: PageData }) {
  return (
    <div className="auth-layout">
      <AuthStory freePlan={data.plans.find((plan) => plan.price_vnd === 0)} />
      <section className="auth-form-panel" aria-labelledby="login-title">
        <div className="auth-form-content">
          <div className="auth-heading"><p className="eyebrow">CloudBox</p><h1 id="login-title">Chào mừng trở lại</h1><p>Đăng nhập vào không gian CloudBox của bạn.</p></div>
          {data.error && <Notice kind="error" title="Chưa thể đăng nhập">{data.error}</Notice>}
          <Form action="/login" method="post">
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="login-email">Email</FieldLabel>
                <Input id="login-email" name="email" type="email" defaultValue={data.form.email ?? ""} autoComplete="email" placeholder="ban@example.com" required maxLength={200} />
              </Field>
              <Field data-invalid={Boolean(data.error) || undefined}>
                <FieldLabel htmlFor="login-password">Mật khẩu</FieldLabel>
                <PasswordInput id="login-password" name="password" autoComplete="current-password" invalid={Boolean(data.error)} />
              </Field>
              <Button type="submit" className="w-full">Đăng nhập<ArrowRight data-icon="inline-end" aria-hidden /></Button>
            </FieldGroup>
          </Form>
          {data.unverified && (
            <Form action="/resend" method="post">
              <input name="email" type="hidden" value={data.form.email ?? ""} />
              <Button type="submit" variant="outline" className="w-full"><Mail data-icon="inline-start" aria-hidden />Gửi lại email xác thực</Button>
            </Form>
          )}
          <div className="auth-help-row"><p>Chưa nhận được email xác thực?</p><ResendVerificationDialog initialEmail={data.form.email ?? ""} /></div>
          <p className="auth-switch">Chưa có tài khoản? <a href="/register">Đăng ký miễn phí<ArrowRight className="size-4" aria-hidden /></a></p>
        </div>
      </section>
    </div>
  )
}

function RegisterPage({ data }: { data: PageData }) {
  const [errors, setErrors] = useState<Record<string, string>>({})

  function validate(event: FormEvent<HTMLFormElement>) {
    const values = new FormData(event.currentTarget)
    const password = String(values.get("password") ?? "")
    const nextErrors: Record<string, string> = {}
    if (!String(values.get("full_name") ?? "").trim()) nextErrors.full_name = "Vui lòng nhập họ và tên của bạn."
    if (password.length < 10 || !/[A-Za-z]/.test(password) || !/\d/.test(password)) nextErrors.password = "Mật khẩu cần ít nhất 10 ký tự, gồm cả chữ và số."
    if (password !== String(values.get("password2") ?? "")) nextErrors.password2 = "Hai mật khẩu chưa khớp. Vui lòng kiểm tra lại."
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length) {
      event.preventDefault()
      const firstName = Object.keys(nextErrors)[0]
      requestAnimationFrame(() => document.getElementById("register-errors")?.focus())
    }
  }

  return (
    <div className="auth-layout">
      <AuthStory register freePlan={data.plans.find((plan) => plan.price_vnd === 0)} />
      <section className="auth-form-panel" aria-labelledby="register-title">
        <div className="auth-form-content">
          <div className="auth-heading"><p className="eyebrow">Bắt đầu với CloudBox</p><h1 id="register-title">Tạo không gian của bạn</h1><p>Chỉ cần một tài khoản để quản lý tệp và dung lượng.</p></div>
          {data.error && <Notice kind="error" title="Chưa thể tạo tài khoản">{data.error}</Notice>}
          <Form action="/register" method="post" onSubmit={validate} onInput={(event) => {
            const name = (event.target as HTMLInputElement).name
            if (errors[name]) setErrors((current) => { const next = { ...current }; delete next[name]; return next })
          }}>
            <FieldGroup>
              {Object.keys(errors).length > 0 && <div id="register-errors" role="alert" tabIndex={-1} className="validation-summary"><p>Vui lòng kiểm tra thông tin:</p><ul>{Object.entries(errors).map(([name,message])=><li key={name}><a href={"#register-"+name} onClick={event=>{event.preventDefault();document.getElementById("register-"+name)?.focus()}}>{message}</a></li>)}</ul></div>}
              <Field data-invalid={Boolean(errors.full_name) || undefined}>
                <FieldLabel htmlFor="register-full_name">Họ và tên</FieldLabel>
                <Input id="register-full_name" name="full_name" defaultValue={data.form.full_name ?? ""} autoComplete="name" placeholder="Nguyễn Minh Anh" maxLength={120} required aria-invalid={Boolean(errors.full_name) || undefined} aria-describedby={errors.full_name ? "register-name-error" : undefined} />
                {errors.full_name && <FieldError id="register-name-error">{errors.full_name}</FieldError>}
              </Field>
              <Field>
                <FieldLabel htmlFor="register-email">Email</FieldLabel>
                <Input id="register-email" name="email" type="email" defaultValue={data.form.email ?? ""} autoComplete="email" placeholder="ban@example.com" maxLength={200} required aria-describedby="register-email-help" />
                <FieldDescription id="register-email-help">Bạn sẽ nhận một email để xác thực tài khoản.</FieldDescription>
              </Field>
              <Field data-invalid={Boolean(errors.password) || undefined}>
                <FieldLabel htmlFor="register-password">Mật khẩu</FieldLabel>
                <PasswordInput id="register-password" name="password" autoComplete="new-password" minLength={10} invalid={Boolean(errors.password)} describedBy={errors.password ? "register-password-help register-password-error" : "register-password-help"} />
                <FieldDescription id="register-password-help">Ít nhất 10 ký tự, gồm cả chữ và số.</FieldDescription>
                {errors.password && <FieldError id="register-password-error">{errors.password}</FieldError>}
              </Field>
              <Field data-invalid={Boolean(errors.password2) || undefined}>
                <FieldLabel htmlFor="register-password2">Nhập lại mật khẩu</FieldLabel>
                <PasswordInput id="register-password2" name="password2" autoComplete="new-password" minLength={10} invalid={Boolean(errors.password2)} describedBy={errors.password2 ? "register-password2-error" : undefined} />
                {errors.password2 && <FieldError id="register-password2-error">{errors.password2}</FieldError>}
              </Field>
              <Button type="submit" className="w-full">Tạo tài khoản<ArrowRight data-icon="inline-end" aria-hidden /></Button>
            </FieldGroup>
          </Form>
          <p className="auth-switch">Đã có tài khoản? <a href="/login">Đăng nhập<ArrowRight className="size-4" aria-hidden /></a></p>
        </div>
      </section>
    </div>
  )
}

function ResendVerificationDialog({ initialEmail = "", fullButton = false }: { initialEmail?: string; fullButton?: boolean }) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant={fullButton ? "outline" : "link"} type="button">
          {fullButton && <Mail data-icon="inline-start" aria-hidden />}
          Gửi lại email xác thực
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Gửi lại email xác thực</DialogTitle>
          <DialogDescription>Nhập email bạn đã đăng ký. Nếu tài khoản chưa được xác thực, chúng tôi sẽ gửi một liên kết mới.</DialogDescription>
        </DialogHeader>
        <Form action="/resend" method="post">
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="resend-email">Email đăng ký</FieldLabel>
              <Input id="resend-email" name="email" type="email" defaultValue={initialEmail} autoComplete="email" placeholder="ban@example.com" maxLength={200} required />
            </Field>
          </FieldGroup>
          <DialogFooter className="mt-6">
            <DialogClose asChild><Button type="button" variant="outline">Hủy</Button></DialogClose>
            <Button type="submit"><Mail data-icon="inline-start" aria-hidden />Gửi liên kết xác thực</Button>
          </DialogFooter>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

function MessagePage({ data }: { data: PageData }) {
  const isError = data.kind === "error"
  const emailRelated = /email|xác thực|kích hoạt|liên kết/i.test(`${data.title} ${data.text}`)
  const Icon = isError ? CircleAlert : emailRelated && !/thành công/i.test(data.title) ? Mail : CheckCircle2
  const primaryLink = data.link ?? (emailRelated ? ["/login", "Về trang đăng nhập"] : ["/", "Về trang chủ"])

  return (
    <section className="message-page" aria-labelledby="message-title">
      <div className={cn("message-symbol", isError && "message-symbol-error")}><Icon aria-hidden /></div>
      <div className="message-copy" role={isError ? "alert" : "status"}>
        <p className="eyebrow">{isError ? "Cần kiểm tra lại" : "CLOUDBOX"}</p>
        <h1 id="message-title">{data.title}</h1>
        <p>{data.text}</p>
      </div>
      <div className="message-actions">
        <Button asChild><a href={primaryLink[0]}>{primaryLink[1]}<ArrowRight data-icon="inline-end" aria-hidden /></a></Button>
        {emailRelated && <ResendVerificationDialog fullButton />}
      </div>
      {emailRelated && <p className="message-hint">Chưa thấy email? Hãy kiểm tra cả thư mục spam.</p>}
      {!emailRelated && isError && !data.link && <Button variant="link" asChild><a href="/login"><RefreshCw data-icon="inline-start" aria-hidden />Về trang đăng nhập</a></Button>}
    </section>
  )
}
