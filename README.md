# Porthole

一个在终端里查看本机监听 TCP / UDP 端口的 TUI 小工具。

## 安装

### 安装预编译二进制

默认安装最新 release 到 `~/.local/bin`：

```bash
curl -fsSL https://raw.githubusercontent.com/srt180/porthole/main/scripts/install.sh | bash
```

安装指定版本：

```bash
curl -fsSL https://raw.githubusercontent.com/srt180/porthole/main/scripts/install.sh | bash -s -- --version v0.1.3
```

自定义安装目录：

```bash
curl -fsSL https://raw.githubusercontent.com/srt180/porthole/main/scripts/install.sh | bash -s -- --bin-dir /usr/local/bin
```

脚本会自动识别当前平台，并从 GitHub Releases 下载对应的二进制文件安装到目标目录。当前提供：

- macOS `arm64`
- macOS `x86_64`
- Linux `x86_64`
- Linux `arm64`

Linux 预编译二进制使用 `manylinux2014` 环境构建，目标兼容 `glibc >= 2.17` 的主流发行版。

安装后确认 `~/.local/bin` 或你指定的目录已经在 `PATH` 中，然后执行：

```bash
porthole
```

## 当前能力

- 查看本机 TCP / UDP 监听列表
- 查看端口对应的进程名、PID、用户、FD
- 查看进程可执行文件路径与工作目录
- 支持协议过滤与刷新

## 运行要求

- Python 3.11+
- 系统已安装 `lsof`
- 首版优先支持 macOS，兼容支持 `lsof` 的 Linux 环境

说明：

- 预编译二进制不需要本机安装 Python
- Linux 版本不是完全静态链接，仍依赖目标系统提供 `glibc`
- 当前程序运行时仍需要系统里有 `lsof`

## 启动

```bash
python3 main.py
```

## 发布

推送形如 `v0.1.3` 的 tag 后，GitHub Actions 会自动：

- 校验 tag 版本与 `pyproject.toml` 中的版本一致
- 运行测试
- 在 `manylinux2014` / macOS 环境中构建各平台单文件二进制
- 创建 GitHub Release 并上传构建产物

示例：

```bash
git tag v0.1.3
git push origin v0.1.3
```

## 快捷键

- `j` / `k` 或方向键：移动选中项
- `a`：查看全部协议
- `t`：仅查看 TCP
- `u`：仅查看 UDP
- `r`：刷新
- `q`：退出

## 测试

```bash
python3 -m unittest discover -s tests
```

## 文档

- 需求文档：[docs/requirements.md](docs/requirements.md)
