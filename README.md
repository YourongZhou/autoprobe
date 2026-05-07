# autoprobe

`autoprobe` probes Clash/Mihomo/Clash Verge nodes for Codex/OpenAI connectivity and switches your selector to the best-performing node.

It is designed for cases where:

- `codex` CLI sometimes works but VS Code/Codex reconnects
- `api.openai.com` is reachable on some nodes, while `chatgpt.com` or `ab.chatgpt.com` is unstable
- you want a fast, repeatable way to rank nodes instead of testing them by hand

## What It Tests

By default, `autoprobe` validates these URLs:

- `https://chatgpt.com`
- `https://ab.chatgpt.com`
- `https://api.openai.com`
- `https://auth.openai.com`

It treats any real HTTP response as a successful connection and treats timeouts / TLS resets as failures.

## How It Works

`autoprobe` uses a two-stage strategy:

1. Parallel precheck
   - Calls the Clash controller per-node `delay` API in parallel
   - Avoids changing the shared selector during coarse filtering
2. Serial final validation
   - Switches the selector only for the best prechecked nodes
   - Runs real `curl` checks against OpenAI/Codex-related domains

If not enough nodes pass the precheck, it automatically expands to additional candidates instead of allowing failed nodes into the finalist set.

## Features

- Supports Clash for Windows / Mihomo / Clash Verge style configs
- Auto-detects common config paths
- Prints detected proxy / VPN context to the terminal
- Prefers US nodes by default
- Defaults to `--top 12 --finalists 5`

## Install

Clone the repo and symlink or copy the executable into your `PATH`:

```bash
git clone git@github.com:YourongZhou/autoprobe.git
cd autoprobe
chmod +x autoprobe
mkdir -p ~/.local/bin
ln -sf "$PWD/autoprobe" ~/.local/bin/autoprobe
```

Optional shell alias:

```bash
echo 'autoprobe() { "$HOME/.local/bin/autoprobe" "$@"; }' >> ~/.bashrc
source ~/.bashrc
```

## Usage

Dry run:

```bash
autoprobe --dry-run
```

Use defaults:

```bash
autoprobe
```

Specify a Clash Verge config explicitly:

```bash
autoprobe --config ~/.local/share/io.github.clash-verge-rev.clash-verge-rev/config.yaml
```

Test a custom shortlist of nodes:

```bash
autoprobe --nodes "🇺🇲 美国W02 | IEPL | x1.5" "🇯🇵 日本W01 | IEPL"
```

## Default Config Discovery

The script tries these paths in order:

- `~/.config/clash/config.yaml`
- `~/.config/mihomo/config.yaml`
- `~/.local/share/io.github.clash-verge-rev.clash-verge-rev/config.yaml`
- `~/.local/share/io.github.clash-verge-rev.clash-verge-rev/profiles/config.yaml`
- `~/.local/share/clash-verge/config.yaml`
- `~/.local/share/clash-verge/profiles/config.yaml`

You can always override this with `--config`.

## Notes

- The precheck phase is safe to parallelize because it does not mutate the shared selector.
- The final validation phase is intentionally serial because selector switching is global state.
- Repeated high-frequency probing against `chatgpt.com` may trigger Cloudflare challenges. Use it manually, not as a tight cron loop.
