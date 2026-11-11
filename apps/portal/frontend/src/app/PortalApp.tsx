import type { ReactNode } from "react"
import { App } from "@/app/AppShell"
import { OverviewPage } from "@/features/dashboard/OverviewPage"
import { LandingPage } from "@/features/public/LandingPage"
import type { PageData } from "@/shared/types"
import "@/styles/overview.css"
import "@/styles/landing.css"
import "@/styles/generated.css"
import "@/styles/unified.css"
import "@/styles/native-files.css"

// Reuse the proven full page renderers; all routes/forms remain server-backed.
document.documentElement.dataset.ui = "preview"
document.documentElement.dataset.cloudbox = "unified"
function Toolbar({children}:{children:ReactNode}) {
 return <div className="cb-toolbar">{children}</div>
}
export default function PortalApp({data}:{data:PageData}) {
 return <div className="cloudbox-preview cloudbox-unified"><App data={data} DashboardComponent={OverviewPage} PublicComponent={LandingPage} ToolbarSurface={Toolbar}/></div>
}
