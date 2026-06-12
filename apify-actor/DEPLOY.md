# Deploy & monetize this Actor on Apify

Steps you run yourself (account + billing can't be automated). Each step is copy-paste.

## 1. Create an Apify account (free)

1. Go to https://console.apify.com/sign-up — sign up with email or Google.
2. Confirm the email if prompted.
3. Free tier includes monthly platform credits — enough to build and test.

## 2. Install the CLI and log in

```bash
npm i -g apify-cli
apify login        # opens browser / pastes your API token
```

Get your API token at: https://console.apify.com/settings/integrations

## 3. Push this Actor

```bash
cd D:\mcp\bilibili-mcp\apify-actor
apify push
```

First push builds the Docker image in Apify's cloud and creates the Actor in your
account. Watch the build log; it must end with **BUILD SUCCEEDED**.

## 4. Turn on Standby mode & test the endpoint

1. Open the Actor in https://console.apify.com → **Standby** tab → enable.
2. Your MCP endpoint becomes:
   `https://<username>--bilibili-data-mcp.apify.actor/mcp`
3. Test it from any MCP client (Claude Desktop, Cursor, or `npx @modelcontextprotocol/inspector`):
   point it at that URL (streamable-HTTP transport) and call
   `get_video_info` with `bvid: BV1GJ411x7h7`.

## 5. (Optional) Set the subtitle cookie

Console → Actor → **Settings → Environment variables** → add `BILI_SESSDATA`
(mark **Secret**) to enable `get_video_subtitle`.

## 6. Publish to the Store + enable monetization

1. Console → Actor → **Publication** tab → fill title, description, categories
   (pick *AI*, *Developer tools*), set it **Public**.
2. **Monetization** tab → Pricing model = **Pay per event** → it picks up
   `.actor/pay_per_event.json` (`tool-call` = $0.02). Adjust the price here.
3. Submit. Once approved it appears in the Apify Store and is searchable by the
   ~130k Apify users — that's the distribution you're after.

## Updating later

Edit code → `apify push` again → bump `version` in `.actor/actor.json` when you
want a new published build.
