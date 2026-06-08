# -*- coding: utf-8 -*-
"""
计算「大块头 / 小不点」的身高(尺寸)、体重判定范围。

逻辑还原自小程序 pages/eggAppraisal（神秘蛋鉴定）页面：
  - 大块头(isDynamicBigGuy)  : 输入值贴近区间【上限】, 阈值 = 上限 - 2% * (上限-下限)
  - 小不点(isDynamicSmallGuy): 输入值贴近区间【下限】, 阈值 = 下限 + 5% * (上限-下限)
  - 身高与体重需【同时】满足才会被打上对应标签
源码对应 app-service.js:23754-23769

零依赖，纯标准库，python3 直接运行。
"""

# 与源码一致的常量
BIG_RATIO = 0.02     # 大块头: 顶部 2%
SMALL_RATIO = 0.05   # 小不点: 底部 5%
EPS = 1e-5           # 源码里的浮点容差 (_g = 1e-5)


def parse_range(s):
    """把 "0.23-0.31" 解析成 (min, max); 单值 "0.3" -> (0.3, 0.3); 空 -> None。"""
    if s is None or str(s).strip() == "":
        return None
    parts = [float(x) for x in str(s).split("-")]
    if len(parts) == 1:
        return (parts[0], parts[0])
    lo, hi = min(parts), max(parts)   # 源码会升序排序
    return (lo, hi)


def big_threshold(lo, hi):
    """大块头下界: 输入 >= 此值即算大块头 (含 1e-5 容差)。"""
    return hi - BIG_RATIO * (hi - lo) - EPS


def small_threshold(lo, hi):
    """小不点上界: 输入 <= 此值即算小不点 (含 1e-5 容差)。"""
    return lo + SMALL_RATIO * (hi - lo) + EPS


def calc_guy_ranges(size_str, weight_str):
    """
    输入尺寸范围字符串、体重范围字符串, 返回大块头/小不点的判定区间。

    返回结构:
    {
        "size":   (下限, 上限) 或 None,
        "weight": (下限, 上限) 或 None,
        "big":   {"size": (下界, 上限), "weight": (下界, 上限)},   # 大块头落在区间顶部
        "small": {"size": (下限, 上界), "weight": (下限, 上界)},   # 小不点落在区间底部
    }
    """
    size = parse_range(size_str)
    weight = parse_range(weight_str)

    result = {"size": size, "weight": weight, "big": {}, "small": {}}

    if size is not None:
        lo, hi = size
        result["big"]["size"] = (big_threshold(lo, hi), hi)
        result["small"]["size"] = (lo, small_threshold(lo, hi))
    if weight is not None:
        lo, hi = weight
        result["big"]["weight"] = (big_threshold(lo, hi), hi)
        result["small"]["weight"] = (lo, small_threshold(lo, hi))

    return result


def _fmt(rng):
    return "—" if rng is None else "{:.4f} ~ {:.4f}".format(rng[0], rng[1])


def describe(size_str, weight_str):
    """打印人类可读的结果。"""
    r = calc_guy_ranges(size_str, weight_str)
    print("输入  尺寸范围: {}   体重范围: {}".format(size_str, weight_str))
    print("  解析  尺寸: {}   体重: {}".format(_fmt(r["size"]), _fmt(r["weight"])))
    print("【大块头】(贴近上限)")
    print("    尺寸: {}".format(_fmt(r["big"].get("size"))))
    print("    体重: {}".format(_fmt(r["big"].get("weight"))))
    print("【小不点】(贴近下限)")
    print("    尺寸: {}".format(_fmt(r["small"].get("size"))))
    print("    体重: {}".format(_fmt(r["small"].get("weight"))))
    return r


if __name__ == "__main__":
    # 示例: 喵喵
    describe("0.23-0.31", "1.267-1.84")
