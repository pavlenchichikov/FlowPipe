/* ── FlowPipe Frontend ─────────────────────────────────────── */

let editor;
let nodeTypes = [];
let selectedNodeId = null;
let lastRunResult = null;
let generatedCode = "";

/* ── Drawflow init ────────────────────────────────────────── */

document.addEventListener("DOMContentLoaded", async () => {
    const container = document.getElementById("drawflow");
    editor = new Drawflow(container);
    editor.reroute = true;
    editor.start();

    editor.on("nodeSelected", (id) => {
        selectedNodeId = id;
        renderProperties(id);
    });

    editor.on("nodeUnselected", () => {
        selectedNodeId = null;
        document.getElementById("properties").innerHTML =
            '<div class="empty">Select a node to edit its properties</div>';
    });

    editor.on("nodeRemoved", () => {
        selectedNodeId = null;
        document.getElementById("properties").innerHTML =
            '<div class="empty">Select a node to edit its properties</div>';
    });

    await loadNodeTypes();
    renderSidebar();
});

/* ── Load node types from API ─────────────────────────────── */

async function loadNodeTypes() {
    const res = await fetch("/api/nodes");
    nodeTypes = await res.json();
}

/* ── Sidebar rendering ────────────────────────────────────── */

function renderSidebar() {
    const sidebar = document.getElementById("sidebar");
    const categories = { source: [], transform: [], destination: [] };

    nodeTypes.forEach(n => {
        const cat = categories[n.category] || [];
        cat.push(n);
        categories[n.category] = cat;
    });

    const catLabels = { source: "Sources", transform: "Transforms", destination: "Destinations" };
    let html = "";

    for (const [cat, items] of Object.entries(categories)) {
        if (items.length === 0) continue;
        html += `<h3>${catLabels[cat] || cat}</h3>`;
        items.forEach(n => {
            html += `<div class="node-item cat-${cat}" draggable="true"
                          ondragstart="dragNode(event, '${n.type}')"
                          ondblclick="addNodeToCanvas('${n.type}')">
                <div>${n.display_name}</div>
                <div class="desc">${n.description}</div>
            </div>`;
        });
    }

    sidebar.innerHTML = html;
}

/* ── Drag & drop ──────────────────────────────────────────── */

function dragNode(ev, type) {
    ev.dataTransfer.setData("nodeType", type);
}

document.addEventListener("drop", (ev) => {
    if (ev.target.closest(".canvas-area")) {
        ev.preventDefault();
        const type = ev.dataTransfer.getData("nodeType");
        if (type) addNodeAtPos(type, ev.clientX, ev.clientY);
    }
});

document.addEventListener("dragover", (ev) => {
    if (ev.target.closest(".canvas-area")) ev.preventDefault();
});

/* ── Add node to canvas ───────────────────────────────────── */

function addNodeToCanvas(type) {
    addNodeAtPos(type, 400, 300);
}

function addNodeAtPos(type, x, y) {
    const spec = nodeTypes.find(n => n.type === type);
    if (!spec) return;

    const cat = spec.category;
    const inputs = cat === "source" ? 0 : (type === "JoinTables" ? 2 : 1);
    const outputs = cat === "destination" ? 0 : 1;

    const defaults = {};
    (spec.params || []).forEach(p => {
        defaults[p.name] = p.default || "";
    });

    const htmlContent = `
        <div class="title-box ${cat}">${spec.display_name}</div>
        <div class="box">${spec.description}</div>
    `;

    const rect = document.getElementById("drawflow").getBoundingClientRect();
    const posX = (x - rect.left) / editor.zoom - editor.precanvas.getBoundingClientRect().left / editor.zoom + editor.canvas_x;
    const posY = (y - rect.top) / editor.zoom - editor.precanvas.getBoundingClientRect().top / editor.zoom + editor.canvas_y;

    editor.addNode(
        type,
        inputs, outputs,
        posX, posY,
        cat,
        { params: defaults, nodeType: type, displayName: spec.display_name },
        htmlContent
    );
}

/* ── Properties panel ─────────────────────────────────────── */

function renderProperties(nodeId) {
    const panel = document.getElementById("properties");
    const nodeData = editor.getNodeFromId(nodeId);
    if (!nodeData) return;

    const type = nodeData.data.nodeType;
    const spec = nodeTypes.find(n => n.type === type);
    if (!spec) return;

    const params = nodeData.data.params || {};

    let html = `<h2>${spec.display_name}</h2>`;

    (spec.params || []).forEach(p => {
        const val = params[p.name] !== undefined ? params[p.name] : (p.default || "");
        html += `<div class="form-group"><label>${p.label}</label>`;

        if (p.type === "select") {
            html += `<select onchange="updateParam(${nodeId}, '${p.name}', this.value)">`;
            (p.options || []).forEach(opt => {
                html += `<option value="${opt}" ${val === opt ? "selected" : ""}>${opt}</option>`;
            });
            html += `</select>`;
        } else if (p.type === "textarea") {
            html += `<textarea onchange="updateParam(${nodeId}, '${p.name}', this.value)"
                        placeholder="${p.placeholder || ''}">${val}</textarea>`;
        } else if (p.type === "file") {
            html += `<input type="text" value="${val}"
                        onchange="updateParam(${nodeId}, '${p.name}', this.value)"
                        placeholder="filename (upload first)">`;
            html += `<div style="margin-top:4px;font-size:11px;color:var(--text-dim)">
                Upload files via the header button</div>`;
        } else {
            html += `<input type="${p.type === 'number' ? 'number' : 'text'}" value="${val}"
                        onchange="updateParam(${nodeId}, '${p.name}', this.value)"
                        placeholder="${p.placeholder || ''}">`;
        }

        html += `</div>`;
    });

    panel.innerHTML = html;
}

function updateParam(nodeId, paramName, value) {
    const nodeData = editor.getNodeFromId(nodeId);
    if (nodeData) {
        nodeData.data.params[paramName] = value;
    }
}

/* ── Build pipeline payload ───────────────────────────────── */

function buildPipelinePayload() {
    const exportData = editor.export();
    const moduleData = exportData.drawflow.Home.data;
    const nodes = [];
    const edges = [];

    for (const [id, node] of Object.entries(moduleData)) {
        nodes.push({
            id: `n${id}`,
            type: node.data.nodeType,
            params: node.data.params || {},
        });

        for (const [, conns] of Object.entries(node.outputs)) {
            for (const conn of conns.connections) {
                edges.push({
                    source: `n${id}`,
                    target: `n${conn.node}`,
                });
            }
        }
    }

    return { nodes, edges };
}

/* ── Run pipeline ─────────────────────────────────────────── */

async function runPipeline() {
    const payload = buildPipelinePayload();
    if (payload.nodes.length === 0) {
        alert("Add some nodes to the canvas first!");
        return;
    }

    const statsBar = document.getElementById("stats-bar");
    statsBar.innerHTML = '<span>Running...</span>';

    try {
        const res = await fetch("/api/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        lastRunResult = await res.json();
        renderPreview();
        renderStats();
    } catch (err) {
        statsBar.innerHTML = `<span class="err">Error: ${err.message}</span>`;
    }
}

/* ── Render preview table ─────────────────────────────────── */

function renderPreview() {
    if (!lastRunResult || !lastRunResult.nodes) return;

    const content = document.getElementById("tab-content");
    const lastNode = lastRunResult.nodes[lastRunResult.nodes.length - 1];

    if (lastNode.error) {
        content.innerHTML = `<div class="err" style="padding:12px">Error at ${lastNode.node_type}: ${lastNode.error}</div>`;
        return;
    }

    if (!lastNode.preview || lastNode.preview.length === 0) {
        content.innerHTML = '<div class="empty" style="margin-top:20px">No data to preview</div>';
        return;
    }

    const cols = Object.keys(lastNode.preview[0]);
    let html = '<table class="data-table"><thead><tr>';
    cols.forEach(c => html += `<th>${c}</th>`);
    html += '</tr></thead><tbody>';

    lastNode.preview.forEach(row => {
        html += '<tr>';
        cols.forEach(c => html += `<td>${row[c] !== null ? row[c] : ''}</td>`);
        html += '</tr>';
    });

    html += '</tbody></table>';
    content.innerHTML = html;
}

function renderStats() {
    if (!lastRunResult) return;
    const bar = document.getElementById("stats-bar");
    const ok = lastRunResult.success;
    const last = lastRunResult.nodes[lastRunResult.nodes.length - 1];
    const nodesCount = lastRunResult.nodes.length;

    bar.innerHTML = `
        <span class="${ok ? 'ok' : 'err'}">${ok ? 'Success' : 'Failed'}</span>
        <span>Nodes: ${nodesCount}</span>
        <span>Rows: ${last.rows}</span>
        <span>Columns: ${last.columns}</span>
        <span>Time: ${lastRunResult.total_ms}ms</span>
    `;
}

/* ── Export Python code ───────────────────────────────────── */

async function exportCode() {
    const payload = buildPipelinePayload();
    if (payload.nodes.length === 0) {
        alert("Add some nodes first!");
        return;
    }

    try {
        const res = await fetch("/api/codegen", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await res.json();
        generatedCode = data.script || data.error;

        // Switch to code tab
        document.querySelectorAll(".bottom-panel .tab").forEach(t => t.classList.remove("active"));
        document.querySelector('.tab[data-tab="code"]').classList.add("active");
        document.getElementById("tab-content").innerHTML =
            `<div class="code-block">${escapeHtml(generatedCode)}</div>
             <div style="margin-top:8px">
                <button class="btn" onclick="copyCode()">Copy to Clipboard</button>
                <button class="btn" onclick="downloadCode()">Download .py</button>
             </div>`;
    } catch (err) {
        alert("Error generating code: " + err.message);
    }
}

function copyCode() {
    navigator.clipboard.writeText(generatedCode);
}

function downloadCode() {
    const blob = new Blob([generatedCode], { type: "text/plain" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "pipeline.py";
    a.click();
}

/* ── Tab switching ────────────────────────────────────────── */

function switchTab(el) {
    document.querySelectorAll(".bottom-panel .tab").forEach(t => t.classList.remove("active"));
    el.classList.add("active");
    const tab = el.dataset.tab;

    const content = document.getElementById("tab-content");

    if (tab === "preview") {
        if (lastRunResult) renderPreview();
        else content.innerHTML = '<div class="empty" style="margin-top:20px">Run the pipeline to see results</div>';
    } else if (tab === "code") {
        if (generatedCode) {
            content.innerHTML =
                `<div class="code-block">${escapeHtml(generatedCode)}</div>
                 <div style="margin-top:8px">
                    <button class="btn" onclick="copyCode()">Copy to Clipboard</button>
                    <button class="btn" onclick="downloadCode()">Download .py</button>
                 </div>`;
        } else {
            content.innerHTML = '<div class="empty" style="margin-top:20px">Click "Export Python" to generate code</div>';
        }
    } else if (tab === "log") {
        if (lastRunResult) {
            let html = '<div style="font-family:monospace;font-size:12px">';
            lastRunResult.nodes.forEach(n => {
                const icon = n.error ? '<span class="err">[FAIL]</span>' : '<span class="ok">[OK]</span>';
                html += `<div>${icon} ${n.node_type} — ${n.rows} rows, ${n.columns} cols, ${n.elapsed_ms}ms`;
                if (n.error) html += ` <span class="err">${n.error}</span>`;
                html += `</div>`;
            });
            html += '</div>';
            content.innerHTML = html;
        } else {
            content.innerHTML = '<div class="empty" style="margin-top:20px">No run log yet</div>';
        }
    }
}

/* ── File upload ──────────────────────────────────────────── */

function uploadFileDialog() {
    document.getElementById("file-input").click();
}

async function handleFileUpload(input) {
    const file = input.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/api/upload", { method: "POST", body: formData });
        const data = await res.json();
        alert(`File uploaded: ${data.filename} (${(data.size / 1024).toFixed(1)} KB)`);
    } catch (err) {
        alert("Upload failed: " + err.message);
    }

    input.value = "";
}

/* ── Schedule ─────────────────────────────────────────────── */

function schedulePipeline() {
    const payload = buildPipelinePayload();
    if (payload.nodes.length === 0) {
        alert("Add some nodes first!");
        return;
    }

    const modal = document.getElementById("modal-root");
    modal.innerHTML = `
        <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
            <div class="modal">
                <h2>Schedule Pipeline</h2>
                <div class="form-group">
                    <label>Name</label>
                    <input type="text" id="sched-name" placeholder="My ETL Job">
                </div>
                <div class="form-group">
                    <label>Cron Expression</label>
                    <input type="text" id="sched-cron" placeholder="0 8 * * *" value="0 8 * * *">
                    <div style="font-size:11px;color:var(--text-dim);margin-top:4px">
                        min hour day month weekday (e.g. "0 8 * * *" = daily at 8:00)
                    </div>
                </div>
                <div class="btn-row">
                    <button class="btn" onclick="closeModal()">Cancel</button>
                    <button class="btn btn-primary" onclick="saveSchedule()">Save Schedule</button>
                </div>
            </div>
        </div>
    `;
}

async function saveSchedule() {
    const name = document.getElementById("sched-name").value || "Untitled";
    const cron = document.getElementById("sched-cron").value || "0 8 * * *";
    const pipeline = buildPipelinePayload();

    try {
        await fetch("/api/schedules", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, cron, pipeline }),
        });
        alert(`Schedule "${name}" created (${cron})`);
        closeModal();
    } catch (err) {
        alert("Failed to save schedule: " + err.message);
    }
}

function closeModal() {
    document.getElementById("modal-root").innerHTML = "";
}

/* ── Clear canvas ─────────────────────────────────────────── */

function clearCanvas() {
    if (confirm("Clear all nodes from the canvas?")) {
        editor.clear();
        selectedNodeId = null;
        document.getElementById("properties").innerHTML =
            '<div class="empty">Select a node to edit its properties</div>';
    }
}

/* ── Utility ──────────────────────────────────────────────── */

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}
