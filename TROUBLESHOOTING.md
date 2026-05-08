# 故障排查

[English](./TROUBLESHOOTING.en.md) | [返回中文 README](./README.md)

## `git clone https://github.com/...` 无法解析或超时

有些网络环境下，GitHub 的 HTTPS 访问会不稳定。可以直接改用 SSH 地址：

```bash
git clone git@github.com:YourongZhou/autoprobe.git
```

用下面的命令确认 SSH 可用：

```bash
ssh -T git@github.com
```

GitHub 正常会返回认证成功提示。它同时提示不提供 shell access 也是正常现象。

## Clash controller 无法连接

如果 `autoprobe --dry-run` 报错类似 `Failed to connect to 127.0.0.1 port ...`，先确认 Clash / Mihomo / Clash Verge 正在运行，并且配置中的 controller 和当前实际使用的应用一致。

先检查配置里的 controller：

```yaml
external-controller: 127.0.0.1:9090
secret: your-secret
```

必要时显式传参：

```bash
autoprobe --controller http://127.0.0.1:9090 --secret your-secret --dry-run
```

## Controller 返回 `Unauthorized`

这说明 controller 能连通，但 `secret` 缺失或者不对。把 Clash / Mihomo 配置里的 `secret` 拿出来，通过 `--secret` 传入，或者写到 `autoprobe` 自动发现的配置文件里。

## 代理端口能连，但 OpenAI / ChatGPT 请求超时

这通常表示本地代理进程是活的，但当前选中的节点无法访问一个或多个目标域名。先跑一次 dry run，让 `autoprobe` 比较节点，但不永久切换：

```bash
autoprobe --dry-run
```

如果只是想先快速筛一轮：

```bash
autoprobe --dry-run --attempts 1 --timeout 8 --finalists 3 --top 8
```

## 在 Codex、VS Code、容器或沙箱里运行失败

某些开发环境默认不能访问宿主机上的 `127.0.0.1` 服务，除非显式授予 host network 访问权限。如果你的普通终端里能连 controller，但工具环境里不行，就在宿主机终端执行 `autoprobe`，或者给当前环境开放本地网络访问。
