import os

class ProxyHandler:
    def __init__(self, proxy_arg, config, verbose):
        self.original_env = os.environ.copy()
        # 安全获取代理配置
        proxy_config = config.get_proxy() or {}
        self.proxy_url = proxy_arg or proxy_config.get('url')
        self.verbose = verbose

    def setup_proxy_env(self):
        env = os.environ.copy()
        if self.proxy_url:
            if self.verbose:
                print(f"设置代理: {self.proxy_url}")
            env['HTTP_PROXY'] = self.proxy_url
            env['HTTPS_PROXY'] = self.proxy_url
        return env

    def restore_proxy_settings(self):
        if self.proxy_url and self.verbose:
            print("恢复原始代理设置")