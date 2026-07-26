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

$("pl-download").addEventListener("click", () => {
    runJob(
        "/api/download-playlist",
        {
            url: $("pl-url").value.trim(),
            subtitle_language: $("pl-subs").value,
            numerate: $("pl-numerate").checked,
            save_path: $("pl-folder").value.trim(),
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
