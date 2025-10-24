import os
from loguru import logger
import requests


class ProxyHandler:
    """代理处理器"""
    
    def __init__(self, proxy_arg, config, verbose=False):
        """
        初始化代理处理器
        
        Args:
            proxy_arg (str): 命令行传入的代理URL
            config (ConfigHandler): 配置处理器实例
            verbose (bool): 是否显示详细信息
        """
        self.original_env = os.environ.copy()
        # 安全获取代理配置
        proxy_config = config.get_proxy() or {}
        self.proxy_url = proxy_arg or proxy_config.get('url')
        self.verbose = verbose

    def setup_proxy_env(self):
        """
        设置代理环境变量
        
        Returns:
            dict: 环境变量字典
        """
        env = os.environ.copy()
        if self.proxy_url:
            try:
                requests.get(self.proxy_url, timeout=2)
            except Exception as e:
                logger.exception(f'Error connecting to proxy server: {e}')
                logger.error("无法连接到代理服务器, 代理模式将不可用")
                self.proxy_url = None
                return env
            logger.debug(f"🌐 设置代理: {self.proxy_url}")
            env['HTTP_PROXY'] = self.proxy_url
            env['HTTPS_PROXY'] = self.proxy_url
        return env

    def restore_proxy_settings(self):
        """恢复代理设置"""
        if self.proxy_url and self.verbose:
            logger.info("恢复原始代理设置")