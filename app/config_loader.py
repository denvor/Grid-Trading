"""加载币种配置。"""
import configparser
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.ini")

_config = configparser.ConfigParser()
_config.read(CONFIG_PATH, encoding="utf-8")


def get_symbols() -> list[dict]:
    """返回所有币种配置列表（仅包含有 'name' 字段的 section）。"""
    symbols = []
    for section in _config.sections():
        # 跳过非币种 section（如 [api] [database]）
        if not _config.has_option(section, "name"):
            continue
        symbols.append({
            "symbol": section.upper(),
            "name": _config.get(section, "name"),
            "entry_price": _config.get(section, "entry_price"),
            "upper_pct": _config.get(section, "upper_pct"),
            "lower_pct": _config.get(section, "lower_pct"),
            "grid_size": _config.get(section, "grid_size"),
            "quantity_per_grid": _config.get(section, "quantity_per_grid"),
            "capital": _config.get(section, "capital"),
            "leverage": _config.get(section, "leverage", fallback="1"),
            "margin_mode": _config.get(section, "margin_mode", fallback="cross"),
        })
    return symbols


def get_symbol(symbol: str) -> dict | None:
    """返回指定币种配置，不存在返回 None。"""
    for s in get_symbols():
        if s["symbol"] == symbol.upper():
            return s
    return None


def save_symbol(symbol: str, capital: str, leverage: str, upper_price: str,
                lower_price: str, grid_size: str, quantity_per_grid: str,
                margin_mode: str) -> None:
    """保存币种参数到 config.ini（保留 entry_price / upper_pct / lower_pct 等原始字段）。"""
    section = symbol.upper()
    if not _config.has_section(section):
        return
    # 仅更新用户可编辑字段
    _config.set(section, "capital", str(capital))
    _config.set(section, "grid_size", str(grid_size))
    _config.set(section, "quantity_per_grid", str(quantity_per_grid))
    _config.set(section, "leverage", str(leverage))
    _config.set(section, "margin_mode", str(margin_mode))
    # 同步更新 upper_pct / lower_pct（基于 entry_price 反算）
    entry = _config.get(section, "entry_price", fallback="0")
    try:
        entry_f = float(entry)
        if entry_f > 0 and float(upper_price) > 0:
            _config.set(section, "upper_pct", f"{(float(upper_price) / entry_f - 1) * 100:.4f}")
        if entry_f > 0 and float(lower_price) > 0:
            _config.set(section, "lower_pct", f"{(1 - float(lower_price) / entry_f) * 100:.4f}")
    except (ValueError, ZeroDivisionError):
        pass
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        _config.write(f)
