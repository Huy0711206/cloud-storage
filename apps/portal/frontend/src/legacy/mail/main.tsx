import { Component, type ReactNode } from "react"
import { createRoot } from "react-dom/client"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Button } from "@/components/ui/button"
import { MailApp } from "@/legacy/mail/MailApp"
import "@/legacy/mail/mail.css"

document.documentElement.dataset.app="mail"
try{const t=localStorage.getItem("cloudbox-theme");document.documentElement.classList.toggle("dark",t==="dark"||((!t||t==="system")&&matchMedia("(prefers-color-scheme: dark)").matches))}catch{}
class ErrorBoundary extends Component<{children:ReactNode},{error:boolean}>{
 state={error:false}
 static getDerivedStateFromError(){return {error:true}}
 componentDidCatch(error:Error){console.error("CloudBox Mail:",error)}
 render(){return this.state.error?<main className="mail-fatal"><h1>Chưa mở được hộp thư</h1><p>Hãy tải lại trang để kết nối lại với Mailpit.</p><Button onClick={()=>location.reload()}>Tải lại trang</Button></main>:this.props.children}
}
createRoot(document.getElementById("root")!).render(<ErrorBoundary><TooltipProvider><MailApp/></TooltipProvider></ErrorBoundary>)
