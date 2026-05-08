# Troubleshooting

[中文](./TROUBLESHOOTING.md) | [Back to English README](./README.en.md)

## `git clone https://github.com/...` cannot resolve or times out

Some networks have unstable HTTPS access to GitHub. Use the SSH URL instead:

```bash
git clone git@github.com:YourongZhou/autoprobe.git
```

Verify SSH access with:

```bash
ssh -T git@github.com
```

GitHub should respond with a successful authentication message. It is normal for GitHub to say it does not provide shell access.

## Clash controller is unreachable

If `autoprobe --dry-run` fails with an error like `Failed to connect to 127.0.0.1 port ...`, check that Clash / Mihomo / Clash Verge is running and that the configured controller matches your active app.

Check the controller in your config:

```yaml
external-controller: 127.0.0.1:9090
secret: your-secret
```

Then pass the values explicitly if needed:

```bash
autoprobe --controller http://127.0.0.1:9090 --secret your-secret --dry-run
```

## Controller returns `Unauthorized`

The controller is reachable, but the secret is missing or wrong. Copy the `secret` value from your Clash / Mihomo config and pass it with `--secret`, or set it in the config file that `autoprobe` discovers.

## Proxy port connects but OpenAI / ChatGPT requests time out

This usually means the local proxy is running, but the current selected node cannot reach one or more target domains. Run a dry run so `autoprobe` can compare nodes without permanently switching:

```bash
autoprobe --dry-run
```

For a faster first pass:

```bash
autoprobe --dry-run --attempts 1 --timeout 8 --finalists 3 --top 8
```

## Running inside Codex, VS Code, containers, or sandboxes

Some development environments cannot access host `127.0.0.1` services unless they are granted host network access. If the controller works in your normal terminal but fails inside the tool, run `autoprobe` from the host terminal or allow the environment to access local network services.
