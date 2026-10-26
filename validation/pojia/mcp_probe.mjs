// Exercise the installed stdio MCP server, without model API calls or extra dependencies.
import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { parseArgs } from "node:util";

const { values } = parseArgs({ options: {
  dispatcher: { type: "string" }, sample: { type: "string" }, out: { type: "string" },
} });
if (!values.dispatcher || !values.sample || !values.out) {
  throw new Error("Required: --dispatcher FILE --sample FILE --out DIRECTORY");
}
const out = resolve(values.out);
await mkdir(out, { recursive: true });
const child = spawn(process.execPath, [resolve(values.dispatcher), "mcp"], {
  stdio: ["pipe", "pipe", "pipe"], windowsHide: true,
});
const pending = new Map();
const transcript = [];
let counter = 0;
let buffer = "";
let stderr = "";
let protocolError;
child.stderr.setEncoding("utf8").on("data", (chunk) => { stderr += chunk; });
child.stdout.setEncoding("utf8").on("data", (chunk) => {
  buffer += chunk;
  let newline;
  while ((newline = buffer.indexOf("\n")) >= 0) {
    const line = buffer.slice(0, newline).trim();
    buffer = buffer.slice(newline + 1);
    if (!line) continue;
    try {
      const message = JSON.parse(line);
      transcript.push({ direction: "received", message });
      const waiter = pending.get(message.id);
      if (waiter) {
        pending.delete(message.id);
        clearTimeout(waiter.timer);
        if (message.error) waiter.reject(new Error(JSON.stringify(message.error)));
        else waiter.resolve(message.result);
      }
    } catch (error) { protocolError = error; }
  }
});
function failPending(error) {
  for (const waiter of pending.values()) {
    clearTimeout(waiter.timer);
    waiter.reject(error);
  }
  pending.clear();
}
child.on("error", failPending);
child.on("exit", (code) => failPending(new Error(`MCP exited with ${code}`)));
function send(message) {
  if (protocolError) throw protocolError;
  transcript.push({ direction: "sent", message });
  child.stdin.write(JSON.stringify({ jsonrpc: "2.0", ...message }) + "\n");
}
function request(method, params = {}) {
  return new Promise((accept, reject) => {
    const id = ++counter;
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`Timeout: ${method}`));
    }, 30000);
    pending.set(id, { resolve: accept, reject, timer });
    try { send({ id, method, params }); }
    catch (error) { clearTimeout(timer); pending.delete(id); reject(error); }
  });
}
async function save(name, data) {
  await writeFile(resolve(out, name), JSON.stringify(data, null, 2) + "\n", { flag: "wx" });
}
try {
  const initialized = await request("initialize", {
    protocolVersion: "2024-11-05", capabilities: {},
    clientInfo: { name: "pojia-validation", version: "1.0.0" },
  });
  await save("initialize.json", initialized);
  send({ method: "notifications/initialized" });
  const tools = [];
  let cursor;
  do {
    const page = await request("tools/list", cursor ? { cursor } : {});
    tools.push(...page.tools);
    cursor = page.nextCursor;
  } while (cursor);
  await save("tools-list.json", { tools });
  for (const name of ["inspect_managed_artifact", "inspect_managed_members"]) {
    const tool = tools.find((entry) => entry.name === name);
    if (!tool?.inputSchema?.properties?.path) throw new Error(`Missing path schema: ${name}`);
    const result = await request("tools/call", { name, arguments: { path: resolve(values.sample) } });
    await save(`${name}.json`, result);
    if (result.isError) throw new Error(`Analysis returned isError: ${name}`);
  }
  console.log(JSON.stringify({ ok: true, tool_count: tools.length, server: initialized.serverInfo }));
} finally {
  child.stdin.end();
  if (child.exitCode === null) {
    await new Promise((accept) => {
      const timer = setTimeout(() => { child.kill(); accept(); }, 1500);
      child.once("close", () => { clearTimeout(timer); accept(); });
    });
  }
  await writeFile(resolve(out, "transcript.jsonl"), transcript.map((entry) => JSON.stringify(entry)).join("\n") + "\n", { flag: "wx" });
  await writeFile(resolve(out, "stderr.txt"), stderr, { flag: "wx" });
}
