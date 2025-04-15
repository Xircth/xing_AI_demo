import json, os, logging
from logging.handlers import RotatingFileHandler

class Config:
    _instance = None
    def __new__(cls, config_path='config.json'): return cls._instance if cls._instance else super().__new__(cls) # 单例模式
    
    def __init__(self, config_path='config.json'):
        if not hasattr(self, 'config'):
            with open(config_path, 'r', encoding='utf-8') as f: self.config = json.load(f) # 加载配置文件

    def get(self, key=None): return self.config[key] if key else self.config # 获取配置
    
    def set(self, key, value): 
        if key in self.config: self.config[key] = value # 更新配置
        
    def save(self, config_path='config.json'):
        with open(config_path, 'w', encoding='utf-8') as f: json.dump(self.config, f, indent=4) # 保存配置

def setup_logger(name, log_file=None, level=logging.INFO):
    """设置日志记录器，确保处理器不重复添加"""
    cfg = Config().get('logging') # 获取日志配置
    logger = logging.getLogger(name)
    
    # 如果logger已有处理器，说明已配置过，直接返回
    if logger.handlers:
        return logger
        
    logger.setLevel(level if not cfg else getattr(logging, cfg['level']))
    logger.propagate = False  # 避免日志传播到根logger
    
    # 创建日志目录
    if not log_file and cfg and 'file' in cfg:
        log_dir = os.path.dirname(cfg['file'])
        if not os.path.exists(log_dir): os.makedirs(log_dir)
        log_file = cfg['file']
        
    if log_file:
        handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=3) # 设置日志轮转
        file_format = cfg.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s') # Default with name
        handler.setFormatter(logging.Formatter(file_format))
        logger.addHandler(handler)
    
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console_format = '[%(name)s] %(levelname)s: %(message)s' # Simple format with name
    console.setFormatter(logging.Formatter(console_format))
    logger.addHandler(console)
    
    return logger 