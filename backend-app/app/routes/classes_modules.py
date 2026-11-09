from flask import jsonify, request
from flask_login import current_user
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models.academic_structure import Department, SchoolClass, Trade
from app.models.academics import AcademicSubject, ClassModule
from app.models.user import User
from app.utils.decorators import permission_for, role_required
from app.utils.rendering import page

CLASSES_MODULES_BODY = r"""<style>
:root{--bg:#f6f7f9;--card:#fff;--tx:#1d2330;--mu:#667085;--bd:#e3e6ec;--ac:#1f5eff;--c1:#0e7490;--c2:#6b7280;--c3:#c2410c;box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#14171c;--card:#1d2128;--tx:#eceff4;--mu:#98a2b3;--bd:#2c323c;--ac:#6b93ff;--c1:#38bdf8;--c2:#9ca3af;--c3:#fb923c;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#14171c;--card:#1d2128;--tx:#eceff4;--mu:#98a2b3;--bd:#2c323c;--ac:#6b93ff;--c1:#38bdf8;--c2:#9ca3af;--c3:#fb923c;color-scheme:dark}
*{box-sizing:border-box}html{scroll-padding-top:env(safe-area-inset-top,0px)}
body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{padding:16px 20px;border-bottom:1px solid var(--bd);background:var(--card)}
h1{margin:0;font-size:18px}header p{margin:2px 0 0;color:var(--mu);font-size:13px}
.wrap{display:flex;gap:16px;padding:16px 20px;max-width:1100px;margin:auto}
nav{width:290px;flex:none}
.dept{font-weight:700;font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--mu);margin:14px 0 6px}
.dept:first-child{margin-top:0}
.trade{font-size:13px;font-weight:600;margin:8px 0 4px}
.cls{display:block;width:100%;text-align:left;background:var(--card);border:1px solid var(--bd);color:var(--tx);padding:8px 10px;border-radius:8px;margin-bottom:5px;cursor:pointer;font:inherit;font-size:14px}
.cls:hover{border-color:var(--ac)}.cls.on{background:var(--ac);color:#fff;border-color:var(--ac)}
main{flex:1;min-width:0}
.top{display:flex;flex-wrap:wrap;gap:8px;align-items:baseline;justify-content:space-between;margin-bottom:10px}
.top h2{margin:0;font-size:20px}.stats{color:var(--mu);font-size:13px}
input{width:100%;padding:9px 12px;border:1px solid var(--bd);border-radius:8px;background:var(--card);color:var(--tx);font:inherit;margin-bottom:12px}
.grp{background:var(--card);border:1px solid var(--bd);border-radius:10px;margin-bottom:14px;overflow:hidden}
.gh{display:flex;justify-content:space-between;padding:10px 14px;font-weight:700;border-left:5px solid var(--g)}
.gh span{font-weight:500;color:var(--mu);font-size:13px}
.tw{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:14px}
th,td{padding:8px 14px;text-align:left;border-top:1px solid var(--bd)}th{font-size:12px;color:var(--mu);font-weight:600}
td.n{text-align:right;white-space:nowrap}code{font-weight:600}
.empty{background:var(--card);border:1px dashed var(--bd);border-radius:10px;padding:28px;text-align:center;color:var(--mu)}
.actions{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end;padding:12px 20px;background:var(--card);border-bottom:1px solid var(--bd)}
.actions button,.dialog button{border:1px solid var(--bd);border-radius:8px;padding:9px 13px;background:var(--card);color:var(--tx);font:inherit;cursor:pointer}
.actions .primary,.dialog .primary{background:var(--ac);border-color:var(--ac);color:#fff}
dialog{width:min(460px,calc(100% - 28px));border:1px solid var(--bd);border-radius:14px;background:var(--card);color:var(--tx);padding:20px;box-shadow:0 18px 60px #0003}dialog::backdrop{background:#10182888}
.dialog h2{margin:0 0 14px;font-size:19px}.dialog label{display:block;font-size:13px;font-weight:600;margin:10px 0 5px}.dialog input,.dialog select{width:100%;padding:10px;border:1px solid var(--bd);border-radius:8px;background:var(--card);color:var(--tx);font:inherit;margin:0}.dialog .row{display:grid;grid-template-columns:1fr 1fr;gap:10px}.dialog .buttons{display:flex;justify-content:flex-end;gap:8px;margin-top:18px}.form-error{min-height:20px;color:#b42318;font-size:13px;margin-top:8px}
.module-controls{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:12px 14px;margin:0 0 14px}.module-controls h3{margin:0 0 8px;font-size:15px}.module-control{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:7px 0;border-top:1px solid var(--bd);font-size:13px}.module-control button{border:1px solid var(--bd);border-radius:7px;background:var(--card);color:var(--tx);padding:6px 9px;cursor:pointer}.module-control button:hover{border-color:var(--ac)}
@media(max-width:760px){.wrap{flex-direction:column}nav{width:100%}}
</style>
<header><h1>Classes &amp; Modules — School Year 2026–2027</h1><p>Select a class to see its Complementary, General and Specific (core) modules.</p></header>
{% if can_manage %}<div class="actions"><button type="button" id="open-class">＋ Add class</button><button type="button" class="primary" id="open-module">＋ Add module</button></div>
<dialog id="class-dialog"><form class="dialog" id="class-form"><h2>Add a class</h2><label for="class-department">Department</label><select id="class-department" name="department_id" required></select><label for="class-trade">Trade</label><select id="class-trade" name="trade_id" required></select><label for="class-name">Class name</label><input id="class-name" name="name" maxlength="160" required placeholder="e.g. L4 Software Development C"><div class="row"><div><label for="class-level">Level</label><input id="class-level" name="level" maxlength="30" required placeholder="e.g. L4"></div><div><label for="class-code">Class code (optional)</label><input id="class-code" name="code" maxlength="80"></div></div><div class="form-error" role="alert"></div><div class="buttons"><button type="button" data-close="class-dialog">Cancel</button><button class="primary" type="submit">Save class</button></div></form></dialog>
<dialog id="module-dialog"><form class="dialog" id="module-form"><h2>Add a module</h2><label for="module-class">Class</label><select id="module-class" name="class_id" required></select><label for="module-code">Module code</label><input id="module-code" name="code" maxlength="32" required placeholder="e.g. SWDPR401"><label for="module-title">Module title</label><input id="module-title" name="title" maxlength="200" required><div class="row"><div><label for="module-category">Category</label><select id="module-category" name="category" required><option value="C">Complementary</option><option value="G">General</option><option value="S">Specific (Core)</option></select></div><div><label for="module-hours">Hours</label><input id="module-hours" name="hours" type="number" min="0" max="10000" value="0" required></div></div><label for="module-teacher">Assigned teacher (optional)</label><select id="module-teacher" name="teacher_id"><option value="">Unassigned</option></select><div class="form-error" role="alert"></div><div class="buttons"><button type="button" data-close="module-dialog">Cancel</button><button class="primary" type="submit">Save module</button></div></form></dialog>{% endif %}
<div class="wrap"><nav id="nav"></nav><main id="main"></main></div>
<script>
const P=s=>s.split("\n").filter(Boolean).map(l=>{const[a,b,c]=l.split("|");return{code:a,title:b,h:+c}});
const COMP5=P(`CMEN502|Use upper-intermediate English at the workplace|30
CCMCZ502|Develop attitudes of living together in harmony|30
CCMBO502|Organise a business|30
CCMFT502|Echanger les idées en français élémentaire|30
CCMKN502|Gukoresha ikinyarwanda k’intyoza|30
CCMKK502|Kutumia Kiswahili katika mawasiliano ya kazini|30
CCMPE502|Apply Professional and multicultural ethics at workplace|30
CCMIW502|Use ICT at Workplace|30`);
const COMP4=P(`CCMBP402|Develop a business plan|30
CCMCS402|Apply computer skills|30
CCMCZ401|Promote the Culture of Peace|30
CCMEN402|Use intermediate English at workplace|30
CCMKN402|Gukoresha ikinyarwanda cy’umunyamwuga|30
CCMFT401|Exprimer des Opinions en Français élémentaire|30`);
const COMP3=P(`CCMOL302|Describe the Occupation and learning process|30
CCMBC302|Create a Business|30
CCMCL302|Apply computer literacy|30
CCMCZ301|Comply With Citizenship Values|30
CCMEN302|Use Pre-intermediate English at the Workplace|30
CCMFR303|Communiquer simplement en français au quotidien|30
CCMHE303|Maintain SHE at Workplace|30
CCMKK302|Kutumia Kiswahili wastani|30
CCMKN302|Gukoresha Ikinyarwanda Kiboneye|30`);
const AP=P(`GENAP502|Apply mathematical analysis, statistics and probability|60`),DM=P(`GENDM502|Apply dynamics and mechanical waves|40`);
const NIT4={C:COMP4,G:P(`GENFA402|Apply fundamental mathematical analysis|60
GENMP402|Apply mechanics and properties of matter|40
GENTD401|Apply Basics of Technical Drawing|50
GENDD401|Develop Database|70`),S:P(`NITWN401|Set up Wide Area Network|100
NITID401|Develop IoT System|140
NITIW401|Develop IoT web application using PHP|100
NITWA401|Administer Windows Server|100
NITWO401|Set up wireless network outdoor|80
NITFO401|Deploy Fiber Optics Network|80
NITIA401|Integrate the workplace|200`)};
const CSA4={C:COMP4,G:P(`GENFA402|Apply fundamental mathematical analysis|60
GENMP402|Apply mechanics and properties of matter|40
GENSW401|Apply SolidWorks Design|60
GENFC401|Apply C++ programming|70
GENCP401|Apply C Programming|80
GENDE401|Apply digital electronics|80`),S:P(`CSACR401|Refurbish Computer system|70
CSAES401|Develop embedded System Hardware|120
CSAFD401|Develop embedded system firmware|80
CSALS401|Set up LED and LCD screen|70
CSACE401|Create Electronics Enclosure|70
CSAIA401|Integrate the workplace|200`)};
const SWD4={C:COMP4,G:P(`GENFA402|Apply fundamental mathematical analysis|60
GENMP402|Apply mechanics and properties of matter|40
GENBN401|Perform Basic of Networking|70`),S:P(`SWDDA401|Apply Data Structure and Algorithm fundamentals using JavaScript|130
SWDBS401|Design Backend System|80
SWDBA401|Develop a Backend Application using Node.js|100
SWDDD401|Develop Database|100
SWDPP401|Apply PHP Programming|150
SWDWS401|Perform Basic Windows Server Administration|90
SWDIA401|Integrate the workplace|200`)};
const SWD3={C:COMP3,G:P(`GENGD301|Apply basic graphics design|80
GENAT302|Apply Algebra and Trigonometry|60
GENGP302|Apply General Physics|40`),S:P(`SWDPR301|Analyse Project Requirements|50
SWDWD301|Develop Website|110
SWDVC301|Conduct Version Control|70
SWDUX301|Design UI/UX|100
SWDJF301|Apply JavaScript|100
SWDVF301|Develop game in Vue|120
ICTIA301|Integrate the Workplace|200`)};
const NIT3={C:COMP3,G:P(`GENCP302|Apply C Programming Fundamentals|80
GENNT301|Apply Network Fundamentals|80
GENEF302|Apply Electronic fundamentals|80
GENBE302|Apply Basics of Electricity|70
GENAT302|Apply Algebra and Trigonometry|60
GENGP302|Apply General Physics|40`),S:P(`NITLI301|Setup LAN|60
NITCI301|Install CCTV System|70
NITWI301|Set up Wireless Network indoor|50
NITVI301|Setup VoIP System|70
NITIS301|Install IoT System|70
NITIA301|Integrate the Workplace|200`)};
const CSA3={C:COMP3,G:P(`GENNF301|Apply Network Fundamentals|50
GENBE302|Apply Fundamentals of Electricity|70
GENEF302|Apply Electronic fundamentals|60
GENTD301|Apply basic of technical drawing|50
GENAC302|Demonstrate Basics Of Chemistry|30
GENAT302|Apply Algebra and Trigonometry|60
GENGP302|Apply General Physics|40`),S:P(`CSAIA301|Assemble PCB and Computer system|80
CSATM301|Maintain Telephone|50
CSACM301|Maintain computer system|60
CSACI301|Implement electronic circuit|70
CSACD301|Deploy computer system|50
CSAPD301|Deploy Computer Peripherals|60
CSAPA301|Integrate the workplace|200`)};
const SWD5={C:COMP5,G:[...AP,...DM,...P(`GENPP501|Apply Python Programming|80
GENQA501|Apply Quality Assurance|30`)],S:P(`SWDFA501|Develop FrontEnd Using ReactJS|110
SWDMA501|Develop Mobile Application using Flutter|100
SWDBF501|Apply fundamentals of Blockchain|100
SWDML501|Apply fundamental machine learning|100
SWDDO501|Apply DevOps Techniques|70
SWDND501|Develop NoSQL Database|70
NITIA501|Integrate the Workplace|200`)};
const NIT5={C:COMP5,G:[...AP,...DM,...P(`GENPP501|Apply Python Programming Fundamentals|100`)],S:P(`NITLS501|Administer Linux Server|100
NITZC501|Apply Zero Client using Ncomputing Technology|100
NITCS501|Apply Cyber Security|120
NITCC501|Apply cloud computing Technology in Datacenter|120
NITML501|Apply Machine Learning fundamentals|120
NITIA501|Integrate the Workplace|200`)};
const CSA5={C:COMP5,G:[...AP,...DM],S:P(`GENDS501|Apply Data Structure and Algorithm using C programming|100
GENWS501|Apply Windows Server Administration|60
GENCC501|Consume Cloud Computing Services|60
CSAPS501|Develop Computer Power System|100
CSACH501|Design Computer Hardware Architecture|100
CSASA501|Automate System using PLC|90
CSAHK501|Develop Hobby Kernel Development|120
GENQA501|Apply Quality Assurance|30
CSAIA501|Integrate the Workplace|200`)};
const FAD3={C:COMP3,G:P(`GENBE302|Apply Basics of Domestic Electricity|30
GENAC302|Demonstrate Basics of Chemistry|30
GENAT302|Apply Basic Algebra and Trigonometry|60
GENCE303|Apply cost estimation|30
GENTD301|Perform technical drawing|50
GENMS301|Perform Basic Maintenance of sewing machines|40`),S:P(`FADHP301|Draft Hand Pattern|80
FADHS301|Perform hand sketching|50
FADSA301|Perform Basic stitches and surface application|80
FADGC301|Perform Garment Construction|110
FADHS301|Perform Hand Weaving|70
FADCK301|Perform Crocheting and knitting|50
FADFC301|Perform Fabric Care|50
FADIA302|Integrate the Workplace|200`)};
const FAD4={C:[...COMP4,{code:"CCMKK402",title:"Kutumia Kiswahili katika mawasiliano ya kawaida",h:30}],G:P(`GENFA402|Apply Elementary Mathematical Analysis|60
GENAC402|Demonstrate Knowledge of Organic Chemistry|30
GENST401|Perform sewing techniques|60
FADSP401|Sell Fashion Products and Services|40`),S:P(`FADFC401|Perform Fabric cutting|50
FADFFM401|Perform fabric manipulation|70
FADPM401|Manipulate block pattern|110
FADDM401|Make formal dress|120
FADMJ401|Make Jumpsuit|70
FADME401|Perform machine embroidery|70
FADWJ401|Make women jacket|110
FADIA402|Integrate the workplace|200`)};
const FAD5={C:COMP5,G:[...AP.map(x=>x),...P(`FADDI501|Perform Digital Illustration|90
FADDP501|Make Digital Pattern|100`)],S:P(`FADEG501|Make Evening Gown|100
FADMS501|Make Men suit|120
FADMW501|Make Men’s Wear|90
FADWW501|Make Women’s wear|110
FADFA501|Make Fashion Accessories|90
FADIA502|Integrate the Workplace|200`)};
const ACCB=["English for Accounting","Management in Accounting","ICT in Accounting","Financial Accounting","Mathematics for Accounting","Taxation","Entrepreneurship","Ikinyarwanda","General Studies","Physical Education and Sport","French (combination, non-literary)"];
const mk=a=>({A:a.map((n,i)=>({code:String(i+1).padStart(2,"0"),title:n}))});
const DEPTS=[
{n:"ICT and Multimedia",t:[
 {n:"Software Development",c:[["L3 Software Development",SWD3],["L4 Software Development A",SWD4],["L4 Software Development B",SWD4],["L5 Software Development",SWD5]]},
 {n:"Networking and Internet Technologies",c:[["L3 Networking and Internet Technologies",NIT3],["L4 Networking and Internet Technologies A",NIT4],["L4 Networking and Internet Technologies B",NIT4],["L5 Networking and Internet Technologies",NIT5]]},
 {n:"Computer System and Architecture",c:[["L3 Computer System and Architecture",CSA3],["L4 Computer System and Architecture",CSA4],["L5 Computer System and Architecture",CSA5]]}]},
{n:"Fashion and Design",t:[{n:"Fashion Design",c:[["L3 Fashion Design",FAD3],["L4 Fashion Design",FAD4],["L5 Fashion Design",FAD5]]}]},
{n:"Professional Accountant",t:[{n:"Accounting",c:[["Senior 4 Accounting",mk(ACCB)],["Senior 5 Accounting",mk(ACCB)],["Senior 6 Accounting",mk(["Auditing",...ACCB])]]}]}];
const GR=[["C","Complementary Modules","--c1"],["G","General Modules","--c2"],["S","Specific (Core) Modules","--c3"],["A","All Subjects","--c1"]];
let sel="L3 Software Development",q="",departmentData=[];
const all={};DEPTS.forEach(d=>d.t.forEach(t=>t.c.forEach(([n,x])=>all[n]=x)));
const esc=s=>String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function nav(){document.getElementById("nav").innerHTML=DEPTS.map(d=>`<div class="dept">${esc(d.n)}</div>`+d.t.map(t=>`<div class="trade">${esc(t.n)}</div>`+t.c.map(([n])=>`<button class="cls${n===sel?" on":""}" data-c="${esc(n)}">${esc(n)}</button>`).join("")).join("")).join("")}
function main(){
 const d=all[sel];let h=`<div class="top"><h2>${esc(sel)}</h2>`;
 if(!d){document.getElementById("main").innerHTML=h+`</div><div class="empty">No module data yet for this class.<br>Upload its training chronogram and it will be added.</div>`;return}
 const tot=GR.reduce((a,[k])=>a+(d[k]||[]).reduce((s,m)=>s+(m.h||0),0),0),cnt=GR.reduce((a,[k])=>a+(d[k]||[]).length,0);
 const controls=GR.flatMap(([k])=>d[k]||[]).filter(m=>m.can_toggle);
 if(controls.length)h+=`<section class="module-controls"><h3>Assigned module availability</h3>${controls.map(m=>`<div class="module-control"><span><strong>${esc(m.code)}</strong> · ${esc(m.title)} — ${m.is_active?"Available":"Deactivated"}</span><button type="button" data-module-toggle="${m.module_id}" data-next-active="${!m.is_active}">${m.is_active?"Deactivate":"Reactivate"}</button></div>`).join("")}</section>`;
 h+=`<div class="stats">${cnt} ${tot?"modules · "+tot+" hours · "+tot*1.5+" periods":"subjects"}</div></div><input id="q" placeholder="Search module code or title…" value="${esc(q)}">`;
 GR.forEach(([k,t,col])=>{const rows=(d[k]||[]).filter(m=>(m.code+m.title).toLowerCase().includes(q.toLowerCase()));if(!rows.length)return;
  h+=`<div class="grp" style="--g:var(${col})"><div class="gh">${t}<span>${rows.length} ${k==="A"?"subjects":"modules · "+rows.reduce((s,m)=>s+m.h,0)+" h"}</span></div><div class="tw"><table><tr><th>Code</th><th>Module title</th><th class="n">Hours</th><th class="n">Periods</th></tr>${rows.map(m=>`<tr><td><code>${m.code}</code></td><td>${esc(m.title)}</td><td class="n">${m.h||"—"}</td><td class="n">${m.h?m.h*1.5:"—"}</td></tr>`).join("")}</table></div></div>`});
 document.getElementById("main").innerHTML=h;
 const i=document.getElementById("q");i.oninput=e=>{q=e.target.value;const p=i.selectionStart;main();const j=document.getElementById("q");j.focus();j.setSelectionRange(p,p)}}
async function loadSavedData(){
 const response=await fetch("/classes-modules/data");if(!response.ok)return;
 const data=await response.json();departmentData=data.departments||[];
 (data.classes||[]).forEach(item=>{
  if(all[item.name])return;
  let department=DEPTS.find(d=>d.n===item.department);if(!department){department={n:item.department,t:[]};DEPTS.push(department)}
  let trade=department.t.find(t=>t.n===item.trade);if(!trade){trade={n:item.trade,c:[]};department.t.push(trade)}
  const modules={C:[],G:[],S:[],A:[]};trade.c.push([item.name,modules]);all[item.name]=modules;
 });
 (data.hidden_modules||[]).forEach(item=>{const group=all[item.class_name];if(group&&group[item.category])group[item.category]=group[item.category].filter(m=>m.code!==item.code)});
 (data.modules||[]).forEach(item=>{const group=all[item.class_name];if(!group||!group[item.category])return;const row=group[item.category].find(m=>m.code===item.code);const saved={code:item.code,title:item.title,h:item.hours,module_id:item.id,teacher_name:item.teacher_name,is_active:item.is_active,can_toggle:item.can_toggle};if(row)Object.assign(row,saved);else group[item.category].push(saved)});
 const departmentSelect=document.getElementById("class-department"),tradeSelect=document.getElementById("class-trade"),classSelect=document.getElementById("module-class");
 if(departmentSelect){departmentSelect.innerHTML=departmentData.map(d=>`<option value="${d.id}">${esc(d.name)}</option>`).join("");
  const fillTrades=()=>{const d=departmentData.find(item=>item.id===Number(departmentSelect.value));tradeSelect.innerHTML=(d?.trades||[]).map(t=>`<option value="${t.id}">${esc(t.name)}</option>`).join("")};
  departmentSelect.onchange=fillTrades;fillTrades();
  classSelect.innerHTML=(data.classes||[]).map(c=>`<option value="${c.id}">${esc(c.name)} · ${esc(c.trade)}</option>`).join("");
  const teacherSelect=document.getElementById("module-teacher");if(teacherSelect)teacherSelect.innerHTML='<option value="">Unassigned</option>'+(data.teachers||[]).map(t=>`<option value="${t.id}">${esc(t.name)}</option>`).join("");
 }
 nav();main();
}
async function submitForm(form,url,onSuccess){
 const error=form.querySelector(".form-error"),submit=form.querySelector('[type="submit"]');error.textContent="";submit.disabled=true;
 try{const response=await fetch(url,{method:"POST",body:new FormData(form)}),result=await response.json();if(!response.ok){error.textContent=result.error||"Could not save this entry.";return}form.reset();form.closest("dialog").close();await loadSavedData();onSuccess?.(result)}
 catch(_){error.textContent="Could not reach the server. Please try again."}
 finally{submit.disabled=false}
}
document.getElementById("nav").onclick=e=>{const b=e.target.closest("button");if(b){sel=b.dataset.c;q="";nav();main()}};
 document.getElementById("main").onclick=async e=>{const button=e.target.closest("[data-module-toggle]");if(!button)return;button.disabled=true;const body=new FormData();body.append("is_active",button.dataset.nextActive);try{const response=await fetch(`/classes-modules/modules/${button.dataset.moduleToggle}/status`,{method:"POST",body}),result=await response.json();if(!response.ok){window.alert(result.error||"Unable to change module status.");return}await loadSavedData()}catch(_){window.alert("Could not reach the server. Please try again.")}finally{button.disabled=false}};
document.querySelectorAll("[data-close]").forEach(button=>button.onclick=()=>document.getElementById(button.dataset.close).close());
const classDialog=document.getElementById("class-dialog"),moduleDialog=document.getElementById("module-dialog");
if(classDialog){document.getElementById("open-class").onclick=()=>classDialog.showModal();document.getElementById("open-module").onclick=()=>moduleDialog.showModal();
 document.getElementById("class-form").onsubmit=e=>{e.preventDefault();submitForm(e.currentTarget,"/classes-modules/classes",result=>{sel=result.name;q="";nav();main()})};
 document.getElementById("module-form").onsubmit=e=>{e.preventDefault();submitForm(e.currentTarget,"/classes-modules/modules",result=>{sel=result.class_name;q="";nav();main()})};
}
nav();main();loadSavedData();
</script>"""

def classes_modules():
    from flask_login import current_user
    can_manage = current_user.role in {"master_admin", "head_teacher"}
    return page("Classes & Modules", CLASSES_MODULES_BODY, "dashboard", can_manage=can_manage)


def classes_modules_data():
    can_manage = current_user.role in {"master_admin", "head_teacher"}
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    classes = SchoolClass.query.join(Trade).join(Department).filter(
        SchoolClass.is_active.is_(True), Trade.is_active.is_(True), Department.is_active.is_(True)
    ).order_by(Department.name, Trade.name, SchoolClass.name).all()
    module_query = ClassModule.query.join(SchoolClass).filter(SchoolClass.is_active.is_(True))
    hidden_modules = []
    if current_user.role == "teacher":
        hidden_modules = [{"class_name": module.school_class.name, "code": module.code, "category": module.category}
                          for module in module_query.filter(ClassModule.is_active.is_(False),
                                                           ClassModule.teacher_id != current_user.id).all()]
        module_query = module_query.filter(or_(ClassModule.is_active.is_(True),
                                               ClassModule.teacher_id == current_user.id))
    elif not can_manage:
        hidden_modules = [{"class_name": module.school_class.name, "code": module.code, "category": module.category}
                          for module in module_query.filter(ClassModule.is_active.is_(False)).all()]
        module_query = module_query.filter(ClassModule.is_active.is_(True))
    modules = module_query.order_by(ClassModule.id).all()
    return jsonify({
        "departments": [{
            "id": department.id,
            "name": department.name,
            "trades": [{"id": trade.id, "name": trade.name} for trade in sorted(
                (trade for trade in department.trades if trade.is_active), key=lambda item: item.name.lower()
            )],
        } for department in departments],
        "classes": [{
            "id": school_class.id,
            "name": school_class.name,
            "level": school_class.level,
            "trade": school_class.trade.name,
            "department": school_class.trade.department.name,
        } for school_class in classes],
        "teachers": [{"id": teacher.id, "name": teacher.full_name} for teacher in
                     (User.query.filter_by(role="teacher", is_active_account=True).order_by(User.full_name).all()
                      if can_manage else [])],
        "hidden_modules": hidden_modules,
        "modules": [{
            "id": module.id,
            "class_name": module.school_class.name,
            "code": module.code,
            "title": module.title,
            "category": module.category,
            "hours": module.hours,
            "teacher_id": module.teacher_id,
            "teacher_name": module.teacher.full_name if module.teacher else None,
            "is_active": module.is_active,
            "can_toggle": can_manage or (current_user.role == "teacher" and module.teacher_id == current_user.id),
        } for module in modules],
    })


def add_class():
    department_id = request.form.get("department_id", type=int)
    trade_id = request.form.get("trade_id", type=int)
    name = request.form.get("name", "").strip()
    level = request.form.get("level", "").strip()
    code = request.form.get("code", "").strip() or None
    trade = db.session.get(Trade, trade_id) if trade_id else None
    department = db.session.get(Department, department_id) if department_id else None
    if not name or not level or not trade or not department or trade.department_id != department.id:
        return jsonify(error="Choose a department and its trade, and provide a class name and level."), 400
    if len(name) > 160 or len(level) > 30 or (code and len(code) > 80):
        return jsonify(error="One or more class fields are too long."), 400
    school_class = SchoolClass(trade_id=trade.id, name=name, level=level, code=code)
    db.session.add(school_class)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="That class name or class code is already in use."), 409
    return jsonify({"id": school_class.id, "name": school_class.name, "level": school_class.level,
                    "trade": trade.name, "department": department.name}), 201


def add_module():
    class_id = request.form.get("class_id", type=int)
    school_class = db.session.get(SchoolClass, class_id) if class_id else None
    code = request.form.get("code", "").strip().upper()
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "").strip().upper()
    hours = request.form.get("hours", type=int)
    teacher_id = request.form.get("teacher_id", type=int)
    teacher = db.session.get(User, teacher_id) if teacher_id else None
    if not school_class or not school_class.is_active or not code or not title or category not in {"C", "G", "S"}:
        return jsonify(error="Choose an active class and provide a code, title, and module category."), 400
    if len(code) > 32 or len(title) > 200 or hours is None or hours < 0 or hours > 10000:
        return jsonify(error="Check the code, title, and hours. Hours must be between 0 and 10000."), 400
    if teacher_id and (not teacher or teacher.role != "teacher" or not teacher.is_active_account):
        return jsonify(error="Choose an active teacher account."), 400
    module = ClassModule(class_id=school_class.id, code=code, title=title, category=category,
                         hours=hours, teacher_id=teacher_id, created_by_id=current_user.id)
    db.session.add(module)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="That module code already exists for this class."), 409
    return jsonify({"class_name": school_class.name, "code": code, "title": title,
                    "category": category, "hours": hours, "is_active": module.is_active}), 201


def set_module_status(module_id):
    module = db.session.get(ClassModule, module_id)
    if not module:
        return jsonify(error="Module not found."), 404
    if current_user.role == "teacher" and module.teacher_id != current_user.id:
        return jsonify(error="You can only change the status of a module assigned to you."), 403
    value = request.form.get("is_active", "").strip().lower()
    if value not in {"true", "false"}:
        return jsonify(error="Choose a valid module status."), 400
    module.is_active = value == "true"
    for subject in AcademicSubject.query.filter_by(
        class_name=module.school_class.name, subject=module.title
    ).all():
        subject.is_active = module.is_active
    db.session.commit()
    return jsonify({"id": module.id, "is_active": module.is_active})

def register_routes(app):
    app.add_url_rule(
        "/classes-modules",
        endpoint="classes_modules",
        view_func=permission_for("classes_modules")(classes_modules),
        methods=["GET"],
    )
    app.add_url_rule(
        "/classes-modules/data",
        endpoint="classes_modules_data",
        view_func=permission_for("classes_modules")(classes_modules_data),
        methods=["GET"],
    )
    app.add_url_rule(
        "/classes-modules/classes",
        endpoint="classes_modules_add_class",
        view_func=role_required("master_admin", "head_teacher")(add_class),
        methods=["POST"],
    )
    app.add_url_rule(
        "/classes-modules/modules",
        endpoint="classes_modules_add_module",
        view_func=role_required("master_admin", "head_teacher")(add_module),
        methods=["POST"],
    )
    app.add_url_rule(
        "/classes-modules/modules/<int:module_id>/status",
        endpoint="classes_modules_module_status",
        view_func=role_required("master_admin", "head_teacher", "teacher")(set_module_status),
        methods=["POST"],
    )
