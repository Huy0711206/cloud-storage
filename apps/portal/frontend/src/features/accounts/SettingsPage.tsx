import {useState, type FormEvent} from "react"
import {LockKeyhole} from "lucide-react"
import {Button} from "@/components/ui/button"
import {Card, CardHeader, CardTitle, CardDescription, CardContent} from "@/components/ui/card"
import {Field, FieldGroup, FieldLabel, FieldDescription} from "@/components/ui/field"
import {Form, PageHeading, PasswordInput, StatusBadge, Notice, date} from "@/shared/ui"
import type {PageData} from "@/shared/types"


export function SettingsPage({data}:{data:PageData}) {
 const user=data.user!,[error,setError]=useState("")
 const validate=(event:FormEvent<HTMLFormElement>)=>{
  const form=new FormData(event.currentTarget),pwd=String(form.get("new")),confirm=String(form.get("new2"))
  if(pwd!==confirm){event.preventDefault();setError("Hai mật khẩu mới không khớp.");event.currentTarget.querySelector<HTMLInputElement>('[name="new2"]')?.focus()}
  else if(!/[A-Za-z]/.test(pwd)||!/[0-9]/.test(pwd)){event.preventDefault();setError("Mật khẩu mới cần có cả chữ và số.");event.currentTarget.querySelector<HTMLInputElement>('[name="new"]')?.focus()}
  else setError("")
 }
 return <div className="flex min-w-0 flex-col gap-7"><PageHeading title="Tài khoản & bảo mật" description="Quản lý thông tin đăng nhập và bảo vệ tài khoản."/><div className="settings-grid"><Card><CardHeader><CardTitle>Thông tin tài khoản</CardTitle><CardDescription>Thông tin tài khoản CloudBox của bạn.</CardDescription></CardHeader><CardContent><dl className="profile-details"><div><dt>Họ và tên</dt><dd>{user.full_name}</dd></div><div><dt>Email</dt><dd>{user.email}</dd></div><div><dt>Xác thực</dt><dd><StatusBadge status="verified"/></dd></div><div><dt>Ngày tham gia</dt><dd>{date(user.created_at)}</dd></div></dl></CardContent></Card><Card><CardHeader><CardTitle>Đổi mật khẩu</CardTitle><CardDescription>Mật khẩu mới dùng để đăng nhập CloudBox.</CardDescription></CardHeader><CardContent><Form method="post" action="/account/password" onSubmit={validate}><FieldGroup>{error&&<Notice kind="error" title={error}/>}<Field><FieldLabel htmlFor="current-password">Mật khẩu hiện tại</FieldLabel><PasswordInput id="current-password" name="current" autoComplete="current-password"/></Field><Field data-invalid={!!error}><FieldLabel htmlFor="new-password">Mật khẩu mới</FieldLabel><PasswordInput id="new-password" name="new" autoComplete="new-password" minLength={10} invalid={!!error} describedBy="password-help"/><FieldDescription id="password-help">Ít nhất 10 ký tự, có cả chữ và số.</FieldDescription></Field><Field data-invalid={!!error}><FieldLabel htmlFor="confirm-password">Nhập lại mật khẩu mới</FieldLabel><PasswordInput id="confirm-password" name="new2" autoComplete="new-password" minLength={10} invalid={!!error}/></Field><Button type="submit"><LockKeyhole data-icon="inline-start" aria-hidden/>Cập nhật mật khẩu</Button></FieldGroup></Form></CardContent></Card></div></div>
}
