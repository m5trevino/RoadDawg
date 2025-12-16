// ==UserScript==
// @name         ROAD DAWG v2.0 | The Scout
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  Hydration, Exfiltration, Bottom-Right HUD
// @author       The Architect
// @match        *://aistudio.google.com/*
// @grant        GM_xmlhttpRequest
// @grant        GM_setClipboard
// ==/UserScript==

(function() {
    'use strict';
    const C2_URL = "http://localhost:5575/api/drop";
    const GREEN = "#30d158";
    const RED = "#ff3b30";
    
    // STATE
    let eofMode = localStorage.getItem("rd_eof") === "true";
    let execMode = localStorage.getItem("rd_exec") === "true";

    // 1. THE TRIGGER (FOLLOW ME) - BOTTOM RIGHT
    const trigger = document.createElement("div");
    trigger.innerHTML = "🐺"; // Placeholder Dog
    trigger.title = "Road Dawg: Hydrate Chat";
    trigger.style.cssText = `
        position: fixed; bottom: 20px; right: 20px; z-index: 99999;
        font-size: 24px; cursor: pointer; background: #000;
        width: 50px; height: 50px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        border: 2px solid ${GREEN}; box-shadow: 0 0 15px rgba(48, 209, 88, 0.4);
        transition: all 0.2s;
    `;
    trigger.onclick = () => startWalk();
    document.body.appendChild(trigger);

    // --- LOGIC ---
    async function startWalk() {
        const dots = Array.from(document.querySelectorAll('.prompt-scrollbar-item button'));
        if(dots.length === 0) { trigger.innerText = "❌"; setTimeout(()=>trigger.innerText="🐺", 2000); return; }
        
        trigger.innerText = "⏳"; trigger.style.borderColor = RED;

        for (let i = 0; i < dots.length; i++) {
            const dot = dots[i];
            dot.scrollIntoView({ block: "center", behavior: "instant" });
            dot.click();
            const targetId = dot.getAttribute("aria-controls");
            if(targetId && await waitForHydration(targetId)) {
                scanBlock(i);
                dot.style.backgroundColor = GREEN;
                const inner = dot.querySelector('.prompt-scrollbar-dot');
                if(inner) inner.style.backgroundColor = GREEN;
            }
            await new Promise(r => setTimeout(r, 150));
        }
        trigger.innerText = "✅"; trigger.style.borderColor = GREEN; setTimeout(() => trigger.innerText = "🐺", 4000);
    }

    function waitForHydration(id) {
        return new Promise(r => {
            let n = 0;
            const i = setInterval(() => {
                n++; const el = document.getElementById(id);
                if((el && el.offsetHeight > 10) || n > 60) { clearInterval(i); r(true); }
            }, 100);
        });
    }

    const observer = new MutationObserver(() => scanBlock(-1));
    observer.observe(document.body, { childList: true, subtree: true });

    // SANITIZER
    function cleanCode(raw) {
        let lines = raw.split('\n');
        if (lines.length > 0 && lines[0].trim().startsWith("```")) lines.shift();
        if (lines.length > 0 && lines[lines.length-1].trim().startsWith("```")) lines.pop();
        return lines.join('\n').replace(/```/g, "'''"); 
    }

    function scanBlock(seq) {
        let title = "Untitled";
        const tEl = document.querySelector('h1.mode-title');
        if(tEl) title = tEl.innerText.trim();
        
        document.querySelectorAll('pre').forEach(b => {
            if(!b.dataset.hasSouthpaw) { injectSouthpaw(b); b.dataset.hasSouthpaw = "true"; }
            if(b.dataset.sent) return;
            if(b.offsetHeight < 10) return;
            
            const code = cleanCode(b.innerText);
            const fname = detectFilename(code) || `snippet_${Date.now()}.txt`;
            
            GM_xmlhttpRequest({
                method: "POST", url: C2_URL, headers: { "Content-Type": "application/json" },
                data: JSON.stringify({ uuid: getUUID(), title: title, platform: "AI Studio", sequence_index: (seq === -1 ? 999 : seq), filename: fname, content: code, type: detectType(fname) }),
                onload: () => {}, onerror: () => {}
            });
            b.dataset.sent = "true";
        });
    }

    function injectSouthpaw(preBlock) {
        if (getComputedStyle(preBlock).position === 'static') preBlock.style.position = 'relative';
        
        // BOTTOM RIGHT GLASS HUD
        const bar = document.createElement("div");
        bar.style.cssText = "position: absolute; bottom: 0; right: 0; display: flex; gap: 8px; background: rgba(0,0,0,0.8); padding: 4px 8px; z-index: 50; border-top-left-radius: 4px; border-left: 1px solid #333; border-top: 1px solid #333;";

        const getInfo = () => {
             const raw = preBlock.innerText;
             const code = cleanCode(raw);
             const fn = detectFilename(code) || "snippet.txt";
             return { code, fn };
        };
        
        // TOGGLES
        const mkCheck = (lbl, val, cb) => {
            const sp = document.createElement("span"); 
            sp.innerText = lbl + (val ? " [x]" : " [ ]");
            sp.style.cssText = "font-size: 10px; color: #888; font-family: monospace; cursor: pointer; border-right: 1px solid #444; padding-right: 6px;";
            sp.onclick = () => { cb(!val); sp.innerText = lbl + (!val ? " [x]" : " [ ]"); };
            bar.appendChild(sp);
        };
        
        mkCheck("EOF", eofMode, (v) => { eofMode = v; localStorage.setItem("rd_eof", v); });
        mkCheck("EXEC", execMode, (v) => { execMode = v; localStorage.setItem("rd_exec", v); });

        // BUTTONS
        createBtn(bar, "📄 COPY", GREEN, () => {
            const { code, fn } = getInfo();
            let finalCode = code;
            if (eofMode) { 
                const rnd = Math.floor(Math.random() * 90000) + 10000;
                const delim = "EOF_" + rnd; 
                const echoCmd = `echo -e "\\n\\033[1;92m[🐶 ROAD DAWG]\\033[0m \\033[1;37m${fn}\\033[0m \\033[0;90mSECURED\\033[0m"`;
                finalCode = `cat << '${delim}' > "${fn}"\n${code}\n${delim}\n${echoCmd}`; 
                if (execMode) {
                    let runCmd = "";
                    if(fn.endsWith(".py")) runCmd = `python3 ${fn}`;
                    else if(fn.endsWith(".js")) runCmd = `node ${fn}`;
                    else if(fn.endsWith(".sh")) runCmd = `chmod +x ${fn} && ./${fn}`;
                    if(runCmd) finalCode += `\n${runCmd}`;
                }
            }
            GM_setClipboard(finalCode);
        });

        createBtn(bar, "▶ RUN", "#fff", () => {
            const { fn } = getInfo();
            let runCmd = `./${fn}`;
            if(fn.endsWith(".py")) runCmd = `python3 ${fn}`;
            if(fn.endsWith(".js")) runCmd = `node ${fn}`;
            GM_setClipboard(runCmd);
        });
        
        preBlock.appendChild(bar);
    }

    function createBtn(parent, text, color, action) {
        const b = document.createElement("span"); b.innerText = text;
        b.style.cssText = `font-size: 10px; font-weight: bold; font-family: monospace; cursor: pointer; color: ${color};`;
        b.onclick = () => { action(); const orig = b.innerText; b.innerText = "✔"; setTimeout(() => { b.innerText = orig; }, 500); };
        parent.appendChild(b);
    }

    function getUUID() { const m = window.location.href.match(/prompts\/([a-zA-Z0-9_-]+)/); return m ? m[1] : "unknown"; }
    function detectFilename(c) { const l = c.split('\n')[0]; if(l.includes("cat <<")) { const m = l.match(/>\s*['"]?([\w.-]+)['"]?/); if(m) return m[1]; } if(l.includes("filename:")) return l.split(":")[1].trim(); return null; }
    function detectType(f) { if(f.endsWith(".py")) return "PYTHON"; if(f.endsWith(".js")) return "JS"; if(f.endsWith(".sh")) return "BASH"; return "TXT"; }
})();
