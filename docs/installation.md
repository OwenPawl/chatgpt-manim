# Installation and ChatGPT status

## Verified surface and current status

Official OpenAI plugin quickstart instructions use ChatGPT **Work**. On 2026-10-27,
the signed-in personal Plugins page was inspected. Its **Add custom MCP server**
dialog offered Server URL or Tunnel and OAuth / No authentication / OAuth or no
authentication. No fixed API-key option was present. The plugin has not been
registered or installed in that account, and no actual ChatGPT-hosted invocation or
embedded-player test has been completed.

A portable package, public GitHub repository, personal installation, and approval
in the universal public directory are separate milestones. None implies the others.

## Remote OAuth installation

1. Deploy the server at a stable HTTPS origin and configure the OAuth settings in
   [deployment](deployment.md). Verify `/mcp` returns 401 anonymously and accepts a
   correctly scoped, audience-bound token.
2. Open [ChatGPT Plugins](https://chatgpt.com/plugins), choose **+ → Add custom MCP
   server**, enter **Manim Animation** and your `https://HOST/mcp` URL.
3. Select **OAuth**, configure the discovered provider/client settings, review the
   risk notice and select **Create as a plugin**. Complete the provider login.
4. In **Personal**, open the resulting plugin and press **+** to install it.
5. Start a new **Work** chat; first explicitly select it with `@` and request the
   Fourier example. Confirm a completed tool result and playable iframe. Then test
   “Make it twice as slow.” Run the prompt evaluations without explicit tagging too.
6. To bundle the skill with the registered server, copy the `plugin_asdk_app...` ID
   from its URL and use the official plugin-creator workflow, or add the registered
   mapping to `.app.json` and reference it in `plugin.json` per OpenAI's packaging guide.

Do not claim automatic selection just because an explicit `@` invocation works.
Record positive, negative and follow-up outcomes in the evaluation log.

## Private tunnel alternative

[Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
can connect a private server without public ingress. It requires a Platform tunnel
ID, a restricted runtime API key, and association with the intended ChatGPT
workspace. Configure tunnel-client to forward to the local authenticated server,
including its upstream bearer header as supported by tunnel-client. This path was
not provisioned or verified. It does not satisfy public plugin submission; media
also needs an origin reachable by the iframe.

## Local portable package

The root `plugin.json`, `mcp.json`, and `skills/` follow the portable Agent Plugins
layout. Add the folder to a local marketplace using the current official plugin
packaging instructions, configure the endpoint and credential through the host,
restart the desktop client if required, then install from that marketplace.
Local marketplace presence is not proof of installation.

The downloaded Agent Plugins 1.0.0 MCP JSON Schema rejects server `extensions`,
although OpenAI's current packaging page documents `extensions.com.openai.auth`.
Therefore the default `mcp.json` stays strictly portable and schema-valid. The
separate `mcp.oauth.example.json` demonstrates the documented OpenAI extension;
validate that overlay with the target OpenAI host, not the unextended portable schema.

## Public submission prerequisites

Provide a stable HTTPS URL, OAuth configuration and review account, a verified
same-site widget domain, privacy policy, terms, branding, support information,
real ChatGPT screenshots and completed invocation/avoidance evaluations. Follow the
[submission guide](https://developers.openai.com/plugins/deploy/submission). The
project is not submitted, approved, or listed in the official public directory.

Sources: [quickstart](https://developers.openai.com/plugins/quickstart),
[package format](https://developers.openai.com/plugins/build/plugins),
[UI quickstart](https://developers.openai.com/plugins/build/app-quickstart),
[authentication](https://developers.openai.com/plugins/build/auth).
