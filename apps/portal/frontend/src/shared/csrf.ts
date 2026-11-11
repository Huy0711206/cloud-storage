/** Token comes from the current server-rendered page, never from local storage. */
export function csrfToken():string {
  try {return JSON.parse(document.getElementById("cloudbox-data")?.textContent??"{}").csrf_token??""}
  catch {return ""}
}
