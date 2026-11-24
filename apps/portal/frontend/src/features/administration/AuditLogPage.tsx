import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { EmptyState, PageHeading } from "@/shared/ui"
import type { AdminAuditData } from "@/shared/types"

const timestamp = new Intl.DateTimeFormat("vi-VN", {
  dateStyle: "short", timeStyle: "medium", timeZone: "Asia/Ho_Chi_Minh",
})

export function AuditLogPage({ audit }: { audit?: AdminAuditData | null }) {
  return (
    <div className="flex min-w-0 flex-col gap-6">
      <PageHeading title="Nhật ký quản trị" description="Xem lịch sử khóa tài khoản, cấp gói và đổi giá." />
      {!audit?.entries.length ? (
        <EmptyState title="Chưa có thao tác được ghi nhận" description="Nhật ký sẽ xuất hiện sau khi quản trị viên thực hiện một thao tác được theo dõi." />
      ) : (
        <Card className="min-w-0">
          <CardContent className="flex min-w-0 flex-col gap-4">
            <Table>
              <TableCaption className="sr-only">Lịch sử thao tác quản trị</TableCaption>
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Thời điểm</TableHead>
                  <TableHead scope="col">Người thực hiện</TableHead>
                  <TableHead scope="col">Thao tác</TableHead>
                  <TableHead scope="col">Đối tượng</TableHead>
                  <TableHead scope="col">Trước</TableHead>
                  <TableHead scope="col">Sau</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {audit.entries.map(entry => (
                  <TableRow key={entry.id}>
                    <TableCell><time dateTime={entry.created_at}>{timestamp.format(new Date(entry.created_at))}</time></TableCell>
                    <TableCell>Quản trị viên #{entry.actor_id}</TableCell>
                    <TableCell>{entry.action}</TableCell>
                    <TableCell>{entry.subject}</TableCell>
                    <TableCell>{entry.before}</TableCell>
                    <TableCell>{entry.after}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {audit.pages > 1 && <nav aria-label="Phân trang nhật ký" className="flex flex-wrap items-center gap-2">
              {audit.page > 1 && <Button variant="outline" size="sm" asChild><a href={`/admin/audit?page=${audit.page - 1}`}>Trang trước</a></Button>}
              <span className="px-1 text-sm text-muted-foreground">Trang {audit.page}/{audit.pages}</span>
              {audit.page < audit.pages && <Button variant="outline" size="sm" asChild><a href={`/admin/audit?page=${audit.page + 1}`}>Trang sau</a></Button>}
            </nav>}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
