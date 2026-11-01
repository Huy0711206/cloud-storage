import {
  ArrowUpRight,
  Check,
  Cloud,
  FileText,
  Folder,
  FolderOpen,
  HardDrive,
  Laptop,
  Link2,
  Smartphone,
} from "lucide-react"

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
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"
import { PublicPage } from "@/features/public/PublicPage"
import { EmptyState, money, quota } from "@/shared/ui"
import type { PageData, Plan } from "@/shared/types"
import "@/styles/landing.css"

export function LandingPage({ data }: { data: PageData }) {
  // Preserve the existing native authentication forms and verification flows.
  if (data.page !== "home") {
    return (
      <div className="preview-legacy-public">
        <PublicPage data={data} />
      </div>
    )
  }

  const free = data.plans.find((plan) => plan.price_vnd === 0)
  const destination = data.user
    ? data.user.role === "admin" ? "/admin" : "/dashboard"
    : "/register"

  return (
    <div className="preview-public-home">
      <section className="preview-public-hero" aria-labelledby="preview-home-title">
        <div className="preview-public-hero-copy">
          <h1 id="preview-home-title">Không gian cho mọi điều bạn lưu.</h1>
          <p>
            Tệp công việc, những bức ảnh và ý tưởng tiếp theo. Giữ tất cả gọn một
            nơi, chia sẻ khi cần và theo dõi dung lượng dễ dàng với CloudBox.
          </p>
          <div className="preview-public-hero-actions">
            <Button size="lg" asChild>
              <a href={destination}>
                {data.user ? "Mở không gian của tôi" : "Tạo kho lưu trữ"}
                <ArrowUpRight data-icon="inline-end" aria-hidden />
              </a>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <a href="#plans">Xem các gói</a>
            </Button>
          </div>
          {free && (
            <p className="preview-public-free-note">
              <Check aria-hidden />
              {quota(free.quota_gb)} miễn phí để bắt đầu. Nâng cấp khi bạn cần.
            </p>
          )}
        </div>

        <StorageVault />
      </section>

      <section className="preview-public-capabilities" aria-labelledby="preview-tools-title">
        <h2 id="preview-tools-title" className="sr-only">Một không gian, những công cụ bạn cần</h2>
        <Capability icon={FolderOpen} title="Mọi tệp, gọn một nơi">
          Tạo thư mục, tải lên và tìm lại tài liệu trong kho Nextcloud của bạn.
        </Capability>
        <Capability icon={Link2} title="Chia sẻ theo cách của bạn">
          Gửi liên kết tệp hoặc thư mục để tiếp tục công việc cùng nhau.
        </Capability>
        <Capability icon={HardDrive} title="Dung lượng luôn rõ ràng">
          Theo dõi mức sử dụng, chọn gói và quản lý thanh toán trong CloudBox.
        </Capability>
      </section>

      <section id="plans" className="preview-public-pricing" aria-labelledby="preview-pricing-title">
        <div className="preview-public-section-heading">
          <div>
            <h2 id="preview-pricing-title">Chọn không gian vừa với bạn.</h2>
            <p>Gói nhỏ để bắt đầu, dung lượng lớn hơn khi công việc phát triển.</p>
          </div>
          <Badge variant="outline">12 tháng, thanh toán 10 tháng</Badge>
        </div>

        {data.plans.length ? (
          <div className="preview-public-plans">
            {data.plans.map((plan) => (
              <PublicPlan key={plan.id} plan={plan} data={data} />
            ))}
          </div>
        ) : (
          <EmptyState
            title="Bảng giá chưa sẵn sàng"
            description="Hãy tải lại trang sau ít phút để xem các gói đang mở bán."
          >
            <Button variant="outline" onClick={() => window.location.reload()}>Tải lại bảng giá</Button>
          </EmptyState>
        )}
        <p className="preview-public-pricing-note">
          Giá hiển thị theo tháng. Tạo tài khoản miễn phí trước khi nâng cấp gói.
        </p>
      </section>

      <section className="preview-public-next-step" aria-labelledby="preview-next-title">
        <span className="preview-public-next-icon"><Cloud aria-hidden /></span>
        <div>
          <h2 id="preview-next-title">Bắt đầu từ một không gian gọn gàng.</h2>
          <p>Một tài khoản để quản lý tệp, dung lượng và gói dịch vụ.</p>
        </div>
        <Button variant="outline" asChild>
          <a href={destination}>{data.user ? "Vào không gian của tôi" : "Tạo tài khoản"}</a>
        </Button>
      </section>
    </div>
  )
}

function StorageVault() {
  return (
    <div className="preview-public-vault-scene" aria-hidden="true">
      <div className="preview-public-vault-grid" />
      <div className="preview-public-vault-shadow" />
      <div className="preview-public-vault-back" />
      <div className="preview-public-vault">
        <div className="preview-public-vault-topline"><span /><span /><Cloud /></div>
        <div className="preview-public-vault-door">
          <div className="preview-public-vault-folder"><Folder strokeWidth={1.25} /></div>
          <span className="preview-public-vault-door-rule" />
          <span className="preview-public-vault-door-rule" />
          <span className="preview-public-vault-handle" />
          <div className="preview-public-vault-file"><FileText strokeWidth={1.4} /></div>
        </div>
        <div className="preview-public-vault-base"><span /><span /></div>
      </div>
      <div className="preview-public-vault-connected preview-public-vault-connected-laptop"><Laptop /><span>Máy tính</span></div>
      <div className="preview-public-vault-connected preview-public-vault-connected-phone"><Smartphone /><span>Điện thoại</span></div>
      <div className="preview-public-vault-sharing"><Link2 /><span>Sẵn sàng kết nối</span></div>
    </div>
  )
}

function Capability({ icon: Icon, title, children }: {
  icon: typeof FolderOpen
  title: string
  children: string
}) {
  return (
    <article className="preview-public-capability">
      <Icon aria-hidden />
      <div><h3>{title}</h3><p>{children}</p></div>
    </article>
  )
}

function PublicPlan({ plan, data }: { plan: Plan; data: PageData }) {
  const free = plan.price_vnd === 0
  const featured = plan.code === "standard"
  const active = data.user?.plan_id === plan.id
  const destination = !data.user
    ? "/register"
    : data.user.role === "admin" ? "/admin/plans" : "/dashboard#plans"

  return (
    <Card className={cn("preview-public-plan", featured && "preview-public-plan-featured")}>
      <CardHeader>
        <div className="preview-public-plan-heading">
          <CardTitle>{plan.name}</CardTitle>
          {active ? <Badge variant="outline">Đang dùng</Badge> : featured ? <Badge>Đề xuất</Badge> : null}
        </div>
        <CardDescription>
          {free ? "Cho những tệp đầu tiên." : plan.quota_gb >= 1024 ? "Cho những dự án lớn hơn." : "Thêm chỗ cho công việc mỗi ngày."}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-6">
        <div className="preview-public-plan-capacity">{quota(plan.quota_gb)}</div>
        <div className="preview-public-plan-price">
          <strong>{free ? "Miễn phí" : money(plan.price_vnd)}</strong>
          <span>{free ? "Không giới hạn thời gian" : "mỗi tháng"}</span>
        </div>
        <Separator />
        <ul className="preview-public-plan-features">
          {[
            "Kho lưu trữ riêng",
            "Chia sẻ tệp bằng liên kết",
            "Đồng bộ nhiều thiết bị",
          ].map((text) => <li key={text}><Check aria-hidden /><span>{text}</span></li>)}
        </ul>
      </CardContent>
      <CardFooter>
        <Button variant={featured ? "default" : "outline"} className="w-full" asChild>
          <a href={destination}>{data.user ? "Quản lý gói" : free ? "Bắt đầu miễn phí" : "Tạo tài khoản"}</a>
        </Button>
      </CardFooter>
    </Card>
  )
}
