"""蛋实验匹配器（egg experimental matcher）。

由 docs/egg/eggExperimentalMatcher.js 逐函数翻译而来，保持原有打分 / 混合 /
排序逻辑不变。原 JS 通过 spiritData.getBaseSpirits() 取得候选精灵列表，
Python 版本要求调用方显式传入 base_spirits（每个元素为包含
no / lengthMin / lengthMax / weightMin / weightMax 字段的 dict）。

对外接口：
    match_spirit_by_egg_experiment(egg_length, egg_weight, base_spirits, options=None)
    get_egg_experiment_debug_rules()
"""

import math


# --------------------------------------------------------------------------- #
# 模型参数与常量（对应原 JS 中的 n / g 以及一组单字母阈值常量）
# --------------------------------------------------------------------------- #

# n：当前线上模型参数
CURRENT_MODEL = {
    "bias": 56.350909,
    "diffWeight": 134.898298,
    "avgWeight": 28.493194,
    "targetAvg": 0.378347,
    "areaWeight": 0,
    "spanWeight": 0,
    "invAreaWeight": 0,
    "edgeWeight": 0,
    "highProgressWeight": 0,
    "lowProgressWeight": 0,
    "areaDivideWeight": 8.506597,
    "useAreaDivide": True,
    "outsideDistanceWeight": 180,
    "displayCap": 99.9,
    "activeDisplayFloor": 8.68,
    "fallbackDisplayLimit": 3,
    "displayLimit": 8,
}

# g：v4 实验模型参数
V4_MODEL = {
    "bias": -22.743668,
    "diffWeight": 225.833271,
    "avgWeight": 20.983889,
    "targetAvg": 0.071679,
    "areaWeight": -20.934591,
    "spanWeight": 6.796761,
    "invAreaWeight": 1.245147,
    "edgeWeight": 2.335249,
    "highProgressWeight": -46.029518,
    "lowProgressWeight": 51.45095,
    "areaDivideWeight": 16.425436,
    "useAreaDivide": False,
}

HYBRID_ENABLED = True            # h：是否启用 v4 混合打分
ZERO_V4_WEIGHT = 0               # o：v4 混合权重为 0（即纯当前模型）的哨兵值
FALLBACK_V4_WEIGHT = 0.08        # s：回退分支给出的 v4 权重
MIN_SHARE_FOR_FALLBACK = 0.55    # a：进入回退分支所需的最高占比阈值
MIN_GAP_FOR_FALLBACK = 0.02      # u：进入回退分支所需的占比差阈值
MAX_NORMALIZED_GAP = 0.06        # l：回退分支允许的归一化差值上限
DOMINANT_V4_WEIGHT = 0.58        # d：强势主导时直接给出的 v4 权重
DOMINANT_SHARE_THRESHOLD = 0.78  # r：强势主导的最高占比阈值
DOMINANT_GAP_THRESHOLD = 0.52    # w：强势主导的占比差阈值

# R：按精灵编号的额外打分修正（原 JS 中为空对象）
SPIRIT_SCORE_ADJUSTMENTS = {}

# b：本地 v4 权重乘数规则
LOCAL_V4_WEIGHT_RULES = [
    {"no": 220, "length": 0.32, "weight": 1.191, "lengthRadius": 0.006, "weightRadius": 0.006, "multiplier": 12},
    {"no": 220, "length": 0.32, "weight": 1.268, "lengthRadius": 0.006, "weightRadius": 0.006, "multiplier": 12},
    {"no": 220, "length": 0.34, "weight": 2.034, "lengthRadius": 0.006, "weightRadius": 0.006, "multiplier": 8},
    {"no": 220, "length": 0.35, "weight": 2.49, "lengthRadius": 0.006, "weightRadius": 0.001, "multiplier": 4},
    {"no": 220, "length": 0.35, "weight": 2.57, "lengthRadius": 0.006, "weightRadius": 0.006, "multiplier": 4},
    {"no": 220, "length": 0.35, "weight": 2.5465, "lengthRadius": 0.001, "weightRadius": 0.015, "multiplier": 20},
]

# c：本地冲突加成规则
LOCAL_CONFLICT_RULES = [
    {"no": 220, "length": 0.34, "weight": 2.034, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 100},
    {"no": 220, "length": 0.35, "weight": 2.49, "lengthRadius": 0.006, "weightRadius": 0.001, "boost": 80},
    {"no": 220, "length": 0.34, "weight": 2.63, "lengthRadius": 0.001, "weightRadius": 0.04, "boost": 18},
    {"no": 220, "length": 0.35, "weight": 2.268, "lengthRadius": 0.001, "weightRadius": 0.003, "boost": 50},
    {"no": 274, "length": 0.2, "weight": 1.635, "lengthRadius": 0.012, "weightRadius": 0.12, "boost": 7.825},
    {"no": 44, "length": 0.19, "weight": 2.078, "lengthRadius": 0.012, "weightRadius": 0.12, "boost": 7.012},
    {"no": 137, "length": 0.23, "weight": 2.578, "lengthRadius": 0.012, "weightRadius": 0.12, "boost": 7.028},
    {"no": 299, "length": 0.15, "weight": 0.519, "lengthRadius": 0.012, "weightRadius": 0.12, "boost": 7.606},
    {"no": 283, "length": 0.2, "weight": 2.35, "lengthRadius": 0.012, "weightRadius": 0.12, "boost": 4.684},
    {"no": 283, "length": 0.24, "weight": 2.783, "lengthRadius": 0.012, "weightRadius": 0.12, "boost": 7.318},
    {"no": 18, "length": 0.16, "weight": 1.003, "lengthRadius": 0.012, "weightRadius": 0.12, "boost": 3.87},
    {"no": 71, "length": 0.25, "weight": 1.562, "lengthRadius": 0.012, "weightRadius": 0.12, "boost": 8},
    {"no": 71, "length": 0.25, "weight": 1.568, "lengthRadius": 0.012, "weightRadius": 0.12, "boost": 8},
    {"no": 168, "length": 0.23, "weight": 1.531, "lengthRadius": 0.012, "weightRadius": 0.12, "boost": 7.63},
    {"no": 88, "length": 0.22, "weight": 1.74, "lengthRadius": 0.012, "weightRadius": 0.12, "boost": 8},
    {"no": 32, "length": 0.16, "weight": 1.419, "lengthRadius": 0.006, "weightRadius": 0.04, "boost": 5},
    {"no": 303, "length": 0.16, "weight": 1.308, "lengthRadius": 0.006, "weightRadius": 0.04, "boost": 8},
    {"no": 303, "length": 0.17, "weight": 1.527, "lengthRadius": 0.006, "weightRadius": 0.04, "boost": 35},
    {"no": 303, "length": 0.17, "weight": 1.388, "lengthRadius": 0.006, "weightRadius": 0.04, "boost": 40},
    {"no": 59, "length": 0.16, "weight": 1.632, "lengthRadius": 0.006, "weightRadius": 0.03, "boost": 150},
    {"no": 59, "length": 0.16, "weight": 1.742, "lengthRadius": 0.006, "weightRadius": 0.025, "boost": 160},
    {"no": 59, "length": 0.19, "weight": 2.315, "lengthRadius": 0.006, "weightRadius": 0.035, "boost": 90},
    {"no": 303, "length": 0.17, "weight": 1.474, "lengthRadius": 0.006, "weightRadius": 0.035, "boost": 80},
    {"no": 229, "length": 0.31, "weight": 16.881, "lengthRadius": 0.008, "weightRadius": 0.25, "boost": 12},
    {"no": 185, "length": 0.19, "weight": 3.025, "lengthRadius": 0.006, "weightRadius": 0.05, "boost": 60},
    {"no": 210, "length": 0.17, "weight": 2.233, "lengthRadius": 0.006, "weightRadius": 0.05, "boost": 50},
    {"no": 82, "length": 0.22, "weight": 2.135, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 25},
    {"no": 82, "length": 0.22, "weight": 2.17, "lengthRadius": 0.006, "weightRadius": 0.012, "boost": 25},
    {"no": 234, "length": 0.14, "weight": 0.74, "lengthRadius": 0.018, "weightRadius": 0.18, "boost": -35},
    {"no": 234, "length": 0.16, "weight": 1.31, "lengthRadius": 0.012, "weightRadius": 0.12, "boost": -30},
    {"no": 280, "length": 0.16, "weight": 1.35, "lengthRadius": 0.018, "weightRadius": 0.25, "boost": -35},
    {"no": 280, "length": 0.17, "weight": 1.55, "lengthRadius": 0.012, "weightRadius": 0.12, "boost": -30},
    {"no": 177, "length": 0.22, "weight": 2.071, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 11.991},
    {"no": 289, "length": 0.37, "weight": 8.417, "lengthRadius": 0.006, "weightRadius": 0.02, "boost": 36.234},
    {"no": 289, "length": 0.42, "weight": 12.84, "lengthRadius": 0.006, "weightRadius": 0.02, "boost": 37.035},
    {"no": 277, "length": 0.27, "weight": 0.937, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 1.767},
    {"no": 239, "length": 0.15, "weight": 0.48, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 95.024},
    {"no": 125, "length": 0.27, "weight": 7.356, "lengthRadius": 0.006, "weightRadius": 0.02, "boost": 15.435},
    {"no": 108, "length": 0.19, "weight": 5.368, "lengthRadius": 0.006, "weightRadius": 0.02, "boost": 17.364},
    {"no": 274, "length": 0.21, "weight": 1.72, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 16.247},
    {"no": 162, "length": 0.25, "weight": 1.491, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 36.679},
    {"no": 162, "length": 0.25, "weight": 1.508, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 23.44},
    {"no": 76, "length": 0.29, "weight": 3.36, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 15.927},
    {"no": 76, "length": 0.29, "weight": 3.37, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 16.394},
    {"no": 137, "length": 0.24, "weight": 2.715, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 27.854},
    {"no": 47, "length": 0.32, "weight": 5.848, "lengthRadius": 0.006, "weightRadius": 0.02, "boost": 7.915},
    {"no": 47, "length": 0.36, "weight": 6.5, "lengthRadius": 0.006, "weightRadius": 0.02, "boost": 13.991},
    {"no": 47, "length": 0.38, "weight": 5.888, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 30},
    {"no": 128, "length": 0.17, "weight": 0.996, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 80.997},
    {"no": 49, "length": 0.23, "weight": 1.727, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 27.927},
    {"no": 49, "length": 0.28, "weight": 2.309, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 44.21},
    {"no": 32, "length": 0.19, "weight": 1.738, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 23.878},
    {"no": 41, "length": 0.18, "weight": 1.735, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 10.497},
    {"no": 41, "length": 0.22, "weight": 2.116, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 25.346},
    {"no": 132, "length": 0.23, "weight": 2.01, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 27.137},
    {"no": 283, "length": 0.25, "weight": 2.883, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 23.209},
    {"no": 283, "length": 0.27, "weight": 3.167, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 28.871},
    {"no": 21, "length": 0.19, "weight": 2.067, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 2.161},
    {"no": 21, "length": 0.23, "weight": 2.494, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 35.863},
    {"no": 21, "length": 0.24, "weight": 2.649, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 35.991},
    {"no": 21, "length": 0.25, "weight": 2.814, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 20.96},
    {"no": 163, "length": 0.31, "weight": 7.747, "lengthRadius": 0.006, "weightRadius": 0.02, "boost": 15.782},
    {"no": 18, "length": 0.16, "weight": 1.066, "lengthRadius": 0.006, "weightRadius": 0.002, "boost": 27.372},
    {"no": 18, "length": 0.17, "weight": 1.18, "lengthRadius": 0.006, "weightRadius": 0.002, "boost": 1.297},
    {"no": 18, "length": 0.18, "weight": 1.335, "lengthRadius": 0.006, "weightRadius": 0.002, "boost": 33.851},
    {"no": 18, "length": 0.19, "weight": 1.425, "lengthRadius": 0.006, "weightRadius": 0.002, "boost": 17.54},
    {"no": 18, "length": 0.19, "weight": 1.496, "lengthRadius": 0.006, "weightRadius": 0.002, "boost": 2.736},
    {"no": 18, "length": 0.19, "weight": 1.519, "lengthRadius": 0.006, "weightRadius": 0.002, "boost": 11.504},
    {"no": 18, "length": 0.21, "weight": 1.68, "lengthRadius": 0.006, "weightRadius": 0.002, "boost": 34.633},
    {"no": 71, "length": 0.22, "weight": 1.417, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 32.352},
    {"no": 270, "length": 0.21, "weight": 1.481, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 7.252},
    {"no": 270, "length": 0.22, "weight": 1.572, "lengthRadius": 0.006, "weightRadius": 0.006, "boost": 30.324},
    {"no": 132, "length": 0.21, "weight": 1.817, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 18},
    {"no": 193, "length": 0.21, "weight": 1.505, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 25},
    {"no": 193, "length": 0.22, "weight": 1.73, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 20},
    {"no": 88, "length": 0.23, "weight": 1.799, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 8},
    {"no": 85, "length": 0.23, "weight": 1.812, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 25},
    {"no": 193, "length": 0.21, "weight": 1.53, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 50},
    {"no": 193, "length": 0.21, "weight": 1.55, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 6},
    {"no": 220, "length": 0.35, "weight": 1.92, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 80},
    {"no": 95, "length": 0.41, "weight": 41.423, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 100},
    {"no": 177, "length": 0.2, "weight": 1.799, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 35},
    {"no": 177, "length": 0.21, "weight": 1.916, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 15},
    {"no": 177, "length": 0.21, "weight": 1.9485, "lengthRadius": 0.001, "weightRadius": 0.0025, "boost": 50},
    {"no": 261, "length": 0.19, "weight": 1.629, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 50},
    {"no": 41, "length": 0.21, "weight": 1.991, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 15},
    {"no": 63, "length": 0.2, "weight": 1.556, "lengthRadius": 0.001, "weightRadius": 0.007, "boost": 30},
    {"no": 179, "length": 0.21, "weight": 1.757, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 30},
    {"no": 274, "length": 0.21, "weight": 1.702, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 15},
    {"no": 274, "length": 0.21, "weight": 1.727, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 18},
    {"no": 274, "length": 0.21, "weight": 1.759, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 18},
    {"no": 18, "length": 0.2, "weight": 1.545, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 50},
    {"no": 18, "length": 0.21, "weight": 1.728, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 35},
    {"no": 18, "length": 0.21, "weight": 1.733, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 35},
    {"no": 18, "length": 0.21, "weight": 1.734, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 35},
    {"no": 125, "length": 0.26, "weight": 7.179, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 3},
    {"no": 27, "length": 0.2, "weight": 8.102, "lengthRadius": 0.001, "weightRadius": 0.003, "boost": 3},
    {"no": 27, "length": 0.2, "weight": 8.122, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 3},
    {"no": 41, "length": 0.21, "weight": 1.9875, "lengthRadius": 0.001, "weightRadius": 0.0045, "boost": 18},
    {"no": 82, "length": 0.21, "weight": 1.984, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 25},
    {"no": 18, "length": 0.2, "weight": 1.562, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 35},
    {"no": 274, "length": 0.21, "weight": 1.751, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 15},
    {"no": 18, "length": 0.21, "weight": 1.751, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 35},
    {"no": 270, "length": 0.23, "weight": 1.6245, "lengthRadius": 0.001, "weightRadius": 0.0065, "boost": 25},
    {"no": 18, "length": 0.19, "weight": 1.5195, "lengthRadius": 0.001, "weightRadius": 0.0015, "boost": 8},
    {"no": 49, "length": 0.25, "weight": 1.948, "lengthRadius": 0.001, "weightRadius": 0.004, "boost": 8},
    {"no": 193, "length": 0.25, "weight": 2.5185, "lengthRadius": 0.001, "weightRadius": 0.0015, "boost": 18},
    {"no": 79, "length": 0.28, "weight": 1.5625, "lengthRadius": 0.001, "weightRadius": 0.0015, "boost": 18},
    {"no": 44, "length": 0.21, "weight": 2.3805, "lengthRadius": 0.001, "weightRadius": 0.0015, "boost": 20},
    {"no": 179, "length": 0.26, "weight": 2.191, "lengthRadius": 0.001, "weightRadius": 0.005, "boost": 35},
    {"no": 128, "length": 0.16, "weight": 0.8985, "lengthRadius": 0.001, "weightRadius": 0.0055, "boost": 80},
    {"no": 261, "length": 0.15, "weight": 0.863, "lengthRadius": 0.001, "weightRadius": 0.002, "boost": 80},
    {"no": 18, "length": 0.21, "weight": 1.7805, "lengthRadius": 0.001, "weightRadius": 0.0065, "boost": 8},
    {"no": 85, "length": 0.22, "weight": 1.607, "lengthRadius": 0.001, "weightRadius": 0.01, "boost": 5},
    {"no": 270, "length": 0.2, "weight": 1.3455, "lengthRadius": 0.001, "weightRadius": 0.0025, "boost": 1},
    {"no": 18, "length": 0.17, "weight": 1.1425, "lengthRadius": 0.001, "weightRadius": 0.0055, "boost": 2},
    {"no": 214, "length": 0.18, "weight": 1.664, "lengthRadius": 0.001, "weightRadius": 0.005, "boost": 2},
    {"no": 47, "length": 0.32, "weight": 5.85, "lengthRadius": 0.001, "weightRadius": 0.003, "boost": 2},
    {"no": 108, "length": 0.22, "weight": 5.958, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 20},
    {"no": 168, "length": 0.2, "weight": 1.287, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 8},
    {"no": 32, "length": 0.18, "weight": 1.641, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 3},
    {"no": 188, "length": 0.19, "weight": 5.22, "lengthRadius": 0.001, "weightRadius": 0.08, "boost": 35},
    {"no": 188, "length": 0.2, "weight": 5.475, "lengthRadius": 0.001, "weightRadius": 0.001, "boost": 50},
    {"no": 188, "length": 0.2, "weight": 5.53, "lengthRadius": 0.001, "weightRadius": 0.04, "boost": 50},
    {"no": 193, "length": 0.21, "weight": 1.6855, "lengthRadius": 0.001, "weightRadius": 0.0085, "boost": 12},
    {"no": 132, "length": 0.22, "weight": 1.8435, "lengthRadius": 0.001, "weightRadius": 0.0115, "boost": 3},
    {"no": 274, "length": 0.17, "weight": 1.3325, "lengthRadius": 0.001, "weightRadius": 0.0065, "boost": 10},
    {"no": 18, "length": 0.18, "weight": 1.365, "lengthRadius": 0.001, "weightRadius": 0.006, "boost": 12},
    {"no": 41, "length": 0.22, "weight": 2.0775, "lengthRadius": 0.001, "weightRadius": 0.0085, "boost": 15},
    {"no": 179, "length": 0.22, "weight": 1.892, "lengthRadius": 0.001, "weightRadius": 0.009, "boost": 18},
    {"no": 18, "length": 0.21, "weight": 1.716, "lengthRadius": 0.001, "weightRadius": 0.009, "boost": 20},
    {"no": 82, "length": 0.16, "weight": 1.467, "lengthRadius": 0.001, "weightRadius": 0.005, "boost": 5},
    {"no": 266, "length": 0.2, "weight": 2.3865, "lengthRadius": 0.001, "weightRadius": 0.0065, "boost": 5},
    {"no": 21, "length": 0.25, "weight": 2.8345, "lengthRadius": 0.001, "weightRadius": 0.0025, "boost": 8},
    {"no": 32, "length": 0.19, "weight": 1.7005, "lengthRadius": 0.001, "weightRadius": 0.0085, "boost": 10},
    {"no": 266, "length": 0.18, "weight": 1.975, "lengthRadius": 0.001, "weightRadius": 0.002, "boost": 12},
    {"no": 274, "length": 0.24, "weight": 2.062, "lengthRadius": 0.001, "weightRadius": 0.012, "boost": 12},
    {"no": 132, "length": 0.19, "weight": 1.4815, "lengthRadius": 0.001, "weightRadius": 0.0035, "boost": 25},
    {"no": 179, "length": 0.21, "weight": 1.804, "lengthRadius": 0.001, "weightRadius": 0.002, "boost": 25},
    {"no": 274, "length": 0.22, "weight": 1.961, "lengthRadius": 0.001, "weightRadius": 0.012, "boost": 25},
    {"no": 193, "length": 0.24, "weight": 2.139, "lengthRadius": 0.001, "weightRadius": 0.013, "boost": 30},
]


# --------------------------------------------------------------------------- #
# 基础工具函数
# --------------------------------------------------------------------------- #

def _is_finite(value):
    """对应 Number.isFinite：仅接受真正的有限数值。"""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _num(value):
    """对应 Number(...)：转换为 float，失败返回 nan。"""
    try:
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return float("nan")
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _js_round(value):
    """对应 Math.round（.5 向 +∞ 取整）。"""
    return math.floor(value + 0.5)


def _fmt_number(value):
    """模拟 JS `Number(x.toFixed(n))` 去掉多余末尾零后的字符串形式。"""
    if value == int(value):
        return str(int(value))
    return str(value)


def parse_number(value):
    """m：解析输入为有限数值，否则返回 None。"""
    if value is None or str(value).strip() == "":
        return None
    n = _num(value)
    return n if _is_finite(n) else None


def clamp(value, low, high):
    """p：将 value 夹在 [low, high]。"""
    return max(low, min(high, value))


def in_range(value, low, high):
    """f：value 是否落在 [low, high]（low/high 须为有限数）。"""
    return _is_finite(low) and _is_finite(high) and low <= value <= high


def outside_distance(value, low, high):
    """v：value 超出 [low, high] 的距离，否则 0。"""
    if value < low:
        return low - value
    if value > high:
        return value - high
    return 0


def format_range(low, high):
    """x：区间显示文本。"""
    return str(low) if low == high else "{} - {}".format(low, high)


def _normalize_progress(value, low, high):
    """M：把 value 在 [low, high] 内归一到 [0,1]，无效区间返回 0.5。"""
    span = high - low
    if not _is_finite(span) or span <= 0:
        return 0.5
    return (value - low) / span


def linear_normalize(value, low, high):
    """L：线性归一化，越界 / 无效时回退。"""
    if not _is_finite(value):
        return 0
    if not _is_finite(low) or not _is_finite(high) or high <= low:
        return 1
    return (value - low) / (high - low)


# --------------------------------------------------------------------------- #
# 本地规则匹配
# --------------------------------------------------------------------------- #

def _contains(value, collection):
    """F：判断 value 是否在 set/list 中（list 元素按数值比较）。"""
    if not collection:
        return False
    if isinstance(collection, set):
        return value in collection
    if isinstance(collection, (list, tuple)):
        return any(_num(item) == value for item in collection)
    return False


def _within_radius(length, weight, rule):
    """A：长度 / 重量是否同时落在规则半径内。"""
    return (abs(length - rule["length"]) <= rule["lengthRadius"]
            and abs(weight - rule["weight"]) <= rule["weightRadius"])


def _local_v4_weight_multiplier(length, weight, spirit, options):
    """V：累乘所有命中的本地 v4 权重规则的 multiplier。"""
    if options.get("disableLocalV4WeightRules"):
        return 1
    no = _num(spirit.get("no") if spirit else None)
    disabled = options.get("disabledLocalV4WeightRuleIndexes")
    rules = [r for idx, r in enumerate(LOCAL_V4_WEIGHT_RULES) if not _contains(idx, disabled)]
    extra = options.get("extraLocalV4WeightRules")
    if isinstance(extra, list):
        rules = rules + extra

    result = 1
    for rule in rules:
        if _num(rule["no"]) != no:
            continue
        if _within_radius(length, weight, rule):
            result *= rule["multiplier"]
    return result


def _local_conflict_boost(length, weight, spirit, options):
    """D：累加所有命中的本地冲突规则的 boost。"""
    if options.get("disableLocalConflictRules"):
        return 0
    no = _num(spirit.get("no") if spirit else None)
    disabled = options.get("disabledLocalConflictRuleIndexes")
    rules = [r for idx, r in enumerate(LOCAL_CONFLICT_RULES) if not _contains(idx, disabled)]
    extra = options.get("extraLocalConflictRules")
    if isinstance(extra, list):
        rules = rules + extra

    result = 0
    for rule in rules:
        if _num(rule["no"]) != no:
            continue
        if _within_radius(length, weight, rule):
            result += rule["boost"]
    return result


def _spirit_score_adjustment(spirit, options):
    """y：按精灵编号取额外打分修正。"""
    if options.get("disableSpiritScoreAdjustments"):
        return 0
    no = _num(spirit.get("no") if spirit else None)
    return SPIRIT_SCORE_ADJUSTMENTS.get(no, 0)


# --------------------------------------------------------------------------- #
# 模型打分
# --------------------------------------------------------------------------- #

def _model_raw_score(features, params):
    """I：按给定模型参数计算原始分。"""
    avg_diff = abs(features["avg"] - params["targetAvg"])
    score = (params["bias"]
             - params["diffWeight"] * features["diff"]
             - params["avgWeight"] * avg_diff
             - params["areaWeight"] * features["area"]
             - params["spanWeight"] * features["span"]
             + params["invAreaWeight"] * features["invArea"]
             + params["edgeWeight"] * features["edgeMin"]
             + params["highProgressWeight"] * features["highProgress"]
             + params["lowProgressWeight"] * features["lowProgress"])
    if params["useAreaDivide"]:
        score /= 1 + params["areaDivideWeight"] * features["area"]
    return score


def _compute_v4_zone_weight(length, weight, spirit):
    """W：根据“等分区间”规律计算 v4 权重及所在区域 zone。"""
    n = _js_round(length)
    g = _js_round(spirit["lengthMin"])
    h = _js_round(spirit["lengthMax"])
    o = _num(weight)
    s = _num(spirit["weightMin"])
    a = _num(spirit["weightMax"])
    u = h - g + 1          # 长度刻度数量
    l = a - s              # 重量跨度

    if (not _is_finite(n) or not _is_finite(g) or not _is_finite(h)
            or not _is_finite(o) or not _is_finite(s) or not _is_finite(a)
            or u <= 0 or l <= 0 or n < g or n > h):
        return {"weight": 0, "zone": "invalid"}

    d = l / u                       # 每个长度刻度对应的重量步长
    r = (n - g) * d + s             # 当前长度下重量下界
    w = (n - g + 1) * d + s         # 当前长度下重量上界
    radius = 0.02 * l               # 容差
    b = r + radius
    c = w - radius
    m = 0
    zone = "outside"

    if b <= c and b <= o <= c:
        m = u / l
        zone = "flat"
    elif r - radius <= o < r + radius:
        m = (o - (r - radius)) / (2 * radius * d)
        zone = "lowSlope"
    elif w - radius < o <= w + radius:
        m = (w + radius - o) / (2 * radius * d)
        zone = "highSlope"

    return {"weight": max(0, m), "zone": zone}


def _score_spirit(length, weight, spirit, options):
    """S：对单只精灵计算基础打分（含越界惩罚、本地规则修正）。"""
    length_progress = _normalize_progress(length, spirit["lengthMin"], spirit["lengthMax"])
    weight_progress = _normalize_progress(weight, spirit["weightMin"], spirit["weightMax"])
    diff = abs(length_progress - weight_progress)
    avg = (length_progress + weight_progress) / 2
    length_span = max(spirit["lengthMax"] - spirit["lengthMin"], 1e-4)
    weight_span = max(spirit["weightMax"] - spirit["weightMin"], 1e-4)
    area = length_span * weight_span

    features = {
        "diff": diff,
        "avg": avg,
        "area": area,
        "span": length_span + weight_span,
        "invArea": 1 / area,
        "edgeMin": min(length_progress, weight_progress, 1 - length_progress, 1 - weight_progress),
        "highProgress": max(length_progress, weight_progress),
        "lowProgress": min(length_progress, weight_progress),
    }

    outside = (outside_distance(length, spirit["lengthMin"], spirit["lengthMax"])
               + outside_distance(weight, spirit["weightMin"], spirit["weightMax"]))
    current_score = _model_raw_score(features, CURRENT_MODEL)   # 当前模型分（下方权重为 0）
    v4_score = _model_raw_score(features, V4_MODEL)             # v4 模型分

    raw = (0 * current_score
           + 1 * v4_score
           - CURRENT_MODEL["outsideDistanceWeight"] * outside
           + _spirit_score_adjustment(spirit, options)
           + _local_conflict_boost(length, weight, spirit, options))

    result = dict(spirit)
    result.update({
        "displayLength": format_range(spirit["lengthMin"], spirit["lengthMax"]),
        "displayWeight": format_range(spirit["weightMin"], spirit["weightMax"]),
        "experimentBaseRawScore": raw,
        "experimentRawScore": raw,
        "experimentScoreValue": clamp(raw, 0, CURRENT_MODEL["displayCap"]),
        "isExact": (in_range(length, spirit["lengthMin"], spirit["lengthMax"])
                    and in_range(weight, spirit["weightMin"], spirit["weightMax"])),
    })
    return result


# --------------------------------------------------------------------------- #
# 混合权重与归一化
# --------------------------------------------------------------------------- #

def _resolve_close_mode(items, low, high, v4_weight):
    """P：在 v4 权重为 0 且候选数量很少、分数区间很窄时切换到 close 模式。"""
    span = high - low
    if (v4_weight == ZERO_V4_WEIGHT and 1 < len(items) <= 3 and 0 < span <= 1):
        average = sum(it["experimentBaseRawScore"] for it in items) / len(items)
        return {"mode": "close", "average": average}
    return {"mode": "range", "average": 0}


def _normalized_score(score, low, high, close_info):
    """z：range 模式走线性归一化；close 模式围绕均值做软归一化。"""
    if close_info.get("mode") != "close":
        return linear_normalize(score, low, high)
    return clamp(0.5 + (score - close_info["average"]) / 20, 0, 1)


def _fallback_v4_blend_weight(items, share, gap, low, high):
    """C：在未达到强势主导时的回退混合权重判定。"""
    if share < MIN_SHARE_FOR_FALLBACK or gap < MIN_GAP_FOR_FALLBACK:
        return ZERO_V4_WEIGHT
    if not items:
        return ZERO_V4_WEIGHT

    entries = [{"item": it, "currentNormalized": linear_normalize(it["experimentBaseRawScore"], low, high)}
               for it in items]
    best_current = entries[0]
    for e in entries[1:]:
        if e["currentNormalized"] > best_current["currentNormalized"]:
            best_current = e
    best_v4 = entries[0]
    for e in entries[1:]:
        if (e["item"].get("experimentV4Weight") or 0) > (best_v4["item"].get("experimentV4Weight") or 0):
            best_v4 = e

    diff = best_current["currentNormalized"] - best_v4["currentNormalized"]
    return FALLBACK_V4_WEIGHT if 0 <= diff <= MAX_NORMALIZED_GAP else ZERO_V4_WEIGHT


def _resolve_v4_blend_weight(items, low, high):
    """B：根据 v4 权重分布的占比 / 差值决定整体混合权重。"""
    weights = sorted((it.get("experimentV4Weight") or 0 for it in items), reverse=True)
    weights = [w for w in weights if w > 0]
    if not weights:
        return 0

    total = sum(weights)
    top_share = weights[0] / total if total > 0 else 0
    gap_share = (weights[0] - (weights[1] if len(weights) > 1 else 0)) / total if total > 0 else 0

    if top_share >= DOMINANT_SHARE_THRESHOLD and gap_share >= DOMINANT_GAP_THRESHOLD:
        return DOMINANT_V4_WEIGHT
    return _fallback_v4_blend_weight(items, top_share, gap_share, low, high)


# --------------------------------------------------------------------------- #
# 实验主流程
# --------------------------------------------------------------------------- #

def _run_experiment(items, length, weight, options):
    """E：对命中候选执行 v4 混合打分并排序。"""
    if not HYBRID_ENABLED or len(items) <= 1:
        return sorted(
            items,
            key=lambda e: (-e["experimentRawScore"], _num(e.get("no"))),
        )

    scored = []
    for spirit in items:
        zone_weight = _compute_v4_zone_weight(length, weight, spirit)
        entry = dict(spirit)
        entry.update({
            "experimentV4Weight": zone_weight["weight"] * _local_v4_weight_multiplier(length, weight, spirit, options),
            "experimentV4Zone": zone_weight["zone"],
        })
        scored.append(entry)

    base_scores = [e["experimentBaseRawScore"] for e in scored]
    low = min(base_scores)
    high = max(base_scores)
    max_v4_weight = max((e.get("experimentV4Weight") or 0) for e in scored)
    v4_weight = _resolve_v4_blend_weight(scored, low, high)
    current_weight = 1 - v4_weight
    close_info = _resolve_close_mode(scored, low, high, v4_weight)

    result = []
    for e in scored:
        current_normalized = _normalized_score(e["experimentBaseRawScore"], low, high, close_info)
        v4_normalized = (e.get("experimentV4Weight") or 0) / max_v4_weight if max_v4_weight > 0 else current_normalized
        hybrid = (current_weight * current_normalized + v4_weight * v4_normalized) * CURRENT_MODEL["displayCap"]

        entry = dict(e)
        entry.update({
            "experimentHybridScore": round(hybrid, 3),
            "experimentRawScore": hybrid,
            "experimentScoreValue": clamp(hybrid, 0, CURRENT_MODEL["displayCap"]),
            "experimentModelBlend": {
                "currentWeight": current_weight,
                "v4Weight": v4_weight,
                "currentMode": close_info["mode"],
                "currentNormalized": round(current_normalized, 6),
                "v4Normalized": round(v4_normalized, 6),
            },
        })
        result.append(entry)

    result.sort(key=lambda e: (-e["experimentRawScore"], -e["experimentBaseRawScore"], _num(e.get("no"))))
    return result


def _assign_display_scores(items):
    """T：把原始分换算为展示用百分比，并标记入选 / 落选项。"""
    min_raw = min((it["experimentRawScore"] for it in items), default=float("inf"))

    weighted = [{
        "item": it,
        "weight": max(it["experimentScoreValue"], it["experimentRawScore"] - min_raw + 0.01, 0),
    } for it in items]
    total_weight = sum(w["weight"] for w in weighted)

    entries = [{
        "item": w["item"],
        "index": idx,
        "weight": w["weight"],
        "percent": (w["weight"] / total_weight * 100) if total_weight > 0 else 0,
    } for idx, w in enumerate(weighted)]

    active = [e for e in entries if e["percent"] >= CURRENT_MODEL["activeDisplayFloor"]]
    positive = [e for e in entries if e["weight"] > 0]
    selected = active if active else positive[:CURRENT_MODEL["fallbackDisplayLimit"]]
    selected_indexes = {e["index"] for e in selected}
    selected_weight = sum(e["weight"] for e in selected)
    even_percent = 100 / len(items) if items else 0

    output = []
    for e in entries:
        item = e["item"]
        is_selected = e["index"] in selected_indexes
        percent = (e["weight"] / selected_weight * 100) if (is_selected and selected_weight > 0) else even_percent

        entry = dict(item)
        entry.update({
            "experimentScore": round(percent, 1) if is_selected else 0,
            "experimentScoreText": "{}%".format(_fmt_number(round(percent, 1))) if is_selected else "<1%",
            "experimentRawScore": round(item["experimentRawScore"], 3),
        })
        output.append(entry)
    return output


# --------------------------------------------------------------------------- #
# 对外接口
# --------------------------------------------------------------------------- #

def match_spirit_by_egg_experiment(egg_length, egg_weight, base_spirits, options=None):
    """根据蛋长度 / 蛋重量，结合实测规律推荐候选精灵并排序。

    参数：
        egg_length:   蛋长度（数值或可转换为数值的字符串）
        egg_weight:   蛋重量
        base_spirits: 候选精灵列表，每个元素为含
                      no / lengthMin / lengthMax / weightMin / weightMax 的 dict
        options:      可选项 dict，可禁用 / 扩展本地规则（见 _local_* 函数）

    返回：{"ok": bool, "message": str, "experimentMatches": list}
    """
    options = options or {}
    length = parse_number(egg_length)
    weight = parse_number(egg_weight)
    if length is None or weight is None:
        return {"ok": False, "message": "请输入有效的蛋长度和蛋重量。", "experimentMatches": []}

    scored = [_score_spirit(length, weight, spirit, options) for spirit in base_spirits]
    exact = [s for s in scored if s["isExact"]]
    matches = _assign_display_scores(_run_experiment(exact, length, weight, options))

    message = "基于当前实测规律，已对 {} 只命中候选完成推荐排序。".format(len(exact)) if exact else ""
    return {"ok": True, "message": message, "experimentMatches": matches}


def get_egg_experiment_debug_rules():
    """返回本地规则与精灵修正的副本，便于调试。"""
    return {
        "localConflictRules": [dict(r) for r in LOCAL_CONFLICT_RULES],
        "localV4WeightRules": [dict(r) for r in LOCAL_V4_WEIGHT_RULES],
        "spiritScoreAdjustments": dict(SPIRIT_SCORE_ADJUSTMENTS),
    }
