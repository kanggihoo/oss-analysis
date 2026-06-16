---
type: official-doc-translation
repo: agent-browser
source: artifacts/agent-browser/official/25-next.md
order: 25
title: "Next.js + Vercel"
---

# Next.js + Vercel

Vercel Sandbox를 사용해 Vercel의 Next.js app에서 agent-browser를 실행합니다.
Linux microVM이 필요할 때 시작되어 agent-browser + Chrome을 실행한 뒤 종료됩니다. binary size limits도 없고, Chromium bundling 복잡성도 없습니다.

## 설정

```bash
pnpm add @vercel/sandbox
```

## Server action

Vercel Sandbox는 Amazon Linux를 실행합니다. Chromium에는 기본적으로 설치되어 있지 않은 system libraries가 필요하므로, 새 sandbox에서는 agent-browser가 Chrome을 실행하기 전에 `dnf install` 단계가 필요합니다. production에서는 sandbox snapshot(아래)을 사용해 이 과정을 완전히 건너뛰세요.

```ts
"use server";

const snapshotId = process.env.AGENT_BROWSER_SNAPSHOT_ID;

const CHROMIUM_SYSTEM_DEPS = [
  "nss", "nspr", "libxkbcommon", "atk", "at-spi2-atk", "at-spi2-core",
  "libXcomposite", "libXdamage", "libXrandr", "libXfixes", "libXcursor",
  "libXi", "libXtst", "libXScrnSaver", "libXext", "mesa-libgbm", "libdrm",
  "mesa-libGL", "mesa-libEGL", "cups-libs", "alsa-lib", "pango", "cairo",
  "gtk3", "dbus-libs",
];

function getSandboxCredentials() {
  if (
    process.env.VERCEL_TOKEN &&
    process.env.VERCEL_TEAM_ID &&
    process.env.VERCEL_PROJECT_ID
  ) {
    return {
      token: process.env.VERCEL_TOKEN,
      teamId: process.env.VERCEL_TEAM_ID,
      projectId: process.env.VERCEL_PROJECT_ID,
    };
  }
  return {};
}

async function withBrowser<T>(
  fn: (sandbox: InstanceType<typeof Sandbox>) => Promise<T>,
): Promise<T> {
  const credentials = getSandboxCredentials();

  const sandbox = snapshotId
    ? await Sandbox.create({
        ...credentials,
        source: { type: "snapshot", snapshotId },
        timeout: 120_000,
      })
    : await Sandbox.create({ ...credentials, runtime: "node24", timeout: 120_000 });

  if (!snapshotId) {
    await sandbox.runCommand("sh", [
      "-c",
      `sudo dnf clean all 2>&1 && sudo dnf install -y --skip-broken ${CHROMIUM_SYSTEM_DEPS.join(" ")} 2>&1 && sudo ldconfig 2>&1`,
    ]);
    await sandbox.runCommand("npm", ["install", "-g", "agent-browser"]);
    await sandbox.runCommand("npx", ["agent-browser", "install"]);
  }

  try {
    return await fn(sandbox);
  } finally {
    await sandbox.stop();
  }
}

  return withBrowser(async (sandbox) => {
    await sandbox.runCommand("agent-browser", ["open", url]);

    const ssResult = await sandbox.runCommand("agent-browser", [
      "screenshot", "--json",
    ]);
    const ssPath = JSON.parse(await ssResult.stdout())?.data?.path;
    const b64Result = await sandbox.runCommand("base64", ["-w", "0", ssPath]);
    const screenshot = (await b64Result.stdout()).trim();

    await sandbox.runCommand("agent-browser", ["close"]);
    return { ok: true, screenshot };
  });
}

  return withBrowser(async (sandbox) => {
    await sandbox.runCommand("agent-browser", ["open", url]);

    const result = await sandbox.runCommand("agent-browser", [
      "snapshot", "-i", "-c",
    ]);
    const snapshot = await result.stdout();

    await sandbox.runCommand("agent-browser", ["close"]);
    return { ok: true, snapshot };
  });
}
```

## Sandbox snapshots

최적화하지 않으면 각 Sandbox 실행은 system dependencies + agent-browser + Chromium을 처음부터 설치합니다(~30초). **sandbox snapshot**은 모든 것이 미리 설치된 저장된 VM image입니다. Vercel Sandbox용 Docker image와 비슷합니다. `AGENT_BROWSER_SNAPSHOT_ID`가 설정되면 sandbox는 설치 대신 해당 image에서 boot하므로 startup이 1초 미만으로 줄어듭니다.

이는 agent-browser *accessibility snapshot*(page의 accessibility tree를 dump하는 것)과 다릅니다. sandbox snapshot은 Vercel infrastructure concept입니다.

helper script를 한 번 실행해 sandbox snapshot을 생성하세요.

```bash
npx tsx scripts/create-snapshot.ts
```

script는 새 sandbox를 시작하고, system dependencies + agent-browser + Chromium을 설치하고, VM state를 저장한 뒤 snapshot ID를 출력합니다.

```
AGENT_BROWSER_SNAPSHOT_ID=snap_xxxxxxxxxxxx
```

이를 Vercel project environment variables(또는 local development용 `.env.local`)에 추가하세요. 모든 production deployment에 권장됩니다.

## Authentication

Vercel deployments에서는 Sandbox SDK가 OIDC를 통해 자동으로 인증합니다. local development에서는 명시적 credentials를 제공하세요.

<table>
  <thead>
    <tr><th>Variable</th><th>Description</th></tr>
  </thead>
  <tbody>
    <tr><td><code>VERCEL_TOKEN</code></td><td>Vercel personal access token</td></tr>
    <tr><td><code>VERCEL_TEAM_ID</code></td><td>Vercel team ID</td></tr>
    <tr><td><code>VERCEL_PROJECT_ID</code></td><td>Vercel project ID</td></tr>
  </tbody>
</table>

세 가지가 모두 설정되면 `Sandbox.create()`에 전달됩니다. 없으면 SDK는 `VERCEL_OIDC_TOKEN`으로 fallback합니다(Vercel에서는 자동).

## Scheduled workflows (cron)

daily monitoring 같은 recurring tasks에는 Vercel Cron Jobs를 사용하세요.

```ts
// app/api/cron/monitor/route.ts
  const result = await withBrowser(async (sandbox) => {
    await sandbox.runCommand("agent-browser", [
      "open", "https://example.com/pricing",
    ]);
    const snap = await sandbox.runCommand("agent-browser", [
      "snapshot", "-i", "-c",
    ]);
    await sandbox.runCommand("agent-browser", ["close"]);
    return await snap.stdout();
  });

  // Process results, send alerts, store data...
  return Response.json({ ok: true, snapshot: result });
}
```

```json
// vercel.json
{
  "crons": [
    { "path": "/api/cron/monitor", "schedule": "0 9 * * *" }
  ]
}
```

## Environment variables

<table>
  <thead>
    <tr><th>Variable</th><th>Description</th></tr>
  </thead>
  <tbody>
    <tr><td><code>AGENT_BROWSER_SNAPSHOT_ID</code></td><td>1초 미만 startup을 위한 Sandbox snapshot ID(위 참조)</td></tr>
    <tr><td><code>VERCEL_TOKEN</code></td><td>Vercel personal access token(local dev용, Vercel에서는 OIDC가 자동)</td></tr>
    <tr><td><code>VERCEL_TEAM_ID</code></td><td>Vercel team ID(local dev용)</td></tr>
    <tr><td><code>VERCEL_PROJECT_ID</code></td><td>Vercel project ID(local dev용)</td></tr>
  </tbody>
</table>

## Demo app

streaming progress UI, rate limiting, deploy-to-Vercel button이 포함된 작동하는 demo는 [`examples/environments/`](https://github.com/vercel-labs/agent-browser/tree/main/examples/environments)에 있습니다.
