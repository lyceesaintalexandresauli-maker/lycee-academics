from app.utils.rendering import page
from app.utils.decorators import permission_for

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
@media(max-width:760px){.wrap{flex-direction:column}nav{width:100%}}
</style>
<header><h1>Classes &amp; Modules — School Year 2026–2027</h1><p>Select a class to see its Complementary, General and Specific (core) modules.</p></header>
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
let sel="L3 Software Development",q="";
const all={};DEPTS.forEach(d=>d.t.forEach(t=>t.c.forEach(([n,x])=>all[n]=x)));
const esc=s=>s.replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
function nav(){document.getElementById("nav").innerHTML=DEPTS.map(d=>`<div class="dept">${d.n}</div>`+d.t.map(t=>`<div class="trade">${t.n}</div>`+t.c.map(([n])=>`<button class="cls${n===sel?" on":""}" data-c="${n}">${n}</button>`).join("")).join("")).join("")}
function main(){
 const d=all[sel];let h=`<div class="top"><h2>${sel}</h2>`;
 if(!d){document.getElementById("main").innerHTML=h+`</div><div class="empty">No module data yet for this class.<br>Upload its training chronogram and it will be added.</div>`;return}
 const tot=GR.reduce((a,[k])=>a+(d[k]||[]).reduce((s,m)=>s+(m.h||0),0),0),cnt=GR.reduce((a,[k])=>a+(d[k]||[]).length,0);
 h+=`<div class="stats">${cnt} ${tot?"modules · "+tot+" hours · "+tot*1.5+" periods":"subjects"}</div></div><input id="q" placeholder="Search module code or title…" value="${esc(q)}">`;
 GR.forEach(([k,t,col])=>{const rows=(d[k]||[]).filter(m=>(m.code+m.title).toLowerCase().includes(q.toLowerCase()));if(!rows.length)return;
  h+=`<div class="grp" style="--g:var(${col})"><div class="gh">${t}<span>${rows.length} ${k==="A"?"subjects":"modules · "+rows.reduce((s,m)=>s+m.h,0)+" h"}</span></div><div class="tw"><table><tr><th>Code</th><th>Module title</th><th class="n">Hours</th><th class="n">Periods</th></tr>${rows.map(m=>`<tr><td><code>${m.code}</code></td><td>${esc(m.title)}</td><td class="n">${m.h||"—"}</td><td class="n">${m.h?m.h*1.5:"—"}</td></tr>`).join("")}</table></div></div>`});
 document.getElementById("main").innerHTML=h;
 const i=document.getElementById("q");i.oninput=e=>{q=e.target.value;const p=i.selectionStart;main();const j=document.getElementById("q");j.focus();j.setSelectionRange(p,p)}}
document.getElementById("nav").onclick=e=>{const b=e.target.closest("button");if(b){sel=b.dataset.c;q="";nav();main()}};
nav();main();
</script>"""

def classes_modules():
    return page("Classes & Modules", CLASSES_MODULES_BODY, "dashboard")

def register_routes(app):
    app.add_url_rule(
        "/classes-modules",
        endpoint="classes_modules",
        view_func=permission_for("classes_modules")(classes_modules),
        methods=["GET"],
    )
