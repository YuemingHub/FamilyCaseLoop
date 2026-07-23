"""单页可视化工作台 HTML（密钥设置 + 决策可视化 + 回复展示）。

纯前端：调用 /settings（GET/POST）与 /reply 两个接口，不依赖外部 CDN。
主题：暗色，对齐 IDE 暗色主题。
"""
from __future__ import annotations

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>月明家长回复生成器 · 可视化工作台</title>
<style>
  :root{
    --bg:#0f1117; --panel:#171a23; --panel2:#1e2230; --border:#2a3040;
    --text:#e6e9f0; --muted:#9aa3b2; --accent:#6ea8fe; --accent2:#7ee0c0;
    --warn:#ffb454; --danger:#ff6b6b; --ok:#7ee0c0;
  }
  *{box-sizing:border-box;}
  body{margin:0;background:var(--bg);color:var(--text);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;
    line-height:1.55;}
  header{padding:18px 22px;border-bottom:1px solid var(--border);
    display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;}
  header h1{font-size:18px;margin:0;font-weight:600;}
  header .sub{color:var(--muted);font-size:13px;}
  .badge{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;
    border:1px solid var(--border);color:var(--muted);}
  .badge.on{color:var(--ok);border-color:#2e4d44;background:#10211c;}
  .badge.off{color:var(--warn);border-color:#4d3e2e;background:#211a10;}
  .wrap{max-width:1080px;margin:0 auto;padding:20px 22px 60px;}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
  @media(max-width:820px){.grid{grid-template-columns:1fr;}}
  .card{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:16px 18px;}
  .card h2{font-size:14px;margin:0 0 12px;color:var(--accent);font-weight:600;
    letter-spacing:.3px;display:flex;align-items:center;gap:8px;}
  label{display:block;font-size:12px;color:var(--muted);margin:10px 0 5px;}
  input,textarea,select{width:100%;background:var(--panel2);border:1px solid var(--border);
    color:var(--text);border-radius:8px;padding:9px 11px;font-size:14px;font-family:inherit;}
  textarea{resize:vertical;min-height:96px;}
  button{background:var(--accent);color:#0b1020;border:none;border-radius:8px;
    padding:10px 16px;font-size:14px;font-weight:600;cursor:pointer;margin-top:12px;}
  button.ghost{background:transparent;color:var(--accent);border:1px solid var(--border);}
  button:hover{filter:brightness(1.08);}
  .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;}
  .kv{font-size:13px;color:var(--muted);margin:4px 0;}
  .kv b{color:var(--text);font-weight:600;}
  .pill{display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;
    background:var(--panel2);border:1px solid var(--border);margin:3px 4px 3px 0;}
  .pill.lens{color:var(--accent2);border-color:#2e4d44;}
  .reply{white-space:pre-wrap;background:var(--panel2);border:1px solid var(--border);
    border-radius:8px;padding:12px 14px;font-size:14px;min-height:60px;}
  .tag-safety{color:var(--danger);}
  .tag-handoff{color:var(--warn);}
  .tag-normal{color:var(--ok);}
  .meta{font-size:12px;color:var(--muted);margin-top:8px;}
  .small{font-size:12px;color:var(--muted);}
  .err{color:var(--danger);font-size:13px;margin-top:8px;}
  .viz-empty{color:var(--muted);font-size:13px;}
  ul.clean{margin:6px 0 0;padding-left:18px;font-size:13px;}
  ul.clean li{margin:3px 0;}
</style>
</head>
<body>
<header>
  <div>
    <h1>月明家长回复生成器</h1>
    <div class="sub">双维诊断 · 七层透镜 · 安全门 · MingOS 两级路由 — 决策过程可视化</div>
  </div>
  <div class="row">
    <span class="badge" id="provBadge">provider: —</span>
    <span class="badge" id="llmBadge">LLM: —</span>
    <span class="badge" id="keyBadge">key: —</span>
  </div>
</header>

<div class="wrap">
  <div class="grid">
    <!-- 左：密钥设置 -->
    <div class="card">
      <h2>① LLM 密钥设置</h2>
      <div class="kv">当前状态：<b id="curKey">—</b> · provider <b id="curProv">—</b></div>
      <label for="apiKey">API Key（仅存本机 .env，掩码显示，不出本机）</label>
      <input id="apiKey" type="password" placeholder="粘贴 DeepSeek / 兼容 OpenAI 的 Key" autocomplete="off" />
      <label for="provider">Provider</label>
      <select id="provider">
        <option value="deepseek">deepseek（云端）</option>
        <option value="ollama">ollama（本机离线）</option>
      </select>
      <div class="row">
        <button id="saveBtn">保存并立即生效</button>
        <button class="ghost" id="refreshBtn">刷新状态</button>
      </div>
      <div class="small" style="margin-top:10px">
        若留空 API Key，将自动走「月明签名动作库」确定性降级，无需联网也能出回复。
      </div>
      <div class="err" id="setErr"></div>
    </div>

    <!-- 右：家长原话 -->
    <div class="card">
      <h2>② 家长原话</h2>
      <textarea id="parentMsg" placeholder="例如：孩子天天玩手机，我说两句就摔门，我真的不知道该怎么跟他说话了……"></textarea>
      <div class="row">
        <button id="genBtn">生成回复 + 可视化</button>
        <span class="small">默认同时返回决策链路（双维/透镜/路由/安全门）</span>
      </div>
      <div class="err" id="genErr"></div>
    </div>
  </div>

  <!-- 可视化区 -->
  <div class="card" style="margin-top:16px">
    <h2>③ 决策可视化</h2>
    <div id="viz" class="viz-empty">生成后这里展示方法论的逐步决策过程。</div>
  </div>

  <!-- 回复区 -->
  <div class="card" style="margin-top:16px">
    <h2>④ 给家长的回复</h2>
    <div class="reply" id="replyBox">（空）</div>
    <div class="meta" id="replyMeta"></div>
  </div>
</div>

<script>
const $ = (id) => document.getElementById(id);

async function refreshSettings(){
  try{
    const r = await fetch("/settings");
    const d = await r.json();
    $("curKey").textContent = d.has_key ? d.api_key_masked : "（未设置，走降级）";
    $("curProv").textContent = d.provider;
    $("provBadge").textContent = "provider: " + d.provider;
    $("keyBadge").textContent = d.has_key ? ("key: " + d.api_key_masked) : "key: 未设置";
    $("llmBadge").textContent = "LLM: " + (d.llm_enabled ? "已启用" : "降级模式");
    $("llmBadge").className = "badge " + (d.llm_enabled ? "on" : "off");
    $("provider").value = d.provider;
  }catch(e){ $("setErr").textContent = "读取状态失败：" + e; }
}

$("refreshBtn").onclick = refreshSettings;
$("saveBtn").onclick = async () => {
  $("setErr").textContent = "";
  const body = { api_key: $("apiKey").value, provider: $("provider").value };
  try{
    const r = await fetch("/settings", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
    const d = await r.json();
    if(d.ok){
      $("apiKey").value = "";
      await refreshSettings();
    } else { $("setErr").textContent = "保存失败"; }
  }catch(e){ $("setErr").textContent = "保存失败：" + e; }
};

function esc(s){ return (s==null?"":String(s)).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])); }

function renderViz(d){
  const viz = $("viz");
  let h = "";
  // 风险等级
  const rl = d.risk_level || "常规";
  const cls = rl==="安全门" ? "tag-safety" : (rl==="交还月明" ? "tag-handoff" : "tag-normal");
  h += `<div class="kv">风险等级：<b class="${cls}">${esc(rl)}</b>`
     + (d.handoff_to_yueming ? " · 已交还月明人工处理" : "")
     + (d.safety_triggered ? " · 安全门最高优先级拦截" : "") + `</div>`;

  // 双维诊断
  const diag = (d.analysis && d.analysis.diagnosis) || (d.diagnosis ? d.diagnosis : null);
  if(diag){
    h += `<div class="kv" style="margin-top:10px"><b>双维诊断</b></div>`;
    h += `<span class="pill">承载力：${esc(diag.capacity)}</span>`;
    h += `<span class="pill">行为惯性：${esc(diag.inertia)}</span>`;
    if(diag.tags && diag.tags.length) h += `<span class="pill">标签：${esc(diag.tags.join("、"))}</span>`;
    if(diag.primary) h += `<span class="pill">主标签：${esc(diag.primary)}</span>`;
    if(diag.secondary && diag.secondary.length) h += `<span class="pill">次标签：${esc(diag.secondary.join("、"))}</span>`;
    if(diag.confidence_score!=null) h += `<span class="pill">置信度：${esc(diag.confidence_score)}</span>`;
    if(diag.needs_review) h += `<span class="pill" style="color:var(--warn)">需人工复核</span>`;
    if(diag.risk) h += `<span class="pill tag-safety">风险主体：${esc(diag.risk.subject)}</span>`;
    if(diag.evidence){
      const ev = diag.evidence;
      const evKeys = Object.keys(ev);
      if(evKeys.length){
        h += `<div class="kv" style="margin-top:8px"><b>命中证据</b></div><ul class="clean">`;
        for(const k of evKeys){
          const v = ev[k];
          h += `<li>${esc(k)}：${esc(Array.isArray(v)?v.join("、"):v)}</li>`;
        }
        h += `</ul>`;
      }
    }
    if(diag.note) h += `<div class="small" style="margin-top:6px;color:var(--muted)">${esc(diag.note)}</div>`;
  }

  // 七层透镜
  const lens = (d.analysis && d.analysis.lens) || d.lens || [];
  if(lens && lens.length){
    h += `<div class="kv" style="margin-top:10px"><b>七层透镜（已化进话术，不露名词）</b></div>`;
    lens.forEach(l=>{ h += `<span class="pill lens">${esc(l)}</span>`; });
  }

  // 路由
  const route = (d.analysis && d.analysis.route) || d.route || null;
  if(route){
    h += `<div class="kv" style="margin-top:10px"><b>MingOS 路由决策</b></div>`;
    h += `<span class="pill">姿态：${esc(route.posture)}</span>`;
    h += `<span class="pill">内容：${esc(route.content_plan)}</span>`;
    h += `<span class="pill">动作数：${esc(route.action_count)}</span>`;
    h += `<span class="pill">禁步骤清单：${route.no_step_list?"是":"否"}</span>`;
    h += `<span class="pill">邀请式：${route.invite_style?"是":"否"}</span>`;
  }

  // FM 失败模式拦截
  const fm = (d.analysis && d.analysis.fm_violations) || d.fm_violations || [];
  if(fm && fm.length){
    h += `<div class="kv" style="margin-top:10px;color:var(--warn)"><b>失败模式硬拦截</b></div><ul class="clean">`;
    fm.forEach(f=>{ h += `<li>${esc(f)}</li>`; });
    h += `</ul>`;
  }
  viz.innerHTML = h;
}

$("genBtn").onclick = async () => {
  $("genErr").textContent = "";
  const text = $("parentMsg").value.trim();
  if(!text){ $("genErr").textContent = "请先输入家长原话"; return; }
  try{
    const r = await fetch("/reply", {method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({parent_message:text, mode:"analyze"})});
    const d = await r.json();
    renderViz(d);
    $("replyBox").textContent = d.reply || "（无回复内容）";
    $("replyMeta").textContent = "来源：" + (d.source||"—") + (d.meta ? " · " + d.meta : "");
  }catch(e){ $("genErr").textContent = "生成失败：" + e; }
};

refreshSettings();
</script>
</body>
</html>
"""
