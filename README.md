# Sponge Pet

一个适用于 Windows 10/11 的海绵宝宝桌面宠物，支持自由走动、跟随鼠标和吃蟹黄堡。

## 运行

安装 Windows 版 Python 3（包含 Tcl/Tk），解压后双击 `start.bat`。无需安装额外依赖，请保留 `assets` 文件夹和 `pet.ini`，并在 Windows 中运行。

## 操作

- **左键点击**：切换自由走动与跟随鼠标。
- **左键拖动**：移动宠物。
- **右键点击**：喂蟹黄堡，再次点击会重新播放动画。
- **点击托盘图标**：打开设置，调整大小、透明度和置顶，或暂停、隐藏、退出。

## 配置

修改 `pet.ini` 后重启生效：

```ini
[animation]
walk_fps = 4
eat_fps = 4

[movement]
walk_speed = 65
follow_speed = 220
```

`fps` 为动画帧率，速度单位为像素/秒；均支持正小数。

大小、透明度和置顶设置保存在 `%LOCALAPPDATA%\SpongePet\settings.json`。目前仅支持主显示器工作区。
