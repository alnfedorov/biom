from collections import defaultdict
from typing import Dict, List

import numpy as np

from .result import Result, Track
import numba

from .pvalues import FILTERED_PQVALUE


@numba.jit(cache=True, nopython=True, nogil=True)
def _make_pqtable(pvalues: Dict[float, int]) -> Dict[float, float]:
    N = 0
    for x in pvalues.values():
        N += x
    f = -np.log10(N)
    rank = 1

    pv2qv = numba.typed.Dict()
    # Order pvalues, from 1 to 0
    pvalues = sorted(pvalues.items(), key=lambda x: x[0], reverse=True)
    assert pvalues, "Empty pvalues dictionary!"
    for i in range(len(pvalues)):
        pv, count = pvalues[i]
        q = pv + (np.log10(rank) + f)
        if q <= 0:
            break
        pv2qv[pv] = q
        rank += count
    # bottom rank pscores all have qscores 0
    for j in range(i, len(pvalues)):
        pv, _ = pvalues[j]
        pv2qv[pv] = 0
    return pv2qv


def make_pqtable(counts: List[Dict[float, int]]) -> Dict[float, float]:
    merged = numba.typed.Dict()
    for item in counts:
        for k, v in item.items():
            if k not in merged:
                merged[k] = 0
            merged[k] += v
    result = _make_pqtable(merged)
    return {k: v for k, v in result.items()}  # turn into a usual dict


def apply_pqtable(pvalues: Result, table: Dict[float, float]) -> Result:
    pv = pvalues.track.values
    qv = np.empty_like(pv)
    for i in range(pv.size):
        if pv[i] == FILTERED_PQVALUE:
            qv[i] = FILTERED_PQVALUE
        else:
            qv[i] = table[pv[i]]
    return Result(
        pvalues.contig, pvalues.contiglen, pvalues.trstrand,
        Track(pvalues.track.bounds, qv)
    )
