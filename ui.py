# ui.py — صفحات وب: لاگین، داشبورد SPA (تم روشن/تاریک)، صفحه ساب عمومی
from __future__ import annotations

import html

BASE_CSS = """
:root{
  --bg:#f1f5fb; --bg2:#ffffff; --card:#ffffff; --text:#0f1e33; --muted:#5b6b82;
  --line:#e2e9f4; --brand:#5b6cff; --brand2:#8b5cf6; --ok:#16a34a; --warn:#d97706;
  --bad:#dc2626; --chip:#eef2ff; --shadow:0 10px 30px rgba(30,50,100,.08);
  --grad:linear-gradient(135deg,#5b6cff,#8b5cf6 60%,#d946ef);
}
[data-theme=dark]{
  --bg:#0b1220; --bg2:#0f172a; --card:#111c33; --text:#e8eefb; --muted:#93a3bd;
  --line:#1e2c47; --brand:#7c8aff; --brand2:#a78bfa; --chip:#182449;
  --shadow:0 10px 30px rgba(0,0,0,.45);
}
*{box-sizing:border-box}
body{margin:0;font-family:Vazirmatn,Tahoma,IRANSans,"Segoe UI",sans-serif;background:var(--bg);color:var(--text);direction:rtl}
a{color:var(--brand)}
.wrap{max-width:1180px;margin:0 auto;padding:20px}
.topbar{position:sticky;top:0;z-index:50;background:color-mix(in srgb,var(--bg2) 88%,transparent);backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}
.topbar .wrap{display:flex;align-items:center;gap:12px;padding-top:12px;padding-bottom:12px}
.logo{width:40px;height:40px;border-radius:14px;background:var(--grad);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:900;font-size:20px;box-shadow:var(--shadow)}
.brand-name{font-weight:800;font-size:18px}
.brand-sub{font-size:12px;color:var(--muted)}
.spacer{flex:1}
.btn{border:1px solid var(--line);background:var(--card);color:var(--text);border-radius:12px;padding:9px 16px;cursor:pointer;font-family:inherit;font-size:14px;transition:.15s}
.btn:hover{transform:translateY(-1px);box-shadow:var(--shadow)}
.btn.primary{background:var(--grad);color:#fff;border:none;font-weight:700}
.btn.danger{background:#fee2e2;color:#b91c1c;border-color:#fecaca}
[data-theme=dark] .btn.danger{background:#3b1420;color:#fca5a5;border-color:#5b2230}
.btn.small{padding:5px 10px;font-size:12px;border-radius:9px}
.btn.ghost{background:transparent}
.grid{display:grid;gap:14px}
.cards{grid-template-columns:repeat(auto-fit,minmax(170px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:16px;box-shadow:var(--shadow)}
.stat-num{font-size:26px;font-weight:800;margin:4px 0}
.stat-lbl{font-size:12px;color:var(--muted)}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}
.tab{border:1px solid var(--line);background:var(--card);color:var(--muted);border-radius:999px;padding:8px 18px;cursor:pointer;font-family:inherit;font-size:14px}
.tab.on{background:var(--grad);color:#fff;border:none;font-weight:700}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:10px 8px;border-bottom:1px solid var(--line);text-align:right;vertical-align:middle}
th{color:var(--muted);font-weight:600;font-size:12px}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-left:6px}
.dot.ok{background:var(--ok);box-shadow:0 0 8px var(--ok)}
.dot.bad{background:var(--bad)} .dot.warn{background:var(--warn)}
.bar{height:8px;background:var(--line);border-radius:99px;overflow:hidden;min-width:90px}
.bar>i{display:block;height:100%;background:var(--grad);border-radius:99px}
.mono{direction:ltr;font-family:Consolas,monospace;font-size:11px;word-break:break-all;color:var(--muted)}
.chip{display:inline-block;background:var(--chip);color:var(--brand);border-radius:8px;padding:2px 10px;font-size:12px;margin:1px}
.modal-bg{position:fixed;inset:0;background:rgba(5,10,25,.55);display:none;align-items:center;justify-content:center;z-index:99;padding:16px}
.modal-bg.show{display:flex}
.modal{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:22px;width:min(620px,100%);max-height:90vh;overflow:auto}
.modal h3{margin:0 0 14px}
.frm{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.frm .full{grid-column:1/-1}
label.fl{display:flex;flex-direction:column;gap:5px;font-size:12px;color:var(--muted)}
input,select,textarea{background:var(--bg);border:1px solid var(--line);color:var(--text);border-radius:10px;padding:9px 11px;font-family:inherit;font-size:14px;width:100%}
input:focus,select:focus{outline:2px solid var(--brand);border-color:transparent}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.toast{position:fixed;bottom:22px;right:50%;transform:translateX(50%);background:#0f172a;color:#fff;padding:10px 22px;border-radius:12px;font-size:14px;display:none;z-index:200;box-shadow:var(--shadow)}
[data-theme=dark] .toast{background:#e8eefb;color:#0f172a}
.log{font-size:12.5px;padding:8px 10px;border-bottom:1px solid var(--line);display:flex;gap:8px;align-items:baseline}
.log time{color:var(--muted);font-size:11px;white-space:nowrap}
.lv-ok{color:var(--ok)} .lv-warn{color:var(--warn)} .lv-info{color:var(--brand)} .lv-err{color:var(--bad)}
.linkbox{background:var(--bg);border:1px dashed var(--line);border-radius:10px;padding:8px;margin:4px 0}
.hero{background:var(--grad);border-radius:24px;color:#fff;padding:34px 26px;text-align:center;box-shadow:var(--shadow);margin-bottom:18px}
.hero h1{margin:0 0 6px;font-size:26px}
.hero p{margin:4px 0;opacity:.92}
.qr{background:#fff;border-radius:14px;padding:8px;display:inline-block}
@media(max-width:700px){.frm{grid-template-columns:1fr}table{font-size:12px}}
"""

LOGIN_HTML = """<!DOCTYPE html><html lang="fa" data-theme="dark"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>NovaPanel · ورود</title>
<link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet">
<style>""" + BASE_CSS + """</style></head><body>
<div class="wrap" style="max-width:400px;padding-top:9vh">
<div class="card" style="text-align:center;padding:34px 26px">
<div class="logo" style="margin:0 auto 12px;width:56px;height:56px;font-size:28px">N</div>
<div class="brand-name" style="font-size:22px">NovaPanel ⚡</div>
<div class="brand-sub" style="margin-bottom:18px">ورود به پنل مدیریت</div>
<input id="pw" type="password" placeholder="رمز ادمین" onkeydown="if(event.key==='Enter')login()">
<div style="height:10px"></div>
<button class="btn primary" style="width:100%" onclick="login()">ورود 🚀</button>
<div id="err" style="color:var(--bad);font-size:13px;margin-top:10px"></div>
</div></div>
<script>
async function login(){
  const password=document.getElementById('pw').value;
  const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password})});
  if(r.ok) location.href='/dashboard'; else document.getElementById('err').textContent='❌ رمز اشتباه است';
}
</script></body></html>"""

DASHBOARD_HTML = """<!DOCTYPE html><html lang="fa" data-theme="dark"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>NovaPanel · داشبورد</title>
<link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet">
<style>""" + BASE_CSS + """</style></head><body>
<div class="topbar"><div class="wrap">
<div class="logo">N</div>
<div><div class="brand-name">NovaPanel ⚡</div><div class="brand-sub" id="hostLine">…</div></div>
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
let TAB='overview', DATA=null, GROUPS=[], CONNS=[], timer=null;
const $=s=>document.querySelector(s);
function toast(m){const t=$('#toast');t.textContent=m;t.style.display='block';setTimeout(()=>t.style.display='none',2200)}
function toggleTheme(){const h=document.documentElement;h.dataset.theme=h.dataset.theme==='dark'?'light':'dark';localStorage.setItem('nv-theme',h.dataset.theme);$('#themeBtn').textContent=h.dataset.theme==='dark'?'🌙':'☀️'}
if(localStorage.getItem('nv-theme')){document.documentElement.dataset.theme=localStorage.getItem('nv-theme');$('#themeBtn').textContent=document.documentElement.dataset.theme==='dark'?'🌙':'☀️'}
async function api(p,o={}){const r=await fetch(p,{headers:{'Content-Type':'application/json'},...o});if(r.status===401){location.href='/login';throw 0}return r.json()}
function copyT(t){navigator.clipboard.writeText(t).then(()=>toast('✅ کپی شد'))}
function qrURL(t){return '/api/qr?text='+encodeURIComponent(t)}
function showQR(t,title){$('#modalBox').innerHTML=`<h3>${title||'QR Code 📷'}</h3><div style="text-align:center"><span class="qr"><img src="${qrURL(t)}" width="230" height="230"></span><div class="mono" style="margin-top:10px;max-width:100%">${esc(t.slice(0,120))}…</div><div class="row" style="justify-content:center;margin-top:12px"><button class="btn primary" onclick="copyT(${JSON.stringify(t).replace(/"/g,'&quot;')})">کپی لینک 📋</button><button class="btn" onclick="closeModal()">بستن</button></div></div>`;$('#modalBg').classList.add('show')}
function closeModal(){$('#modalBg').classList.remove('show')}
function esc(s){return String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function pctColor(p){return p>90?'var(--bad)':p>70?'var(--warn)':'var(--ok)'}
function daysLeft(l){if(!l.expires_at)return'∞';const d=Math.ceil((new Date(l.expires_at)-Date.now())/864e5);return d<0?'⛔ تمام شده':d+' روز'}
function statusDot(l){if(!l.active)return'<span class="dot bad"></span>غیرفعال';if(l.expired)return'<span class="dot bad"></span>منقضی';if(l.limit_bytes&&l.used_bytes>=l.limit_bytes)return'<span class="dot warn"></span>تمام‌حجم';return'<span class="dot ok"></span>فعال'}

const TABS=[['overview','📊 نمای کلی'],['links','🔗 کانفیگ‌ها'],['groups','🗂 گروه‌های ساب'],['live','🟢 اتصالات زنده'],['logs','📝 لاگ‌ها'],['settings','⚙️ تنظیمات']];
function renderTabs(){$('#tabs').innerHTML=TABS.map(([k,n])=>`<button class="tab ${k===TAB?'on':''}" onclick="go('${k}')">${n}</button>`).join('')}
async function go(t){TAB=t;renderTabs();clearInterval(timer);await load();if(t==='live')timer=setInterval(loadLive,5000)}
async function load(){
  if(TAB==='overview'||TAB==='links'){DATA=await api('/api/overview');$('#hostLine').textContent='🌐 '+DATA.host}
  if(TAB==='groups'){GROUPS=(await api('/api/groups')).groups;DATA=await api('/api/overview')}
  if(TAB==='live')return loadLive();
  if(TAB==='logs')return loadLogs();
  if(TAB==='settings')return renderSettings();
  render();
}
async function loadLive(){const d=await api('/api/connections');CONNS=d.connections;renderLive()}
async function loadLogs(){const d=await api('/api/logs');renderLogs(d)}

function render(){({overview:renderOverview,links:renderLinks,groups:renderGroups})[TAB]()}

function renderOverview(){
  const t=DATA.totals;
  const hours=[...Array(24).keys()].map(h=>String(h).padStart(2,'0')+':00');
  const maxV=Math.max(1,...hours.map(h=>DATA.hourly[h]||0));
  const bars=hours.map(h=>{const v=DATA.hourly[h]||0;const pct=Math.round(v/maxV*100);
    return `<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:3px"><div title="${h} · ${fmtB(v)}" style="width:100%;max-width:22px;height:${Math.max(4,pct*1.4)}px;background:var(--grad);border-radius:5px"></div><span style="font-size:9px;color:var(--muted)">${h.slice(0,2)}</span></div>`}).join('');
  $('#view').innerHTML=`
  <div class="grid cards">
    <div class="card"><div class="stat-lbl">🔗 کل کانفیگ‌ها</div><div class="stat-num">${t.links}</div><div class="stat-lbl">${t.active_links} فعال</div></div>
    <div class="card"><div class="stat-lbl">🟢 آنلاین</div><div class="stat-num">${t.online}</div><div class="stat-lbl">${t.xhttp_sessions} سشن XHTTP</div></div>
    <div class="card"><div class="stat-lbl">📦 ترافیک کل</div><div class="stat-num" style="font-size:22px">${t.total_bytes_h}</div><div class="stat-lbl">${t.total_requests} درخواست</div></div>
    <div class="card"><div class="stat-lbl">🗂 گروه‌های ساب</div><div class="stat-num">${t.groups}</div><div class="stat-lbl">${t.total_errors} خطا</div></div>
  </div>
  <div class="card" style="margin-top:14px"><b>📈 ترافیک ساعتی امروز</b><div class="row" style="align-items:flex-end;margin-top:12px;flex-wrap:nowrap">${bars}</div></div>
  <div class="card" style="margin-top:14px"><b>🔗 آخرین کانفیگ‌ها</b><div style="overflow:auto"><table><tr><th>نام</th><th>وضعیت</th><th>مصرف</th><th>آنلاین</th></tr>
  ${DATA.links.slice(-8).reverse().map(l=>`<tr><td>${esc(l.label)}</td><td>${statusDot(l)}</td><td><div class="bar"><i style="width:${Math.min(100,l.pct)}%"></i></div><small>${l.used_h} / ${l.limit_h}</small></td><td>${l.ips} 👤</td></tr>`).join('')||'<tr><td colspan=4 style="text-align:center;color:var(--muted)">هنوز کانفیگی نساختی — از تب کانفیگ‌ها بساز ✨</td></tr>'}</table></div></div>`;
}
function fmtB(n){if(n>1e9)return (n/1e9).toFixed(1)+' GB';if(n>1e6)return (n/1e6).toFixed(1)+' MB';if(n>1e3)return (n/1e3).toFixed(0)+' KB';return n+' B'}

function linkRow(l){
  const links=l.vless_links.map((v,i)=>`<div class="linkbox"><span class="chip">${i===0?'⚡ مستقیم':'☁️ ابری'}</span>
    <div class="mono">${esc(v.slice(0,90))}…</div>
    <div class="row" style="margin-top:5px"><button class="btn small" onclick='copyT(${JSON.stringify(v)})'>کپی 📋</button><button class="btn small" onclick='showQR(${JSON.stringify(v)},"${esc(l.label)}")'>QR 📷</button></div></div>`).join('');
  return `<tr><td><b>${esc(l.label)}</b><br><small style="color:var(--muted)">${esc(l.protocol)} · ${daysLeft(l)} · ${l.ips}${l.ip_limit?'/'+l.ip_limit:''} 👤</small></td>
  <td>${statusDot(l)}<br><div class="bar" style="margin-top:5px"><i style="width:${Math.min(100,l.pct)}%;background:${pctColor(l.pct)}"></i></div><small>${l.used_h} / ${l.limit_h}</small></td>
  <td style="min-width:230px">${links}<div class="row" style="margin-top:6px">
    <button class="btn small" onclick="toggleLink('${l.uuid}',${!l.active})">${l.active?'⏸ غیرفعال':'▶️ فعال'}</button>
    <button class="btn small" onclick="resetLink('${l.uuid}')">🔄 صفر</button>
    <button class="btn small" onclick="editLink('${l.uuid}')">✏️</button>
    <button class="btn small danger" onclick="delLink('${l.uuid}')">🗑</button></div></td></tr>`;
}
function renderLinks(){
  $('#view').innerHTML=`<div class="row" style="margin-bottom:12px"><button class="btn primary" onclick="editLink()">➕ کانفیگ جدید</button>
  <input id="q" placeholder="🔍 جستجو…" style="max-width:220px" oninput="filterLinks(this.value)"><div class="spacer"></div>
  <span class="stat-lbl">هر کانفیگ = ۲ لینک (⚡ مستقیم + ☁️ ابری) برای فالبک خودکار</span></div>
  <div class="card"><div style="overflow:auto"><table id="linkTable"><tr><th>نام</th><th>وضعیت / مصرف</th><th>لینک‌ها و عملیات</th></tr>
  ${DATA.links.map(linkRow).join('')||'<tr><td colspan=3 style="text-align:center">خالی</td></tr>'}</table></div></div>`;
}
function filterLinks(q){document.querySelectorAll('#linkTable tr').forEach((tr,i)=>{if(i===0)return;tr.style.display=tr.textContent.includes(q)?'':'none'})}
async function toggleLink(uid,active){await api(`/api/links/${uid}/toggle`,{method:'POST',body:JSON.stringify({active})});toast(active?'✅ فعال شد':'⏸ غیرفعال شد');load()}
async function resetLink(uid){if(!confirm('مصرف صفر شود؟'))return;await api(`/api/links/${uid}/reset`,{method:'POST'});toast('🔄 مصرف صفر شد');load()}
async function delLink(uid){if(!confirm('حذف شود؟'))return;await api(`/api/links/${uid}`,{method:'DELETE'});toast('🗑 حذف شد');load()}

async function editLink(uid){
  let d={label:'',protocol:'vless-ws',fingerprint:'chrome',alpn:'',port:443,limit_value:0,limit_unit:'GB',speed_mbps:0,ip_limit:0,expires_days:0,cdn_host:'',cdn_protocol:'',cdn_port:0,note:'',sub_id:null};
  let title='➕ کانفیگ جدید';
  if(uid){const g=await api(`/api/links/${uid}`);const r=g.raw;title='✏️ ویرایش «'+esc(r.label)+'»';
    d={label:r.label,protocol:r.protocol,fingerprint:r.fingerprint,alpn:r.alpn,port:r.port,limit_value:r.limit_bytes>0?(r.limit_bytes>=1073741824?(r.limit_bytes/1073741824).toFixed(1):(r.limit_bytes/1048576).toFixed(0)):0,limit_unit:r.limit_bytes>=1073741824?'GB':'MB',speed_mbps:r.speed_limit_bytes>0?(r.speed_limit_bytes*8/1e6):0,ip_limit:r.ip_limit,expires_days:r.expires_days||0,cdn_host:r.cdn_host||'',cdn_protocol:r.cdn_protocol||'',cdn_port:r.cdn_port||0,note:r.note||'',sub_id:r.sub_id};}
  const groups=uid?[]:(await api('/api/groups')).groups;
  $('#modalBox').innerHTML=`<h3>${title}</h3><div class="frm">
  <label class="fl">نام<textarea style="display:none"></textarea><input id="f_label" value="${esc(d.label)}"></label>
  <label class="fl">پروتکل مسیر مستقیم<select id="f_protocol"><option value="vless-ws" ${d.protocol==='vless-ws'?'selected':''}>VLESS + WebSocket ⚡</option><option value="xhttp-stream-up" ${d.protocol==='xhttp-stream-up'?'selected':''}>XHTTP stream-up 🚀</option><option value="xhttp-packet-up" ${d.protocol==='xhttp-packet-up'?'selected':''}>XHTTP packet-up 📦</option></select></label>
  <label class="fl">Fingerprint<select id="f_fp">${['chrome','firefox','safari','ios','android','edge','random'].map(f=>`<option ${d.fingerprint===f?'selected':''}>${f}</option>`).join('')}</select></label>
  <label class="fl">ALPN<input id="f_alpn" value="${esc(d.alpn)}" placeholder="http/1.1 (خالی=پیش‌فرض)"></label>
  <label class="fl">پورت<input id="f_port" type="number" value="${d.port}"></label>
  <label class="fl">محدودیت آی‌پی (0=نامحدود)<input id="f_ip" type="number" value="${d.ip_limit}"></label>
  <label class="fl">حجم<input id="f_lim" type="number" step="any" value="${d.limit_value}"></label>
  <label class="fl">واحد حجم<select id="f_limU"><option ${d.limit_unit==='MB'?'selected':''}>MB</option><option ${d.limit_unit==='GB'?'selected':''}>GB</option></select></label>
  <label class="fl">سرعت (Mbps، 0=نامحدود)<input id="f_spd" type="number" step="any" value="${d.speed_mbps}"></label>
  <label class="fl">انقضا (روز، 0=بدون انقضا)<input id="f_exp" type="number" value="${d.expires_days}"></label>
  <label class="fl full">دامنه ابری ☁️ (خالی = مثل مسیر مستقیم)<input id="f_cdn" dir="ltr" value="${esc(d.cdn_host)}" placeholder="cdn.example.com"></label>
  <label class="fl">پروتکل ابری<select id="f_cdnP"><option value="">خودکار (جایگزین)</option>${['vless-ws','xhttp-stream-up','xhttp-packet-up'].map(p=>`<option value="${p}" ${d.cdn_protocol===p?'selected':''}>${p}</option>`).join('')}</select></label>
  <label class="fl">پورت ابری (0=مثل اصلی)<input id="f_cdnPort" type="number" value="${d.cdn_port}"></label>
  <label class="fl full">یادداشت<input id="f_note" value="${esc(d.note)}"></label>
  </div><div class="row" style="margin-top:14px"><button class="btn primary" onclick="saveLink('${uid||''}')">💾 ذخیره</button><button class="btn" onclick="closeModal()">انصراف</button></div>`;
  $('#modalBg').classList.add('show');
}
async function saveLink(uid){
  const b={label:$('#f_label').value,protocol:$('#f_protocol').value,fingerprint:$('#f_fp').value,alpn:$('#f_alpn').value,port:+$('#f_port').value,ip_limit:+$('#f_ip').value,limit_value:+$('#f_lim').value,limit_unit:$('#f_limU').value,speed_mbps:+$('#f_spd').value,expires_days:+$('#f_exp').value,cdn_host:$('#f_cdn').value.trim(),cdn_protocol:$('#f_cdnP').value,cdn_port:+$('#f_cdnPort').value,note:$('#f_note').value};
  if(uid)await api(`/api/links/${uid}`,{method:'PATCH',body:JSON.stringify(b)});
  else await api('/api/links',{method:'POST',body:JSON.stringify(b)});
  closeModal();toast('✅ ذخیره شد');load();
}

function renderGroups(){
  $('#view').innerHTML=`<div class="row" style="margin-bottom:12px"><button class="btn primary" onclick="newGroup()">➕ گروه جدید</button></div>
  <div class="grid" style="grid-template-columns:repeat(auto-fill,minmax(300px,1fr))">
  ${GROUPS.map(g=>`<div class="card"><b>🗂 ${esc(g.name)}</b> ${g.protected?'🔒':''}<br><small style="color:var(--muted)">${g.count} کانفیگ</small>
    <div class="linkbox"><small>🌐 صفحه عمومی:</small><div class="mono">${esc(g.public_url)}</div><div class="row" style="margin-top:5px"><button class="btn small" onclick="copyT('${g.public_url}')">کپی 📋</button><button class="btn small" onclick="showQR('${g.public_url}','${esc(g.name)}')">QR 📷</button></div></div>
    <div class="linkbox"><small>📡 لینک ساب (اپ):</small><div class="mono">${esc(g.sub_url)}</div><div class="row" style="margin-top:5px"><button class="btn small" onclick="copyT('${g.sub_url}')">کپی 📋</button><button class="btn small" onclick="showQR('${g.sub_url}','ساب ${esc(g.name)}')">QR 📷</button></div></div>
    <div class="row" style="margin-top:8px"><button class="btn small" onclick="assignGroup('${g.sub_id}')">➕ عضویت کانفیگ</button><button class="btn small danger" onclick="delGroup('${g.sub_id}')">🗑</button></div></div>`).join('')||'<div class="card">هنوز گروهی نیست</div>'}</div>`;
}
async function newGroup(){const name=prompt('نام گروه:','گروه جدید');if(!name)return;const password=prompt('رمز صفحه (خالی=بدون رمز):','')||'';await api('/api/groups',{method:'POST',body:JSON.stringify({name,password})});toast('✅ گروه ساخته شد');load()}
async function delGroup(sid){if(!confirm('گروه حذف شود؟ (کانفیگ‌ها پاک نمی‌شوند)'))return;await api(`/api/groups/${sid}`,{method:'DELETE'});toast('🗑 حذف شد');load()}
async function assignGroup(sid){
  const links=DATA?DATA.links:(await api('/api/overview')).links;
  const cur=new Set((await api('/api/groups')).groups.find(g=>g.sub_id===sid)?[]:[]);
  $('#modalBox').innerHTML=`<h3>➕ عضویت کانفیگ در گروه</h3>${links.map(l=>`<label class="row" style="padding:6px;border-bottom:1px solid var(--line)"><input type="checkbox" value="${l.uuid}" style="width:auto"> ${esc(l.label)}</label>`).join('')}<div class="row" style="margin-top:12px"><button class="btn primary" onclick="doAssign('${sid}')">💾 ذخیره</button><button class="btn" onclick="closeModal()">انصراف</button></div>`;
  $('#modalBg').classList.add('show');
}
async function doAssign(sid){const ids=[...$('#modalBox').querySelectorAll('input:checked')].map(i=>i.value);await api(`/api/groups/${sid}/assign`,{method:'POST',body:JSON.stringify({link_ids:ids})});closeModal();toast('✅ انجام شد');load()}

function renderLive(){
  $('#view').innerHTML=`<div class="card"><b>🟢 اتصالات زنده (${CONNS.length})</b> <small style="color:var(--muted)">· بروزرسانی خودکار هر ۵ ثانیه</small><div style="overflow:auto"><table><tr><th>آی‌پی</th><th>کانفیگ</th><th>مسیر</th><th>حجم</th></tr>
  ${CONNS.map(c=>`<tr><td class="mono">${esc(c.ip)}</td><td>${esc(c.label)}</td><td><span class="chip">${esc(c.transport)}</span></td><td>${c.bytes_h}</td></tr>`).join('')||'<tr><td colspan=4 style="text-align:center;color:var(--muted)">کسی آنلاین نیست 😴</td></tr>'}</table></div></div>`;
}
function renderLogs(d){
  const lv=c=>({ok:'lv-ok',warn:'lv-warn',info:'lv-info',error:'lv-err'}[c]||'lv-info');
  $('#view').innerHTML=`<div class="row" style="margin-bottom:12px"><button class="btn" onclick="loadLogs()">🔄 بروزرسانی</button></div>
  <div class="grid" style="grid-template-columns:1fr 1fr">
  <div class="card"><b>📝 فعالیت‌ها</b><div style="max-height:60vh;overflow:auto;margin-top:8px">${(d.activity||[]).map(a=>`<div class="log"><span class="${lv(a.level)}">●</span><span>${esc(a.message)}</span><time>${(a.time||'').slice(11,19)}</time></div>`).join('')||'خالی'}</div></div>
  <div class="card"><b>⚠️ خطاها</b><div style="max-height:60vh;overflow:auto;margin-top:8px">${(d.errors||[]).map(e=>`<div class="log"><span class="lv-err">●</span><span class="mono">${esc(e.error)}</span><time>${(e.time||'').slice(11,19)}</time></div>`).join('')||'بدون خطا ✅'}</div></div></div>`;
}
function renderSettings(){
  $('#view').innerHTML=`<div class="card" style="max-width:520px"><b>🔑 تغییر رمز ادمین</b><div class="frm" style="margin-top:12px;grid-template-columns:1fr">
  <label class="fl">رمز فعلی<input id="s_cur" type="password"></label>
  <label class="fl">رمز جدید<input id="s_new" type="password"></label></div>
  <div class="row" style="margin-top:12px"><button class="btn primary" onclick="changePw()">💾 تغییر رمز</button></div></div>`;
}
async function changePw(){const r=await fetch('/api/password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({current:$('#s_cur').value,new:$('#s_new').value})});toast(r.ok?'✅ رمز عوض شد':'❌ خطا: '+(await r.json()).detail)}
async function logout(){await fetch('/api/logout',{method:'POST'});location.href='/login'}
$('#modalBg').addEventListener('click',e=>{if(e.target.id==='modalBg')closeModal()});
go('overview');
</script></body></html>"""


def public_sub_page(sub: dict, items: list, host: str, authed: bool) -> str:
    """صفحه عمومی گروه ساب: اگر مرورگر باشد نمایش شیک، وگرنه اپ‌ها متن ساب می‌گیرند."""
    esc = html.escape
    if sub.get("password") and not authed:
        return f"""<!DOCTYPE html><html lang="fa" data-theme="dark"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>🔒 {esc(sub.get('name',''))}</title>
<style>{BASE_CSS}</style></head><body><div class="wrap" style="max-width:420px;padding-top:10vh">
<div class="card" style="text-align:center"><div style="font-size:44px">🔒</div><h2>{esc(sub.get('name',''))}</h2>
<p style="color:var(--muted)">این صفحه با رمز محافظت می‌شود</p>
<form method="get"><input name="password" type="password" placeholder="رمز صفحه"><div style="height:10px"></div>
<button class="btn primary" style="width:100%">باز کردن 🔓</button></form></div></div></body></html>"""

    cards = []
    for uid, link, vlinks in items:
        limit = int(link.get("limit_bytes", 0) or 0)
        used = int(link.get("used_bytes", 0) or 0)
        pct = round(used / limit * 100, 1) if limit else 0
        exp = link.get("expires_at")
        try:
            from datetime import datetime
            days = "∞" if not exp else max(0, (datetime.fromisoformat(exp) - datetime.now().astimezone()).days)
            days = f"{days} روز" if days != "∞" else "بدون انقضا ∞"
        except Exception:
            days = "—"
        btns = "".join(
            f'<button class="btn small" onclick="copyT({v!r})">کپی {"⚡ مستقیم" if i == 0 else "☁️ ابری"} 📋</button>'
            for i, v in enumerate(vlinks)
        )
        qr = f"/api/qr?text={vlinks[0]}" if vlinks else ""
        cards.append(f"""<div class="card"><b>🔗 {esc(link.get('label',''))}</b>
<div class="row" style="margin:8px 0"><span class="chip">📦 {esc(_fmt(used))} / {esc(_fmt(limit) if limit else 'نامحدود')}</span>
<span class="chip">⏳ {esc(str(days))}</span><span class="chip">{'✅ فعال' if link.get('active') else '⏸ غیرفعال'}</span></div>
<div class="bar"><i style="width:{min(100, pct)}%"></i></div>
<div class="row" style="margin-top:10px">{btns}<span class="qr"><img src="{qr}" width="90" height="90" loading="lazy"></span></div></div>""")

    sub_url = f"https://{host}/sub-group/{sub.get('uuid_key')}"
    return f"""<!DOCTYPE html><html lang="fa" data-theme="dark"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>⚡ {esc(sub.get('name','Nova'))}</title>
<style>{BASE_CSS}</style></head><body><div class="wrap" style="max-width:760px">
<div class="hero"><div style="font-size:44px">⚡</div><h1>{esc(sub.get('name','Nova'))}</h1>
<p>{esc(sub.get('desc','سرویس پرسرعت نوا · اتصال امن و پایدار 🚀'))}</p>
<p style="font-size:13px">📡 لینک ساب رو توی v2rayNG / NekoBox / Streisand وارد کن — خودش بهترین مسیر رو انتخاب می‌کنه ✨</p>
<div class="row" style="justify-content:center;margin-top:14px">
<button class="btn" style="background:#fff;color:#5b6cff;border:none;font-weight:800" onclick="copyT('{sub_url}')">📋 کپی لینک ساب</button>
<span class="qr"><img src="/api/qr?text={sub_url}" width="100" height="100"></span></div></div>
<div class="grid">{"".join(cards) or '<div class="card">کانفیگی نیست 😴</div>'}</div>
<p style="text-align:center;color:var(--muted);font-size:12px;margin-top:18px">⚡ NovaPanel · هر کانفیگ ۲ مسیره (مستقیم + ابری) برای اتصال بدون قطعی</p>
</div><div class="toast" id="toast"></div>
<script>function copyT(t){{navigator.clipboard.writeText(t).then(()=>{{const x=document.getElementById('toast');x.textContent='✅ کپی شد';x.style.display='block';setTimeout(()=>x.style.display='none',2000)}})}}</script>
</body></html>"""


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
