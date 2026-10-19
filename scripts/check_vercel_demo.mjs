/** Production Next smoke: original snapshot only, deliberately unreachable API. */
import assert from "node:assert/strict";
import fs from "node:fs";
import net from "node:net";
import path from "node:path";
import { spawn } from "node:child_process";
const root = path.resolve(import.meta.dirname, "..");
const catalog = JSON.parse(
  fs.readFileSync(path.join(root, "apps/web/src/demo/catalog.json"), "utf8"),
);
const fragrance = catalog.fragrances.find((f) => f.primary_image);
const listener = net.createServer();
await new Promise((resolve) => listener.listen(0, "127.0.0.1", resolve));
const port = listener.address().port;
await new Promise((resolve) => listener.close(resolve));
const child = spawn(
  process.execPath,
  [
    "node_modules/next/dist/bin/next",
    "start",
    "--hostname",
    "127.0.0.1",
    "--port",
    String(port),
  ],
  {
    cwd: path.join(root, "apps/web"),
    detached: true,
    stdio: "ignore",
    env: {
      ...process.env,
      FRAGGY_DEMO_MODE: "synthetic",
      API_BASE_URL: "http://127.0.0.1:1/unreachable",
      NEXT_TELEMETRY_DISABLED: "1",
    },
  },
);
let spawnFailed = false;
child.once("error", () => {
  spawnFailed = true;
});
const base = `http://127.0.0.1:${port}`;
let checks = 0;
async function response(route, status = 200, options = {}) {
  const result = await fetch(base + route, {
    ...options,
    signal: AbortSignal.timeout(10000),
  });
  assert.equal(result.status, status, `HTTP status for ${route}`);
  checks++;
  return result;
}
try {
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    if (spawnFailed || child.exitCode !== null)
      throw new Error("Owned demo server failed to start");
    try {
      if ((await fetch(base, { signal: AbortSignal.timeout(1000) })).ok) {
        ready = true;
        break;
      }
    } catch {
      /* wait only for owned server */
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  assert(ready, "Owned demo server startup timed out");
  for (const route of [
    "/",
    "/brands",
    "/fragrances",
    "/fragrances?brand=invented-house-000&concentration=eau_de_parfum",
    "/fragrances?offset=20",
    `/fragrances/${fragrance.id}`,
  ]) {
    const result = await response(route);
    assert.match(result.headers.get("x-robots-tag") ?? "", /noindex/);
    assert.match(await result.text(), /Read-only fictional demo/);
  }
  assert.match(
    await (
      await response(`/fragrances?q=${encodeURIComponent(fragrance.name)}`)
    ).text(),
    new RegExp(fragrance.name),
  );
  assert.match(
    await (await response("/fragrances?q=NoSuchFictionalPerfumeXYZ")).text(),
    /No scents found/,
  );
  const ids = new Set(
    JSON.stringify(catalog)
      .match(/\/api\/v1\/media\/([a-f0-9-]{36})\/display/g)
      .map((url) => url.split("/")[4]),
  );
  assert.equal(ids.size, 4);
  for (const id of ids)
    for (const preset of ["display", "thumb"]) {
      const result = await response(`/media/${id}/${preset}`);
      assert.equal(result.headers.get("content-type"), "image/webp");
      assert.equal(
        Buffer.from(await result.arrayBuffer())
          .subarray(8, 12)
          .toString(),
        "WEBP",
      );
    }
  await response("/fragrances/00000000-0000-0000-0000-000000000000", 404);
  await response("/media/00000000-0000-0000-0000-000000000000/display", 404);
  await response(`/media/${fragrance.primary_image.id}/raw`, 404);
  await response(`/media/${fragrance.primary_image.id}/display`, 405, {
    method: "POST",
  });
  await response("/api/v1/fragrances", 404);
  console.log(
    JSON.stringify({
      passed: checks,
      failed: 0,
      self_contained_demo: true,
      fragrances: 100,
      original_images: 4,
      api_base: "unreachable",
      deployed: false,
    }),
  );
} finally {
  if (child.pid && child.exitCode === null && child.signalCode === null) {
    const exited = new Promise((resolve) => child.once("exit", resolve));
    process.kill(-child.pid, "SIGTERM");
    await exited;
  }
}
