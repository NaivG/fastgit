import os
import configparser
import time

class ConfigHandler:
    def __init__(self):
        self.config_file = os.path.expanduser('~/.fgit.conf')
        self.config = configparser.ConfigParser()
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)

    def get_mirrors(self):
        if self.config.has_option('mirrors', 'sorted') and \
           time.time() - self.config.getfloat('mirrors', 'timestamp') < 3600:
            return self.config.get('mirrors', 'sorted').split(',')
        return None

    def save_mirrors(self, mirrors):
        if not self.config.has_section('mirrors'):
            self.config.add_section('mirrors')
        self.config.set('mirrors', 'sorted', ','.join(mirrors))
        self.config.set('mirrors', 'timestamp', str(time.time()))
        self._save()

    def get_proxy(self):
        if self.config.has_section('proxy'):
            return dict(self.config.items('proxy'))
        return None

    def save_proxy(self, proxy):
        if not self.config.has_section('proxy'):
            self.config.add_section('proxy')
        for k, v in proxy.items():
            self.config.set('proxy', k, v)
        self._save()

    def _save(self):
        with open(self.config_file, 'w') as f:
            self.config.write(f)