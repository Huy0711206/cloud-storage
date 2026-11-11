import {FolderOpen, HardDrive, Info, RefreshCw, ShieldCheck, AlertCircle} from "lucide-react"
import {Button} from "@/components/ui/button"
import {Badge} from "@/components/ui/badge"
import {Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter} from "@/components/ui/card"
import {Alert, AlertTitle, AlertDescription} from "@/components/ui/alert"
import {Separator} from "@/components/ui/separator"
import {bytes, quota} from "@/shared/ui"
import type {PageData} from "@/shared/types"
import {cn} from "@/lib/utils"


export function StorageButton({data:_data}:{data:PageData}) { return <Button asChild><a href={_data.user?.role==="admin"?"/files#storage":"/dashboard#storage"}><FolderOpen data-icon="inline-start" aria-hidden/>Mở kho lưu trữ</a></Button> }

export function UsageCard({data}:{data:PageData}) {
 const usage=data.usage
 return <Card className="usage-card"><CardHeader className="flex flex-row items-start justify-between gap-3"><div><CardTitle>Dung lượng lưu trữ</CardTitle><CardDescription>Không gian dành cho những điều quan trọng.</CardDescription></div><Badge variant="secondary">{quota(data.user!.plan!.quota_gb)}</Badge></CardHeader><CardContent>
  {usage?<div className="usage-content"><div className={cn("storage-ring",usage.percent>=90&&"storage-ring-warning")} role="img" aria-label={"Đã dùng "+usage.percent+" phần trăm dung lượng"}><svg viewBox="0 0 160 160" aria-hidden><circle className="ring-track" cx="80" cy="80" r="65"/><circle className="ring-value" cx="80" cy="80" r="65" strokeDasharray={(Math.max(usage.percent,0.3)/100*408.4)+" 408.4"} transform="rotate(-90 80 80)"/></svg><div className="storage-ring-label"><HardDrive aria-hidden/><strong>{usage.percent}<small>%</small></strong><span>đã sử dụng</span></div></div><div className="usage-details"><div><p className="label-dot">Đã sử dụng</p><strong>{bytes(usage.used)}</strong></div><Separator/><div><p className="label-dot label-dot-muted">Còn trống</p><strong>{bytes(Math.max(usage.total-usage.used,0))}</strong></div><p className="text-xs leading-relaxed text-muted-foreground">Tổng dung lượng {bytes(usage.total)}</p></div></div>:<div className="usage-unavailable"><AlertCircle className="size-8" aria-hidden/><h2>Chưa đọc được dung lượng</h2><p>Kho lưu trữ đang phản hồi chậm. Dữ liệu của bạn vẫn được giữ nguyên.</p><Button variant="outline" onClick={()=>window.location.reload()}><RefreshCw data-icon="inline-start" aria-hidden/>Thử lại</Button></div>}
  {usage&&usage.percent>=90&&<Alert data-tone="warning"><Info aria-hidden/><AlertTitle>Kho lưu trữ sắp đầy</AlertTitle><AlertDescription>Xóa tệp không cần thiết hoặc nâng cấp gói để có thêm dung lượng.</AlertDescription></Alert>}
 </CardContent><CardFooter className="justify-between gap-4"><span className="flex items-center gap-2 text-xs text-muted-foreground"><ShieldCheck className="size-4" aria-hidden/>Kho riêng cho tài khoản của bạn</span><Button variant="ghost" size="sm" onClick={()=>window.location.reload()} aria-label="Cập nhật dung lượng"><RefreshCw data-icon="inline-start" aria-hidden/>Cập nhật</Button></CardFooter></Card>
}
export { NativeFilesPage as StoragePage } from "./NativeFilesPage"
