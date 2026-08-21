/**
 * DataFlow Automator Pro - Client Application Logic
 */

// Tab Navigation
const tabTitles = {
    "overview": { title: "Overview & Telemetry", desc: "Real-time automation engine monitoring and rapid execution console" },
    "file-manager": { title: "File Automation Studio", desc: "Categorize directories, detect SHA-256 duplicates & batch rename files" },
    "excel-studio": { title: "Excel & Data Processing Studio", desc: "Ingest CSV/XLSX, auto-clean nulls & duplicates, export styled spreadsheets" },
    "pdf-studio": { title: "PDF Report & Invoice Synthesizer", desc: "Generate publication-grade PDF documents with embedded charts" },
    "web-scraper": { title: "Web Scraping Engine", desc: "Extract live e-commerce pricing, news headlines, and custom web tables" },
    "email-center": { title: "Email Automation Dispatcher", desc: "Dispatch automated reports via SMTP with Jinja2 HTML templates & attachments" },
    "pipelines": { title: "Automated Workflow Orchestrator", desc: "Chain scraping, cleaning, Excel, PDF, and email into multi-step pipelines" },
    "live-logs": { title: "Centralized Execution Logs", desc: "Live streaming log feed with rotating file storage" },
    "project-report": { title: "Official Project Report", desc: "Comprehensive technical specification and project deliverable (PDF)" }
};

function switchTab(tabId) {
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));

    const btn = document.querySelector(`.nav-item[data-tab="${tabId}"]`);
    const pane = document.getElementById(`tab-${tabId}`);

    if (btn) btn.classList.add('active');
    if (pane) pane.classList.add('active');

    if (tabTitles[tabId]) {
        document.getElementById('page-title').innerText = tabTitles[tabId].title;
        document.getElementById('page-desc').innerText = tabTitles[tabId].desc;
    }
}

document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = btn.getAttribute('data-tab');
        switchTab(tab);
    });
});

// Toast notification helper
function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    toast.innerText = message;
    toast.style.borderColor = isError ? 'var(--accent-red)' : 'var(--primary-light)';
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3500);
}

// ----------------- SYSTEM STATS & LOGS -----------------

async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        if (data.success) {
            document.getElementById('top-cpu').innerText = `${data.stats.cpu_percent}%`;
            document.getElementById('top-ram').innerText = `${data.stats.ram_percent}%`;
        }
    } catch (e) {
        // quiet fail on disconnect
    }
}

async function fetchLogs() {
    try {
        const res = await fetch('/api/logs?limit=40');
        const data = await res.json();
        if (data.success) {
            const terminal = document.getElementById('log-terminal');
            const mini = document.getElementById('mini-logs');
            
            let html = '';
            let miniHtml = '';

            data.logs.forEach(l => {
                let colorClass = 'text-cyan';
                if (l.level === 'WARNING') colorClass = 'text-purple';
                if (l.level === 'ERROR') colorClass = 'text-red';

                const line = `[${l.timestamp}] [${l.level}] ${l.message}`;
                html += `<div class="log-line ${colorClass}">${escapeHtml(line)}</div>`;
                miniHtml += `<div class="log-row ${colorClass}">${escapeHtml(line)}</div>`;
            });

            if (terminal && html) terminal.innerHTML = html;
            if (mini && miniHtml) {
                mini.innerHTML = miniHtml;
                mini.scrollTop = mini.scrollHeight;
            }
        }
    } catch (e) {}
}

async function clearLogs() {
    await fetch('/api/logs/clear', { method: 'POST' });
    document.getElementById('log-terminal').innerHTML = '<div class="log-line text-cyan">Logs cleared.</div>';
    showToast("Logs cleared.");
}

function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ----------------- FILE AUTOMATION -----------------

document.getElementById('btn-fm-scan').addEventListener('click', async () => {
    const dir = document.getElementById('fm-dir').value.trim();
    showToast("Scanning directory...");
    try {
        const res = await fetch('/api/files/scan', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ directory: dir })
        });
        const data = await res.json();
        if (data.success) {
            renderFileList(data.items);
            if (data.stats) {
                document.getElementById('fm-stats-box').style.display = 'flex';
                document.getElementById('fm-total-files').innerText = data.stats.total_files;
                document.getElementById('fm-total-size').innerText = data.stats.total_size_formatted;
                document.getElementById('fm-categories').innerText = Object.entries(data.stats.categories).map(([k, v]) => `${k}: ${v}`).join(', ');
            }
            showToast(`Found ${data.items.length} items in directory.`);
        } else {
            showToast(data.error, true);
        }
    } catch (e) {
        showToast("Directory scan error", true);
    }
});

document.getElementById('btn-fm-organize').addEventListener('click', async () => {
    const dir = document.getElementById('fm-dir').value.trim();
    const rule = document.getElementById('fm-rule').value;
    showToast("Organizing files...");
    try {
        const res = await fetch('/api/files/organize', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ source_dir: dir, rule_type: rule, dry_run: false })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Successfully organized ${data.moved_count} files.`);
            document.getElementById('btn-fm-scan').click();
        } else {
            showToast(data.error || "Organization failed", true);
        }
    } catch (e) {
        showToast("Error organizing files", true);
    }
});

document.getElementById('btn-fm-duplicates').addEventListener('click', async () => {
    const dir = document.getElementById('fm-dir').value.trim();
    showToast("Scanning SHA-256 hashes for duplicates...");
    try {
        const res = await fetch('/api/files/duplicates', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ directory: dir, delete: false })
        });
        const data = await res.json();
        if (data.success) {
            const d = data.data;
            alert(`Duplicate Scan Results:\n- Duplicate Groups: ${d.duplicate_groups_count}\n- Duplicate Files: ${d.total_duplicates_found}\n- Wasted Space: ${d.total_wasted_space}`);
            showToast(`Found ${d.total_duplicates_found} duplicates.`);
        }
    } catch (e) {
        showToast("Error scanning duplicates", true);
    }
});

function renderFileList(items) {
    const tbody = document.getElementById('fm-tbody');
    document.getElementById('fm-item-count').innerText = `${items.length} items`;
    if (!items || items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Directory is empty.</td></tr>';
        return;
    }

    let html = '';
    items.forEach(it => {
        html += `
            <tr>
                <td><b>${escapeHtml(it.name)}</b></td>
                <td><span class="badge-tag">${it.category}</span></td>
                <td>${it.size_formatted}</td>
                <td>${it.modified}</td>
                <td><span class="text-green">Ready</span></td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}

// ----------------- DATA & EXCEL STUDIO -----------------

const dropzone = document.getElementById('excel-dropzone');
const fileInput = document.getElementById('excel-file-input');

['dragenter', 'dragover'].forEach(name => {
    dropzone.addEventListener(name, (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
});
['dragleave', 'drop'].forEach(name => {
    dropzone.addEventListener(name, (e) => { e.preventDefault(); dropzone.classList.remove('dragover'); });
});
dropzone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) uploadDataFile(files[0]);
});
fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) uploadDataFile(fileInput.files[0]);
});

async function uploadDataFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    showToast(`Uploading ${file.name}...`);

    try {
        const res = await fetch('/api/data/upload', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.success) {
            renderDataSummary(data.filename, data.summary);
            showToast(`Loaded ${data.filename} successfully!`);
        } else {
            showToast(data.error, true);
        }
    } catch (e) {
        showToast("Failed to upload data file", true);
    }
}

function renderDataSummary(filename, summary) {
    document.getElementById('data-studio-controls').style.display = 'block';
    document.getElementById('ds-name').innerText = filename;
    document.getElementById('ds-rows').innerText = summary.shape.rows;
    document.getElementById('ds-cols').innerText = summary.shape.columns;

    // Chips
    const chipsContainer = document.getElementById('ds-summary-chips');
    let chipsHtml = `
        <div class="summary-chip">Rows: <b>${summary.shape.rows}</b></div>
        <div class="summary-chip">Columns: <b>${summary.shape.columns}</b></div>
        <div class="summary-chip">Memory: <b>${summary.memory_usage}</b></div>
    `;
    chipsContainer.innerHTML = chipsHtml;

    // Preview Table
    const thead = document.getElementById('ds-thead');
    const tbody = document.getElementById('ds-tbody');

    thead.innerHTML = `<tr>${summary.columns.map(c => `<th>${escapeHtml(c)}</th>`).join('')}</tr>`;
    
    let rowsHtml = '';
    summary.preview.forEach(row => {
        rowsHtml += `<tr>${summary.columns.map(c => `<td>${escapeHtml(String(row[c] ?? ''))}</td>`).join('')}</tr>`;
    });
    tbody.innerHTML = rowsHtml;
}

document.getElementById('btn-ds-clean').addEventListener('click', async () => {
    showToast("Running automated dataset cleaning...");
    try {
        const res = await fetch('/api/data/clean', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ drop_duplicates: true, standardize_names: true, fill_strategy: 'auto' })
        });
        const data = await res.json();
        if (data.success) {
            renderDataSummary("Cleaned_Dataset", data.summary);
            showToast(`Cleaned! Removed ${data.report.duplicates_removed} duplicates.`);
        }
    } catch (e) {
        showToast("Data cleaning error", true);
    }
});

document.getElementById('btn-ds-export').addEventListener('click', async () => {
    showToast("Exporting styled Excel report...");
    try {
        const res = await fetch('/api/data/export', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ title: "Automated DataFlow Report" })
        });
        const data = await res.json();
        if (data.success) {
            window.location.href = data.download_url;
            showToast("Downloaded styled Excel spreadsheet!");
        }
    } catch (e) {
        showToast("Export failed", true);
    }
});

// ----------------- PDF STUDIO -----------------

document.getElementById('btn-generate-pdf').addEventListener('click', async () => {
    const docType = document.getElementById('pdf-doc-type').value;
    const title = document.getElementById('pdf-title').value;
    const summary = document.getElementById('pdf-summary').value;

    showToast("Synthesizing high-res PDF with ReportLab...");
    try {
        const endpoint = docType === 'invoice' ? '/api/pdf/generate-invoice' : '/api/pdf/generate-report';
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ title: title, summary: summary })
        });
        const data = await res.json();
        if (data.success) {
            const wrapper = document.getElementById('pdf-viewer-wrapper');
            wrapper.innerHTML = `<iframe src="${data.download_url}" width="100%" height="100%" style="border:none;"></iframe>`;
            const dl = document.getElementById('pdf-download-link');
            dl.href = data.download_url;
            dl.style.display = 'inline-flex';
            showToast("PDF document generated successfully!");
        } else {
            showToast(data.error, true);
        }
    } catch (e) {
        showToast("Error generating PDF", true);
    }
});

// ----------------- WEB SCRAPER -----------------

document.getElementById('scraper-source').addEventListener('change', (e) => {
    document.getElementById('custom-url-group').style.display = e.target.value === 'custom' ? 'block' : 'none';
});

document.getElementById('btn-run-scrape').addEventListener('click', async () => {
    const source = document.getElementById('scraper-source').value;
    const pages = parseInt(document.getElementById('scraper-pages').value) || 1;
    const url = document.getElementById('scraper-url').value.trim();

    showToast("Scraping live data with retry backoff...");
    try {
        const res = await fetch('/api/scrape', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ source, pages, url })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Scraped ${data.records_count || 1} records!`);
            document.getElementById('scrape-results-card').style.display = 'block';
            document.getElementById('scrape-record-count').innerText = `${data.records_count} records`;

            if (data.summary) {
                const thead = document.getElementById('scrape-thead');
                const tbody = document.getElementById('scrape-tbody');
                thead.innerHTML = `<tr>${data.summary.columns.map(c => `<th>${escapeHtml(c)}</th>`).join('')}</tr>`;
                let html = '';
                data.summary.preview.forEach(row => {
                    html += `<tr>${data.summary.columns.map(c => `<td>${escapeHtml(String(row[c] ?? ''))}</td>`).join('')}</tr>`;
                });
                tbody.innerHTML = html;
            }
        } else {
            showToast(data.error, true);
        }
    } catch (e) {
        showToast("Web scraping failed", true);
    }
});

// ----------------- EMAIL CENTER -----------------

document.getElementById('btn-send-email').addEventListener('click', async () => {
    const to = document.getElementById('email-to').value.trim();
    const subject = document.getElementById('email-subject').value.trim();
    const template = document.getElementById('email-template').value;
    const message = document.getElementById('email-body').value.trim();
    const mock = document.getElementById('email-mock-mode').checked;

    showToast("Dispatching automated email...");
    try {
        const res = await fetch('/api/email/send', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ to_email: to, subject, template, message, mock_mode: mock })
        });
        const data = await res.json();
        if (data.success) {
            showToast("Email dispatched successfully!");
            fetchEmailHistory();
        } else {
            showToast(data.error, true);
        }
    } catch (e) {
        showToast("Email dispatch error", true);
    }
});

async function fetchEmailHistory() {
    try {
        const res = await fetch('/api/email/history');
        const data = await res.json();
        if (data.success) {
            const list = document.getElementById('email-history-list');
            if (data.emails.length === 0) {
                list.innerHTML = '<div class="text-muted text-center" style="padding: 40px;">No sent emails recorded yet.</div>';
                return;
            }
            let html = '';
            data.emails.forEach(m => {
                html += `
                    <div class="card" style="padding: 12px; margin-bottom: 10px;">
                        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                            <b>${escapeHtml(m.subject)}</b>
                            <span class="badge-tag">${m.status}</span>
                        </div>
                        <div style="font-size: 11px; color: var(--text-dim);">To: ${m.to.join(', ')} | ${m.timestamp}</div>
                    </div>
                `;
            });
            list.innerHTML = html;
        }
    } catch (e) {}
}

// ----------------- PIPELINE RUNNER -----------------

async function runPipeline(pipeName) {
    showToast(`Executing ${pipeName.toUpperCase()} end-to-end pipeline...`);
    const statusCard = document.getElementById('pipeline-status-card');
    const stepsList = document.getElementById('pipe-steps-list');
    statusCard.style.display = 'block';
    stepsList.innerHTML = '<div class="log-line text-cyan">Starting pipeline steps...</div>';

    try {
        const res = await fetch('/api/pipeline/run', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ pipeline: pipeName })
        });
        const data = await res.json();
        if (data.success) {
            let html = '';
            data.result.steps.forEach(s => {
                html += `<div class="card" style="padding: 10px; margin-bottom: 8px;">✓ <b>${s.step}</b> - <span class="text-green">${s.status}</span></div>`;
            });
            stepsList.innerHTML = html;
            showToast("Pipeline completed successfully!");
        } else {
            showToast(data.error, true);
        }
    } catch (e) {
        showToast("Pipeline failed", true);
    }
}

document.getElementById('btn-quick-pipeline').addEventListener('click', () => {
    switchTab('pipelines');
    runPipeline('ecommerce');
});

// Periodic Pollers
setInterval(fetchStats, 3000);
setInterval(fetchLogs, 2500);
fetchStats();
fetchLogs();
fetchEmailHistory();
