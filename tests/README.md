# 测试入口

- offline/：只用标准库，内部按 contracts、planning、artifacts、workflow、robot、api 分组。
- robot/：需要项目 SDK 环境，使用模拟传输或离线反馈帧，不连接设备。
- test_drawing.py：仅兼容旧 unittest 发现命令，实际测试全部转发到 offline/。

从仓库根目录运行：

```sh
PYTHONPATH=src python3.12 -S -m unittest discover -s tests/offline -t . -v
PYTHONPATH=src python3.12 -S -m unittest tests.offline.planning.test_planar -v
PYTHONPATH=src python -m pytest -q
```

新增测试放到对应模块；共享小型样例读取函数在 offline/support.py。
