from models import RoutingHistoryEntry
from typing import List

class LearningComponent:
    def __init__(self):
        self.history: List[RoutingHistoryEntry] = []
        
    def record(self, entry: RoutingHistoryEntry):
        self.history.append(entry)
        
    def get_stats(self):
        total = len(self.history)
        if total == 0:
            return {}
            
        success_rate = sum(1 for e in self.history if e.success) / total
        total_cost = sum(e.cost_estimate for e in self.history)
        
        return {
            "total_requests": total,
            "success_rate": success_rate,
            "total_estimated_cost": total_cost
        }
