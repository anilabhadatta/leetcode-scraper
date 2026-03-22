// =======Config START=======
const authConfig = {
  siteName: "LeetCode Scraper",
  // Google OAuth2 credentials
  client_id: "YOUR_CLIENT_ID.apps.googleusercontent.com",
  client_secret: "YOUR_CLIENT_SECRET",
  refresh_token: "YOUR_REFRESH_TOKEN",
  // Root folder ID of your "Leetcode" folder on Google Drive
  root_id: "YOUR_GOOGLE_DRIVE_FOLDER_ID",
  // Basic auth to protect the site
  user: "admin",
  pass: "your-password",
  // How many files to list per page
  page_size: 200,
};
// =======Config END=======

// ---------------------------------------------------------------------------
// Token cache
// ---------------------------------------------------------------------------

let _access_token = null;
let _token_expires = 0;

async function getAccessToken() {
  if (_access_token && Date.now() < _token_expires) {
    return _access_token;
  }
  const resp = await fetch("https://www.googleapis.com/oauth2/v4/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: authConfig.client_id,
      client_secret: authConfig.client_secret,
      refresh_token: authConfig.refresh_token,
      grant_type: "refresh_token",
    }),
  });
  const data = await resp.json();
  if (!data.access_token) {
    throw new Error("Failed to obtain access token: " + JSON.stringify(data));
  }
  _access_token = data.access_token;
  _token_expires = Date.now() + (data.expires_in - 60) * 1000;
  return _access_token;
}

async function driveHeaders() {
  const token = await getAccessToken();
  return { Authorization: "Bearer " + token };
}

// ---------------------------------------------------------------------------
// Google Drive helpers
// ---------------------------------------------------------------------------

/**
 * List children of a folder by ID.
 * Returns { files: [{id, name, mimeType, size, modifiedTime}], nextPageToken }
 */
async function listFolder(folderId, pageToken = null) {
  const params = new URLSearchParams({
    q: `'${folderId}' in parents and trashed = false`,
    fields: "nextPageToken, files(id, name, mimeType, size, modifiedTime)",
    orderBy: "folder,name",
    pageSize: String(authConfig.page_size),
    includeItemsFromAllDrives: "true",
    supportsAllDrives: "true",
  });
  if (pageToken) params.set("pageToken", pageToken);

  const resp = await fetch(
    `https://www.googleapis.com/drive/v3/files?${params}`,
    { headers: await driveHeaders() }
  );
  if (!resp.ok) throw new Error(`Drive list error: ${resp.status}`);
  return resp.json();
}

/**
 * Get file metadata by ID.
 */
async function getFileMeta(fileId) {
  const params = new URLSearchParams({
    fields: "id, name, mimeType, size, modifiedTime",
    supportsAllDrives: "true",
  });
  const resp = await fetch(
    `https://www.googleapis.com/drive/v3/files/${fileId}?${params}`,
    { headers: await driveHeaders() }
  );
  if (!resp.ok) throw new Error(`Drive meta error: ${resp.status}`);
  return resp.json();
}

/**
 * Resolve a slash-separated path under root_id to a folder/file ID.
 * Returns null if not found.
 */
async function resolvePath(pathParts) {
  let currentId = authConfig.root_id;
  for (const part of pathParts) {
    if (!part) continue;
    const escaped = part.replace(/\\/g, "\\\\").replace(/'/g, "\\'");
    const params = new URLSearchParams({
      q: `'${currentId}' in parents and name = '${escaped}' and trashed = false`,
      fields: "files(id, name, mimeType)",
      includeItemsFromAllDrives: "true",
      supportsAllDrives: "true",
    });
    const resp = await fetch(
      `https://www.googleapis.com/drive/v3/files?${params}`,
      { headers: await driveHeaders() }
    );
    const data = await resp.json();
    if (!data.files || data.files.length === 0) return null;
    currentId = data.files[0].id;
  }
  return currentId;
}

const FOLDER_MIME = "application/vnd.google-apps.folder";

// ---------------------------------------------------------------------------
// Basic auth
// ---------------------------------------------------------------------------

function basicAuthResponse() {
  return new Response("Unauthorized", {
    status: 401,
    headers: {
      "WWW-Authenticate": `Basic realm="${authConfig.siteName}"`,
      "Content-Type": "text/plain",
    },
  });
}

function checkBasicAuth(request) {
  const { user, pass } = authConfig;
  if (!user && !pass) return true; // auth disabled if both empty
  const authHeader = request.headers.get("Authorization") || "";
  if (!authHeader.startsWith("Basic ")) return false;
  try {
    const decoded = atob(authHeader.slice(6));
    const colon = decoded.indexOf(":");
    if (colon === -1) return false;
    const u = decoded.slice(0, colon);
    const p = decoded.slice(colon + 1);
    // Constant-time-ish comparison
    return u === user && p === pass;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// HTML renderer
// ---------------------------------------------------------------------------

function formatSize(bytes) {
  if (!bytes) return "—";
  const n = Number(bytes);
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
  if (n < 1024 * 1024 * 1024) return (n / (1024 * 1024)).toFixed(1) + " MB";
  return (n / (1024 * 1024 * 1024)).toFixed(2) + " GB";
}

function renderDirectory(urlPath, files, nextPageToken) {
  const breadcrumbs = buildBreadcrumbs(urlPath);

  const rows = files
    .map((f) => {
      const isFolder = f.mimeType === FOLDER_MIME;
      const href = urlPath.replace(/\/?$/, "/") + encodeURIComponent(f.name) + (isFolder ? "/" : "");
      const icon = isFolder ? "📁" : getFileIcon(f.name);
      const size = isFolder ? "—" : formatSize(f.size);
      const modified = f.modifiedTime ? f.modifiedTime.slice(0, 10) : "—";
      return `<tr>
        <td>${icon}</td>
        <td><a href="${href}">${escHtml(f.name)}</a></td>
        <td>${size}</td>
        <td>${modified}</td>
      </tr>`;
    })
    .join("\n");

  const nextLink = nextPageToken
    ? `<p><a href="?pageToken=${encodeURIComponent(nextPageToken)}">Next page →</a></p>`
    : "";

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escHtml(authConfig.siteName)} — ${escHtml(urlPath)}</title>
<style>
  *{box-sizing:border-box}
  body{font-family:system-ui,sans-serif;max-width:900px;margin:0 auto;padding:1rem 1.5rem;color:#222}
  h1{font-size:1.2rem;margin-bottom:.5rem;word-break:break-all}
  nav{font-size:.9rem;margin-bottom:1rem;color:#555}
  nav a{color:#0070f3;text-decoration:none}
  nav a:hover{text-decoration:underline}
  table{width:100%;border-collapse:collapse;font-size:.9rem}
  th{text-align:left;padding:.4rem .6rem;border-bottom:2px solid #ddd;white-space:nowrap}
  td{padding:.35rem .6rem;border-bottom:1px solid #eee;vertical-align:middle}
  td:first-child{width:1.8rem;font-size:1rem}
  td:nth-child(3),td:nth-child(4){white-space:nowrap;color:#666;text-align:right;width:7rem}
  a{color:#0070f3;text-decoration:none}
  a:hover{text-decoration:underline}
  @media(max-width:540px){td:nth-child(4){display:none}th:nth-child(4){display:none}}
</style>
</head>
<body>
<h1>📂 ${escHtml(authConfig.siteName)}</h1>
<nav>${breadcrumbs}</nav>
<table>
  <thead><tr><th></th><th>Name</th><th style="text-align:right">Size</th><th style="text-align:right">Modified</th></tr></thead>
  <tbody>
  ${urlPath !== "/" ? `<tr><td>⬆️</td><td><a href="../">../</a></td><td></td><td></td></tr>` : ""}
  ${rows}
  </tbody>
</table>
${nextLink}
</body>
</html>`;
}

function buildBreadcrumbs(urlPath) {
  const parts = urlPath.split("/").filter(Boolean);
  let crumbs = `<a href="/">${escHtml(authConfig.siteName)}</a>`;
  let cumulative = "";
  for (const part of parts) {
    cumulative += "/" + part;
    crumbs += ` / <a href="${cumulative}/">${escHtml(decodeURIComponent(part))}</a>`;
  }
  return crumbs;
}

function getFileIcon(name) {
  const ext = name.split(".").pop().toLowerCase();
  const map = { md: "📝", txt: "📄", json: "📋", html: "🌐", pdf: "📕", png: "🖼️", jpg: "🖼️", jpeg: "🖼️", gif: "🖼️" };
  return map[ext] || "📄";
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ---------------------------------------------------------------------------
// Request handler
// ---------------------------------------------------------------------------

addEventListener("fetch", (event) => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  // Only allow GET/HEAD
  if (request.method !== "GET" && request.method !== "HEAD") {
    return new Response("Method Not Allowed", { status: 405 });
  }

  // Basic auth check
  if (!checkBasicAuth(request)) {
    return basicAuthResponse();
  }

  const url = new URL(request.url);
  // Decode and normalize path
  let urlPath = decodeURIComponent(url.pathname) || "/";

  try {
    const pathParts = urlPath.split("/").filter(Boolean).map(decodeURIComponent);

    if (pathParts.length === 0) {
      // Root: list root folder
      const pageToken = url.searchParams.get("pageToken") || null;
      const result = await listFolder(authConfig.root_id, pageToken);
      return new Response(renderDirectory("/", result.files || [], result.nextPageToken || null), {
        headers: { "Content-Type": "text/html; charset=utf-8" },
      });
    }

    // Resolve the path to a Drive ID
    const driveId = await resolvePath(pathParts);
    if (!driveId) {
      return new Response("Not Found", { status: 404 });
    }

    const meta = await getFileMeta(driveId);

    if (meta.mimeType === FOLDER_MIME) {
      // Directory listing
      const pageToken = url.searchParams.get("pageToken") || null;
      const result = await listFolder(driveId, pageToken);
      const normalizedPath = "/" + pathParts.map(encodeURIComponent).join("/");
      return new Response(
        renderDirectory(normalizedPath, result.files || [], result.nextPageToken || null),
        { headers: { "Content-Type": "text/html; charset=utf-8" } }
      );
    } else {
      // File: proxy the download
      return proxyFile(driveId, request.headers.get("Range"));
    }
  } catch (err) {
    return new Response("Internal Error: " + err.message, {
      status: 500,
      headers: { "Content-Type": "text/plain" },
    });
  }
}

async function proxyFile(fileId, range) {
  const headers = await driveHeaders();
  if (range) headers["Range"] = range;

  const resp = await fetch(
    `https://www.googleapis.com/drive/v3/files/${fileId}?alt=media&supportsAllDrives=true`,
    { headers }
  );

  const responseHeaders = new Headers();
  // Forward relevant headers
  for (const h of ["Content-Type", "Content-Length", "Content-Range", "Accept-Ranges", "Last-Modified", "ETag"]) {
    const v = resp.headers.get(h);
    if (v) responseHeaders.set(h, v);
  }
  responseHeaders.set("Cache-Control", "public, max-age=3600");

  return new Response(resp.body, {
    status: resp.status,
    headers: responseHeaders,
  });
}
