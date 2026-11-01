export type Entry = {path:string;name:string;folder:boolean;size:number;mime:string;modified:string;etag:string;id:string;permissions:string;favorite:boolean;original:string;deleted:number}
export type Listing = {items:Entry[];permissions:string;used:number;available:number;path:string;view:View}
export type View = 'files'|'favorites'|'trash'
export type Session = {csrf:string;authenticated:boolean;uid:string;name:string;nextcloud:string}
let csrf = ''
export class ApiError extends Error { constructor(message:string,public status:number){super(message)} }
export async function api<T>(path:string,options:RequestInit={}):Promise<T>{
 const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),35000)
 try{
  const response=await fetch('/api/files'+path,{...options,signal:options.signal??controller.signal,headers:{...(options.body?{'Content-Type':'application/json'}:{}),'X-CSRF-Token':csrf,...options.headers}})
  if(!response.ok){const payload=await response.json().catch(()=>null);throw new ApiError(payload?.detail??'Không kết nối được kho tệp. Hãy thử lại.',response.status)}
  return await response.json() as T
 }catch(error){if(error instanceof ApiError)throw error;throw new ApiError('Mất kết nối hoặc yêu cầu quá lâu. Hãy thử lại.',0)}finally{clearTimeout(timeout)}
}
export async function getSession(){const s=await api<Session>('/session');csrf=s.csrf;return s}
export function post<T>(path:string,data?:unknown){return api<T>(path,{method:'POST',...(data!==undefined?{body:JSON.stringify(data)}:{})})}
export function action(op:string,path:string,extra:Record<string,unknown>={}){return post('/action',{op,path,...extra})}
export function downloadURL(path:string,preview=false){return '/api/files/download?'+new URLSearchParams({path,...(preview?{preview:'true'}:{})})}
export function upload(file:File,path:string,onProgress:(progress:number)=>void):Promise<void>{
 return new Promise((resolve,reject)=>{const xhr=new XMLHttpRequest();xhr.open('PUT','/api/files/upload?'+new URLSearchParams({path}));xhr.timeout=300000;xhr.setRequestHeader('X-CSRF-Token',csrf);xhr.setRequestHeader('Content-Type','application/octet-stream');xhr.upload.onprogress=e=>{if(e.lengthComputable)onProgress(Math.round(e.loaded/e.total*100))};xhr.onload=()=>{if(xhr.status>=200&&xhr.status<300)resolve();else{let message='Không tải lên được tệp.';try{message=JSON.parse(xhr.responseText).detail??message}catch{}reject(new ApiError(message,xhr.status))}};xhr.onerror=()=>reject(new ApiError('Mất kết nối khi tải lên. Hãy thử lại.',0));xhr.ontimeout=()=>reject(new ApiError('Tải lên quá lâu. Hãy thử lại.',0));xhr.send(file)})
}
export function bytes(n:number){if(n<0)return 'Không giới hạn';if(n===0)return '0 B';const i=Math.min(Math.floor(Math.log(n)/Math.log(1024)),4);return new Intl.NumberFormat('vi-VN',{maximumFractionDigits:i?1:0}).format(n/1024**i)+' '+['B','KB','MB','GB','TB'][i]}
export function date(s:string){const d=new Date(s);return Number.isNaN(d.getTime())?'—':new Intl.DateTimeFormat('vi-VN',{dateStyle:'medium'}).format(d)}
