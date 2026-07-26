"use strict";

const $ = (id) => document.getElementById(id);

function api(path, body) {
    return fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body || {}),
    }).then((r) => r.json());
}

function fmtSpeed(bytesPerSec) {
    if (!bytesPerSec) return "";
    const mb = bytesPerSec / (1024 * 1024);
    return mb >= 1 ? `${mb.toFixed(1)} MB/s` : `${(bytesPerSec / 1024).toFixed(0)} KB/s`;
}

// Format a number of seconds as a timestamp (h:mm:ss or m:ss).
function fmtTimestamp(seconds) {
    const total = Math.max(0, Math.floor(seconds || 0));
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    const pad = (n) => String(n).padStart(2, "0");
    return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}

// Format a duration in seconds as human-readable parts, e.g. "2 min, 34 sec".
function fmtDuration(seconds) {
    const total = Math.max(0, Math.floor(seconds || 0));
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    const parts = [];
    if (h > 0) parts.push(`${h} hr`);
    if (m > 0) parts.push(`${m} min`);
    if (s > 0 || !parts.length) parts.push(`${s} sec`);
    return parts.join(", ");
}

// Render the chapter list (with timestamps) inside the video info card.
// Also toggles the "Split into chapters" checkbox — only shown when chapters exist.
function renderVideoChapters(chapters) {
    const box = $("video-chapters-box");
    const list = $("video-chapters-list");
    const splitLabel = $("video-split-label");
    list.innerHTML = "";
    if (!chapters || !chapters.length) {
        box.classList.add("hidden");
        box.open = false;
        splitLabel.classList.add("hidden");
        $("video-split").checked = false;
        return;
    }
    $("video-chapters-summary").textContent = `${chapters.length} chapters`;
    chapters.forEach((ch) => {
        const li = document.createElement("li");
        const time = document.createElement("span");
        time.className = "ch-time";
        time.textContent = fmtTimestamp(ch.start_time);
        const title = document.createElement("span");
        title.className = "ch-title";
        title.textContent = ch.title;
        const dur = document.createElement("span");
        dur.className = "ch-dur";
        dur.textContent = fmtDuration(ch.end_time - ch.start_time);
        li.appendChild(time);
        li.appendChild(title);
        li.appendChild(dur);
        list.appendChild(li);
    });
    box.classList.remove("hidden");
    box.open = true;
    splitLabel.classList.remove("hidden");
}

function fillSubtitleSelect(select, langs) {
    select.innerHTML = "";
    const none = document.createElement("option");
    none.value = "";
    none.textContent = "None";
    select.appendChild(none);
    (langs || []).forEach((lang) => {
        const opt = document.createElement("option");
        opt.value = lang;
        opt.textContent = lang;
        select.appendChild(opt);
    });
}

// ------------------------------------------------------------------ //
// Tabs
// ------------------------------------------------------------------ //
document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
        document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
        document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
        tab.classList.add("active");
        $("tab-" + tab.dataset.tab).classList.add("active");
    });
});

// ------------------------------------------------------------------ //
// Metadata + defaults
// ------------------------------------------------------------------ //
let defaultSavePath = "";
fetch("/api/metadata")
    .then((r) => r.json())
    .then((meta) => {
        $("app-name").textContent = meta.name || "Youtube Downloader";
        const dev = (meta.author && meta.author.name) || "";
        $("app-meta").textContent = `v${meta.version || "?"}${dev ? " · " + dev : ""}`;
        document.title = meta.name || document.title;
        defaultSavePath = meta.default_save_path || "";
        $("video-folder").value = defaultSavePath;
        $("pl-folder").value = defaultSavePath;
    });

// ------------------------------------------------------------------ //
// Update check (shows a dialog when GitHub has a newer version)
// ------------------------------------------------------------------ //
fetch("/api/check-update")
    .then((r) => r.json())
    .then((info) => {
        if (!info || !info.update_available) return;
        $("update-latest").textContent = "v" + info.latest_version;
        $("update-current").textContent = "v" + info.current_version;
        if (info.download_url) $("update-download").href = info.download_url;
        $("update-modal").classList.remove("hidden");
    })
    .catch(() => {});

$("update-later").addEventListener("click", () => $("update-modal").classList.add("hidden"));
$("update-download").addEventListener("click", () => $("update-modal").classList.add("hidden"));

// ------------------------------------------------------------------ //
// Shared job runner (SSE)
// ------------------------------------------------------------------ //
function runJob(endpoint, payload, ui) {
    ui.progress.classList.remove("hidden");
    ui.open.classList.add("hidden");
    ui.status.classList.remove("done");
    ui.bar.style.width = "0%";
    ui.status.textContent = "Starting…";
    if (ui.results) {
        ui.results.innerHTML = "";
        ui.rows = {};
    }
    ui.download.disabled = true;

    api(endpoint, payload).then(({ job_id, error }) => {
        if (error || !job_id) {
            ui.status.textContent = error || "Could not start download";
            ui.download.disabled = false;
            return;
        }
        streamJob(job_id, ui);
    });
}

function streamJob(job_id, ui) {
    const es = new EventSource("/api/progress/" + job_id);
    es.onmessage = (e) => {
        const ev = JSON.parse(e.data);
        if (ev.type === "progress") {
            ui.bar.style.width = (ev.percent || 0) + "%";
            ui.status.textContent =
                ev.stage === "processing"
                    ? "Processing…"
                    : `Downloading… ${ev.percent || 0}%` + (ev.speed ? ` (${fmtSpeed(ev.speed)})` : "");
        } else if (ev.type === "status") {
            ui.status.textContent = ev.message;
        } else if (ev.type === "video") {
            if (ui.results) setVideoRow(ui, ev.index, ev.title, "downloading");
            ui.bar.style.width = "0%";
            ui.status.textContent = `[${ev.index}/${ev.total}] ${ev.title}`;
        } else if (ev.type === "video_result") {
            if (ui.results) setVideoRow(ui, ev.index, ev.title, ev.success ? "success" : "failed", ev);
        } else if (ev.type === "error") {
            ui.status.textContent = "Error: " + ev.message;
            ui.download.disabled = false;
            es.close();
        } else if (ev.type === "done") {
            ui.bar.style.width = "100%";
            const failed = (ev.failed_videos && ev.failed_videos.length) || 0;
            ui.status.textContent = failed ? `Done — ${failed} failed (retry below)` : "Done!";
            ui.status.classList.add("done");
            if (ev.output_path) {
                ui.open.dataset.path = ev.output_path;
                ui.open.classList.remove("hidden");
            }
            ui.download.disabled = false;
            es.close();
        }
    };
    es.onerror = () => {
        ui.download.disabled = false;
        es.close();
    };
}

// Create/update a per-video result row (playlist). `ev` carries url/id/save_path/error.
function setVideoRow(ui, index, title, status, ev) {
    let row = ui.rows[index];
    if (!row) {
        row = document.createElement("li");
        row.innerHTML =
            '<span class="r-status"></span>' +
            '<span class="r-title"></span>' +
            '<span class="r-error"></span>' +
            '<button class="btn ghost r-retry hidden">Retry</button>';
        ui.results.appendChild(row);
        ui.rows[index] = row;
    }
    row.className = "result-row " + status;
    // row.querySelector(".r-title").textContent = `${index}. ${title}`;
    row.querySelector(".r-title").textContent = `${title}`;
    const statusEl = row.querySelector(".r-status");
    const errorEl = row.querySelector(".r-error");
    const retryBtn = row.querySelector(".r-retry");

    if (status === "success") {
        statusEl.textContent = "✓";
        errorEl.textContent = "";
        retryBtn.classList.add("hidden");
    } else if (status === "failed") {
        statusEl.textContent = "✗";
        errorEl.textContent = (ev && ev.error) || "download failed";
        retryBtn.classList.remove("hidden");
        retryBtn.dataset.url = (ev && ev.url) || "";
        retryBtn.dataset.id = (ev && ev.id) || "";
        retryBtn.dataset.title = title;
        retryBtn.dataset.savePath = (ev && ev.save_path) || "";
        retryBtn.dataset.index = index;
    } else {
        // downloading / retrying
        statusEl.textContent = "⏳";
        errorEl.textContent = status === "retrying" ? "retrying…" : "";
        retryBtn.classList.add("hidden");
    }
}

// Retry a single failed playlist video (uses the persistent playlist UI state).
function retryVideo(btn) {
    const index = parseInt(btn.dataset.index, 10);
    const retryData = {
        url: btn.dataset.url,
        id: btn.dataset.id,
        title: btn.dataset.title,
        save_path: btn.dataset.savePath,
    };
    setVideoRow(plUi, index, retryData.title, "retrying");
    const fail = (message) =>
        setVideoRow(plUi, index, retryData.title, "failed", { ...retryData, error: message });

    api("/api/retry-video", { ...retryData, subtitle_language: $("pl-subs").value }).then(
        ({ job_id, error }) => {
            if (error || !job_id) return fail(error || "retry failed");
            const es = new EventSource("/api/progress/" + job_id);
            es.onmessage = (e) => {
                const ev = JSON.parse(e.data);
                if (ev.type === "progress") {
                    const row = plUi.rows[index];
                    if (row) row.querySelector(".r-error").textContent = `retrying… ${ev.percent || 0}%`;
                } else if (ev.type === "done") {
                    setVideoRow(plUi, index, retryData.title, ev.success ? "success" : "failed",
                        { ...retryData, error: ev.error });
                    es.close();
                } else if (ev.type === "error") {
                    fail(ev.message);
                    es.close();
                }
            };
            es.onerror = () => es.close();
        }
    );
}

function wireBrowse(buttonId, inputId) {
    $(buttonId).addEventListener("click", () => {
        api("/api/pick-folder").then(({ path }) => {
            if (path) $(inputId).value = path;
        });
    });
}

function renderPlaylistVideos(videos) {
    const list = $("pl-videos");
    list.innerHTML = "";
    videos.forEach((v) => {
        const li = document.createElement("li");
        const check = document.createElement("input");
        check.type = "checkbox";
        check.className = "v-check";
        check.checked = true;
        check.dataset.index = v.index;
        check.addEventListener("change", updateSelection);
        li.appendChild(check);
        if (v.thumbnail) {
            const img = document.createElement("img");
            img.src = v.thumbnail;
            img.className = "v-thumb";
            img.alt = "";
            li.appendChild(img);
        }
        const body = document.createElement("span");
        body.className = "v-body";
        const title = document.createElement("span");
        title.className = "v-title";
        // title.textContent = `${v.index}. ${v.title}`;
        title.textContent = v.title;
        const meta = document.createElement("span");
        meta.className = "v-meta";
        meta.textContent = v.length + (v.chapters ? ` · ${v.chapters} chapters` : "");
        body.appendChild(title);
        body.appendChild(meta);
        li.appendChild(body);
        list.appendChild(li);
    });
    updateSelection();
}

// All per-video selection checkboxes in the playlist list.
function plChecks() {
    return Array.from(document.querySelectorAll("#pl-videos .v-check"));
}

// 1-based indices of the currently selected playlist videos.
function selectedIndices() {
    return plChecks()
        .filter((c) => c.checked)
        .map((c) => Number.parseInt(c.dataset.index, 10));
}

// Sync the "Select all" checkbox, selected-count label, and Download button.
function updateSelection() {
    const checks = plChecks();
    const selected = checks.filter((c) => c.checked).length;
    const total = checks.length;
    const master = $("pl-select-all");
    master.checked = selected === total && total > 0;
    master.indeterminate = selected > 0 && selected < total;
    $("pl-selected-count").textContent = `${selected} of ${total} selected`;
    $("pl-download").disabled = selected === 0;
}

function wireOpen(buttonId) {
    $(buttonId).addEventListener("click", (e) => {
        const path = e.target.dataset.path;
        if (path) api("/api/open-folder", { path });
    });
}

// ------------------------------------------------------------------ //
// Video tab
// ------------------------------------------------------------------ //
$("video-fetch").addEventListener("click", () => {
    const url = $("video-url").value.trim();
    if (!url) return;
    $("video-error").classList.add("hidden");
    $("video-info").classList.add("hidden");
    $("video-fetch").disabled = true;
    $("video-fetch").textContent = "Fetching…";
    api("/api/video-info", { url })
        .then((info) => {
            if (info.error) {
                $("video-error").textContent = info.error;
                $("video-error").classList.remove("hidden");
                return;
            }
            $("video-title").textContent = info.title;
            $("video-duration").textContent = info.length;
            $("video-chapters").textContent =
                info.chapters && info.chapters.length ? `· ${info.chapters.length} chapters` : "";
            renderVideoChapters(info.chapters);
            $("video-thumb").src = info.thumbnail || "";
            fillSubtitleSelect($("video-subs"), info.transcript_list);
            $("video-info").classList.remove("hidden");
        })
        .finally(() => {
            $("video-fetch").disabled = false;
            $("video-fetch").textContent = "Fetch";
        });
});

$("video-download").addEventListener("click", () => {
    runJob(
        "/api/download-video",
        {
            url: $("video-url").value.trim(),
            subtitle_language: $("video-subs").value,
            split_chapters: $("video-split").checked,
            save_path: $("video-folder").value.trim(),
        },
        {
            progress: $("video-progress"),
            bar: $("video-bar"),
            status: $("video-status"),
            open: $("video-open"),
            download: $("video-download"),
        }
    );
});

wireBrowse("video-browse", "video-folder");
wireOpen("video-open");

// ------------------------------------------------------------------ //
// Playlist tab
// ------------------------------------------------------------------ //
$("pl-fetch").addEventListener("click", () => {
    const url = $("pl-url").value.trim();
    if (!url) return;
    $("pl-error").classList.add("hidden");
    $("pl-info").classList.add("hidden");
    $("pl-fetch").disabled = true;
    $("pl-fetch").textContent = "Fetching…";
    api("/api/playlist-info", { url })
        .then((info) => {
            if (info.error) {
                $("pl-error").textContent = info.error;
                $("pl-error").classList.remove("hidden");
                return;
            }
            $("pl-title").textContent = info.title;
            $("pl-count").textContent = `${info.number_videos} videos`;
            $("pl-duration").textContent = info.length;
            renderPlaylistVideos(info.videos || []);
            fillSubtitleSelect($("pl-subs"), info.transcript_list);
            $("pl-info").classList.remove("hidden");
        })
        .finally(() => {
            $("pl-fetch").disabled = false;
            $("pl-fetch").textContent = "Fetch";
        });
});

// Persistent playlist UI state (shared by download + per-video retry).
const plUi = {
    progress: $("pl-progress"),
    bar: $("pl-bar"),
    status: $("pl-status"),
    open: $("pl-open"),
    results: $("pl-results"),
    download: $("pl-download"),
    rows: {},
};

// "Select all" toggles every per-video checkbox.
$("pl-select-all").addEventListener("change", (e) => {
    plChecks().forEach((c) => {
        c.checked = e.target.checked;
    });
    updateSelection();
});

$("pl-download").addEventListener("click", () => {
    const selected = selectedIndices();
    if (!selected.length) return;
    runJob(
        "/api/download-playlist",
        {
            url: $("pl-url").value.trim(),
            subtitle_language: $("pl-subs").value,
            numerate: $("pl-numerate").checked,
            save_path: $("pl-folder").value.trim(),
            // Omit when every video is selected — the backend treats that as "all".
            selected_indices: selected.length === plChecks().length ? null : selected,
        },
        plUi
    );
});

// Retry buttons are created dynamically -> delegate the click.
$("pl-results").addEventListener("click", (e) => {
    const btn = e.target.closest(".r-retry");
    if (btn) retryVideo(btn);
});

wireBrowse("pl-browse", "pl-folder");
wireOpen("pl-open");

// ------------------------------------------------------------------ //
// System logs panel
// ------------------------------------------------------------------ //
let logsRefreshTimer = null;

function loadLogs() {
    const content = $("logs-content");
    return fetch("/api/logs")
        .then((r) => r.json())
        .then((data) => {
            if (data.error) {
                content.textContent = "Could not load logs: " + data.error;
                return;
            }
            const wasAtBottom =
                content.scrollTop + content.clientHeight >= content.scrollHeight - 20;
            content.textContent = (data.lines || []).join("\n") || "(no log entries yet)";
            if (wasAtBottom) content.scrollTop = content.scrollHeight;
        })
        .catch((e) => {
            content.textContent = "Could not load logs: " + e;
        });
}

function setLogsOpen(open) {
    const panel = $("logs-panel");
    panel.classList.toggle("hidden", !open);
    document.body.classList.toggle("logs-open", open);
    $("logs-toggle").classList.toggle("active", open);
    if (open) {
        loadLogs().then(() => {
            const content = $("logs-content");
            content.scrollTop = content.scrollHeight;
        });
    } else if (logsRefreshTimer) {
        clearInterval(logsRefreshTimer);
        logsRefreshTimer = null;
        $("logs-autorefresh").checked = false;
    }
}

$("logs-toggle").addEventListener("click", () =>
    setLogsOpen($("logs-panel").classList.contains("hidden"))
);
$("logs-close").addEventListener("click", () => setLogsOpen(false));
$("logs-refresh").addEventListener("click", loadLogs);
$("logs-clear").addEventListener("click", () => {
    const btn = $("logs-clear");
    btn.disabled = true;
    api("/api/logs/clear")
        .then(() => loadLogs())
        .finally(() => {
            btn.disabled = false;
        });
});
$("logs-autorefresh").addEventListener("change", (e) => {
    if (e.target.checked) {
        logsRefreshTimer = setInterval(loadLogs, 1000);
    } else if (logsRefreshTimer) {
        clearInterval(logsRefreshTimer);
        logsRefreshTimer = null;
    }
});
