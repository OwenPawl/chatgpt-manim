# Installation and ChatGPT status

## Verified surface and current status

On 2026-10-27 (America/Los_Angeles), **Manim Animation** was registered and connected
in the personal ChatGPT Plugins directory using a Secure MCP Tunnel. ChatGPT Work
completed an explicitly selected render, a natural-language follow-up revision,
and an untagged animation request. The player displayed and played real MP4s both
inline and in ChatGPT's side panel. Standard **Chat** also invoked the explicitly named plugin and played its result
inline after a host retry; untagged selection and revision were only tested in
Work. Standard Chat also displayed a text-response loading error. The bundled
reusable skill remains in this
repository; the installed cloud connection currently consists of the MCP app and
its tool descriptions. Untagged selection was observed, not guaranteed.

The first host iframe load failed in the tested runs; **Try again** loaded the
player successfully. No permanent fix is claimed. Fullscreen was denied by this
host and the player showed its supported fallback. No security settings were
weakened to perform these tests.

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
was verified with the official tunnel-client v0.0.18. It connects the private MCP
server through outbound traffic to OpenAI.

1. Start the authenticated server at `http://127.0.0.1:8787/mcp`. Keep a reachable
   HTTPS media origin configured in `MANIM_BASE_URL`.
2. In Platform organization settings, create a tunnel scoped to your ChatGPT
   workspace. Create a restricted runtime key with only **Tunnels: Read + Use**.
   The verified installation used a seven-day expiration, with model/data
   permissions disabled. Store credentials in protected ignored files.
3. Configure the official client profile using the example in
   [tunnel-client configuration](https://github.com/openai/tunnel-client/blob/master/docs/configuration.md).
   Use file references, not literal secrets:

   ```yaml
   config_version: 1
   control_plane:
     base_url: https://api.openai.com
     tunnel_id: YOUR_TUNNEL_ID
     api_key: file:/private/path/control-plane.key
   mcp:
     server_urls:
       - channel: main
         url: http://127.0.0.1:8787/mcp
     extra_headers:
       Authorization: file:/private/path/upstream-authorization
     discovery_extra_headers:
       Authorization: file:/private/path/upstream-authorization
   ```

   The upstream authorization file contains `Bearer ` followed by the server's
   `MANIM_API_KEY`; it is distinct from the Platform runtime key. Protect both
   files with mode 0600. In v0.0.18, `runtimes connect` rewrote the profile and
   removed these extra headers, so the verified path runs the prepared profile
   with `tunnel-client run --profile manim --profile-dir /private/profiles`.
   Verify readiness **and** successful authenticated MCP initialization.
4. In ChatGPT Plugins choose **+ → Add custom MCP server → Tunnel**, paste the
   tunnel ID and select **No authentication**, then **Create as a plugin** and
   **Connect Manim Animation**. Here the private tunnel authenticates the
   connection and injects the upstream bearer; the public server is not anonymous.
5. Open the personal plugin and **Try in chat**, choose **Work**, then test a
   render and “Make it twice as slow.” If the host says it could not display
   the app, try its **Try again** button; this workaround was required in testing.

This is a personal development installation, not public directory submission.
The local server, tunnel-client, and temporary Cloudflare media tunnel must keep
running. They are not configured to restart after reboot. The Platform runtime
key expires after seven days; expired credentials must be renewed through the
normal authorized process. A restarted quick tunnel may change the media origin,
requiring a server configuration update and a fresh tool result. For durable
operation use a stable HTTPS origin and a supervised deployment. No paid services
were provisioned.

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
