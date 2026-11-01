import { reactive } from "vue";
const values=["auto","light","dark","deep-dark"];
const saved=localStorage.getItem("mp-theme");
export const theme=reactive({value:values.includes(saved)?saved:"auto"});
const media=window.matchMedia("(prefers-color-scheme: dark)");
function apply(){
 const value=theme.value;
 document.documentElement.setAttribute("data-bs-theme",value==="auto"?(media.matches?"dark":"light"):value==="deep-dark"?"dark":value);
 if(value==="deep-dark")document.documentElement.setAttribute("data-mp-theme","deep-dark");else document.documentElement.removeAttribute("data-mp-theme");
}
export function setTheme(value){
 if(!values.includes(value))return;
 theme.value=value;
 if(value==="auto")localStorage.removeItem("mp-theme");else localStorage.setItem("mp-theme",value);
 apply();
}
media.addEventListener("change",()=>{if(theme.value==="auto")apply()});
apply();
