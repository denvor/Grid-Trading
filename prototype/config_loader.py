"""加载币种配置。"""
import configparser
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.ini")

_config = configparser.ConfigParser()
_config.read(CONFIG_PATH, encoding="utf-8")


def get_symbols() -> list[dict]:
    """返回所有币种配置列表。"""
    symbols = []
    for section in _config.sections():
        symbols.append({
            "symbol": section.upper(),
            "name": _config.get(section, "name"),
            "entry_price": _config.get(section, "entry_price"),
            "upper_pct": _config.get(section, "upper_pct"),
            "lower_pct": _config.get(section, "lower_pct"),
            "grid_size": _config.get(section, "grid_size"),
            "quantity_per_grid": _config.get(section, "quantity_per_grid"),
            "capital": _config.get(section, "capital"),
        })
    return symbols


def get_symbol(symbol: str) -> dict | None:
    """返回指定币种配置，不存在返回 None。"""
    for s in get_symbols():
        if s["symbol"] == symbol.upper():
            return s
    return None
