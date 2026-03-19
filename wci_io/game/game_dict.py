from typing import Dict, Callable, Any, List, Tuple
from functools import wraps

# 全局字典，用于存储所有游戏的buffer和pattern数据
buffer_dict: Dict[str, Dict[str, Any]] = {}
pattern_dict: Dict[str, Dict[str, Any]] = {}

# 已注册的游戏信息: {game_key: name}
registered_games: Dict[str, str] = {}


def register_buffer(game_key: str, name: str):
    """
    装饰器，用于注册游戏的buffer字典。
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if result:
                buffer_dict[game_key] = result
                # 同时注册游戏信息
                if game_key not in registered_games:
                    registered_games[game_key] = name
            return result
        # 立即执行以注册数据
        wrapper()
        return wrapper
    return decorator


def register_pattern(game_key: str, name: str):
    """
    装饰器，用于注册游戏的pattern字典。
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if result:
                pattern_dict[game_key] = result
                # 同时注册游戏信息
                if game_key not in registered_games:
                    registered_games[game_key] = name
            return result
        # 立即执行以注册数据
        wrapper()
        return wrapper
    return decorator


def get_registered_games() -> List[str]:
    """
    获取已注册的游戏信息。
    """
    return list(registered_games.keys())


def game_to_enum_items() -> List[Tuple[str, str, str, int]]:
    """
    生成枚举项列表
    """
    items = []
    for index, (game_key, name) in enumerate(sorted(registered_games.items())):
        items.append((game_key, game_key, name, index))
    return items
