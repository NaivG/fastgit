# fastgit🚀

🚀加速git命令，让git clone再次伟大<s>(MGGA)</s>

一个基于Python的Git加速工具，支持镜像源自动选择与代理配置，提升克隆/拉取仓库速度。

最近git clone速度一直很慢，时不时还直接爆炸，于是想着自己写个工具来加速git clone。一番搜索后，发现了[fgit](https://github.com/fastgh/fgit)这个项目，但是大概或许已经似了，一年没更新了，于是自己动手写了一个。 <s>(某种意义上也算是一种继承？)</s>

本项目采用 `AGPL-3.0` 协议开源，详情请参阅 `LICENSE` 文件。

    Copyright (C) 2025-2026 NaivG (https://github.com/NaivG)

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.


## 主要功能

**完全无感化**，和常规的git命令行相同，支持各种命令行参数，也就是说，平时git命令行怎么用，fgit就怎么用，区别只是git换成了fgit。

- **镜像加速**  
  自动测试多个Git镜像源延迟，选择最快的源进行克隆/拉取(支持`clone`/`pull`/`push`/`fetch`)。
- **下载文件**
  支持直接下载仓库压缩包(TODO: 支持下载release文件)。
- **代理支持**  
  可通过命令行参数或配置文件设置HTTP/HTTPS代理。
- **智能缓存**  
  镜像测速结果缓存1小时，减少重复测试开销。
- **兼容性**  
  支持SSH/HTTPS格式仓库地址自动转换。
- **友好交互**  
  彩色终端输出、超时提示、详细日志（`--verbose`模式）。

---

## 安装与使用

### 直接使用

1. 下载编译后的可执行文件：[releases](https://github.com/NaivG/fastgit/releases)(稳定版)  / [GitHub Actions](https://github.com/NaivG/fastgit/actions)(最新版)
2. 将可执行文件加入系统路径环境变量，或是移动到PATH目录下，如`C:\Windows\System32`
3. 打开命令行，输入`fgit`命令，即可使用加速版git命令。

### 自行编译

1. 安装python3.9+环境，并安装依赖包
   
```bash
pip install -r requirements.txt
```

1. 克隆项目
   
```bash
git clone https://github.com/NaivG/fgit.git
```

1. 进入项目目录，使用python库编译可执行文件
   
**本项目选择nuitka编译，若需复现则编译前请先安装Visual C++ Build Tools**

```bash
pip install nuitka
nuitka --standalone --onefile fgit.py
```


### 基础命令
```bash
# 克隆仓库（自动选择镜像源）
fgit clone <仓库URL>
fgit clone <user>/<repo> # fgit的特色方式，会自动转换为https://github.com/<user>/<repo>

# 拉取仓库（在失败时自动选择镜像源）
fgit pull

# 下载仓库压缩包（自动选择镜像源）
fgit download-zip <仓库URL>
fgit download-zip <user>/<repo>

# 启用代理
fgit --use-proxy http://127.0.0.1:7890 clone <仓库URL>
fgit --use-proxy http://127.0.0.1:7890 push

# 显示详细输出
fgit --verbose clone <仓库URL>

...
```

**本项目的配置文件默认保存在`C:\Users\USERNAME\.fgit.conf`或`~/.fgit.conf`文件中。**

## bug反馈

如果遇到任何问题，欢迎提交issue。

## 鸣谢

- 感谢以下git镜像源(排序不分先后)：
  - [bgithub.xyz](https://bgithub.xyz)
  - [ghproxy.net](https://ghproxy.net)
  - [ghfast.top](https://ghfast.top)
  - [ghp.ci](https://ghp.ci)
  - [kgithub.com](https://kkgithub.com)
  - [gitproxy.click](https://gitproxy.click)
  - [moeyy.xyz](https://github.moeyy.xyz)
  - [gitclone.com](https://gitclone.com)
  - [tbedu](https://github.tbedu.top)
  - [gh.llkk.cc](https://gh.llkk.cc)
  - [gh-deno.mocn.top](https://gh-deno.mocn.top)

- 感谢[fgit](https://github.com/fastgh/fgit)项目，本项目的实现参考了fgit项目，在此基础上进行了重构，并添加了一些新的功能。


Star History：

[![Star History Chart](https://api.star-history.com/svg?repos=NaivG/fastgit&type=Date)](https://star-history.com/#NaivG/fastgit&Date)