import {useState, type FormEvent} from "react"
import {ArrowRight, CheckCircle2, CircleAlert, HardDrive, Mail, RefreshCw} from "lucide-react"

import {Button} from "@/components/ui/button"
import {Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger} from "@/components/ui/dialog"
import {Field, FieldDescription, FieldError, FieldGroup, FieldLabel} from "@/components/ui/field"
import {Input} from "@/components/ui/input"
import {cn} from "@/lib/utils"
import {Form, Notice, PasswordInput, quota} from "@/shared/ui"
import type {PageData, Plan} from "@/shared/types"

import { StorageIllustration } from "@/shared/StorageIllustration"
export function AuthStory({ register, freePlan }: { register?: boolean; freePlan?: Plan }) {
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

export function LoginPage({ data }: { data: PageData }) {
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

export function RegisterPage({ data }: { data: PageData }) {
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

export function ResendVerificationDialog({ initialEmail = "", fullButton = false }: { initialEmail?: string; fullButton?: boolean }) {
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

export function MessagePage({ data }: { data: PageData }) {
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
