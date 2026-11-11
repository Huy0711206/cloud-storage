import {useEffect,useState} from "react"
import {Check} from "lucide-react"
import {Table,TableBody,TableCell,TableHead,TableHeader,TableRow} from "@/components/ui/table"
import {Notice,bytes} from "@/shared/ui"
import type {Plan} from "@/shared/types"

interface PlanBenefits {code:string;versions?:boolean;version_days:number;expiring_links:boolean;password_links:boolean;file_requests:boolean;team_space:boolean;share_stats:boolean;team_members:number}
interface BenefitsResponse {plans:Record<string,PlanBenefits>;current:PlanBenefits|null;deployment?:{trial:boolean;storage_pool_limit_bytes:number};capacity?:{pool_limit_bytes:number;used_bytes:number;reserved_bytes:number;available_bytes:number|null;warning:string|null}|null}
const empty:PlanBenefits={code:"free",version_days:0,expiring_links:false,password_links:false,file_requests:false,team_space:false,share_stats:false,team_members:0}
let pending:Promise<BenefitsResponse>|null=null
export function usePlanBenefits(){
 const [value,setValue]=useState<BenefitsResponse>({plans:{},current:null})
 useEffect(()=>{let active=true;pending??=fetch("/api/plan-benefits",{credentials:"same-origin"}).then(async response=>{if(!response.ok)throw new Error("benefits unavailable");return response.json() as Promise<BenefitsResponse>}).catch(()=>{pending=null;return {plans:{},current:null}});void pending.then(result=>{if(active)setValue(result)});return()=>{active=false}},[])
 return value
}
export const benefitsFor=(plans:Record<string,PlanBenefits>,code:string)=>plans[code]??{...empty,code}
export function planDescription(code:string,benefits:PlanBenefits){
 if(code==="free")return "Bắt đầu lưu tài liệu, không mất phí."
 if(code==="basic")return "Thêm chỗ cho học tập và công việc mỗi ngày."
 if(code==="standard")return benefits.password_links?"Chia sẻ tài liệu với khách hàng, kiểm soát cách truy cập.":"Dành chỗ cho tài liệu và những dự án đang phát triển."
 return benefits.team_space?"Một không gian chung cho nhóm nhỏ và dự án lớn.":"Dung lượng rộng rãi cho những dự án lớn."
}
function planHighlights(code:string,benefits:PlanBenefits):string[]{
 if(code==="free")return ["Quản lý tệp và thư mục","Chia sẻ và thu hồi liên kết","Thùng rác và khôi phục"]
 const items:string[]=[]
 if(benefits.version_days)items.push(`Lịch sử phiên bản ${benefits.version_days} ngày`)
 if(benefits.team_space)items.push(`Không gian nhóm tối đa ${benefits.team_members} người`)
 if(benefits.share_stats)items.push("Thống kê lượt xem và tải xuống")
 if(benefits.password_links)items.push("Liên kết có mật khẩu và hạn dùng")
 else if(benefits.expiring_links)items.push("Đặt hạn dùng liên kết")
 if(benefits.file_requests)items.push("Nhận tệp qua liên kết riêng")
 return items.length?items.slice(0,4):["Thêm chỗ cho tài liệu của bạn","Chia sẻ và thu hồi liên kết","Truy cập trên nhiều thiết bị"]
}
export function PlanFeatureList({code,benefits}:{code:string;benefits:PlanBenefits}){return <ul className="plan-benefit-list">{planHighlights(code,benefits).map(text=><li key={text}><Check aria-hidden/><span>{text}</span></li>)}</ul>}
export function PlanComparison({plans,benefits}:{plans:Plan[];benefits:Record<string,PlanBenefits>}){
 const rows:[string,(value:PlanBenefits)=>string][]=[
  ["Quản lý tệp, chia sẻ và thùng rác",()=>"Có"],
  ["Lịch sử phiên bản tự động",v=>v.version_days?`${v.version_days} ngày`:"—"],
  ["Hạn dùng liên kết",v=>v.expiring_links?"Có":"—"],
  ["Mật khẩu liên kết",v=>v.password_links?"Có":"—"],
  ["Yêu cầu nhận tệp",v=>v.file_requests?"Có":"—"],
  ["Không gian nhóm",v=>v.team_space?`Tối đa ${v.team_members} người`:"—"],
  ["Thống kê chia sẻ",v=>v.share_stats?"Có":"—"],
 ]
 return <section className="plan-comparison" aria-label="So sánh quyền lợi các gói"><h3>So sánh quyền lợi</h3><p>Mọi gói đều có quản lý thư mục, truy cập qua trình duyệt, thùng rác và chia sẻ liên kết. Bảo mật tài khoản được áp dụng cho tất cả các gói.</p>{Object.keys(benefits).length>0&&<Table><TableHeader><TableRow><TableHead>Quyền lợi</TableHead>{plans.map(plan=><TableHead key={plan.id}>{plan.name}</TableHead>)}</TableRow></TableHeader><TableBody>{rows.map(([label,get])=><TableRow key={label}><TableCell>{label}</TableCell>{plans.map(plan=><TableCell key={plan.id}>{get(benefitsFor(benefits,plan.code))}</TableCell>)}</TableRow>)}</TableBody></Table>}<p>Thùng rác và phiên bản được lưu vẫn tính vào dung lượng. Lịch sử phiên bản giúp quay lại bản trước; không thay thế bản sao lưu khi hỏng ổ đĩa. Quyền lợi giống nhau ở kỳ 1, 3 và 12 tháng.</p>{Object.values(benefits).some(value=>value.team_space)&&<p>Dung lượng gói Cao cấp là tổng dung lượng dùng chung của chủ gói và nhóm, không phải dung lượng riêng cho mỗi thành viên.</p>}</section>
}

export function PlanCapacityNotice(){const info=usePlanBenefits();return info.deployment?.trial?<Notice title="CloudBox đang trong giai đoạn thử nghiệm">Toàn hệ thống hiện dùng chung {bytes(info.deployment?.storage_pool_limit_bytes??0)} dung lượng thử nghiệm. Dung lượng ghi trên gói là hạn mức tài khoản; khả năng tải thêm còn phụ thuộc dung lượng máy chủ đang có. Hệ thống sẽ báo rõ khi không còn đủ chỗ.</Notice>:null}

export function AdminStorageCapacity(){
 const {capacity}=usePlanBenefits()
 if(!capacity)return null
 return <Notice title="Ngân sách lưu trữ toàn hệ thống"><p>Đã dùng {bytes(capacity.used_bytes)} · Đang giữ chỗ {bytes(capacity.reserved_bytes)} · Còn {capacity.available_bytes===null?"chưa đặt giới hạn":bytes(capacity.available_bytes)} trong ngân sách {bytes(capacity.pool_limit_bytes)}.</p><p>{capacity.warning} Đây không phải phép đo chỗ trống ổ C:. Hãy kiểm tra dung lượng Windows trước khi tăng ngân sách.</p></Notice>
}
