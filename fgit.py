#!/usr/bin/env python3
import sys
import subprocess
import argparse
import os
import json
from threading import Thread
from loguru import logger
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from colorama import Fore, Style, init
from utils.config import ConfigHandler
from utils.mirrors import select_mirror, convert_url
from utils.downloader import download_file
from utils.proxy import ProxyHandler

init(autoreset=True)

# 定义常量
GIT_COMMANDS_NEED_MIRROR = {'clone', 'pull', 'push', 'fetch'}
HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

parser = argparse.ArgumentParser(description='Git加速工具，支持镜像源和代理')
parser.add_argument('command', type=str, help='git命令, 或是fgit命令')
parser.add_argument('--use-proxy', type=str, help='设置HTTP代理（格式: http://[user:pass@]host:port）')
parser.add_argument('--branch', type=str, help='分支名(仅在download命令时有效)', default='main')
parser.add_argument('--verbose', action='store_true', help='显示详细输出')

args, unknown_args = parser.parse_known_args()

# 配置日志
logger.remove()
if args.verbose:
    logger.add(sys.stderr, level='DEBUG', colorize=True, format='{time:HH:mm:ss} | {level} | {message}')
else:
    logger.add(sys.stderr, level='INFO', colorize=True, format='{time:HH:mm:ss} | {level} | {message}')

def print_missing_arg():
    """打印缺少参数的提示"""
    logger.error(Fore.RED + "❌ 缺少必要参数" + Style.RESET_ALL)
    logger.error(' '.join(sys.argv))
    logger.error(len(sys.argv) * " " + "        ^^")
    logger.info(Fore.CYAN + "📖 使用帮助: fgit -h" + Style.RESET_ALL)

def main():
    """主函数"""
    config = ConfigHandler()
    proxy = ProxyHandler(args.use_proxy, config, args.verbose)
    env = proxy.setup_proxy_env()

    # 显示运行模式
    if proxy.proxy_url:
        logger.debug(Fore.CYAN + "🔧 运行于代理模式" + Style.RESET_ALL)
    else:
        logger.debug(Fore.CYAN + "🔧 运行于镜像模式" + Style.RESET_ALL)
    
    logger.debug(Fore.CYAN + f"命令参数: {' '.join(sys.argv)}" + Style.RESET_ALL)

    if not args.command or len(sys.argv) < 2:
        print_missing_arg()
        return

    # 处理 download 命令
    if args.command == 'download':
        handle_download_zip(args, unknown_args, config, env, args.verbose)
        return
    
    # 处理不需要镜像的 Git 命令
    if args.command not in GIT_COMMANDS_NEED_MIRROR:
        subprocess.run(['git'] + sys.argv[1:], env=env)
        return

    # 处理需要镜像的 Git 命令
    try:
        if args.command == 'clone':
            handle_clone(args, unknown_args, config, env, args.verbose, proxy)
        else:
            handle_other_commands(args, unknown_args, config, env, args.verbose, proxy)
    finally:
        proxy.restore_proxy_settings()


def handle_download_zip(args, unknown_args, config, env, verbose):
    """处理下载zip文件命令"""
    if unknown_args is None or len(unknown_args) < 1:
        print_missing_arg()
        return
    
    downloader_config = config.get_downloader_config()
    if not downloader_config:
        logger.warning(Fore.YELLOW + "🧐 下载配置不存在, 使用默认配置" + Style.RESET_ALL)
    
    chunk_size = downloader_config.get('chunk_size', 1024)
    min_file_size = downloader_config.get('min_file_size', 100)
    
    original_url = unknown_args[0]
    original_url = normalize_repo_url(original_url)

    repo_name = original_url.split('/')[-1].split('.git')[0]
    zip_filename = f"{repo_name}-{args.branch}.zip"
    zip_filepath = os.path.join(os.getcwd(), zip_filename)
    
    if os.path.exists(zip_filepath):
        logger.warning(Fore.YELLOW + f"😪 压缩包 {zip_filename} 已存在" + Style.RESET_ALL)
        return
    
    repo_status = get_repo(original_url)
    if repo_status is None:
        logger.warning(Fore.YELLOW + "🧐 无法获取到仓库信息, 尝试下载" + Style.RESET_ALL)
    elif repo_status is False and not input_with_timeout(Fore.YELLOW + "🧐 仓库可能不存在，5秒内按任意键忽略..." + Style.RESET_ALL, 5):
        return
        
    mirror_list = select_mirror(config, verbose)
    for mirror in mirror_list:
        new_url = convert_url(original_url, mirror) + f'/archive/refs/heads/{args.branch}.zip'
        logger.info(Fore.GREEN + f"🔄 尝试镜像源 {mirror} [{mirror_list.index(mirror) + 1}/{len(mirror_list)}]: {new_url}" + Style.RESET_ALL)
        if download_file(new_url, zip_filepath, chunk_size=chunk_size, MIN_FILE_SIZE=min_file_size):
            return
            
    logger.error(Fore.RED + "❌ 所有镜像源尝试失败" + Style.RESET_ALL)


def handle_clone(args, unknown_args, config, env, verbose, proxy):
    """处理克隆命令"""
    if unknown_args is None or len(unknown_args) < 1:
        print_missing_arg()
        return

    original_url = unknown_args[0]
    original_url = normalize_repo_url(original_url)

    # 查找是否指定了自定义 remote 名称
    remote_name = 'origin'  # 默认 remote 名称
    custom_remote_index = None
    for i, arg in enumerate(unknown_args):
        if arg in ['-o', '--origin'] and i + 1 < len(unknown_args):
            remote_name = unknown_args[i + 1]
            custom_remote_index = i
            break

    # 获取仓库路径
    if len(unknown_args) >= 2 and not unknown_args[-2].startswith('-') and not unknown_args[-1].startswith('-'):
        # 用户指定了目标目录
        repo_path = os.path.join(os.getcwd(), unknown_args[-1])
        repo_name = unknown_args[-1]
    else:
        # 使用默认仓库名
        repo_name = original_url.split('/')[-1].split('.git')[0]
        repo_path = os.path.join(os.getcwd(), repo_name)
    
    if os.path.exists(repo_path):
        logger.warning(Fore.YELLOW + f"😪 仓库 {repo_name} 已存在" + Style.RESET_ALL)
        return
    
    repo_status = get_repo(original_url)
    if repo_status is None:
        logger.warning(Fore.YELLOW + "🧐 无法获取到仓库信息, 尝试克隆" + Style.RESET_ALL)
    elif repo_status is False and not input_with_timeout(Fore.YELLOW + "🧐 仓库可能不存在，5秒内按任意键忽略..." + Style.RESET_ALL, 5):
        return
    
    # 如果设置了代理，则优先使用代理模式
    if proxy.proxy_url:
        cmd = ['git', 'clone', original_url] + unknown_args[1:]
        result = subprocess.run(cmd, env=env, check=False)
        if result.returncode == 0:
            return
        else:
            logger.error(Fore.RED + "❌ 在代理模式下克隆失败, 尝试使用镜像模式..." + Style.RESET_ALL)
            
    # 使用镜像源尝试克隆
    mirror_list = select_mirror(config, verbose)
    for mirror in mirror_list:
        new_url = convert_url(original_url, mirror)
        logger.info(Fore.GREEN + f"🔄 尝试镜像源 {mirror} [{mirror_list.index(mirror) + 1}/{len(mirror_list)}]: {new_url}" + Style.RESET_ALL)
        cmd = ['git', 'clone', new_url] + unknown_args[1:]
        result = subprocess.run(cmd, env=env, check=False)
        if result.returncode == 0:
            # 克隆成功后，将远程仓库地址还原为原始地址
            subprocess.run(['git', '-C', repo_path, 'remote', 'set-url', remote_name, original_url], check=True)
            return
            
    logger.error(Fore.RED + "❌ 所有镜像源尝试失败" + Style.RESET_ALL)


def handle_other_commands(args, unknown_args, config, env, verbose, proxy):
    """处理其他Git命令 (pull, push, fetch等)"""
    if not os.path.exists(os.path.join(os.getcwd(), '.git')):
        logger.warning(Fore.YELLOW + "❌ 当前目录不是有效的 Git 仓库" + Style.RESET_ALL)
        return
        
    git_args = [args.command] + unknown_args
    result = subprocess.run(['git'] + git_args, env=env, check=False)
    
    # 如果命令执行成功，直接返回
    if result.returncode == 0:
        return
    # 如果使用代理但执行失败，则尝试镜像模式
    elif proxy.proxy_url:
        logger.error(Fore.RED + "❌ 在代理模式下运行失败, 尝试使用镜像模式..." + Style.RESET_ALL)
        
    # 使用镜像源尝试执行命令
    mirror_list = select_mirror(config, verbose)
    for mirror in mirror_list:
        modify_git_config(mirror)
        try:
            result = subprocess.run(['git'] + git_args, env=env, check=False)
            if result.returncode == 0:
                return
        finally:
            restore_git_config()
            
    logger.error(Fore.RED + "❌ 所有镜像源尝试失败" + Style.RESET_ALL)


def normalize_repo_url(url):
    """标准化仓库URL格式"""
    if '://' not in url and '/' in url:
        if '@' in url:  # SSH格式
            url = f"https://{url.split('@')[1].replace(':', '/', 1)}"
        else:  # 简写格式 (如 user/repo)
            url = f"https://github.com/{url}"
    return url.split('.git')[0]


def get_repo(repo_url):
    """
    获取仓库信息
    
    Args:
        repo_url (str): 仓库URL
        
    Returns:
        bool or None: True表示仓库存在，False表示仓库不存在，None表示获取信息失败
    """
    clean_url = repo_url.split('.git')[0] if repo_url.endswith('.git') else repo_url
    
    # 处理 URL 形式的仓库名
    if '://' in clean_url and '/' in clean_url:
        clean_url = clean_url.split('/')[-2] + '/' + clean_url.split('/')[-1]
        
    logger.debug(Fore.CYAN + f"🔍 正在获取仓库: {clean_url}" + Style.RESET_ALL)
    api_url = f"https://api.github.com/repos/{clean_url}"
    req = Request(api_url, headers=HEADERS)
    
    try:
        with urlopen(req) as response:
            if response.status == 200:
                result = json.loads(response.read().decode())
                logger.info(Fore.GREEN + f"✅ 获取到仓库信息: {result['full_name']}({result['id']})" + Style.RESET_ALL)
                return True
            elif response.status == 404:
                logger.warning(Fore.RED + "❌ 获取仓库信息失败，该仓库可能不存在或未公开" + Style.RESET_ALL)
                return False
            else:
                logger.debug(Fore.RED + f"❌ 获取仓库信息失败: {response.status} {response.reason}" + Style.RESET_ALL)
                return None
                
    except HTTPError as e:
        if e.code == 404:
            logger.warning(Fore.RED + "❌ 获取仓库信息失败，该仓库可能不存在或未公开" + Style.RESET_ALL)
            return False
        else:
            logger.debug(Fore.RED + f"❌ 获取仓库信息失败: {e}" + Style.RESET_ALL)
            return None
            
    except Exception as e:
        logger.debug(Fore.RED + f"❌ 获取仓库信息失败: {e}" + Style.RESET_ALL)
        return None


def modify_git_config(mirror):
    """修改本地Git配置以使用镜像源"""
    subprocess.run(['git', 'config', '--local', 'url.https://github.com/.insteadOf', f'https://{mirror}'])


def restore_git_config():
    """恢复本地Git配置"""
    subprocess.run(['git', 'config', '--local', '--unset', 'url.https://github.com/.insteadOf'])


def input_with_timeout(prompt, timeout):
    """
    带超时的输入函数
    
    Args:
        prompt (str): 提示信息
        timeout (int): 超时时间（秒）
        
    Returns:
        bool: 用户是否在超时前输入了内容
    """
    logger.info(prompt)
    result = []
    thread = Thread(target=lambda: result.append(sys.stdin.read(1)))
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    return bool(result)


if __name__ == '__main__':
    try:
        print(Fore.GREEN + "fastgit🚀 by NaivG" + Style.RESET_ALL)
        main()
    except KeyboardInterrupt:
        logger.warning(Fore.YELLOW + "❗ 操作已取消" + Style.RESET_ALL)
    except Exception as e:
        logger.exception(Fore.RED + f"❌ 错误: {str(e)}" + Style.RESET_ALL)
        sys.exit(1)
    finally:
        sys.exit(0)