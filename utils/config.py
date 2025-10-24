import os
import configparser
import time

class ConfigHandler:
    """配置处理器，用于读取和保存用户配置"""
    
    def __init__(self):
        """初始化配置处理器"""
        self.config_file = os.path.expanduser('~/.fgit.conf')
        self.config = configparser.ConfigParser()
        self.load_config()

    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)

    def get_mirrors(self):
        """
        获取镜像源列表
        
        Returns:
            list or None: 镜像源列表，如果缓存过期或不存在则返回None
        """
        if (self.config.has_option('mirrors', 'sorted') and 
            time.time() - self.config.getfloat('mirrors', 'timestamp') < 3600):
            return self.config.get('mirrors', 'sorted').split(',')
        return None

    def save_mirrors(self, mirrors):
        """
        保存镜像源列表到配置文件
        
        Args:
            mirrors (list): 镜像源列表
        """
        if not self.config.has_section('mirrors'):
            self.config.add_section('mirrors')
        self.config.set('mirrors', 'sorted', ','.join(mirrors))
        self.config.set('mirrors', 'timestamp', str(time.time()))
        self._save()

    def get_proxy(self):
        """
        获取代理配置
        
        Returns:
            dict or None: 代理配置字典，如果没有配置则返回None
        """
        if self.config.has_section('proxy'):
            return dict(self.config.items('proxy'))
        return None

    def save_proxy(self, proxy):
        """
        保存代理配置
        
        Args:
            proxy (dict): 代理配置字典
        """
        if not self.config.has_section('proxy'):
            self.config.add_section('proxy')
        for k, v in proxy.items():
            self.config.set('proxy', k, v)
        self._save()

    def get_downloader_config(self):
        """
        获取下载器配置
        
        Returns:
            dict: 下载器配置字典
        """
        if self.config.has_section('downloader'):
            return dict(self.config.items('downloader'))
        
        # 如果没有配置节，创建默认配置
        self.config.add_section('downloader')
        self.config.set('downloader', 'chunk_size', '1024')
        self.config.set('downloader', 'min_file_size', '100')
        self._save()
        return dict(self.config.items('downloader'))

    def _save(self):
        """保存配置到文件"""
        with open(self.config_file, 'w') as f:
            self.config.write(f)