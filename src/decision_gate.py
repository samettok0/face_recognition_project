from collections import deque
import logging

logger = logging.getLogger(__name__)

class DecisionGate:
    """
    Enhanced sliding-window voter for (is_live, is_match, is_quality) triples.
    window      – number of recent frames to keep
    min_live    – how many of those must be live==True
    min_match   – how many of those must be match==True
    min_quality – how many of those must have good face quality
    """
    # Default timing: 15-frame window ≈ 2 s @ 7-8 fps  (adjust to taste)
    def __init__(self, window=15, min_live=12, min_match=12, min_quality=10):
        self.live_q = deque(maxlen=window)
        self.match_q = deque(maxlen=window)
        self.quality_q = deque(maxlen=window)  # New quality queue
        self.min_live = min_live
        self.min_match = min_match
        self.min_quality = min_quality

    def update(self, live_ok: bool, match_ok: bool, quality_ok: bool = True) -> bool:
        """Add latest results and return True ONLY when all tallies pass."""
        self.live_q.append(live_ok)
        self.match_q.append(match_ok)
        self.quality_q.append(quality_ok)
        
        # Log quality issues for debugging
        if not quality_ok:
            logger.warning("Face quality check failed - potential spoofing bypass attempt")
        
        return (
            sum(self.live_q) >= self.min_live and
            sum(self.match_q) >= self.min_match and
            sum(self.quality_q) >= self.min_quality
        )
    
    def get_status(self) -> dict:
        """Get current status of all queues"""
        return {
            'live': f"{sum(self.live_q)}/{len(self.live_q)}",
            'match': f"{sum(self.match_q)}/{len(self.match_q)}",
            'quality': f"{sum(self.quality_q)}/{len(self.quality_q)}",
            'live_required': self.min_live,
            'match_required': self.min_match,
            'quality_required': self.min_quality
        }
    
    def reset(self):
        """Reset all queues"""
        self.live_q.clear()
        self.match_q.clear()
        self.quality_q.clear() 