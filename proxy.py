import os
import requests

class ProxyHandler:
    def __init__(self, proxy_arg, config, verbose=False):
        self.original_env = os.environ.copy()
        # 安全获取代理配置
        proxy_config = config.get_proxy() or {}
        self.proxy_url = proxy_arg or proxy_config.get('url')
        self.verbose = verbose

    def setup_proxy_env(self):
        env = os.environ.copy()
        if self.proxy_url:
            try:
                requests.get(self.proxy_url, timeout=2)
            except Exception as e:
                print(f'Error connecting to proxy server: {e}')
                print("无法连接到代理服务器, 代理模式将不可用")
                self.proxy_url = None
                return env
            if self.verbose:
                print(f"🌐 设置代理: {self.proxy_url}")
            env['HTTP_PROXY'] = self.proxy_url
            env['HTTPS_PROXY'] = self.proxy_url
        return env

    def restore_proxy_settings(self):
        if self.proxy_url and self.verbose:
            print("恢复原始代理设置")
        