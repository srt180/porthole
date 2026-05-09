# Porthole

一个在终端里查看本机监听 TCP / UDP 端口的 TUI 小工具。

## 当前能力

- 查看本机 TCP / UDP 监听列表
- 查看端口对应的进程名、PID、用户、FD
- 查看进程可执行文件路径与工作目录
- 支持协议过滤与刷新

## 运行要求

- Python 3.11+
- 系统已安装 `lsof`
- 首版优先支持 macOS，兼容支持 `lsof` 的 Linux 环境

## 启动

```bash
python3 main.py
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
