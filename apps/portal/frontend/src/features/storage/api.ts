import {csrfToken} from "@/shared/csrf"
export interface FileItem {
  id: string; name: string; is_folder: boolean; parent_id: string|null; size: number;
  modified_at: string; deleted_at: string|null; mime_type?: string; sha256?: string;
}
export interface StorageUsage {used:number;total:number;reserved:number;available:number;percent:number;trash_counts?:boolean}
export interface FileList {items:FileItem[]; ancestors:{id:string;name:string}[]; usage:StorageUsage;limit?:number;offset?:number;total_count?:number;has_more?:boolean;next_offset?:number|null}
export interface ShareItem {id:string;file_id?:string;name?:string;is_folder?:boolean;created_at:string;permission:string;revoked:boolean;expires_at?:string|null;password_protected?:boolean;views?:number;downloads?:number;stats_since?:string|null}
export interface CreatedShare {id:string;token:string;url:string;permission:string}
export async function storageApi<T>(url:string, options:RequestInit={}):Promise<T> {
  let response:Response
  try{response=await fetch(url,{...options,credentials:"same-origin",headers:{...((options.method??"GET").toUpperCase()!=="GET"?{"X-CSRF-Token":csrfToken()}:{}),...(typeof options.body==="string"?{"Content-Type":"application/json"}:{}),...options.headers}})}catch(cause){if(cause instanceof DOMException&&cause.name==="AbortError")throw cause;throw new Error("Không kết nối được với CloudBox. Kiểm tra mạng rồi thử lại.")}
  if(response.status===401||(response.redirected&&new URL(response.url).pathname==="/login")){window.location.assign("/login");throw new Error("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.")}
  if(!response.ok){const content=await response.json().catch(()=>null);throw new Error(typeof content?.detail==="string"?content.detail:"Chưa thể hoàn tất thao tác. Vui lòng thử lại.")}
  if(response.status===204) return undefined as T
  if(!response.headers.get("content-type")?.includes("application/json"))throw new Error("CloudBox chưa trả về kết quả hợp lệ. Hãy tải lại trang rồi thử lại.")
  return response.json() as Promise<T>
}
export const jsonBody=(value:unknown)=>JSON.stringify(value)
export function publishUsage(usage:StorageUsage){window.dispatchEvent(new CustomEvent("cloudbox:usage",{detail:usage}))}
