import {csrfToken} from "@/shared/csrf"
import {useEffect, useRef, useState, type FormEvent} from "react"
import {ArrowRight, CheckCircle2, CircleAlert, HardDrive, Mail, RefreshCw} from "lucide-react"

import {Button} from "@/components/ui/button"
import {Field, FieldDescription, FieldError, FieldGroup, FieldLabel} from "@/components/ui/field"
import {Input} from "@/components/ui/input"
import {cn} from "@/lib/utils"
import {Form, Notice, PasswordInput, quota} from "@/shared/ui"
import type {PageData, Plan} from "@/shared/types"

import { StorageIllustration } from "@/shared/StorageIllustration"
function AuthStory({ register, freePlan }: { register?: boolean; freePlan?: Plan }) {
  return (
    <aside className="auth-story" aria-label="Về CloudBox">
      <div>
        <p className="eyebrow">Không gian của bạn</p>
        <h2>{register ? <>Thêm không gian.<br />Thêm cảm hứng.</> : <>Tệp quan trọng.<br />Luôn gọn một nơi.</>}</h2>
        <p>{register ? "Bắt đầu sắp xếp tệp, truy cập trên nhiều thiết bị và chia sẻ điều bạn cần." : "Đăng nhập để theo dõi dung lượng, quản lý gói dịch vụ và tiếp tục công việc của bạn."}</p>
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
          <a className="auth-recovery-link" href="/forgot-password">Quên mật khẩu?</a>
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
    if (!/^[^@\s]+@gmail\.com$/i.test(String(values.get("email") ?? "").trim())) nextErrors.email = "Vui lòng sử dụng địa chỉ Gmail của bạn (@gmail.com)."
    if (!String(values.get("full_name") ?? "").trim()) nextErrors.full_name = "Vui lòng nhập họ và tên của bạn."
    if (password.length < 10 || !/[A-Za-z]/.test(password) || !/\d/.test(password)) nextErrors.password = "Mật khẩu cần ít nhất 10 ký tự, gồm cả chữ và số."
    if (password !== String(values.get("password2") ?? "")) nextErrors.password2 = "Hai mật khẩu chưa khớp. Vui lòng kiểm tra lại."
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length) {
      event.preventDefault()
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
              <Field data-invalid={Boolean(errors.email) || undefined}>
                <FieldLabel htmlFor="register-email">Gmail</FieldLabel>
                <Input id="register-email" name="email" type="email" defaultValue={data.form.email ?? ""} autoComplete="email" placeholder="ban@gmail.com" maxLength={200} required aria-invalid={Boolean(errors.email) || undefined} aria-describedby="register-email-help" />
                <FieldDescription id="register-email-help">CloudBox gửi mã xác minh đến Gmail này. Mật khẩu bên dưới chỉ dùng cho CloudBox.</FieldDescription>
                {errors.email && <FieldError>{errors.email}</FieldError>}
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

export function VerifyPage({ data }: { data: PageData }) {
  const [seconds, setSeconds] = useState(Math.max(0, data.cooldown_seconds ?? 0))
  const [code, setCode] = useState("")
  const [sending,setSending]=useState(false),[resendError,setResendError]=useState("")
  const cooldownUntil=useRef(Date.now()+Math.max(0,data.cooldown_seconds??0)*1000)
  useEffect(()=>{
    const tick=()=>setSeconds(Math.max(0,Math.ceil((cooldownUntil.current-Date.now())/1000)))
    const returned=()=>{setSending(false);tick()}
    const timer=window.setInterval(tick,1000)
    window.addEventListener("pageshow",returned)
    return()=>{window.clearInterval(timer);window.removeEventListener("pageshow",returned)}
  },[])
  function resend(event:FormEvent<HTMLFormElement>){
    if(seconds>0||sending){event.preventDefault();return}
    if(!navigator.onLine){event.preventDefault();setResendError("Chưa có kết nối Internet. Kiểm tra mạng rồi gửi lại mã.");return}
    setResendError("");setSending(true)
  }
  return <div className="auth-layout"><AuthStory /><section className="auth-form-panel" aria-labelledby="verify-title"><div className="auth-form-content">
    <div className="auth-heading"><h1 id="verify-title">Xác minh Gmail của bạn</h1><p>Nhập mã 6 chữ số cho <strong className="auth-email">{data.form.email}</strong>.</p></div>
    {(data.error||resendError) && <Notice kind="error" title="Chưa thể xác minh">{resendError||data.error}</Notice>}
    {data.sent && <Notice kind="ok" title="Đã gửi mã xác minh">Kiểm tra hộp thư đến và thư mục spam trong Gmail.</Notice>}
    <Form action="/verify" method="post"><FieldGroup><Field><FieldLabel htmlFor="verification-code">Mã xác minh</FieldLabel><Input className="otp-code-input" id="verification-code" name="code" type="text" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" minLength={6} maxLength={6} value={code} onChange={event => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))} required aria-describedby="verification-help" /><FieldDescription id="verification-help">Mã có hiệu lực trong 10 phút và chỉ dùng một lần.</FieldDescription></Field><Button type="submit">Xác minh và tiếp tục<ArrowRight data-icon="inline-end" aria-hidden /></Button></FieldGroup></Form>
    <div className="auth-help-row"><p>Chưa nhận được mã?</p><form action="/resend" method="post" onSubmit={resend}><input type="hidden" name="csrf_token" value={csrfToken()}/><Button type="submit" variant="outline" disabled={seconds>0||sending}><RefreshCw data-icon="inline-start" aria-hidden />{sending?"Đang gửi…":seconds>0?`Gửi lại sau ${seconds}s`:"Gửi lại mã"}</Button></form><p>Mã được gửi lại sẽ thay thế mã trước đó.</p></div>
    <p className="auth-switch"><a href="/register">Quay lại đăng ký</a><span>·</span><a href="/login">Đăng nhập</a></p>
  </div></section></div>
}

export function ForgotPasswordPage({data}:{data:PageData}) {
  return <div className="auth-layout"><AuthStory /><section className="auth-form-panel" aria-labelledby="forgot-title"><div className="auth-form-content"><div className="auth-heading"><h1 id="forgot-title">Khôi phục tài khoản</h1><p>Nhập email đăng ký để nhận hướng dẫn đặt lại mật khẩu CloudBox.</p></div>{data.error&&<Notice kind="error" title="Chưa thể gửi yêu cầu">{data.error}</Notice>}<Form action="/forgot-password" method="post"><FieldGroup><Field><FieldLabel htmlFor="forgot-email">Email tài khoản</FieldLabel><Input id="forgot-email" name="email" type="email" defaultValue={data.form.email??""} autoComplete="email" required maxLength={200}/></Field><Button type="submit"><Mail data-icon="inline-start" aria-hidden/>Gửi hướng dẫn</Button></FieldGroup></Form><p className="auth-switch"><a href="/login">Về trang đăng nhập</a></p></div></section></div>
}

export function ResetPasswordPage({data}:{data:PageData}) {
  const [error,setError]=useState("")
  function validate(event:FormEvent<HTMLFormElement>){const values=new FormData(event.currentTarget);if(values.get("password")!==values.get("password2")){event.preventDefault();setError("Hai mật khẩu không khớp.")}}
  return <div className="auth-layout"><AuthStory/><section className="auth-form-panel" aria-labelledby="reset-title"><div className="auth-form-content"><div className="auth-heading"><h1 id="reset-title">Đặt lại mật khẩu</h1><p>Chọn mật khẩu mới cho tài khoản CloudBox.</p></div>{(data.error||error)&&<Notice kind="error" title="Chưa thể đặt lại mật khẩu">{error||data.error}</Notice>}<Form action="/reset-password" method="post" onSubmit={validate}><input type="hidden" name="token" value={data.reset_token??""}/><FieldGroup><Field><FieldLabel htmlFor="reset-password">Mật khẩu mới</FieldLabel><PasswordInput id="reset-password" name="password" autoComplete="new-password" minLength={10}/><FieldDescription>Ít nhất 10 ký tự, gồm cả chữ và số.</FieldDescription></Field><Field><FieldLabel htmlFor="reset-confirm">Nhập lại mật khẩu</FieldLabel><PasswordInput id="reset-confirm" name="password2" autoComplete="new-password" minLength={10}/></Field><Button type="submit">Lưu mật khẩu mới</Button></FieldGroup></Form><p className="auth-switch"><a href="/forgot-password">Yêu cầu liên kết mới</a></p></div></section></div>
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
      </div>
      {emailRelated && <p className="message-hint">Nếu đang chờ thư, hãy kiểm tra cả thư mục spam.</p>}
      {!emailRelated && isError && !data.link && <Button variant="link" asChild><a href="/login"><RefreshCw data-icon="inline-start" aria-hidden />Về trang đăng nhập</a></Button>}
    </section>
  )
}
