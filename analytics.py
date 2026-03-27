import flet as ft
import random
from datetime import datetime

class SmartAnalytics:
    def __init__(self, data):
        self.data = data

    @staticmethod
    def _is_taught(status: str) -> bool:
        s = (status or "").strip().lower()
        if not s or s.startswith("not") or "being" in s: return False
        if s in ("taught", "taught in class", "in class", "completed"): return True
        return "taught" in s

    def get_progress_stats(self):
        total_topics = 0
        taught_count = 0
        notes_count = 0
        fully_done = 0

        for subject, topic_list in self.data["syllabus"].items():
            total_topics += len(topic_list)
            for topic in topic_list:
                tid = f"{subject}::{topic}"
                td = self.data["topics"].get(tid, {})
                status = (td.get("status") or "").lower()
                has_notes = bool(td.get("notes_made"))
                if SmartAnalytics._is_taught(status):
                    taught_count += 1
                if has_notes:
                    notes_count += 1
                if SmartAnalytics._is_taught(status) and has_notes:
                    fully_done += 1

        if total_topics == 0: return 0.0, 0.0, 0, 0
        completion_rate = 0.5 * (taught_count / total_topics) + 0.5 * (notes_count / total_topics)
        return completion_rate, (notes_count / total_topics), total_topics, fully_done

    def get_revision_queue(self):
        queue = []
        for tid, tdata in self.data["topics"].items():
            status = tdata.get("status", "")
            if not self._is_taught(status): continue
            
            sub, topic = tid.split("::", 1)
            notes = tdata.get("notes_made", False)
            rev = tdata.get("revision", "Not Revised")
            
            if not notes:
                queue.append({"topic": topic, "sub": sub, "priority": "Critical", "color": ft.Colors.RED, "msg": "Notes pending"})
            elif rev == "Not Revised":
                queue.append({"topic": topic, "sub": sub, "priority": "High", "color": ft.Colors.ORANGE, "msg": "First revision due"})
            elif rev == "Rev 1":
                queue.append({"topic": topic, "sub": sub, "priority": "Medium", "color": ft.Colors.YELLOW, "msg": "Ready for Rev 2"})
        
        random.shuffle(queue)
        prio_map = {"Critical": 0, "High": 1, "Medium": 2}
        queue.sort(key=lambda x: prio_map.get(x["priority"], 3))
        return queue[:5]

    def get_weak_areas(self):
        weak_points = []
        # 1. Check Difficult Topics
        for tid, tdata in self.data["topics"].items():
            if tdata.get("difficulty", False):
                s, t = tid.split("::", 1)
                weak_points.append({"type": "Topic", "name": f"{t} ({s})", "reason": "Marked Hard"})

        # 2. Check Subject Scores
        for subj, tests in self.data["test_series"]["subject_wise"].items():
            if not tests: continue
            avg = sum((t['marks']/t['total_marks'])*100 for t in tests) / len(tests)
            if avg < 50:
                weak_points.append({"type": "Subject", "name": subj, "reason": f"Avg Score {avg:.1f}%"})
        
        return weak_points

    def get_chart_data(self, filter_name):
        """
        Returns chart data points filtered by category for Flet LineChart.
        filter_name: "Full Mocks" OR a specific subject name.
        """
        tests = []
        if filter_name == "Full Mocks":
            tests = self.data["test_series"]["full_mock"]
        else:
            tests = self.data["test_series"]["subject_wise"].get(filter_name, [])
        
        if not tests:
            return []
            
        # Sort by date
        tests.sort(key=lambda x: x['date'])
        
        points = []
        for i, t in enumerate(tests):
            pct = (t['marks'] / t['total_marks']) * 100
            # i is the x-axis value (Test Number: 0, 1, 2...)
            points.append(ft.LineChartDataPoint(i, pct, tooltip=f"{t['name']}\n{pct:.1f}%"))
        
        return points

