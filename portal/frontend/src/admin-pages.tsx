import { useState, type ComponentType } from "react"
import {
  ArrowDownUp,
  ArrowRight,
  CheckCheck,
  CircleCheck,
  CreditCard,
  HardDrive,
  Info,
  LockKeyhole,
  Pencil,
  RefreshCw,
  Search,
  ShieldCheck,
  UnlockKeyhole,
  Users,
  Wallet,
} from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
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
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { EmptyState, Form, PageHeading, StatusBadge, date, money, quota } from "./shared"
import type { Order, PageData, Plan, User } from "./types"

const termChoices = [1, 3, 12]

export function AdminPage({ data }: { data: PageData }) {
  if (data.page === "admin_users") return <UsersPage data={data} />
  if (data.page === "admin_orders") return <OrdersPage data={data} />
  if (data.page === "admin_plans") return <PlansPage data={data} />
  return <OverviewPage data={data} />
}

function MetricCard({
  title,
  value,
  description,
  icon: Icon,
}: {
  title: string
  value: string | number
  description: string
  icon: ComponentType<{ className?: string; "aria-hidden"?: boolean }>
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <CardTitle>{title}</CardTitle>
        <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
          <Icon className="size-4" aria-hidden />
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-1.5">
        <p className="text-2xl font-semibold tracking-tight tabular-nums sm:text-3xl">{value}</p>
        <p className="text-sm text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  )
}

function OverviewPage({ data }: { data: PageData }) {
  return (
    <div className="flex min-w-0 flex-col gap-7">
      <PageHeading
        title="Tổng quan quản trị"
        description="Theo dõi người dùng và hoạt động của CloudBox."
        action={
          <Form action="/admin/maintenance" method="post">
            <Button type="submit" variant="outline">
              <RefreshCw data-icon="inline-start" aria-hidden />
              Chạy bảo trì
            </Button>
          </Form>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="Người dùng" value={data.stats.users} description={`${data.stats.verified} tài khoản đã xác thực`} icon={Users} />
        <MetricCard title="Doanh thu" value={money(data.stats.revenue)} description="Từ các đơn đã thanh toán" icon={Wallet} />
        <MetricCard title="Gói trả phí" value={data.stats.paid_users} description="Tài khoản có thời hạn gói" icon={HardDrive} />
        <MetricCard title="Đã thanh toán" value={data.stats.orders_paid} description="Tổng đơn thanh toán thành công" icon={CreditCard} />
      </div>

      <div className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
        <Card className="min-w-0">
          <CardHeader>
            <CardTitle>Đơn hàng gần đây</CardTitle>
            <CardDescription>Các giao dịch mới nhất trên hệ thống.</CardDescription>
          </CardHeader>
          <CardContent>
            {data.recent.length ? (
              <OrderTable orders={data.recent} compact />
            ) : (
              <EmptyState title="Chưa có giao dịch" description="Đơn hàng sẽ xuất hiện tại đây khi người dùng chọn một gói trả phí." />
            )}
          </CardContent>
          <CardFooter className="justify-end">
            <Button variant="ghost" asChild>
              <a href="/admin/orders">Xem tất cả đơn hàng <ArrowRight data-icon="inline-end" aria-hidden /></a>
            </Button>
          </CardFooter>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Vận hành lưu trữ</CardTitle>
            <CardDescription>Đồng bộ tài khoản và hạn mức.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-5">
            <div className="flex items-center gap-3">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-muted text-muted-foreground">
                <ShieldCheck className="size-5" aria-hidden />
              </div>
              <div className="flex flex-col gap-0.5">
                <p className="text-sm font-medium">Đã xác thực email</p>
                <p className="text-sm text-muted-foreground"><span className="tabular-nums">{data.stats.verified}</span> người dùng</p>
              </div>
            </div>
            <Alert>
              {data.stats.unsynced > 0 ? <ArrowDownUp aria-hidden /> : <CircleCheck aria-hidden />}
              <AlertTitle>{data.stats.unsynced > 0 ? `${data.stats.unsynced} hạn mức chờ đồng bộ` : "Không có hạn mức chờ đồng bộ"}</AlertTitle>
              <AlertDescription>
                {data.stats.unsynced > 0
                  ? "Chạy bảo trì để thử đồng bộ lại dung lượng với kho lưu trữ."
                  : "Các hạn mức đã được ghi nhận đồng bộ với kho lưu trữ."}
              </AlertDescription>
            </Alert>
            <p className="text-sm leading-relaxed text-muted-foreground">Bảo trì cũng chuyển tài khoản hết hạn về gói miễn phí.</p>
          </CardContent>
          <CardFooter>
            <Button variant="outline" className="w-full" asChild>
              <a href="/admin/users">Quản lý người dùng <ArrowRight data-icon="inline-end" aria-hidden /></a>
            </Button>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}

function UsersPage({ data }: { data: PageData }) {
  return (
    <div className="flex min-w-0 flex-col gap-7">
      <PageHeading title="Người dùng" description="Quản lý tài khoản, gói dịch vụ và hạn mức lưu trữ." />
      <Card className="min-w-0">
        <CardHeader>
          <div className="flex flex-wrap items-center gap-3">
            <CardTitle>Danh sách người dùng</CardTitle>
            <Badge variant="secondary">{data.users.length} tài khoản</Badge>
          </div>
          <CardDescription>Tìm theo họ tên hoặc email. Hiển thị tối đa 200 kết quả mới nhất.</CardDescription>
        </CardHeader>
        <CardContent className="flex min-w-0 flex-col gap-5">
          <Form action="/admin/users" method="get">
            <FieldGroup className="items-end gap-3 sm:flex-row">
              <Field className="min-w-0 sm:max-w-md">
                <FieldLabel htmlFor="admin-user-search">Tìm người dùng</FieldLabel>
                <Input id="admin-user-search" name="q" type="search" defaultValue={data.q} placeholder="Nhập tên hoặc email…" autoComplete="off" />
              </Field>
              <div className="flex shrink-0 items-center gap-2">
                <Button type="submit" variant="outline"><Search data-icon="inline-start" aria-hidden />Tìm kiếm</Button>
                {data.q && <Button type="button" variant="ghost" asChild><a href="/admin/users">Xóa bộ lọc</a></Button>}
              </div>
            </FieldGroup>
          </Form>
          {data.users.length ? (
            <Table>
              <TableCaption className="sr-only">Người dùng CloudBox và các thao tác quản lý tài khoản</TableCaption>
              <TableHeader>
                <TableRow>
                  <TableHead>Người dùng</TableHead>
                  <TableHead>Gói dịch vụ</TableHead>
                  <TableHead>Hết hạn</TableHead>
                  <TableHead>Trạng thái</TableHead>
                  <TableHead className="text-right">Thao tác</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div className="flex min-w-44 flex-col gap-1 py-2">
                        <span className="font-medium">{user.full_name}</span>
                        <span className="text-sm text-muted-foreground [overflow-wrap:anywhere]">{user.email}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col items-start gap-1.5">
                        <span>{user.plan?.name ?? "Chưa có gói"}</span>
                        {!user.quota_synced && <Badge variant="outline"><ArrowDownUp aria-hidden />Chờ đồng bộ</Badge>}
                      </div>
                    </TableCell>
                    <TableCell className="whitespace-nowrap tabular-nums">{user.plan_expires_at ? date(user.plan_expires_at) : "Không thời hạn"}</TableCell>
                    <TableCell>
                      {!user.is_verified ? (
                        <Badge variant="outline">Chưa xác thực</Badge>
                      ) : user.is_active ? (
                        <Badge variant="secondary"><CheckCheck aria-hidden />Hoạt động</Badge>
                      ) : (
                        <Badge variant="outline"><LockKeyhole aria-hidden />Đã khóa</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex justify-end gap-2">
                        {!user.quota_synced && (
                          <Form action={`/admin/users/${user.id}/sync`} method="post">
                            <Button type="submit" variant="outline" size="sm" aria-label={`Đồng bộ hạn mức của ${user.full_name}`}>
                              <RefreshCw data-icon="inline-start" aria-hidden />Đồng bộ
                            </Button>
                          </Form>
                        )}
                        <GrantPlanDialog user={user} plans={data.plans} />
                        <ToggleUserDialog user={user} />
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <EmptyState
              title={data.q ? "Không tìm thấy người dùng" : "Chưa có người dùng"}
              description={data.q ? "Thử một tên hoặc địa chỉ email khác." : "Các tài khoản đã đăng ký sẽ xuất hiện tại đây."}
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function ToggleUserDialog({ user }: { user: User }) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button type="button" variant="ghost" size="sm" aria-label={`${user.is_active ? "Khóa" : "Mở khóa"} tài khoản ${user.full_name}`}>
          {user.is_active ? <LockKeyhole data-icon="inline-start" aria-hidden /> : <UnlockKeyhole data-icon="inline-start" aria-hidden />}
          {user.is_active ? "Khóa" : "Mở khóa"}
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <Form action={`/admin/users/${user.id}/toggle`} method="post">
          <AlertDialogHeader>
            <AlertDialogTitle>{user.is_active ? "Khóa tài khoản này?" : "Mở khóa tài khoản này?"}</AlertDialogTitle>
            <AlertDialogDescription>
              {user.is_active
                ? `${user.email} sẽ không thể đăng nhập CloudBox và kho lưu trữ. Bạn có thể mở khóa lại sau.`
                : `${user.email} sẽ được phép đăng nhập lại. Tài khoản vẫn cần xác thực email nếu chưa hoàn tất.`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="mt-6">
            <AlertDialogCancel type="button">Hủy</AlertDialogCancel>
            <Button type="submit" variant={user.is_active ? "destructive" : "default"}>
              {user.is_active ? "Xác nhận khóa" : "Xác nhận mở khóa"}
            </Button>
          </AlertDialogFooter>
        </Form>
      </AlertDialogContent>
    </AlertDialog>
  )
}

function GrantPlanDialog({ user, plans }: { user: User; plans: Plan[] }) {
  const [selectedCode, setSelectedCode] = useState(user.plan?.code ?? plans[0]?.code ?? "")
  const selectedPlan = plans.find((plan) => plan.code === selectedCode)
  const isFree = selectedPlan?.price_vnd === 0

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button type="button" variant="outline" size="sm" disabled={!plans.length} aria-label={`Cấp gói cho ${user.full_name}`}>
          Cấp gói
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Cấp gói dịch vụ</DialogTitle>
          <DialogDescription>Thay đổi gói và dung lượng lưu trữ cho {user.email}.</DialogDescription>
        </DialogHeader>
        <Form action={`/admin/users/${user.id}/grant`} method="post">
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor={`user-plan-${user.id}`}>Gói dịch vụ</FieldLabel>
              <Select name="plan_code" value={selectedCode} onValueChange={setSelectedCode} required>
                <SelectTrigger id={`user-plan-${user.id}`} className="w-full"><SelectValue placeholder="Chọn gói dịch vụ" /></SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {plans.map((plan) => <SelectItem key={plan.id} value={plan.code}>{plan.name} · {quota(plan.quota_gb)}{plan.is_active ? "" : " · Ngừng bán"}</SelectItem>)}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </Field>
            <Field data-disabled={isFree || undefined}>
              <FieldLabel htmlFor={`user-months-${user.id}`}>Thời hạn</FieldLabel>
              <Select name="months" defaultValue="1" disabled={isFree}>
                <SelectTrigger id={`user-months-${user.id}`} className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent><SelectGroup>{termChoices.map((months) => <SelectItem key={months} value={String(months)}>{months} tháng</SelectItem>)}</SelectGroup></SelectContent>
              </Select>
              <FieldDescription>{isFree ? "Gói miễn phí không giới hạn thời gian." : "Gia hạn cùng gói sẽ cộng thêm vào thời hạn hiện tại."}</FieldDescription>
            </Field>
            <Alert>
              <Info aria-hidden />
              <AlertTitle>Cấp gói thủ công</AlertTitle>
              <AlertDescription>Thao tác áp dụng gói ngay và đồng bộ dung lượng. Không tạo giao dịch thanh toán.</AlertDescription>
            </Alert>
          </FieldGroup>
          <DialogFooter className="mt-6">
            <DialogClose asChild><Button type="button" variant="outline">Hủy</Button></DialogClose>
            <Button type="submit">Xác nhận cấp gói</Button>
          </DialogFooter>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

function OrderTable({ orders, compact = false }: { orders: Order[]; compact?: boolean }) {
  return (
    <Table>
      <TableCaption className="sr-only">Danh sách đơn hàng và trạng thái thanh toán</TableCaption>
      <TableHeader>
        <TableRow>
          <TableHead>Đơn hàng</TableHead>
          <TableHead>Gói dịch vụ</TableHead>
          <TableHead>Số tiền</TableHead>
          <TableHead>Trạng thái</TableHead>
          {!compact && <TableHead>Mã giao dịch VNPay</TableHead>}
          <TableHead>Ngày tạo</TableHead>
          {!compact && <TableHead>Thanh toán lúc</TableHead>}
        </TableRow>
      </TableHeader>
      <TableBody>
        {orders.map((order) => (
          <TableRow key={order.id}>
            <TableCell>
              <div className="flex min-w-40 flex-col gap-1 py-2">
                <span className="font-mono text-xs font-medium">{order.txn_ref}</span>
                <span className="text-sm text-muted-foreground [overflow-wrap:anywhere]">{order.user?.email ?? "—"}</span>
              </div>
            </TableCell>
            <TableCell className="whitespace-nowrap">{order.plan?.name ?? "—"}<span className="ml-1 text-muted-foreground">· {order.months} tháng</span></TableCell>
            <TableCell className="whitespace-nowrap font-medium tabular-nums">{money(order.amount_vnd)}</TableCell>
            <TableCell><StatusBadge status={order.status} /></TableCell>
            {!compact && <TableCell className="font-mono text-xs">{order.gateway_txn_no || "—"}</TableCell>}
            <TableCell className="whitespace-nowrap tabular-nums">{date(order.created_at)}</TableCell>
            {!compact && <TableCell className="whitespace-nowrap tabular-nums">{date(order.paid_at ?? null)}</TableCell>}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function OrdersPage({ data }: { data: PageData }) {
  return (
    <div className="flex min-w-0 flex-col gap-7">
      <PageHeading title="Đơn hàng" description="Tra cứu giao dịch và trạng thái thanh toán của người dùng." />
      <Card className="min-w-0">
        <CardHeader>
          <div className="flex flex-wrap items-center gap-3">
            <CardTitle>Lịch sử giao dịch</CardTitle>
            <Badge variant="secondary">{data.orders.length} đơn hàng</Badge>
          </div>
          <CardDescription>Hiển thị tối đa 200 đơn hàng mới nhất.</CardDescription>
        </CardHeader>
        <CardContent>
          {data.orders.length ? <OrderTable orders={data.orders} /> : <EmptyState title="Chưa có đơn hàng" description="Đơn được tạo khi người dùng chuyển đến bước thanh toán một gói dịch vụ." />}
        </CardContent>
      </Card>
    </div>
  )
}

function PlansPage({ data }: { data: PageData }) {
  return (
    <div className="flex min-w-0 flex-col gap-7">
      <PageHeading title="Gói dịch vụ" description="Quản lý dung lượng, giá và các gói đang mở bán." />
      <Alert>
        <Info aria-hidden />
        <AlertTitle>Hạn mức được đồng bộ tự động</AlertTitle>
        <AlertDescription>Đổi dung lượng một gói sẽ cập nhật hạn mức cho tất cả người dùng đang sử dụng gói đó.</AlertDescription>
      </Alert>
      <Card className="min-w-0">
        <CardHeader>
          <CardTitle>Các gói lưu trữ</CardTitle>
          <CardDescription>Gói miễn phí luôn được giữ lại với giá 0 ₫.</CardDescription>
        </CardHeader>
        <CardContent>
          {data.plans.length ? (
            <Table>
              <TableCaption className="sr-only">Danh sách gói dịch vụ, dung lượng và giá bán</TableCaption>
              <TableHeader><TableRow><TableHead>Gói dịch vụ</TableHead><TableHead>Dung lượng</TableHead><TableHead>Giá mỗi tháng</TableHead><TableHead>Trạng thái</TableHead><TableHead className="text-right">Thao tác</TableHead></TableRow></TableHeader>
              <TableBody>
                {data.plans.map((plan) => (
                  <TableRow key={plan.id}>
                    <TableCell><div className="flex flex-col gap-1 py-2"><span className="font-medium">{plan.name}</span><span className="font-mono text-xs text-muted-foreground">{plan.code}</span></div></TableCell>
                    <TableCell className="whitespace-nowrap tabular-nums">{quota(plan.quota_gb)}</TableCell>
                    <TableCell className="whitespace-nowrap tabular-nums">{money(plan.price_vnd)}</TableCell>
                    <TableCell><Badge variant={plan.is_active ? "secondary" : "outline"}>{plan.is_active ? "Đang mở bán" : "Ngừng bán"}</Badge></TableCell>
                    <TableCell className="text-right"><EditPlanDialog plan={plan} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : <EmptyState title="Chưa có gói dịch vụ" description="Các gói được cấu hình trên hệ thống sẽ hiển thị tại đây." />}
        </CardContent>
      </Card>
    </div>
  )
}

function EditPlanDialog({ plan }: { plan: Plan }) {
  const isFree = plan.price_vnd === 0
  return (
    <Dialog>
      <DialogTrigger asChild><Button type="button" variant="outline" size="sm" aria-label={`Chỉnh sửa gói ${plan.name}`}><Pencil data-icon="inline-start" aria-hidden />Chỉnh sửa</Button></DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Chỉnh sửa gói {plan.name}</DialogTitle>
          <DialogDescription>Cập nhật thông tin và hạn mức gói dịch vụ.</DialogDescription>
        </DialogHeader>
        <Form action={`/admin/plans/${plan.id}`} method="post">
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor={`plan-name-${plan.id}`}>Tên gói</FieldLabel>
              <Input id={`plan-name-${plan.id}`} name="name" defaultValue={plan.name} required maxLength={60} />
            </Field>
            <Field>
              <FieldLabel htmlFor={`plan-quota-${plan.id}`}>Dung lượng (GB)</FieldLabel>
              <Input id={`plan-quota-${plan.id}`} name="quota_gb" type="number" defaultValue={plan.quota_gb} min={1} step={1} required inputMode="numeric" />
              <FieldDescription>1 TB = 1.024 GB. Áp dụng cho tất cả người dùng của gói.</FieldDescription>
            </Field>
            <Field>
              <FieldLabel htmlFor={`plan-price-${plan.id}`}>Giá mỗi tháng (₫)</FieldLabel>
              <Input id={`plan-price-${plan.id}`} name="price_vnd" type="number" defaultValue={plan.price_vnd} min={0} step={1000} required readOnly={isFree} inputMode="numeric" aria-describedby={isFree ? `plan-price-help-${plan.id}` : undefined} />
              {isFree && <FieldDescription id={`plan-price-help-${plan.id}`}>Gói miễn phí giữ cố định giá 0 ₫.</FieldDescription>}
            </Field>
            <Field orientation="horizontal" data-disabled={isFree || undefined}>
              <input id={`plan-active-${plan.id}`} type="checkbox" name="is_active" value="1" defaultChecked={plan.is_active} disabled={isFree} className="size-4 shrink-0 accent-primary" />
              <FieldLabel htmlFor={`plan-active-${plan.id}`}>Mở bán gói dịch vụ</FieldLabel>
              {isFree && <input type="hidden" name="is_active" value="1" />}
            </Field>
          </FieldGroup>
          <DialogFooter className="mt-6">
            <DialogClose asChild><Button type="button" variant="outline">Hủy</Button></DialogClose>
            <Button type="submit">Lưu thay đổi</Button>
          </DialogFooter>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
