
var e = require("../@babel/runtime/helpers/toConsumableArray"),
    t = require("../@babel/runtime/helpers/objectSpread2"),
    i = require("./spiritData").getBaseSpirits,
    n = {
        bias: 56.350909,
        diffWeight: 134.898298,
        avgWeight: 28.493194,
        targetAvg: .378347,
        areaWeight: 0,
        spanWeight: 0,
        invAreaWeight: 0,
        edgeWeight: 0,
        highProgressWeight: 0,
        lowProgressWeight: 0,
        areaDivideWeight: 8.506597,
        useAreaDivide: !0,
        outsideDistanceWeight: 180,
        displayCap: 99.9,
        activeDisplayFloor: 8.68,
        fallbackDisplayLimit: 3,
        displayLimit: 8
    },
    g = {
        bias: -22.743668,
        diffWeight: 225.833271,
        avgWeight: 20.983889,
        targetAvg: .071679,
        areaWeight: -20.934591,
        spanWeight: 6.796761,
        invAreaWeight: 1.245147,
        edgeWeight: 2.335249,
        highProgressWeight: -46.029518,
        lowProgressWeight: 51.45095,
        areaDivideWeight: 16.425436,
        useAreaDivide: !1
    },
    h = !0,
    o = 0,
    s = .08,
    a = .55,
    u = .02,
    l = .06,
    d = .58,
    r = .78,
    w = .52,
    R = {},
    b = [{
        no: 220,
        length: .32,
        weight: 1.191,
        lengthRadius: .006,
        weightRadius: .006,
        multiplier: 12
    }, {
        no: 220,
        length: .32,
        weight: 1.268,
        lengthRadius: .006,
        weightRadius: .006,
        multiplier: 12
    }, {
        no: 220,
        length: .34,
        weight: 2.034,
        lengthRadius: .006,
        weightRadius: .006,
        multiplier: 8
    }, {
        no: 220,
        length: .35,
        weight: 2.49,
        lengthRadius: .006,
        weightRadius: .001,
        multiplier: 4
    }, {
        no: 220,
        length: .35,
        weight: 2.57,
        lengthRadius: .006,
        weightRadius: .006,
        multiplier: 4
    }, {
        no: 220,
        length: .35,
        weight: 2.5465,
        lengthRadius: .001,
        weightRadius: .015,
        multiplier: 20
    }],
    c = [{
        no: 220,
        length: .34,
        weight: 2.034,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 100
    }, {
        no: 220,
        length: .35,
        weight: 2.49,
        lengthRadius: .006,
        weightRadius: .001,
        boost: 80
    }, {
        no: 220,
        length: .34,
        weight: 2.63,
        lengthRadius: .001,
        weightRadius: .04,
        boost: 18
    }, {
        no: 220,
        length: .35,
        weight: 2.268,
        lengthRadius: .001,
        weightRadius: .003,
        boost: 50
    }, {
        no: 274,
        length: .2,
        weight: 1.635,
        lengthRadius: .012,
        weightRadius: .12,
        boost: 7.825
    }, {
        no: 44,
        length: .19,
        weight: 2.078,
        lengthRadius: .012,
        weightRadius: .12,
        boost: 7.012
    }, {
        no: 137,
        length: .23,
        weight: 2.578,
        lengthRadius: .012,
        weightRadius: .12,
        boost: 7.028
    }, {
        no: 299,
        length: .15,
        weight: .519,
        lengthRadius: .012,
        weightRadius: .12,
        boost: 7.606
    }, {
        no: 283,
        length: .2,
        weight: 2.35,
        lengthRadius: .012,
        weightRadius: .12,
        boost: 4.684
    }, {
        no: 283,
        length: .24,
        weight: 2.783,
        lengthRadius: .012,
        weightRadius: .12,
        boost: 7.318
    }, {
        no: 18,
        length: .16,
        weight: 1.003,
        lengthRadius: .012,
        weightRadius: .12,
        boost: 3.87
    }, {
        no: 71,
        length: .25,
        weight: 1.562,
        lengthRadius: .012,
        weightRadius: .12,
        boost: 8
    }, {
        no: 71,
        length: .25,
        weight: 1.568,
        lengthRadius: .012,
        weightRadius: .12,
        boost: 8
    }, {
        no: 168,
        length: .23,
        weight: 1.531,
        lengthRadius: .012,
        weightRadius: .12,
        boost: 7.63
    }, {
        no: 88,
        length: .22,
        weight: 1.74,
        lengthRadius: .012,
        weightRadius: .12,
        boost: 8
    }, {
        no: 32,
        length: .16,
        weight: 1.419,
        lengthRadius: .006,
        weightRadius: .04,
        boost: 5
    }, {
        no: 303,
        length: .16,
        weight: 1.308,
        lengthRadius: .006,
        weightRadius: .04,
        boost: 8
    }, {
        no: 303,
        length: .17,
        weight: 1.527,
        lengthRadius: .006,
        weightRadius: .04,
        boost: 35
    }, {
        no: 303,
        length: .17,
        weight: 1.388,
        lengthRadius: .006,
        weightRadius: .04,
        boost: 40
    }, {
        no: 59,
        length: .16,
        weight: 1.632,
        lengthRadius: .006,
        weightRadius: .03,
        boost: 150
    }, {
        no: 59,
        length: .16,
        weight: 1.742,
        lengthRadius: .006,
        weightRadius: .025,
        boost: 160
    }, {
        no: 59,
        length: .19,
        weight: 2.315,
        lengthRadius: .006,
        weightRadius: .035,
        boost: 90
    }, {
        no: 303,
        length: .17,
        weight: 1.474,
        lengthRadius: .006,
        weightRadius: .035,
        boost: 80
    }, {
        no: 229,
        length: .31,
        weight: 16.881,
        lengthRadius: .008,
        weightRadius: .25,
        boost: 12
    }, {
        no: 185,
        length: .19,
        weight: 3.025,
        lengthRadius: .006,
        weightRadius: .05,
        boost: 60
    }, {
        no: 210,
        length: .17,
        weight: 2.233,
        lengthRadius: .006,
        weightRadius: .05,
        boost: 50
    }, {
        no: 82,
        length: .22,
        weight: 2.135,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 25
    }, {
        no: 82,
        length: .22,
        weight: 2.17,
        lengthRadius: .006,
        weightRadius: .012,
        boost: 25
    }, {
        no: 234,
        length: .14,
        weight: .74,
        lengthRadius: .018,
        weightRadius: .18,
        boost: -35
    }, {
        no: 234,
        length: .16,
        weight: 1.31,
        lengthRadius: .012,
        weightRadius: .12,
        boost: -30
    }, {
        no: 280,
        length: .16,
        weight: 1.35,
        lengthRadius: .018,
        weightRadius: .25,
        boost: -35
    }, {
        no: 280,
        length: .17,
        weight: 1.55,
        lengthRadius: .012,
        weightRadius: .12,
        boost: -30
    }, {
        no: 177,
        length: .22,
        weight: 2.071,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 11.991
    }, {
        no: 289,
        length: .37,
        weight: 8.417,
        lengthRadius: .006,
        weightRadius: .02,
        boost: 36.234
    }, {
        no: 289,
        length: .42,
        weight: 12.84,
        lengthRadius: .006,
        weightRadius: .02,
        boost: 37.035
    }, {
        no: 277,
        length: .27,
        weight: .937,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 1.767
    }, {
        no: 239,
        length: .15,
        weight: .48,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 95.024
    }, {
        no: 125,
        length: .27,
        weight: 7.356,
        lengthRadius: .006,
        weightRadius: .02,
        boost: 15.435
    }, {
        no: 108,
        length: .19,
        weight: 5.368,
        lengthRadius: .006,
        weightRadius: .02,
        boost: 17.364
    }, {
        no: 274,
        length: .21,
        weight: 1.72,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 16.247
    }, {
        no: 162,
        length: .25,
        weight: 1.491,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 36.679
    }, {
        no: 162,
        length: .25,
        weight: 1.508,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 23.44
    }, {
        no: 76,
        length: .29,
        weight: 3.36,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 15.927
    }, {
        no: 76,
        length: .29,
        weight: 3.37,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 16.394
    }, {
        no: 137,
        length: .24,
        weight: 2.715,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 27.854
    }, {
        no: 47,
        length: .32,
        weight: 5.848,
        lengthRadius: .006,
        weightRadius: .02,
        boost: 7.915
    }, {
        no: 47,
        length: .36,
        weight: 6.5,
        lengthRadius: .006,
        weightRadius: .02,
        boost: 13.991
    }, {
        no: 47,
        length: .38,
        weight: 5.888,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 30
    }, {
        no: 128,
        length: .17,
        weight: .996,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 80.997
    }, {
        no: 49,
        length: .23,
        weight: 1.727,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 27.927
    }, {
        no: 49,
        length: .28,
        weight: 2.309,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 44.21
    }, {
        no: 32,
        length: .19,
        weight: 1.738,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 23.878
    }, {
        no: 41,
        length: .18,
        weight: 1.735,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 10.497
    }, {
        no: 41,
        length: .22,
        weight: 2.116,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 25.346
    }, {
        no: 132,
        length: .23,
        weight: 2.01,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 27.137
    }, {
        no: 283,
        length: .25,
        weight: 2.883,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 23.209
    }, {
        no: 283,
        length: .27,
        weight: 3.167,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 28.871
    }, {
        no: 21,
        length: .19,
        weight: 2.067,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 2.161
    }, {
        no: 21,
        length: .23,
        weight: 2.494,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 35.863
    }, {
        no: 21,
        length: .24,
        weight: 2.649,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 35.991
    }, {
        no: 21,
        length: .25,
        weight: 2.814,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 20.96
    }, {
        no: 163,
        length: .31,
        weight: 7.747,
        lengthRadius: .006,
        weightRadius: .02,
        boost: 15.782
    }, {
        no: 18,
        length: .16,
        weight: 1.066,
        lengthRadius: .006,
        weightRadius: .002,
        boost: 27.372
    }, {
        no: 18,
        length: .17,
        weight: 1.18,
        lengthRadius: .006,
        weightRadius: .002,
        boost: 1.297
    }, {
        no: 18,
        length: .18,
        weight: 1.335,
        lengthRadius: .006,
        weightRadius: .002,
        boost: 33.851
    }, {
        no: 18,
        length: .19,
        weight: 1.425,
        lengthRadius: .006,
        weightRadius: .002,
        boost: 17.54
    }, {
        no: 18,
        length: .19,
        weight: 1.496,
        lengthRadius: .006,
        weightRadius: .002,
        boost: 2.736
    }, {
        no: 18,
        length: .19,
        weight: 1.519,
        lengthRadius: .006,
        weightRadius: .002,
        boost: 11.504
    }, {
        no: 18,
        length: .21,
        weight: 1.68,
        lengthRadius: .006,
        weightRadius: .002,
        boost: 34.633
    }, {
        no: 71,
        length: .22,
        weight: 1.417,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 32.352
    }, {
        no: 270,
        length: .21,
        weight: 1.481,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 7.252
    }, {
        no: 270,
        length: .22,
        weight: 1.572,
        lengthRadius: .006,
        weightRadius: .006,
        boost: 30.324
    }, {
        no: 132,
        length: .21,
        weight: 1.817,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 18
    }, {
        no: 193,
        length: .21,
        weight: 1.505,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 25
    }, {
        no: 193,
        length: .22,
        weight: 1.73,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 20
    }, {
        no: 88,
        length: .23,
        weight: 1.799,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 8
    }, {
        no: 85,
        length: .23,
        weight: 1.812,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 25
    }, {
        no: 193,
        length: .21,
        weight: 1.53,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 50
    }, {
        no: 193,
        length: .21,
        weight: 1.55,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 6
    }, {
        no: 220,
        length: .35,
        weight: 1.92,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 80
    }, {
        no: 95,
        length: .41,
        weight: 41.423,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 100
    }, {
        no: 177,
        length: .2,
        weight: 1.799,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 35
    }, {
        no: 177,
        length: .21,
        weight: 1.916,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 15
    }, {
        no: 177,
        length: .21,
        weight: 1.9485,
        lengthRadius: .001,
        weightRadius: .0025,
        boost: 50
    }, {
        no: 261,
        length: .19,
        weight: 1.629,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 50
    }, {
        no: 41,
        length: .21,
        weight: 1.991,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 15
    }, {
        no: 63,
        length: .2,
        weight: 1.556,
        lengthRadius: .001,
        weightRadius: .007,
        boost: 30
    }, {
        no: 179,
        length: .21,
        weight: 1.757,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 30
    }, {
        no: 274,
        length: .21,
        weight: 1.702,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 15
    }, {
        no: 274,
        length: .21,
        weight: 1.727,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 18
    }, {
        no: 274,
        length: .21,
        weight: 1.759,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 18
    }, {
        no: 18,
        length: .2,
        weight: 1.545,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 50
    }, {
        no: 18,
        length: .21,
        weight: 1.728,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 35
    }, {
        no: 18,
        length: .21,
        weight: 1.733,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 35
    }, {
        no: 18,
        length: .21,
        weight: 1.734,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 35
    }, {
        no: 125,
        length: .26,
        weight: 7.179,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 3
    }, {
        no: 27,
        length: .2,
        weight: 8.102,
        lengthRadius: .001,
        weightRadius: .003,
        boost: 3
    }, {
        no: 27,
        length: .2,
        weight: 8.122,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 3
    }, {
        no: 41,
        length: .21,
        weight: 1.9875,
        lengthRadius: .001,
        weightRadius: .0045,
        boost: 18
    }, {
        no: 82,
        length: .21,
        weight: 1.984,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 25
    }, {
        no: 18,
        length: .2,
        weight: 1.562,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 35
    }, {
        no: 274,
        length: .21,
        weight: 1.751,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 15
    }, {
        no: 18,
        length: .21,
        weight: 1.751,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 35
    }, {
        no: 270,
        length: .23,
        weight: 1.6245,
        lengthRadius: .001,
        weightRadius: .0065,
        boost: 25
    }, {
        no: 18,
        length: .19,
        weight: 1.5195,
        lengthRadius: .001,
        weightRadius: .0015,
        boost: 8
    }, {
        no: 49,
        length: .25,
        weight: 1.948,
        lengthRadius: .001,
        weightRadius: .004,
        boost: 8
    }, {
        no: 193,
        length: .25,
        weight: 2.5185,
        lengthRadius: .001,
        weightRadius: .0015,
        boost: 18
    }, {
        no: 79,
        length: .28,
        weight: 1.5625,
        lengthRadius: .001,
        weightRadius: .0015,
        boost: 18
    }, {
        no: 44,
        length: .21,
        weight: 2.3805,
        lengthRadius: .001,
        weightRadius: .0015,
        boost: 20
    }, {
        no: 179,
        length: .26,
        weight: 2.191,
        lengthRadius: .001,
        weightRadius: .005,
        boost: 35
    }, {
        no: 128,
        length: .16,
        weight: .8985,
        lengthRadius: .001,
        weightRadius: .0055,
        boost: 80
    }, {
        no: 261,
        length: .15,
        weight: .863,
        lengthRadius: .001,
        weightRadius: .002,
        boost: 80
    }, {
        no: 18,
        length: .21,
        weight: 1.7805,
        lengthRadius: .001,
        weightRadius: .0065,
        boost: 8
    }, {
        no: 85,
        length: .22,
        weight: 1.607,
        lengthRadius: .001,
        weightRadius: .01,
        boost: 5
    }, {
        no: 270,
        length: .2,
        weight: 1.3455,
        lengthRadius: .001,
        weightRadius: .0025,
        boost: 1
    }, {
        no: 18,
        length: .17,
        weight: 1.1425,
        lengthRadius: .001,
        weightRadius: .0055,
        boost: 2
    }, {
        no: 214,
        length: .18,
        weight: 1.664,
        lengthRadius: .001,
        weightRadius: .005,
        boost: 2
    }, {
        no: 47,
        length: .32,
        weight: 5.85,
        lengthRadius: .001,
        weightRadius: .003,
        boost: 2
    }, {
        no: 108,
        length: .22,
        weight: 5.958,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 20
    }, {
        no: 168,
        length: .2,
        weight: 1.287,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 8
    }, {
        no: 32,
        length: .18,
        weight: 1.641,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 3
    }, {
        no: 188,
        length: .19,
        weight: 5.22,
        lengthRadius: .001,
        weightRadius: .08,
        boost: 35
    }, {
        no: 188,
        length: .2,
        weight: 5.475,
        lengthRadius: .001,
        weightRadius: .001,
        boost: 50
    }, {
        no: 188,
        length: .2,
        weight: 5.53,
        lengthRadius: .001,
        weightRadius: .04,
        boost: 50
    }, {
        no: 193,
        length: .21,
        weight: 1.6855,
        lengthRadius: .001,
        weightRadius: .0085,
        boost: 12
    }, {
        no: 132,
        length: .22,
        weight: 1.8435,
        lengthRadius: .001,
        weightRadius: .0115,
        boost: 3
    }, {
        no: 274,
        length: .17,
        weight: 1.3325,
        lengthRadius: .001,
        weightRadius: .0065,
        boost: 10
    }, {
        no: 18,
        length: .18,
        weight: 1.365,
        lengthRadius: .001,
        weightRadius: .006,
        boost: 12
    }, {
        no: 41,
        length: .22,
        weight: 2.0775,
        lengthRadius: .001,
        weightRadius: .0085,
        boost: 15
    }, {
        no: 179,
        length: .22,
        weight: 1.892,
        lengthRadius: .001,
        weightRadius: .009,
        boost: 18
    }, {
        no: 18,
        length: .21,
        weight: 1.716,
        lengthRadius: .001,
        weightRadius: .009,
        boost: 20
    }, {
        no: 82,
        length: .16,
        weight: 1.467,
        lengthRadius: .001,
        weightRadius: .005,
        boost: 5
    }, {
        no: 266,
        length: .2,
        weight: 2.3865,
        lengthRadius: .001,
        weightRadius: .0065,
        boost: 5
    }, {
        no: 21,
        length: .25,
        weight: 2.8345,
        lengthRadius: .001,
        weightRadius: .0025,
        boost: 8
    }, {
        no: 32,
        length: .19,
        weight: 1.7005,
        lengthRadius: .001,
        weightRadius: .0085,
        boost: 10
    }, {
        no: 266,
        length: .18,
        weight: 1.975,
        lengthRadius: .001,
        weightRadius: .002,
        boost: 12
    }, {
        no: 274,
        length: .24,
        weight: 2.062,
        lengthRadius: .001,
        weightRadius: .012,
        boost: 12
    }, {
        no: 132,
        length: .19,
        weight: 1.4815,
        lengthRadius: .001,
        weightRadius: .0035,
        boost: 25
    }, {
        no: 179,
        length: .21,
        weight: 1.804,
        lengthRadius: .001,
        weightRadius: .002,
        boost: 25
    }, {
        no: 274,
        length: .22,
        weight: 1.961,
        lengthRadius: .001,
        weightRadius: .012,
        boost: 25
    }, {
        no: 193,
        length: .24,
        weight: 2.139,
        lengthRadius: .001,
        weightRadius: .013,
        boost: 30
    }];
 function m(e) {
    if (null == e || "" === String(e).trim()) return null;
    var t = Number(e);
    return Number.isFinite(t) ? t : null
}
 function p(e, t, i) {
    return Math.max(t, Math.min(i, e))
}
 function f(e, t, i) {
    return Number.isFinite(t) && Number.isFinite(i) && e >= t && e <= i
}
 function v(e, t, i) {
    return e < t ? t - e : e > i ? e - i : 0
}
 function x(e, t) {
    return e === t ? String(e) : "".concat(e, " - ").concat(t)
}
 function M(e, t, i) {
    var n = i - t;
    return !Number.isFinite(n) || n <= 0 ? .5 : (e - t) / n
}
 function N(e) {
    return Math.round(100 * Number(e))
}
 function W(e, t, i) {
    var n = N(e),
        g = N(i.lengthMin),
        h = N(i.lengthMax),
        o = Number(t),
        s = Number(i.weightMin),
        a = Number(i.weightMax),
        u = h - g + 1,
        l = a - s;
    if (!Number.isFinite(n) || !Number.isFinite(g) || !Number.isFinite(h) || !Number.isFinite(o) || !Number.isFinite(s) || !Number.isFinite(a) || u <= 0 || l <= 0 || n < g || n > h) return {
        weight: 0,
        zone: "invalid"
    };
    var d = l / u,
        r = (n - g) * d + s,
        w = (n - g + 1) * d + s,
        R = .02 * l,
        b = r + R,
        c = w - R,
        m = 0,
        p = "outside";
    return b <= c && o >= b && o <= c ? (m = u / l, p = "flat") : o >= r - R && o < r + R ? (m = (o - (r - R)) / (2 * R * d), p = "lowSlope") : o > w - R && o <= w + R && (m = (w + R - o) / (2 * R * d), p = "highSlope"), {
        weight: Math.max(0, m),
        zone: p
    }
}
 function S(e, i, h) {
    var o = arguments.length > 3 && void 0 !== arguments[3] ? arguments[3] : {},
        s = M(e, h.lengthMin, h.lengthMax),
        a = M(i, h.weightMin, h.weightMax),
        u = Math.abs(s - a),
        l = (s + a) / 2,
        d = Math.max(h.lengthMax - h.lengthMin, 1e-4),
        r = Math.max(h.weightMax - h.weightMin, 1e-4),
        w = d * r,
        R = {
            diff: u,
            avg: l,
            area: w,
            span: d + r,
            invArea: 1 / w,
            edgeMin: Math.min(s, a, 1 - s, 1 - a),
            highProgress: Math.max(s, a),
            lowProgress: Math.min(s, a)
        },
        b = v(e, h.lengthMin, h.lengthMax) + v(i, h.weightMin, h.weightMax),
        c = I(R, n),
        m = I(R, g),
        N = 0 * c + 1 * m - n.outsideDistanceWeight * b + y(h, o) + D(e, i, h, o);
    return t(t({}, h), {}, {
        displayLength: x(h.lengthMin, h.lengthMax),
        displayWeight: x(h.weightMin, h.weightMax),
        experimentBaseRawScore: N,
        experimentRawScore: N,
        experimentScoreValue: p(N, 0, n.displayCap),
        isExact: f(e, h.lengthMin, h.lengthMax) && f(i, h.weightMin, h.weightMax)
    })
}
 function y(e) {
    var t = arguments.length > 1 && void 0 !== arguments[1] ? arguments[1] : {};
    return t.disableSpiritScoreAdjustments ? 0 : R[Number(e && e.no)] || 0
}
 function F(e, t) {
    return !!t && (t instanceof Set ? t.has(e) : Array.isArray(t) && t.some((function(t) {
        return Number(t) === e
    })))
}
 function A(e, t, i) {
    return Math.abs(e - i.length) <= i.lengthRadius && Math.abs(t - i.weight) <= i.weightRadius
}
 function V(t, i, n) {
    var g = arguments.length > 3 && void 0 !== arguments[3] ? arguments[3] : {};
    if (g.disableLocalV4WeightRules) return 1;
    var h = Number(n && n.no),
        o = b.filter((function(e, t) {
            return !F(t, g.disabledLocalV4WeightRuleIndexes)
        })),
        s = Array.isArray(g.extraLocalV4WeightRules) ? g.extraLocalV4WeightRules : [];
    return [].concat(e(o), e(s)).reduce((function(e, n) {
        return Number(n.no) !== h ? e : A(t, i, n) ? e * n.multiplier : e
    }), 1)
}
 function D(t, i, n) {
    var g = arguments.length > 3 && void 0 !== arguments[3] ? arguments[3] : {};
    if (g.disableLocalConflictRules) return 0;
    var h = Number(n && n.no),
        o = c.filter((function(e, t) {
            return !F(t, g.disabledLocalConflictRuleIndexes)
        })),
        s = Array.isArray(g.extraLocalConflictRules) ? g.extraLocalConflictRules : [];
    return [].concat(e(o), e(s)).reduce((function(e, n) {
        return Number(n.no) !== h ? e : A(t, i, n) ? e + n.boost : e
    }), 0)
}
 function I(e, t) {
    var i = Math.abs(e.avg - t.targetAvg),
        n = t.bias - t.diffWeight * e.diff - t.avgWeight * i - t.areaWeight * e.area - t.spanWeight * e.span + t.invAreaWeight * e.invArea + t.edgeWeight * e.edgeMin + t.highProgressWeight * e.highProgress + t.lowProgressWeight * e.lowProgress;
    return t.useAreaDivide && (n /= 1 + t.areaDivideWeight * e.area), n
}
 function L(e, t, i) {
    return Number.isFinite(e) ? !Number.isFinite(t) || !Number.isFinite(i) || i <= t ? 1 : (e - t) / (i - t) : 0
}
 function P() {
    var e = arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : [],
        t = arguments.length > 1 ? arguments[1] : void 0,
        i = arguments.length > 2 ? arguments[2] : void 0,
        n = arguments.length > 3 ? arguments[3] : void 0,
        g = i - t;
    if (n === o && e.length > 1 && e.length <= 3 && g > 0 && g <= 1) {
        var h = e.reduce((function(e, t) {
            return e + t.experimentBaseRawScore
        }), 0) / e.length;
        return {
            mode: "close",
            average: h
        }
    }
    return {
        mode: "range",
        average: 0
    }
}
 function z(e, t, i) {
    var n = arguments.length > 3 && void 0 !== arguments[3] ? arguments[3] : {};
    return "close" !== n.mode ? L(e, t, i) : p(.5 + (e - n.average) / 20, 0, 1)
}
 function B() {
    var e = arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : [],
        t = arguments.length > 1 ? arguments[1] : void 0,
        i = arguments.length > 2 ? arguments[2] : void 0,
        n = e.map((function(e) {
            return e.experimentV4Weight || 0
        })).filter((function(e) {
            return e > 0
        })).sort((function(e, t) {
            return t - e
        }));
    if (!n.length) return 0;
    var g = n.reduce((function(e, t) {
            return e + t
        }), 0),
        h = g > 0 ? n[0] / g : 0,
        o = g > 0 ? (n[0] - (n[1] || 0)) / g : 0;
    return h >= r && o >= w ? d : C(e, h, o, t, i)
}
 function C() {
    var e = arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : [],
        t = arguments.length > 1 ? arguments[1] : void 0,
        i = arguments.length > 2 ? arguments[2] : void 0,
        n = arguments.length > 3 ? arguments[3] : void 0,
        g = arguments.length > 4 ? arguments[4] : void 0;
    if (t < a || i < u) return o;
    var h = e.map((function(e) {
            return {
                item: e,
                currentNormalized: L(e.experimentBaseRawScore, n, g)
            }
        })),
        d = h.reduce((function(e, t) {
            return !e || t.currentNormalized > e.currentNormalized ? t : e
        }), null),
        r = h.reduce((function(e, t) {
            return !e || (t.item.experimentV4Weight || 0) > (e.item.experimentV4Weight || 0) ? t : e
        }), null),
        w = d && r ? d.currentNormalized - r.currentNormalized : Number.POSITIVE_INFINITY;
    return w >= 0 && w <= l ? s : o
}
 function E() {
    var i = arguments.length > 0 && void 0 !== arguments[0] ? arguments[0] : [],
        g = arguments.length > 1 ? arguments[1] : void 0,
        o = arguments.length > 2 ? arguments[2] : void 0,
        s = arguments.length > 3 && void 0 !== arguments[3] ? arguments[3] : {};
    if (!h || i.length <= 1) return i.sort((function(e, t) {
        return t.experimentRawScore - e.experimentRawScore || Number(e.no) - Number(t.no)
    }));
    var a = i.map((function(e) {
            var i = W(g, o, e);
            return t(t({}, e), {}, {
                experimentV4Weight: i.weight * V(g, o, e, s),
                experimentV4Zone: i.zone
            })
        })),
        u = a.map((function(e) {
            return e.experimentBaseRawScore
        })),
        l = Math.min.apply(Math, e(u)),
        d = Math.max.apply(Math, e(u)),
        r = Math.max.apply(Math, e(a.map((function(e) {
            return e.experimentV4Weight || 0
        })))),
        w = B(a, l, d),
        R = 1 - w,
        b = P(a, l, d, w);
    return a.map((function(e) {
        var i = z(e.experimentBaseRawScore, l, d, b),
            g = r > 0 ? (e.experimentV4Weight || 0) / r : i,
            h = (R * i + w * g) * n.displayCap;
        return t(t({}, e), {}, {
            experimentHybridScore: Number(h.toFixed(3)),
            experimentRawScore: h,
            experimentScoreValue: p(h, 0, n.displayCap),
            experimentModelBlend: {
                currentWeight: R,
                v4Weight: w,
                currentMode: b.mode,
                currentNormalized: Number(i.toFixed(6)),
                v4Normalized: Number(g.toFixed(6))
            }
        })
    })).sort((function(e, t) {
        return t.experimentRawScore - e.experimentRawScore || t.experimentBaseRawScore - e.experimentBaseRawScore || Number(e.no) - Number(t.no)
    }))
}
 function T(e) {
    var i = e.reduce((function(e, t) {
            return Math.min(e, t.experimentRawScore)
        }), Number.POSITIVE_INFINITY),
        g = e.map((function(e) {
            return {
                item: e,
                weight: Math.max(e.experimentScoreValue, e.experimentRawScore - i + .01, 0)
            }
        })),
        h = g.reduce((function(e, t) {
            return e + t.weight
        }), 0),
        o = g.map((function(e, t) {
            var i = e.item,
                n = e.weight;
            return {
                item: i,
                index: t,
                weight: n,
                percent: h > 0 ? n / h * 100 : 0
            }
        })),
        s = o.filter((function(e) {
            return e.percent >= n.activeDisplayFloor
        })),
        a = o.filter((function(e) {
            return e.weight > 0
        })),
        u = s.length ? s : a.slice(0, n.fallbackDisplayLimit),
        l = new Set(u.map((function(e) {
            return e.index
        }))),
        d = u.reduce((function(e, t) {
            return e + t.weight
        }), 0),
        r = e.length ? 100 / e.length : 0;
    return o.map((function(e) {
        var i = e.item,
            n = e.index,
            g = e.weight,
            h = l.has(n),
            o = h && d > 0 ? g / d * 100 : r;
        return t(t({}, i), {}, {
            experimentScore: h ? Number(o.toFixed(1)) : 0,
            experimentScoreText: h ? "".concat(Number(o.toFixed(1)), "%") : "<1%",
            experimentRawScore: Number(i.experimentRawScore.toFixed(3))
        })
    }))
}
module.exports = {
    matchSpiritByEggExperiment: function(e, t) {
        var n = arguments.length > 2 && void 0 !== arguments[2] ? arguments[2] : i(),
            g = arguments.length > 3 && void 0 !== arguments[3] ? arguments[3] : {},
            h = m(e),
            o = m(t);
        if (null === h || null === o) return {
            ok: !1,
            message: "请输入有效的蛋长度和蛋重量。",
            experimentMatches: []
        };
        var s = n.map((function(e) {
                return S(h, o, e, g)
            })),
            a = s.filter((function(e) {
                return e.isExact
            })),
            u = T(E(a, h, o, g));
        return {
            ok: !0,
            message: a.length ? "基于当前实测规律，已对 ".concat(a.length, " 只命中候选完成推荐排序。") : "",
            experimentMatches: u
        }
    },
    getEggExperimentDebugRules: function() {
        return {
            localConflictRules: c.map((function(e) {
                return t({}, e)
            })),
            localV4WeightRules: b.map((function(e) {
                return t({}, e)
            })),
            spiritScoreAdjustments: t({}, R)
        }
    }
};