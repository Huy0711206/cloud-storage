/* Email HTML stays in an inert template while it is reduced to display markup.
   The result is only used by a sandboxed, opaque-origin iframe with a restrictive CSP. */
const allowedTags = new Set("a abbr address article aside b bdi bdo blockquote br caption center cite code col colgroup dd del details div dl dt em figcaption figure font footer h1 h2 h3 h4 h5 h6 header hr i img ins kbd li main mark ol p pre q s samp section small span strike strong style sub summary sup table tbody td tfoot th thead time tr tt u ul wbr".split(" "))
const discardedTags = new Set("script iframe frame frameset object embed applet form input button textarea select option link meta base svg math video audio source track canvas template noscript title".split(" "))
const allowedAttributes = new Set("style class id title lang dir role aria-label colspan rowspan width height align valign bgcolor border cellpadding cellspacing face color size start type".split(" "))
const voidTags = new Set(["br", "col", "hr", "img", "wbr"])
const escapeText = (text: string) => text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
const escapeAttribute = (text: string) => escapeText(text).replace(/"/g, "&quot;")
const safeDataImage = /^data:image\/(?:png|jpeg|gif|webp|avif);base64,[a-z\d+/\s]+=*$/i

export function normalizeContentId(value: string): string {
  try { return decodeURIComponent(value.replace(/^cid:/i, "")).replace(/^<|>$/g, "").toLowerCase() } catch { return "" }
}

export function referencedContentIds(html: string): Set<string> {
  const template = document.createElement("template")
  template.innerHTML = html
  return new Set([...template.content.querySelectorAll("img")].map(img => img.getAttribute("src") || "").filter(src => /^cid:/i.test(src)).map(normalizeContentId))
}

export function buildEmailDocument(html: string, cidSources: Record<string, string> = {}): string {
  const template = document.createElement("template")
  template.innerHTML = html
  const serialize = (node: Node): string => {
    if (node.nodeType === Node.TEXT_NODE) return escapeText(node.textContent || "")
    if (!(node instanceof Element)) return ""
    const tag = node.tagName.toLowerCase()
    if (discardedTags.has(tag)) return ""
    const children = () => [...node.childNodes].map(serialize).join("")
    if (!allowedTags.has(tag)) return children()
    if (tag === "style") return "<style>" + (node.textContent || "").replace(/<\/style/gi, "<\\/style") + "</style>"
    const attrs: string[] = []
    for (const attribute of [...node.attributes]) {
      const name = attribute.name.toLowerCase()
      if (allowedAttributes.has(name)) attrs.push(name + '="' + escapeAttribute(attribute.value) + '"')
    }
    if (tag === "img") {
      const original = node.getAttribute("src") || ""
      const src = /^cid:/i.test(original) ? cidSources[normalizeContentId(original)] : safeDataImage.test(original) ? original : ""
      if (src && safeDataImage.test(src)) attrs.push('src="' + escapeAttribute(src) + '"')
      attrs.push('alt="' + escapeAttribute(node.getAttribute("alt") || (src ? "Ảnh trong thư" : "Ảnh bên ngoài đã được chặn")) + '"')
    }
    return "<" + tag + (attrs.length ? " " + attrs.join(" ") : "") + ">" + (voidTags.has(tag) ? "" : children() + "</" + tag + ">")
  }
  const body = [...template.content.childNodes].map(serialize).join("")
  const csp = "default-src 'none'; script-src 'none'; img-src data:; style-src 'unsafe-inline'; font-src 'none'; media-src 'none'; frame-src 'none'; object-src 'none'; connect-src 'none'; base-uri 'none'; form-action 'none'"
  return '<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="' + csp + '"><meta name="referrer" content="no-referrer"><meta name="viewport" content="width=device-width,initial-scale=1"><style>html{color-scheme:light}body{margin:0;padding:24px;background:#fff;color:#172033;font:16px/1.7 Arial,sans-serif;overflow-wrap:anywhere}img{max-width:100%;height:auto}table{max-width:100%}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#335cff;text-decoration:underline;cursor:text}</style></head><body>' + body + "</body></html>"
}
