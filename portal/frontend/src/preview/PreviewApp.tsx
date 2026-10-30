import { useEffect, useState, type ReactNode } from "react"
import LiquidGlass from "liquid-glass-react"
import { App } from "../App"
import { PreviewDashboard } from "./PreviewDashboard"
import { PreviewPublicPage } from "./preview-public"
import type { PageData } from "../types"
import "./preview.css"
import "./preview-public.css"

document.documentElement.dataset.ui = "preview"

function GlassToolbar({children}:{children:ReactNode}) {
 const query="(min-width: 768px) and (pointer: fine) and (prefers-reduced-motion: no-preference)"
 const [glass,setGlass]=useState(()=>matchMedia(query).matches)
 const [dark,setDark]=useState(()=>document.documentElement.classList.contains("dark"))
 useEffect(()=>{
  const media=matchMedia(query),update=()=>setGlass(media.matches)
  media.addEventListener("change",update)
  const observer=new MutationObserver(()=>setDark(document.documentElement.classList.contains("dark")))
  observer.observe(document.documentElement,{attributes:true,attributeFilter:["class"]})
  return()=>{media.removeEventListener("change",update);observer.disconnect()}
 },[])
 if(!glass)return <div className="preview-toolbar-fallback">{children}</div>
 return <div className="preview-glass-host" data-glass="active">
  <LiquidGlass mode="standard" displacementScale={22} blurAmount={0.05} saturation={110} aberrationIntensity={0.5} elasticity={0} cornerRadius={18} padding="5px 8px" overLight={!dark} style={{position:"absolute",top:"50%",left:"50%"}} className="preview-glass-main">
   <div className="preview-toolbar-content">{children}</div>
  </LiquidGlass>
 </div>
}
export default function PreviewApp({data}:{data:PageData}) {
 return <div className="cloudbox-preview"><App data={data} DashboardComponent={PreviewDashboard} PublicComponent={PreviewPublicPage} ToolbarSurface={GlassToolbar}/></div>
}
