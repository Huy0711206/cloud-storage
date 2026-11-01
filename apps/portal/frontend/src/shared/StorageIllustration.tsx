import {Cloud, File, FileImage, FileText, Folder, Layers3} from "lucide-react"

import {cn} from "@/lib/utils"


export function StorageIllustration({ compact = false }: { compact?: boolean }) {
  return (
    <div className={cn("storage-illustration", compact && "storage-illustration-compact")} aria-hidden="true">
      <div className="storage-illustration-orbit" />
      <div className="storage-illustration-window">
        <div className="storage-window-toolbar">
          <span /><span /><span />
          <Cloud className="ml-auto size-4" />
        </div>
        <div className="storage-window-content">
          <div className="storage-folder"><Folder strokeWidth={1.25} /></div>
          <div className="storage-file-grid">
            <div className="storage-file"><FileText strokeWidth={1.5} /><span>Tài liệu</span></div>
            <div className="storage-file"><FileImage strokeWidth={1.5} /><span>Hình ảnh</span></div>
            <div className="storage-file"><File strokeWidth={1.5} /><span>Tệp khác</span></div>
          </div>
          <div className="storage-window-line" /><div className="storage-window-line storage-window-line-short" />
        </div>
      </div>
      <div className="storage-floating-label"><Cloud /><span>Một nơi cho mọi tệp</span></div>
      <div className="storage-floating-icon"><Layers3 strokeWidth={1.5} /></div>
    </div>
  )
}

