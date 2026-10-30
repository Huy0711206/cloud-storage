import { Component, Suspense, lazy, type ReactNode } from "react"
import { createRoot } from "react-dom/client"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AlertCircle } from "lucide-react"
import { App as StableApp } from "./App"
const App=import.meta.env.VITE_UI_VARIANT==="preview" ? lazy(()=>import("./preview/PreviewApp")) : StableApp
import type { PageData } from "./types"
import "./index.css"

class ErrorBoundary extends Component<{children:ReactNode},{error:boolean}> {
 state={error:false}
 static getDerivedStateFromError(){return {error:true}}
 componentDidCatch(error:Error){console.error("CloudBox UI:",error)}
 render(){return this.state.error?<main className="error-boundary"><Alert variant="destructive"><AlertCircle aria-hidden/><AlertTitle>Chưa thể hiển thị giao diện</AlertTitle><AlertDescription>Dữ liệu của bạn vẫn được lưu. Hãy tải lại trang để thử lại.</AlertDescription></Alert><Button onClick={()=>window.location.reload()}>Tải lại trang</Button></main>:this.props.children}
}
const element=document.getElementById("cloudbox-data")
const root=createRoot(document.getElementById("root")!)
try {
 if(!element?.textContent)throw new Error("Missing page data")
 const data=JSON.parse(element.textContent) as PageData
 root.render(<ErrorBoundary><TooltipProvider><Suspense fallback={<div className="boot-screen" role="status">Đang mở CloudBox…</div>}><App data={data}/></Suspense></TooltipProvider></ErrorBoundary>)
} catch {
 root.render(<main className="error-boundary"><h1>Chưa tải được CloudBox</h1><p>Hãy mở ứng dụng qua máy chủ CloudBox.</p><Button asChild><a href="http://localhost:8000">Mở CloudBox</a></Button></main>)
}
