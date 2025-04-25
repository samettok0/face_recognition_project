from collections import deque

class DecisionGate:
    """
    Sliding-window voter for (is_live, is_match) pairs.
    window      – number of recent frames to keep
    min_live    – how many of those must be live==True
    min_match   – how many of those must be match==True
    """
    # Default timing: 15-frame window ≈ 2 s @ 7-8 fps  (adjust to taste)
    def __init__(self, window=15, min_live=12, min_match=12):
        self.live_q  = deque(maxlen=window)
        self.match_q = deque(maxlen=window)
        self.min_live  = min_live
        self.min_match = min_match

    def update(self, live_ok: bool, match_ok: bool) -> bool:
        """Add latest results and return True ONLY when both tallies pass."""
        self.live_q.append(live_ok)
        self.match_q.append(match_ok)
        return (
            sum(self.live_q)  >= self.min_live  and
            sum(self.match_q) >= self.min_match
        ) 