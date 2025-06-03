from loguru import logger
from ping3 import ping
from concurrent.futures import ThreadPoolExecutor
from prettytable import PrettyTable
from colorama import Fore, Style
from urllib.parse import urlparse

MIRRORS = {
    'github': 'https://github.com',
    'bgithub': 'https://bgithub.xyz',
    'ghproxy.net': 'https://ghproxy.net/https://github.com',
    'ghfast': 'https://ghfast.top/https://github.com',
    'ghp.ci': 'https://ghp.ci/https://github.com',
    'kgithub': 'https://kkgithub.com',
    'gitproxy.click': 'https://gitproxy.click/https://github.com',
    'moeyy01': 'https://github.moeyy.xyz/https://github.com',
    'gitclone': 'https://gitclone.com/github.com',
    'tbedu': 'https://github.tbedu.top/https://github.com',
    'llkk': 'https://gh.llkk.cc/https://github.com',
    'gh-deno': 'https://gh-deno.mocn.top/https://github.com'
}

RAWCONTENT_MIRRORS = {
    'github': 'https://raw.githubusercontent.com',
    'ghproxy.net': 'https://ghproxy.net/https://raw.githubusercontent.com',
}

def test_latency(verbose=False):
    logger.debug(Fore.CYAN + "🔎 测试镜像源延迟..." + Style.RESET_ALL)
    table = PrettyTable()
    table.field_names = ['Git 镜像源', 'Latency 延迟']
    
    results = {}
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(test_single, name, url): name for name, url in MIRRORS.items()}
        for future in futures:
            name, latency = future.result()
            results[name] = latency
            if latency is not None and latency != 0.0:
                color = Fore.GREEN if latency < 200 else Fore.YELLOW if latency < 500 else Fore.RED
                table.add_row([name, color + f"{latency:.1f}ms" + Style.RESET_ALL])
            else:
                table.add_row([name, Fore.RED + "超时" + Style.RESET_ALL])
    
    if verbose:
        print(table)
    
    sorted_mirrors = sorted(results.items(), key=lambda x: x[1] or float('inf'))
    return [k for k, v in sorted_mirrors if v]

def test_single(name, url):
    host = urlparse(url).netloc
    try:
        return (name, ping(host, unit='ms', timeout=2))
    except:
        return (name, None)

def select_mirror(config, verbose=False):
    if cached := config.get_mirrors():
        logger.debug(Fore.CYAN + f"✔️ 已选择 {cached}(缓存) 作为 Git 镜像源" + Style.RESET_ALL)
        return cached
    mirrors = test_latency(verbose)
    config.save_mirrors(mirrors)
    logger.debug(Fore.CYAN + f"✔️ 已选择 {mirrors} 作为 Git 镜像源" + Style.RESET_ALL)
    return mirrors

def convert_url(url, mirror):
    if mirror == 'github':
        return url
    base = MIRRORS[mirror]
    return url.replace('https://github.com', base)