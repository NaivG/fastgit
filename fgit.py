#!/usr/bin/env python3
import sys
import subprocess
import argparse
import os
import json
import threading
from loguru import logger
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from colorama import Fore, Style, init
from config import ConfigHandler
from mirrors import select_mirror, convert_url
from downloader import download_file
from proxy import ProxyHandler

init(autoreset=True)

parser = argparse.ArgumentParser(description='Git加速工具，支持镜像源和代理')
parser.add_argument('command', type=str, help='git命令, 或是fgit命令')
parser.add_argument('--use-proxy', type=str, help='设置HTTP代理（格式: http://[user:pass@]host:port）')
parser.add_argument('--verbose', action='store_true', help='显示详细输出')
args, unknown_args = parser.parse_known_args()

logger.remove()
logger.add(sys.stderr, level='DEBUG', colorize=True, format='{time:HH:mm:ss} | {level} | {message}') if args.verbose else logger.add(sys.stderr, level='INFO', colorize=True, format='{time:HH:mm:ss} | {level} | {message}')

GIT_COMMANDS_NEED_MIRROR = {'clone', 'pull', 'push', 'fetch'}

headers = {'User-Agent': 'Mozilla/5.0',
           'Content-Type': 'application/json',
           'Accept': 'application/json'
           }

def main():
    config = ConfigHandler()

    proxy = ProxyHandler(args.use_proxy, config, args.verbose)
    env = proxy.setup_proxy_env()

    if proxy.proxy_url:
        logger.debug(Fore.CYAN + "🔧 运行于代理模式" + Style.RESET_ALL)
    else:
        logger.debug(Fore.CYAN + "🔧 运行于镜像模式" + Style.RESET_ALL)
    logger.debug(Fore.CYAN + f"命令参数: {' '.join(sys.argv)}" + Style.RESET_ALL)


    if args.command == 'download-zip':
        handle_download_zip(args, unknown_args, config, env, args.verbose)
        return
    
    if args.command not in GIT_COMMANDS_NEED_MIRROR:
        subprocess.run(['git'] + sys.argv[1:], env=env)
        return

    try:
        if args.command == 'clone':
            handle_clone(args, unknown_args, config, env, args.verbose, proxy)
        else:
            handle_other_commands(args, unknown_args, config, env, args.verbose, proxy)
    finally:
        proxy.restore_proxy_settings()

def handle_download_zip(args, unknown_args, config, env, verbose):
    downloader_config = config.get_downloader_config()
    if not downloader_config:
        logger.warning(Fore.YELLOW + "🧐 下载配置不存在, 使用默认配置" + Style.RESET_ALL)
    chunk_size = downloader_config.get('chunk_size', 1024)
    MIN_FILE_SIZE = downloader_config.get('min_file_size', 1)
    
    original_url = unknown_args[0]
    if '://' not in original_url and '/' in original_url:
        if '@' in original_url:  # SSH格式
            original_url = f"https://{original_url.split('@')[1].replace(':', '/', 1)}"
        else:  # 简写格式
            original_url = f"https://github.com/{original_url}"

    original_url = original_url.split('.git')[0]
    repo_name = original_url.split('/')[-1].split('.git')[0]
    if os.path.exists(os.path.join(os.getcwd(), repo_name + '.zip')):
        logger.warning(Fore.YELLOW + f"😪 压缩包 {repo_name}.zip 已存在" + Style.RESET_ALL)
        return
    
    repo_status = get_repo(original_url)
    if repo_status is None:
        logger.warning(Fore.YELLOW + "🧐 无法获取到仓库信息, 尝试下载" + Style.RESET_ALL)
    elif repo_status is False and not input_with_timeout(Fore.YELLOW + "🧐 仓库可能不存在，5秒内按任意键忽略..." + Style.RESET_ALL, 5):
        return
        
    mirror_list = select_mirror(config, args.verbose)
    for mirror in mirror_list:
        new_url = convert_url(original_url, mirror) + '/archive/refs/heads/main.zip'
        logger.info(Fore.GREEN + f"🔄 尝试镜像源 {mirror} [{mirror_list.index(mirror) + 1}/{len(mirror_list)}]: {new_url}" + Style.RESET_ALL)
        if download_file(new_url, os.path.join(os.getcwd(), repo_name + '.zip'), chunk_size=chunk_size, MIN_FILE_SIZE=MIN_FILE_SIZE):
            return
    logger.error(Fore.RED + "❌ 所有镜像源尝试失败" + Style.RESET_ALL)
    return

def handle_clone(args, unknown_args, config, env, verbose, proxy):
    original_url = unknown_args[0]
    if '://' not in original_url and '/' in original_url:
        if '@' in original_url:  # SSH格式
            original_url = f"https://{original_url.split('@')[1].replace(':', '/', 1)}"
        else:  # 简写格式
            original_url = f"https://github.com/{original_url}"

    repo_name = original_url.split('/')[-1].split('.git')[0]
    if os.path.exists(os.path.join(os.getcwd(), repo_name)):
        logger.warning(Fore.YELLOW + f"😪 仓库 {repo_name} 已存在" + Style.RESET_ALL)
        return
    
    repo_status = get_repo(original_url)
    if repo_status is None:
        logger.warning(Fore.YELLOW + "🧐 无法获取到仓库信息, 尝试克隆" + Style.RESET_ALL)
    elif repo_status is False and not input_with_timeout(Fore.YELLOW + "🧐 仓库可能不存在，5秒内按任意键忽略..." + Style.RESET_ALL, 5):
        return
    
    if proxy.proxy_url: # 代理模式
        cmd = ['git', 'clone', original_url] + unknown_args[1:]
        result = subprocess.run(cmd, env=env, check=False)
        if result.returncode == 0:
            return
        else:
            logger.error(Fore.RED + "❌ 在代理模式下克隆失败, 尝试使用镜像模式..." + Style.RESET_ALL)
    mirror_list = select_mirror(config, verbose)
    for mirror in mirror_list:
        new_url = convert_url(original_url, mirror)
        logger.info(Fore.GREEN + f"🔄 尝试镜像源 {mirror} [{mirror_list.index(mirror) + 1}/{len(mirror_list)}]: {new_url}" + Style.RESET_ALL)
        cmd = ['git', 'clone', new_url] + unknown_args[1:]
        result = subprocess.run(cmd, env=env, check=False)
        if result.returncode == 0:
            repo_path = os.path.join(os.getcwd(), repo_name)
            subprocess.run(['git', '-C', repo_path, 'remote', 'set-url', 'origin', original_url], check=True) # 还原原始 URL
            return
    logger.error(Fore.RED + "❌ 所有镜像源尝试失败" + Style.RESET_ALL)

def handle_other_commands(args, unknown_args, config, env, verbose, proxy):
    if not os.path.exists(os.path.join(os.getcwd(), '.git')):
        logger.warning(Fore.YELLOW + "❌ 当前目录不是有效的 Git 仓库" + Style.RESET_ALL)
        return
    git_args = [args.command] + unknown_args
    result = subprocess.run(['git'] + git_args, env=env, check=False)
    if result.returncode == 0:
        return
    elif proxy.proxy_url:
        logger.error(Fore.RED + "❌ 在代理模式下运行失败, 尝试使用镜像模式..." + Style.RESET_ALL)
        
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

def get_repo(repo: str) -> bool | None:
    if repo.endswith('.git'):
        repo = repo[:-4]
    if '://' in repo and '/' in repo:
        repo = repo.split('/')[-2] + '/' + repo.split('/')[-1]  # 处理 URL 形式的仓库名
    logger.debug(Fore.CYAN + f"🔍 正在获取仓库: {repo}" + Style.RESET_ALL)
    url = f"https://api.github.com/repos/{repo}"
    req = Request(url, headers=headers)
    try:
        with urlopen(req) as response:
            if response.status == 200:
                result = json.loads(response.read().decode())
                # return [result['full_name'], result['id']]
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
    subprocess.run(['git', 'config', '--local', 'url.https://github.com/.insteadOf', f'https://{mirror}'])

def restore_git_config():
    subprocess.run(['git', 'config', '--local', '--unset', 'url.https://github.com/.insteadOf'])

def input_with_timeout(prompt, timeout):
    logger.info(prompt)
    result = []
    thread = threading.Thread(target=lambda: result.append(sys.stdin.read(1)))
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