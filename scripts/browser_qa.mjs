/** Original local preview only. Chromium is optional; no third-party URL is loaded. */
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import net from "node:net";
import { spawn } from "node:child_process";

const reportPath = process.argv[2] || "data/reports/local-preview.json";
const preview = JSON.parse(fs.readFileSync(reportPath, "utf8"));
const standaloneDemo = preview.self_contained_demo === true;
if (
  !preview.running ||
  !preview.synthetic_only ||
  (!standaloneDemo &&
    !/^fraggy_preview_[a-f0-9]{32}$/.test(preview.database_name))
)
  throw new Error("Owned synthetic preview required");
if (standaloneDemo && process.argv.includes("--outage"))
  throw new Error("Self-contained demo has no API process to pause");
for (const base of [preview.frontend, preview.api])
  if (new URL(base).hostname !== "127.0.0.1")
    throw new Error("Literal loopback required");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "fraggy-browser-"));
const output = standaloneDemo
  ? "data/reports/vercel-demo-browser-qa"
  : "data/reports/browser-qa";
fs.mkdirSync(output, { recursive: true });
const listener = net.createServer();
await new Promise((resolve) => listener.listen(0, "127.0.0.1", resolve));
const port = listener.address().port;
await new Promise((resolve) => listener.close(resolve));
const browser = spawn(
  process.env.CHROMIUM_BINARY || "chromium",
  [
    "--headless",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--remote-debugging-address=127.0.0.1",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${dir}`,
    "about:blank",
  ],
  { stdio: "ignore" },
);
let spawnFailed = false;
browser.once("error", () => {
  spawnFailed = true;
});
let socket;
const results = [];
let apiPaused = false;
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
try {
  let pages;
  for (let i = 0; i < 100; i++) {
    if (spawnFailed)
      throw new Error(
        "Chromium unavailable; install it or set CHROMIUM_BINARY",
      );
    try {
      pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      break;
    } catch {
      await delay(100);
    }
  }
  if (!pages) throw new Error("Chromium did not start");
  socket = new WebSocket(
    pages.find((page) => page.type === "page").webSocketDebuggerUrl,
  );
  await new Promise((resolve) =>
    socket.addEventListener("open", resolve, { once: true }),
  );
  let counter = 0;
  const pending = new Map();
  function call(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = ++counter;
      pending.set(id, { resolve, reject });
      socket.send(JSON.stringify({ id, method, params }));
      setTimeout(() => {
        if (pending.has(id)) {
          pending.delete(id);
          reject(new Error(`CDP timeout: ${method}`));
        }
      }, 15000).unref();
    });
  }
  const externalBlocked = [];
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const p = pending.get(message.id);
      if (p) {
        pending.delete(message.id);
        message.error
          ? p.reject(new Error(message.error.message))
          : p.resolve(message.result);
      }
    }
    if (message.method === "Fetch.requestPaused") {
      const request = message.params;
      const url = new URL(request.request.url);
      const allowed =
        !["http:", "https:"].includes(url.protocol) ||
        (url.hostname === "127.0.0.1" &&
          [new URL(preview.frontend).port, new URL(preview.api).port].includes(
            url.port,
          ));
      if (!allowed) externalBlocked.push(url.origin);
      call(
        allowed ? "Fetch.continueRequest" : "Fetch.failRequest",
        allowed
          ? { requestId: request.requestId }
          : { requestId: request.requestId, errorReason: "BlockedByClient" },
      ).catch(() => {});
    }
  });
  async function evaluate(expression) {
    const value = await call("Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    if (value.exceptionDetails) throw new Error("Browser expression failed");
    return value.result.value;
  }
  async function until(expression) {
    for (let i = 0; i < 150; i++) {
      if (await evaluate(expression)) return true;
      await delay(100);
    }
    return false;
  }
  await call("Page.enable");
  await call("Network.enable");
  await call("Fetch.enable", {
    patterns: [{ urlPattern: "*", requestStage: "Request" }],
  });
  const cases = [
    ["home", "/"],
    ["brands", "/brands"],
    ["list", "/fragrances?limit=2"],
    ["search", "/fragrances?q=Cedar"],
    [
      "filter",
      "/fragrances?brand=invented-house-000&concentration=eau_de_parfum",
    ],
    ["pagination", "/fragrances?offset=20"],
    ["detail", `/fragrances/${preview.fragrance_id}`],
    ["empty", "/fragrances?q=NoSuchFictionalPerfumeXYZ"],
  ];
  for (const [device, width, height] of [
    ["desktop", 1440, 1000],
    ["tablet", 768, 1024],
    ["mobile", 390, 844],
  ]) {
    await call("Emulation.setDeviceMetricsOverride", {
      width,
      height,
      deviceScaleFactor: 1,
      mobile: device === "mobile",
    });
    for (const [name, route] of cases) {
      await call("Page.navigate", { url: preview.frontend + route });
      await until(
        `location.href === ${JSON.stringify(preview.frontend + route)} && document.readyState === "complete" && !!document.querySelector("main h1")`,
      );
      await delay(200);
      if (name === "detail") {
        const count = await evaluate(
          "document.querySelectorAll('main img').length",
        );
        for (let index = 0; index < count; index++) {
          await evaluate(
            `document.querySelectorAll('main img')[${index}].scrollIntoView({block:'center'})`,
          );
          await until(
            `document.querySelectorAll('main img')[${index}]?.complete && document.querySelectorAll('main img')[${index}]?.naturalWidth > 0`,
          );
        }
        await evaluate("scrollTo(0,0)");
      }
      const data = await evaluate(
        `({title:document.title,heading:document.querySelector('main h1')?.innerText,viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,main:document.querySelectorAll('main').length,heroOverlap:(()=>{const a=document.querySelector('.hero-art'),c=document.querySelector('.hero-feature .source-credits')||document.querySelector('.hero-art .source-credits');return !!(a&&c&&c.getBoundingClientRect().top<a.getBoundingClientRect().bottom);})(),images:[...document.querySelectorAll('main img')].map(i=>({alt:i.alt,loaded:i.complete&&i.naturalWidth>0,src:i.getAttribute('src')})),placeholders:document.querySelectorAll('.bottle-placeholder').length,credits:document.querySelectorAll('.source-credits').length,links:[...document.querySelectorAll('.catalog-pagination a')].map(a=>a.textContent),empty:document.body.innerText.includes('No scents found'),controls:[...document.querySelectorAll('main input,main select,main button')].filter(e=>!e.getAttribute('aria-label')&&!e.textContent.trim()&&!e.labels?.length).length})`,
      );
      const pass =
        (!standaloneDemo ||
          (await evaluate(
            '!!document.querySelector("[aria-label=\\"Read-only demo\\"]")',
          ))) &&
        data.documentWidth <= width &&
        !data.heroOverlap &&
        data.main === 1 &&
        data.controls === 0 &&
        data.images.every((i) => i.alt && i.src.startsWith("/media/")) &&
        !data.heading?.includes("Something went wrong") &&
        (name !== "detail" ||
          (data.images.length === 4 && data.images.every((i) => i.loaded))) &&
        (name !== "empty" || data.empty);
      results.push({ device, name, pass, ...data });
      if (["home", "list", "detail"].includes(name)) {
        const shot = await call("Page.captureScreenshot", {
          format: "png",
          captureBeyondViewport: false,
        });
        fs.writeFileSync(
          `${output}/${device}-${name}.png`,
          Buffer.from(shot.data, "base64"),
        );
      }
    }
    if (device === "mobile") {
      await evaluate(
        'document.querySelector("button[aria-label=\\"Toggle navigation\\"]").click()',
      );
      const opened = await evaluate(
        'document.querySelector("button[aria-label=\\"Toggle navigation\\"]").getAttribute("aria-expanded")==="true"',
      );
      results.push({ device, name: "navigation-toggle", pass: opened });
      await evaluate(
        'document.querySelector("button[aria-label=\\"Toggle navigation\\"]").click()',
      );
    }
  }
  if (process.argv.includes("--outage")) {
    if (!preview.api_pid || !preview.supervisor_pid)
      throw new Error("Preview PID ownership evidence missing");
    const cmd = fs.readFileSync(`/proc/${preview.api_pid}/cmdline`, "utf8");
    const status = fs.readFileSync(`/proc/${preview.api_pid}/status`, "utf8");
    if (
      !cmd.includes("uvicorn") ||
      !status.includes(`PPid:\t${preview.supervisor_pid}\n`)
    )
      throw new Error("Refuse to pause unrelated process");
    process.kill(preview.api_pid, "SIGSTOP");
    apiPaused = true;
    await call("Page.navigate", {
      url: preview.frontend + "/fragrances?q=Cedar&limit=2",
    });
    const loading = await until('!!document.querySelector("[role=status]")');
    const error = await until(
      'document.body.innerText.includes("Something went wrong.")',
    );
    process.kill(preview.api_pid, "SIGCONT");
    apiPaused = false;
    await evaluate(
      '[...document.querySelectorAll("button")].find(b=>b.textContent.includes("Try again"))?.click()',
    );
    const recovered = await until(
      '!!document.querySelector(".fragrance-card") && !document.body.innerText.includes("Something went wrong.")',
    );
    results.push({
      name: "loading-error-retry",
      loading,
      error,
      recovered,
      pass: error && recovered,
    });
  }
  const summary = {
    synthetic_only: true,
    self_contained_demo: standaloneDemo,
    externalBlocked,
    results,
    passed: results.filter((r) => r.pass).length,
    failed: results.filter((r) => !r.pass).length,
    limited_accessibility_audit:
      "landmarks, labels, alt text, responsive layout and navigation; not WCAG certification",
  };
  fs.writeFileSync(
    `${output}/results.json`,
    JSON.stringify(summary, null, 2) + "\n",
  );
  console.log(JSON.stringify(summary));
  if (summary.failed) process.exitCode = 1;
} finally {
  if (apiPaused) process.kill(preview.api_pid, "SIGCONT");
  socket?.close();
  if (browser.pid && browser.exitCode === null && browser.signalCode === null) {
    const exited = new Promise((resolve) => browser.once("exit", resolve));
    browser.kill("SIGTERM");
    await exited;
  }
  fs.rmSync(dir, { recursive: true, force: true });
}
