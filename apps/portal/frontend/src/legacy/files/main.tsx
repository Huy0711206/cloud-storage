import { Component, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Button } from '@/components/ui/button'
import { Toaster } from 'sonner'
import { FilesApp } from '@/legacy/files/FilesApp'
import '@/legacy/files/files.css'
document.documentElement.dataset.app='files'
try{const t=localStorage.getItem('cloudbox-files-theme');document.documentElement.classList.toggle('dark',t==='dark'||(!t&&matchMedia('(prefers-color-scheme: dark)').matches))}catch{}
class Boundary extends Component<{children:ReactNode},{error:boolean}>{state={error:false};static getDerivedStateFromError(){return {error:true}}render(){return this.state.error?<main className="files-fatal"><h1>Chưa mở được kho tệp</h1><p>Hãy tải lại trang để kết nối lại.</p><Button onClick={()=>location.reload()}>Tải lại</Button></main>:this.props.children}}
createRoot(document.getElementById('root')!).render(<Boundary><TooltipProvider><FilesApp/><Toaster richColors position="bottom-right"/></TooltipProvider></Boundary>)
