<script>
import {theme,setTheme} from './theme.js';
let instance=0;
export default {
 data(){return {theme,name:`cloudbox-mail-theme-${++instance}`,options:[{value:'light',label:'Giao diện sáng',icon:'bi-sun'},{value:'dark',label:'Giao diện tối',icon:'bi-moon'},{value:'auto',label:'Theo thiết bị',icon:'bi-display'}]}},
 methods:{setTheme},
};
</script>
<template><fieldset class="cb-theme"><legend>Giao diện</legend><label v-for="option in options" :key="option.value" :title="option.label"><input type="radio" :name="name" :value="option.value" :checked="theme.value===option.value || (option.value==='dark' && theme.value==='deep-dark')" @change="setTheme(option.value)"><span><i class="bi" :class="option.icon" aria-hidden="true"></i><span class="cb-theme-name">{{option.label}}</span></span></label></fieldset></template>
