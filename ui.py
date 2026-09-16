# ui.py — صفحات وب: لاگین، داشبورد SPA (روشن/تاریک)، صفحه ساب تکی هوشمند
from __future__ import annotations

import html

BASE_CSS = """
:root{
  --bg:#eef1f6; --bg2:#ffffff; --card:#ffffff; --text:#16233a; --muted:#66788f;
  --line:#dde4ee; --brand:#3b5bdb; --brand2:#7048e8; --ok:#0ca678; --warn:#e67700;
  --bad:#e03131; --chip:#edf1fd; --shadow:0 2px 12px rgba(25,45,90,.07);
  --accent:linear-gradient(135deg,#3b5bdb,#7048e8);
  --radius:14px;
}
[data-theme=dark]{
  --bg:#0d1322; --bg2:#111a2e; --card:#131d33; --text:#e6ecf7; --muted:#8b99b3;
  --line:#22304d; --brand:#748ffc; --brand2:#9775fa; --chip:#1a2542;
  --shadow:0 2px 14px rgba(0,0,0,.4);
}
*{box-sizing:border-box}
body{margin:0;font-family:"Vazirmatn","IRANSansX",Tahoma,"Segoe UI",sans-serif;background:var(--bg);color:var(--text);direction:rtl;font-size:14.5px;line-height:1.9}
a{color:var(--brand);text-decoration:none}
.wrap{max-width:960px;margin:0 auto;padding:20px}
.topbar{position:sticky;top:0;z-index:50;background:color-mix(in srgb,var(--bg2) 90%,transparent);backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}
.topbar .wrap{display:flex;align-items:center;gap:12px;padding-top:11px;padding-bottom:11px}
.logo{width:38px;height:38px;border-radius:11px;background:var(--accent);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:800;font-size:18px}
.brand-name{font-weight:800;font-size:17px}
.brand-sub{font-size:11.5px;color:var(--muted);font-family:Consolas,monospace;direction:ltr;text-align:right}
.spacer{flex:1}
.btn{border:1px solid var(--line);background:var(--card);color:var(--text);border-radius:10px;padding:8px 15px;cursor:pointer;font-family:inherit;font-size:13.5px;transition:.15s}
.btn:hover{border-color:var(--brand)}
.btn.primary{background:var(--accent);color:#fff;border:none;font-weight:700}
.btn.danger{background:transparent;color:var(--bad);border-color:color-mix(in srgb,var(--bad) 35%,transparent)}
.btn.danger:hover{background:color-mix(in srgb,var(--bad) 10%,transparent)}
.btn.small{padding:5px 11px;font-size:12.5px;border-radius:8px}
.btn.ghost{background:transparent;border-color:transparent;font-size:16px}
.grid{display:grid;gap:12px}
.cards{grid-template-columns:repeat(auto-fit,minmax(160px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:16px 18px;box-shadow:var(--shadow)}
.stat-num{font-size:24px;font-weight:800;margin:2px 0;font-variant-numeric:tabular-nums}
.stat-lbl{font-size:12px;color:var(--muted)}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}
.tab{border:1px solid var(--line);background:var(--card);color:var(--muted);border-radius:10px;padding:7px 16px;cursor:pointer;font-family:inherit;font-size:13.5px}
.tab.on{background:var(--accent);color:#fff;border:none;font-weight:700}
.pill{display:inline-flex;align-items:center;gap:6px;border-radius:99px;padding:2px 12px;font-size:12px;font-weight:700}
.pill::before{content:"";width:8px;height:8px;border-radius:50%;background:currentColor}
.pill.ok{background:color-mix(in srgb,var(--ok) 13%,transparent);color:var(--ok)}
.pill.off{background:color-mix(in srgb,var(--muted) 15%,transparent);color:var(--muted)}
.pill.end{background:color-mix(in srgb,var(--bad) 12%,transparent);color:var(--bad)}
.pill.full{background:color-mix(in srgb,var(--warn) 14%,transparent);color:var(--warn)}
.bar{height:7px;background:var(--line);border-radius:99px;overflow:hidden}
.bar>i{display:block;height:100%;background:var(--accent);border-radius:99px;transition:width .4s}
.mono{direction:ltr;font-family:Consolas,monospace;font-size:11px;word-break:break-all;color:var(--muted);text-align:left}
.meta{display:flex;gap:14px;flex-wrap:wrap;font-size:12.5px;color:var(--muted)}
.meta b{color:var(--text);font-weight:600}
.route{border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin-top:8px;background:color-mix(in srgb,var(--bg) 55%,var(--card))}
.route-head{display:flex;align-items:center;gap:8px;margin-bottom:6px}
.route-tag{font-size:11.5px;font-weight:700;background:var(--chip);color:var(--brand);border-radius:6px;padding:1px 9px}
.chip{display:inline-block;background:var(--chip);color:var(--brand);border-radius:6px;padding:1px 9px;font-size:12px}
.modal-bg{position:fixed;inset:0;background:rgba(5,10,25,.55);display:none;align-items:center;justify-content:center;z-index:99;padding:16px}
.modal-bg.show{display:flex}
.modal{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:22px;width:min(600px,100%);max-height:90vh;overflow:auto}
.modal h3{margin:0 0 14px;font-size:16px}
.frm{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.frm .full{grid-column:1/-1}
label.fl{display:flex;flex-direction:column;gap:5px;font-size:12px;color:var(--muted)}
input,select{background:var(--bg);border:1px solid var(--line);color:var(--text);border-radius:9px;padding:8px 11px;font-family:inherit;font-size:13.5px;width:100%}
input:focus,select:focus{outline:2px solid var(--brand);border-color:transparent}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.toast{position:fixed;bottom:22px;right:50%;transform:translateX(50%);background:#0f172a;color:#fff;padding:9px 22px;border-radius:10px;font-size:13.5px;display:none;z-index:200;box-shadow:var(--shadow)}
[data-theme=dark] .toast{background:#e8eefb;color:#0f172a}
.log{font-size:12.5px;padding:8px 10px;border-bottom:1px solid var(--line);display:flex;gap:8px;align-items:baseline}
.log time{color:var(--muted);font-size:11px;white-space:nowrap}
.lv-ok{color:var(--ok)} .lv-warn{color:var(--warn)} .lv-info{color:var(--brand)} .lv-err{color:var(--bad)}
.subbox{border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin-top:8px;background:color-mix(in srgb,var(--brand) 5%,var(--card))}
.hero{border:1px solid var(--line);background:var(--card);border-radius:18px;padding:30px 24px;text-align:center;box-shadow:var(--shadow);margin-bottom:14px}
.hero h1{margin:0 0 4px;font-size:22px}
.hero p{margin:4px 0;color:var(--muted);font-size:13.5px}
.qr{background:#fff;border-radius:10px;padding:6px;display:inline-block;line-height:0}
.kv{display:flex;justify-content:space-between;gap:10px;padding:7px 0;border-bottom:1px solid var(--line);font-size:13px}
.kv:last-child{border-bottom:none}
.kv span:first-child{color:var(--muted)}
.kv b{font-variant-numeric:tabular-nums}
.section-t{font-size:13px;font-weight:800;color:var(--muted);margin:16px 2px 8px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:9px 8px;border-bottom:1px solid var(--line);text-align:right;vertical-align:middle}
th{color:var(--muted);font-weight:600;font-size:12px}
@media(max-width:700px){.frm{grid-template-columns:1fr}.wrap{padding:14px}}
"""

LOGIN_HTML = """<!DOCTYPE html><html lang="fa" data-theme="dark"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>NovaPanel · ورود</title>
<link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet">
<style>""" + BASE_CSS + """</style></head><body>
<div class="wrap" style="max-width:380px;padding-top:10vh">
<div class="card" style="text-align:center;padding:32px 26px">
<div class="logo" style="margin:0 auto 12px;width:52px;height:52px;font-size:25px">N</div>
<div class="brand-name" style="font-size:20px">NovaPanel</div>
<div class="brand-sub" style="margin-bottom:18px;text-align:center">پنل مدیریت</div>
<input id="pw" type="password" placeholder="رمز ادمین" onkeydown="if(event.key==='Enter')login()">
<div style="height:10px"></div>
<button class="btn primary" style="width:100%" onclick="login()">ورود</button>
<div id="err" style="color:var(--bad);font-size:13px;margin-top:10px"></div>
</div></div>
<script>
async function login(){
  const password=document.getElementById('pw').value;
  const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password})});
  if(r.ok) location.href='/dashboard'; else document.getElementById('err').textContent='رمز اشتباه است';
}
</script></body></html>"""

DASHBOARD_HTML = """<!DOCTYPE html><html lang="fa" data-theme="dark"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>NovaPanel · داشبورد</title>
<link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet">
<style>""" + BASE_CSS + """</style></head><body>
<div class="topbar"><div class="wrap">
<div class="logo">N</div>
<div><div class="brand-name">NovaPanel</div><div class="brand-sub" id="hostLine">…</div></div>
<div class="spacer"></div>
<button class="btn ghost" onclick="toggleTheme()" id="themeBtn">🌙</button>
<button class="btn" onclick="logout()">خروج</button>
</div></div>
<div class="wrap">
<div class="tabs" id="tabs"></div>
<div id="view"></div>
</div>
<div class="modal-bg" id="modalBg"><div class="modal" id="modalBox"></div></div>
<div class="toast" id="toast"></div>
<script>
let TAB='overview', DATA=null, CONNS=[], timer=null;
const $=s=>document.querySelector(s);
function toast(m){const t=$('#toast');t.textContent=m;t.style.display='block';setTimeout(()=>t.style.display='none',2200)}
function toggleTheme(){const h=document.documentElement;h.dataset.theme=h.dataset.theme==='dark'?'light':'dark';localStorage.setItem('nv-theme',h.dataset.theme);$('#themeBtn').textContent=h.dataset.theme==='dark'?'🌙':'☀️'}
if(localStorage.getItem('nv-theme')){document.documentElement.dataset.theme=localStorage.getItem('nv-theme');$('#themeBtn').textContent=document.documentElement.dataset.theme==='dark'?'🌙':'☀️'}
async function api(p,o={}){const r=await fetch(p,{headers:{'Content-Type':'application/json'},...o});if(r.status===401){location.href='/login';throw 0}return r.json()}
function copyT(t){navigator.clipboard.writeText(t).then(()=>toast('کپی شد'))}
function qrURL(t){return '/api/qr?text='+encodeURIComponent(t)}
function showQR(t,title){$('#modalBox').innerHTML=`<h3>${title||'QR Code'}</h3><div style="text-align:center"><span class="qr"><img src="${qrURL(t)}" width="230" height="230"></span><div class="row" style="justify-content:center;margin-top:12px"><button class="btn primary" onclick='copyT(${JSON.stringify(t)})'>کپی لینک</button><button class="btn" onclick="closeModal()">بستن</button></div></div>`;$('#modalBg').classList.add('show')}
function closeModal(){$('#modalBg').classList.remove('show')}
function esc(s){return String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function daysLeft(l){if(!l.expires_at)return'بدون انقضا';const d=Math.ceil((new Date(l.expires_at)-Date.now())/864e5);return d<0?'تمام شده':d+' روز مانده'}
function statusPill(l){if(!l.active)return'<span class="pill off">غیرفعال</span>';if(l.expired)return'<span class="pill end">منقضی</span>';if(l.limit_bytes&&l.used_bytes>=l.limit_bytes)return'<span class="pill full">تمام شده</span>';return'<span class="pill ok">فعال</span>'}
function uptime(s){const h=Math.floor(s/3600),m=Math.floor(s%3600/60);return h>0?`${h} ساعت و ${m} دقیقه`:`${m} دقیقه`}

const TABS=[['overview','نمای کلی'],['links','کانفیگ‌ها'],['live','اتصالات زنده'],['logs','لاگ‌ها'],['settings','تنظیمات']];
function renderTabs(){$('#tabs').innerHTML=TABS.map(([k,n])=>`<button class="tab ${k===TAB?'on':''}" onclick="go('${k}')">${n}</button>`).join('')}
async function go(t){TAB=t;renderTabs();clearInterval(timer);await load();if(t==='live')timer=setInterval(loadLive,5000)}
async function load(){
  if(TAB==='overview'||TAB==='links'){DATA=await api('/api/overview');$('#hostLine').textContent=DATA.host}
  if(TAB==='live')return loadLive();
  if(TAB==='logs')return loadLogs();
  if(TAB==='settings')return renderSettings();
  render();
}
async function loadLive(){const d=await api('/api/connections');CONNS=d.connections;renderLive()}
async function loadLogs(){const d=await api('/api/logs');renderLogs(d)}
function render(){({overview:renderOverview,links:renderLinks})[TAB]()}
function fmtB(n){if(n>1e9)return (n/1e9).toFixed(1)+' GB';if(n>1e6)return (n/1e6).toFixed(1)+' MB';if(n>1e3)return (n/1e3).toFixed(0)+' KB';return n+' B'}

function renderOverview(){
  const t=DATA.totals;
  const hours=[...Array(24).keys()].map(h=>String(h).padStart(2,'0')+':00');
  const maxV=Math.max(1,...hours.map(h=>DATA.hourly[h]||0));
  const bars=hours.map(h=>{const v=DATA.hourly[h]||0;const pct=Math.round(v/maxV*100);
    return `<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:3px"><div title="${h} · ${fmtB(v)}" style="width:100%;max-width:20px;height:${Math.max(4,pct*1.4)}px;background:var(--accent);border-radius:4px"></div><span style="font-size:9px;color:var(--muted)">${h.slice(0,2)}</span></div>`}).join('');
  $('#view').innerHTML=`
  <div class="grid cards">
    <div class="card"><div class="stat-lbl">کل کانفیگ‌ها</div><div class="stat-num">${t.links}</div><div class="stat-lbl">${t.active_links} فعال</div></div>
    <div class="card"><div class="stat-lbl">کاربران آنلاین</div><div class="stat-num">${t.online}</div><div class="stat-lbl">آپتایم ${uptime(DATA.uptime_secs??t.uptime_secs??0)}</div></div>
    <div class="card"><div class="stat-lbl">ترافیک کل</div><div class="stat-num" style="font-size:21px">${t.total_bytes_h}</div><div class="stat-lbl">${t.total_requests} درخواست</div></div>
    <div class="card"><div class="stat-lbl">خطاها</div><div class="stat-num">${t.total_errors}</div><div class="stat-lbl">${t.xhttp_sessions} سشن XHTTP</div></div>
  </div>
  <div class="card" style="margin-top:12px"><b>ترافیک ساعتی امروز</b><div class="row" style="align-items:flex-end;margin-top:12px;flex-wrap:nowrap">${bars}</div></div>
  <div class="card" style="margin-top:12px"><b>آخرین کانفیگ‌ها</b><div style="overflow:auto"><table><tr><th>نام</th><th>وضعیت</th><th>مصرف</th><th>آنلاین</th></tr>
  ${DATA.links.slice(-8).reverse().map(l=>`<tr><td>${esc(l.label)}</td><td>${statusPill(l)}</td><td><div class="bar"><i style="width:${Math.min(100,l.pct)}%"></i></div><small>${l.used_h} / ${l.limit_h}</small></td><td>${l.ips}</td></tr>`).join('')||'<tr><td colspan=4 style="text-align:center;color:var(--muted)">هنوز کانفیگی ساخته نشده است</td></tr>'}</table></div></div>`;
}

function linkCard(l){
  const routes=l.vless_links.map((v,i)=>`<div class="route"><div class="route-head"><span class="route-tag">${i===0?'مسیر مستقیم':'مسیر ابری'}</span><span class="spacer"></span><button class="btn small" onclick='copyT(${JSON.stringify(v)})'>کپی</button><button class="btn small" onclick='showQR(${JSON.stringify(v)},"${esc(l.label)}")'>QR</button></div><div class="mono">${esc(v)}</div></div>`).join('');
  return `<div class="card" style="margin-bottom:12px">
  <div class="row"><b style="font-size:15px">${esc(l.label)}</b>${statusPill(l)}<span class="spacer"></span>
    <button class="btn small" onclick="toggleLink('${l.uuid}',${!l.active})">${l.active?'غیرفعال':'فعال'}</button>
    <button class="btn small" onclick="resetLink('${l.uuid}')">صفر کردن مصرف</button>
    <button class="btn small" onclick="editLink('${l.uuid}')">ویرایش</button>
    <button class="btn small danger" onclick="delLink('${l.uuid}')">حذف</button></div>
  <div class="meta" style="margin-top:8px"><span>پروتکل <b>${esc(l.protocol)}</b></span><span>انقضا <b>${daysLeft(l)}</b></span><span>آی‌پی <b>${l.ips}${l.ip_limit?' / '+l.ip_limit:''}</b></span></div>
  <div class="row" style="margin-top:8px"><div class="bar" style="flex:1"><i style="width:${Math.min(100,l.pct)}%"></i></div><small style="white-space:nowrap">${l.used_h} از ${l.limit_h} (${l.pct}٪)</small></div>
  ${routes}
  <div class="subbox"><div class="route-head"><span class="route-tag">لینک ساب هوشمند</span><span class="spacer"></span><button class="btn small" onclick="copyT('${l.sub_url}')">کپی</button><button class="btn small" onclick="showQR('${l.sub_url}','لینک ساب')">QR</button></div>
  <div class="mono">${esc(l.sub_url)}</div><small style="color:var(--muted)">در اپ، هر دو مسیر را می‌آورد · در مرورگر، صفحه وضعیت را نشان می‌دهد</small></div>
  </div>`;
}
function renderLinks(){
  $('#view').innerHTML=`<div class="row" style="margin-bottom:12px"><button class="btn primary" onclick="editLink()">کانفیگ جدید</button>
  <input id="q" placeholder="جستجو…" style="max-width:220px" oninput="filterCards(this.value)"><div class="spacer"></div>
  <span class="stat-lbl">هر کانفیگ دو مسیره است تا در صورت اختلال یکی، دیگری متصل شود</span></div>
  <div id="cards">${DATA.links.map(linkCard).join('')||'<div class="card">کانفیگی وجود ندارد</div>'}</div>`;
}
function filterCards(q){document.querySelectorAll('#cards .card').forEach(c=>{c.style.display=c.textContent.includes(q)?'':'none'})}
async function toggleLink(uid,active){await api(`/api/links/${uid}/toggle`,{method:'POST',body:JSON.stringify({active})});toast(active?'فعال شد':'غیرفعال شد');load()}
async function resetLink(uid){if(!confirm('مصرف این کانفیگ صفر شود؟'))return;await api(`/api/links/${uid}/reset`,{method:'POST'});toast('مصرف صفر شد');load()}
async function delLink(uid){if(!confirm('این کانفیگ حذف شود؟'))return;await api(`/api/links/${uid}`,{method:'DELETE'});toast('حذف شد');load()}

async function editLink(uid){
  let d={label:'',protocol:'vless-ws',fingerprint:'chrome',alpn:'',port:443,limit_value:0,limit_unit:'GB',speed_mbps:0,ip_limit:0,expires_days:0,cdn_host:'',cdn_protocol:'',cdn_port:0,note:''};
  let title='کانفیگ جدید';
  if(uid){const g=await api(`/api/links/${uid}`);const r=g.raw;title='ویرایش «'+esc(r.label)+'»';
    d={label:r.label,protocol:r.protocol,fingerprint:r.fingerprint,alpn:r.alpn,port:r.port,limit_value:r.limit_bytes>0?(r.limit_bytes>=1073741824?(r.limit_bytes/1073741824).toFixed(1):(r.limit_bytes/1048576).toFixed(0)):0,limit_unit:r.limit_bytes>=1073741824?'GB':'MB',speed_mbps:r.speed_limit_bytes>0?(r.speed_limit_bytes*8/1e6):0,ip_limit:r.ip_limit,expires_days:r.expires_days||0,cdn_host:r.cdn_host||'',cdn_protocol:r.cdn_protocol||'',cdn_port:r.cdn_port||0,note:r.note||''};}
  $('#modalBox').innerHTML=`<h3>${title}</h3><div class="frm">
  <label class="fl">نام<input id="f_label" value="${esc(d.label)}"></label>
  <label class="fl">پروتکل مسیر مستقیم<select id="f_protocol"><option value="vless-ws" ${d.protocol==='vless-ws'?'selected':''}>VLESS + WebSocket</option><option value="xhttp-stream-up" ${d.protocol==='xhttp-stream-up'?'selected':''}>XHTTP stream-up</option><option value="xhttp-packet-up" ${d.protocol==='xhttp-packet-up'?'selected':''}>XHTTP packet-up</option></select></label>
  <label class="fl">Fingerprint<select id="f_fp">${['chrome','firefox','safari','ios','android','edge','random'].map(f=>`<option ${d.fingerprint===f?'selected':''}>${f}</option>`).join('')}</select></label>
  <label class="fl">ALPN<input id="f_alpn" value="${esc(d.alpn)}" placeholder="خالی = پیش‌فرض"></label>
  <label class="fl">پورت<input id="f_port" type="number" value="${d.port}"></label>
  <label class="fl">سقف آی‌پی هم‌زمان (0 = نامحدود)<input id="f_ip" type="number" value="${d.ip_limit}"></label>
  <label class="fl">حجم<input id="f_lim" type="number" step="any" value="${d.limit_value}"></label>
  <label class="fl">واحد حجم<select id="f_limU"><option ${d.limit_unit==='MB'?'selected':''}>MB</option><option ${d.limit_unit==='GB'?'selected':''}>GB</option></select></label>
  <label class="fl">سرعت (Mbps، 0 = نامحدود)<input id="f_spd" type="number" step="any" value="${d.speed_mbps}"></label>
  <label class="fl">انقضا (روز، 0 = بدون انقضا)<input id="f_exp" type="number" value="${d.expires_days}"></label>
  <label class="fl full">دامنه ابری (خالی = مشابه مسیر مستقیم)<input id="f_cdn" dir="ltr" value="${esc(d.cdn_host)}" placeholder="cdn.example.com"></label>
  <label class="fl">پروتکل ابری<select id="f_cdnP"><option value="">خودکار</option>${['vless-ws','xhttp-stream-up','xhttp-packet-up'].map(p=>`<option value="${p}" ${d.cdn_protocol===p?'selected':''}>${p}</option>`).join('')}</select></label>
  <label class="fl">پورت ابری (0 = مشابه اصلی)<input id="f_cdnPort" type="number" value="${d.cdn_port}"></label>
  <label class="fl full">یادداشت<input id="f_note" value="${esc(d.note)}"></label>
  </div><div class="row" style="margin-top:14px"><button class="btn primary" onclick="saveLink('${uid||''}')">ذخیره</button><button class="btn" onclick="closeModal()">انصراف</button></div>`;
  $('#modalBg').classList.add('show');
}
async function saveLink(uid){
  const b={label:$('#f_label').value,protocol:$('#f_protocol').value,fingerprint:$('#f_fp').value,alpn:$('#f_alpn').value,port:+$('#f_port').value,ip_limit:+$('#f_ip').value,limit_value:+$('#f_lim').value,limit_unit:$('#f_limU').value,speed_mbps:+$('#f_spd').value,expires_days:+$('#f_exp').value,cdn_host:$('#f_cdn').value.trim(),cdn_protocol:$('#f_cdnP').value,cdn_port:+$('#f_cdnPort').value,note:$('#f_note').value};
  if(uid)await api(`/api/links/${uid}`,{method:'PATCH',body:JSON.stringify(b)});
  else await api('/api/links',{method:'POST',body:JSON.stringify(b)});
  closeModal();toast('ذخیره شد');load();
}

function renderLive(){
  $('#view').innerHTML=`<div class="card"><b>اتصالات زنده (${CONNS.length})</b> <small style="color:var(--muted)">· بروزرسانی خودکار هر ۵ ثانیه</small><div style="overflow:auto"><table><tr><th>آی‌پی</th><th>کانفیگ</th><th>مسیر</th><th>حجم</th></tr>
  ${CONNS.map(c=>`<tr><td class="mono">${esc(c.ip)}</td><td>${esc(c.label)}</td><td><span class="chip">${esc(c.transport)}</span></td><td>${c.bytes_h}</td></tr>`).join('')||'<tr><td colspan=4 style="text-align:center;color:var(--muted)">اتصال فعالی وجود ندارد</td></tr>'}</table></div></div>`;
}
function renderLogs(d){
  const lv=c=>({ok:'lv-ok',warn:'lv-warn',info:'lv-info',error:'lv-err'}[c]||'lv-info');
  $('#view').innerHTML=`<div class="row" style="margin-bottom:12px"><button class="btn" onclick="loadLogs()">بروزرسانی</button></div>
  <div class="grid" style="grid-template-columns:1fr 1fr">
  <div class="card"><b>فعالیت‌ها</b><div style="max-height:60vh;overflow:auto;margin-top:8px">${(d.activity||[]).map(a=>`<div class="log"><span class="${lv(a.level)}">●</span><span>${esc(a.message)}</span><time>${(a.time||'').slice(11,19)}</time></div>`).join('')||'خالی'}</div></div>
  <div class="card"><b>خطاها</b><div style="max-height:60vh;overflow:auto;margin-top:8px">${(d.errors||[]).map(e=>`<div class="log"><span class="lv-err">●</span><span class="mono">${esc(e.error)}</span><time>${(e.time||'').slice(11,19)}</time></div>`).join('')||'بدون خطا'}</div></div></div>`;
}
function renderSettings(){
  $('#view').innerHTML=`<div class="card" style="max-width:520px"><b>تغییر رمز ادمین</b><div class="frm" style="margin-top:12px;grid-template-columns:1fr">
  <label class="fl">رمز فعلی<input id="s_cur" type="password"></label>
  <label class="fl">رمز جدید<input id="s_new" type="password"></label></div>
  <div class="row" style="margin-top:12px"><button class="btn primary" onclick="changePw()">تغییر رمز</button></div></div>`;
}
async function changePw(){const r=await fetch('/api/password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({current:$('#s_cur').value,new:$('#s_new').value})});toast(r.ok?'رمز تغییر کرد':'خطا: '+(await r.json()).detail)}
async function logout(){await fetch('/api/logout',{method:'POST'});location.href='/login'}
$('#modalBg').addEventListener('click',e=>{if(e.target.id==='modalBg')closeModal()});
go('overview');
</script></body></html>"""


def config_public_page(uid: str, link: dict, vlinks: list[str], sub_url: str) -> str:
    """صفحه وضعیت تکی هر کانفیگ: در مرورگر باز می‌شود، شامل مصرف، روز، مسیرها و QR."""
    esc = html.escape
    limit = int(link.get("limit_bytes", 0) or 0)
    used = int(link.get("used_bytes", 0) or 0)
    pct = round(used / limit * 100, 1) if limit else 0
    exp = link.get("expires_at")
    try:
        from datetime import datetime
        if not exp:
            days_txt = "بدون انقضا"
        else:
            d = (datetime.fromisoformat(exp) - datetime.now().astimezone()).days
            days_txt = "تمام شده" if d < 0 else f"{d} روز مانده"
    except Exception:
        days_txt = "—"
    spd = int(link.get("speed_limit_bytes", 0) or 0)
    spd_txt = "نامحدود" if not spd else f"{spd * 8 / 1e6:.0f} مگابیت بر ثانیه"
    active = bool(link.get("active", True))
    status = "فعال" if active else "غیرفعال"
    routes = "".join(
        f"""<div class="route"><div class="route-head"><span class="route-tag">{"مسیر مستقیم" if i == 0 else "مسیر ابری"}</span>
<span class="spacer"></span><button class="btn small" onclick="copyT({v!r})">کپی</button></div>
<div class="mono">{esc(v)}</div>
<div class="row" style="justify-content:center;margin-top:8px"><span class="qr"><img src="/qr-pub?text={esc(v)}" width="150" height="150" loading="lazy" alt="QR"></span></div></div>"""
        for i, v in enumerate(vlinks)
    )
    return f"""<!DOCTYPE html><html lang="fa" data-theme="dark"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(link.get('label', 'سرویس'))} · وضعیت سرویس</title>
<link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet">
<style>{BASE_CSS}</style></head><body><div class="wrap" style="max-width:680px">
<div class="hero"><div class="logo" style="margin:0 auto 10px;width:52px;height:52px;font-size:24px">N</div>
<h1>{esc(link.get('label', 'سرویس'))}</h1><p>وضعیت سرویس · {'متصل' if active else 'غیرفعال'}</p>
<p style="font-size:12.5px">این لینک را در v2rayNG ،NekoBox یا Streisand وارد کنید تا هر دو مسیر اضافه شود</p>
<div class="subbox" style="text-align:right"><div class="route-head"><span class="route-tag">لینک ساب</span>
<span class="spacer"></span><button class="btn small" onclick="copyT('{sub_url}')">کپی لینک ساب</button></div>
<div class="mono">{esc(sub_url)}</div></div>
<div class="row" style="justify-content:center;margin-top:10px"><span class="qr"><img src="/qr-pub?text={esc(sub_url)}" width="120" height="120" alt="QR"></span></div></div>
<div class="card"><div class="section-t" style="margin-top:0">مصرف و اعتبار</div>
<div class="kv"><span>حجم مصرف‌شده</span><b>{esc(_fmt(used))} از {esc(_fmt(limit) if limit else "نامحدود")}</b></div>
<div class="bar" style="margin:8px 0"><i style="width:{min(100, pct)}%"></i></div>
<div class="kv"><span>وضعیت</span><b>{status}</b></div>
<div class="kv"><span>اعتبار باقی‌مانده</span><b>{esc(days_txt)}</b></div>
<div class="kv"><span>سقف سرعت</span><b>{esc(spd_txt)}</b></div>
<div class="kv"><span>پروتکل</span><b>{esc(link.get('protocol', ''))}</b></div></div>
<div class="section-t">مسیرهای اتصال</div>
{routes}
<p style="text-align:center;color:var(--muted);font-size:11.5px;margin-top:16px">NovaPanel · در صورت اختلال یک مسیر، مسیر دیگر را امتحان کنید</p>
</div><div class="toast" id="toast"></div>
<script>function copyT(t){{navigator.clipboard.writeText(t).then(()=>{{const x=document.getElementById('toast');x.textContent='کپی شد';x.style.display='block';setTimeout(()=>x.style.display='none',2000)}})}}</script>
</body></html>"""


def public_sub_page(sub: dict, items: list, host: str, authed: bool) -> str:
    """نگه‌داشته شده برای سازگاری (مسیر قدیمی /p)."""
    esc = html.escape
    if sub.get("password") and not authed:
        return f"""<!DOCTYPE html><html lang="fa" data-theme="dark"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(sub.get('name',''))}</title>
<style>{BASE_CSS}</style></head><body><div class="wrap" style="max-width:420px;padding-top:10vh">
<div class="card" style="text-align:center"><h2>{esc(sub.get('name',''))}</h2>
<p style="color:var(--muted)">این صفحه با رمز محافظت می‌شود</p>
<form method="get"><input name="password" type="password" placeholder="رمز صفحه"><div style="height:10px"></div>
<button class="btn primary" style="width:100%">باز کردن</button></form></div></div></body></html>"""
    cards = []
    for uid, link, vlinks in items:
        sub_url = f"https://{host}/sub/{uid}"
        cards.append(config_public_page(uid, link, vlinks, sub_url))
    return cards[0] if cards else f"""<!DOCTYPE html><html lang="fa"><head><meta charset="utf-8"><style>{BASE_CSS}</style></head>
<body><div class="wrap"><div class="card">کانفیگی وجود ندارد</div></div></body></html>"""


def _fmt(n) -> str:
    try:
        n = float(n or 0)
    except (TypeError, ValueError):
        return "0 B"
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return f"{n:.1f} {u}" if u != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TB"
