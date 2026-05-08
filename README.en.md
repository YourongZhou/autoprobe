# autoprobe

[中文](./README.md) | [Troubleshooting](./TROUBLESHOOTING.en.md)

> Proxy keeps dropping?
>
> Codex is stuck on `Reconnecting... 5/5`?
>
> Find the best node quickly and get back to coding.

`autoprobe` probes Clash / Mihomo / Clash Verge nodes for Codex / OpenAI connectivity and switches your selector to the best-performing node.

It is designed for cases where:

- `codex` CLI sometimes works but VS Code / Codex keeps reconnecting
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
   - Runs real `curl` checks against OpenAI / Codex-related domains

If not enough nodes pass the precheck, it automatically expands to additional candidates instead of allowing failed nodes into the finalist set.

## Features

- Supports Clash for Windows / Mihomo / Clash Verge style configs
- Auto-detects common config paths
- Prints detected proxy / VPN context to the terminal
- Prefers US nodes by default
- Defaults to `--top 12 --finalists 5`

## Install

Linux:

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

macOS:

```bash
git clone git@github.com:YourongZhou/autoprobe.git
cd autoprobe
chmod +x autoprobe
./autoprobe --dry-run
```

Windows PowerShell:

```powershell
git clone git@github.com:YourongZhou/autoprobe.git
cd autoprobe
.\autoprobe.cmd --dry-run
```

You can add the repo directory to `PATH`, or run it with `python .\autoprobe`.

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

## Troubleshooting

See [TROUBLESHOOTING.en.md](./TROUBLESHOOTING.en.md).

## Default Config Discovery

The script tries these paths in order:

- `~/.config/clash/config.yaml`
- `~/.config/mihomo/config.yaml`
- `~/.local/share/io.github.clash-verge-rev.clash-verge-rev/config.yaml`
- `~/.local/share/io.github.clash-verge-rev.clash-verge-rev/profiles/config.yaml`
- `~/.local/share/clash-verge/config.yaml`
- `~/.local/share/clash-verge/profiles/config.yaml`
- `~/Library/Application Support/clash/config.yaml`
- `~/Library/Application Support/mihomo/config.yaml`
- `~/Library/Application Support/ClashX/config.yaml`
- `~/Library/Application Support/ClashX Pro/config.yaml`
- `~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/config.yaml`
- `~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/profiles/config.yaml`
- `~/Library/Application Support/clash-verge/config.yaml`
- `~/Library/Application Support/clash-verge/profiles/config.yaml`
- `%LOCALAPPDATA%\\Clash for Windows\\.config\\config.yaml`
- `%LOCALAPPDATA%\\clash\\config.yaml`
- `%LOCALAPPDATA%\\mihomo\\config.yaml`
- `%APPDATA%\\clash\\config.yaml`
- `%APPDATA%\\mihomo\\config.yaml`
- `%APPDATA%\\io.github.clash-verge-rev.clash-verge-rev\\config.yaml`
- `%APPDATA%\\io.github.clash-verge-rev.clash-verge-rev\\profiles\\config.yaml`
- `%APPDATA%\\clash-verge\\config.yaml`
- `%APPDATA%\\clash-verge\\profiles\\config.yaml`

You can always override this with `--config`.

## Notes

- The precheck phase is safe to parallelize because it does not mutate the shared selector.
- The final validation phase is intentionally serial because selector switching is global state.
- Repeated high-frequency probing against `chatgpt.com` may trigger Cloudflare challenges. Use it manually, not as a tight cron loop.

## Todo

- add support for claude family
- add routinely check
