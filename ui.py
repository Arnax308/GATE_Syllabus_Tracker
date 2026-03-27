import flet as ft
import uuid
import random
from datetime import datetime
from config import QUOTES
from data_manager import load_data, save_data_to_file
from analytics import SmartAnalytics

class TopicRow(ft.Column):
    def __init__(self, app, subject, topic_name):
        super().__init__()
        self.app = app
        self.subject = subject
        self.topic_name = topic_name
        self.topic_id = f"{subject}::{topic_name}"
        if self.topic_id not in app.data["topics"]:
            app.data["topics"][self.topic_id] = {"status":"Not Taught","notes_made":False,"workbook_qs":False,"revision":"Not Revised","subtopics":[]}
        self.topic_data = app.data["topics"][self.topic_id]

        self.is_expanded = False
        self.subtopic_col = ft.Column(visible=False, spacing=6)

        self.status_dd = ft.Dropdown(value=self.topic_data["status"], options=[ft.dropdown.Option("Not Taught"), ft.dropdown.Option("Being Taught"), ft.dropdown.Option("Taught in Class")], width=160, dense=True, filled=True, on_change=self.on_change, text_size=12)
        self.rev_dd = ft.Dropdown(value=self.topic_data.get("revision", "Not Revised"), options=[ft.dropdown.Option("Not Revised"), ft.dropdown.Option("Rev 1"), ft.dropdown.Option("Rev 2"), ft.dropdown.Option("Rev 3")], width=120, dense=True, filled=True, on_change=self.on_change, text_size=12)
        
        self.notes_chk = ft.Checkbox(value=self.topic_data["notes_made"], on_change=self.on_change)
        self.work_chk = ft.Checkbox(value=self.topic_data["workbook_qs"], on_change=self.on_change)
        
        is_hard = self.topic_data.get("difficulty", False)
        self.hard_btn = ft.IconButton(
            icon=ft.Icons.WHATSHOT if is_hard else ft.Icons.WHATSHOT_OUTLINED,
            icon_color=ft.Colors.RED if is_hard else ft.Colors.GREY,
            tooltip="Mark as Difficult/Weak Area",
            icon_size=18,
            on_click=self.toggle_difficulty
        )

        self.expand_btn = ft.IconButton(ft.Icons.KEYBOARD_ARROW_DOWN, icon_size=20, on_click=self.toggle_subtopics)
        self.del_btn = ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=18, icon_color=ft.Colors.RED_300, on_click=self.delete_self)

        init_color, init_weight = self.get_text_props()
        self.title_text = ft.Text(topic_name, expand=True, size=14, weight=init_weight, color=init_color)

        self.main_row = ft.Container(
            content=ft.Row([
                self.expand_btn,
                self.title_text,
                self.hard_btn,
                ft.VerticalDivider(width=10),
                self.status_dd,
                ft.Column([ft.Text("N", size=8), self.notes_chk], spacing=0, alignment="center"),
                ft.Column([ft.Text("W", size=8), self.work_chk], spacing=0, alignment="center"),
                self.rev_dd,
                self.del_btn
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=5, border_radius=8, bgcolor=self.get_row_color()
        )

        self.controls = [self.main_row, ft.Container(content=self.subtopic_col, padding=ft.padding.only(left=56))]
        self.render_subtopics()

    def get_row_color(self):
        s = (self.topic_data.get("status") or "").strip().lower()
        if self.topic_data.get("difficulty", False):
            return ft.Colors.with_opacity(0.1, ft.Colors.RED)
        if SmartAnalytics._is_taught(s):
            return ft.Colors.with_opacity(0.05, ft.Colors.GREEN)
        if "being" in s:
            return ft.Colors.with_opacity(0.05, ft.Colors.ORANGE)
        return ft.Colors.with_opacity(0.01, ft.Colors.WHITE)

    def get_text_props(self):
        s = (self.topic_data.get("status") or "").strip().lower()
        notes = bool(self.topic_data.get("notes_made"))
        color = ft.Colors.WHITE
        if SmartAnalytics._is_taught(s): color = ft.Colors.GREEN
        elif "being" in s: color = ft.Colors.AMBER
        
        weight = ft.FontWeight.W_700 if notes else ft.FontWeight.W_400
        return color, weight

    def toggle_difficulty(self, e):
        curr = self.topic_data.get("difficulty", False)
        self.topic_data["difficulty"] = not curr
        self.hard_btn.icon = ft.Icons.WHATSHOT if not curr else ft.Icons.WHATSHOT_OUTLINED
        self.hard_btn.icon_color = ft.Colors.RED if not curr else ft.Colors.GREY
        self.main_row.bgcolor = self.get_row_color()
        self.update()
        self.app.mark_unsaved()
        self.app.log_activity(f"Marked '{self.topic_name}' as {'Hard' if not curr else 'Normal'}")

    def on_change(self, e):
        self.topic_data["status"] = self.status_dd.value
        self.topic_data["revision"] = self.rev_dd.value
        self.topic_data["notes_made"] = self.notes_chk.value
        self.topic_data["workbook_qs"] = self.work_chk.value
        if e.control == self.rev_dd:
            self.topic_data["last_revised"] = datetime.now().strftime("%Y-%m-%d")
        new_color, new_weight = self.get_text_props()
        self.title_text.color = new_color
        self.title_text.weight = new_weight
        self.main_row.bgcolor = self.get_row_color()
        self.main_row.update()
        self.title_text.update()
        self.app.mark_unsaved()
        self.app.update_subject_progress(self.subject)

    def toggle_subtopics(self, e):
        self.is_expanded = not self.is_expanded
        self.subtopic_col.visible = self.is_expanded
        self.expand_btn.icon = ft.Icons.KEYBOARD_ARROW_UP if self.is_expanded else ft.Icons.KEYBOARD_ARROW_DOWN
        self.update()

    def render_subtopics(self):
        self.subtopic_col.controls.clear()
        for i, sub in enumerate(self.topic_data["subtopics"]):
            self.subtopic_col.controls.append(ft.Row([ft.Icon(ft.Icons.SUBDIRECTORY_ARROW_RIGHT, size=12, color="grey"), ft.Text(sub, size=12, expand=True), ft.IconButton(ft.Icons.CLOSE, icon_size=14, on_click=lambda e, idx=i: self.remove_subtopic(idx))]))
        new_sub = ft.TextField(hint_text="New subtopic", height=30, text_size=12, content_padding=5, expand=True)
        def add_s(e):
            if new_sub.value:
                self.topic_data["subtopics"].append(new_sub.value)
                new_sub.value = ""
                self.render_subtopics()
                self.update()
                self.app.mark_unsaved()
        self.subtopic_col.controls.append(ft.Row([new_sub, ft.IconButton(ft.Icons.ADD, icon_size=16, on_click=add_s)]))

    def remove_subtopic(self, idx):
        self.topic_data["subtopics"].pop(idx)
        self.render_subtopics()
        self.update()
        self.app.mark_unsaved()

    def delete_self(self, e):
        self.app.delete_topic_request(self.subject, self.topic_name)

class SubjectCard(ft.Card):
    def __init__(self, app, subject_name):
        super().__init__()
        self.app = app
        self.subject_name = subject_name
        self.prog_bar = ft.ProgressBar(value=0, height=8, border_radius=4, color=ft.Colors.BLUE_300, bgcolor=ft.Colors.GREY_800)
        self.prog_text = ft.Text("0%", size=12, weight="bold")
        self.topic_container = ft.Column(spacing=4)

        def delete_subject_action(e):
            self.app.delete_subject_request(self.subject_name)

        header = ft.Row([
            ft.Row([ft.Icon(ft.Icons.MENU_BOOK, size=18, color=ft.Colors.BLUE_200), ft.Text(subject_name, size=16, weight="bold")], spacing=10),
            ft.Row([ft.Container(content=self.prog_bar, width=100), self.prog_text, ft.IconButton(ft.Icons.DELETE_FOREVER, icon_size=18, icon_color=ft.Colors.RED_300, on_click=delete_subject_action, tooltip="Delete Subject")], spacing=10)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        self.content = ft.ExpansionTile(
            title=header,
            controls=[ft.Container(content=ft.Column([
                self.topic_container,
                ft.Divider(height=10, color="transparent"),
                ft.Row([
                    ft.TextField(ref=app.new_topic_refs.setdefault(subject_name, ft.Ref()), hint_text="Add Topic...", height=40, expand=True, content_padding=10, text_size=13),
                    ft.ElevatedButton("Add", on_click=lambda e: app.add_topic(subject_name), height=40)
                ])
            ]), padding=15)]
        )
        self.render_topics()
        self.recalc_progress()

    def render_topics(self):
        topics = self.app.data["syllabus"].get(self.subject_name, [])
        self.topic_container.controls = [TopicRow(self.app, self.subject_name, t) for t in topics]

    def recalc_progress(self):
        topics = self.app.data["syllabus"].get(self.subject_name, [])
        if not topics: 
            self.prog_bar.value = 0; self.prog_text.value = "0%"
            return
        taught, notes = 0, 0
        for t in topics:
            td = self.app.data["topics"].get(f"{self.subject_name}::{t}", {})
            if SmartAnalytics._is_taught(td.get("status")): taught += 1
            if td.get("notes_made"): notes += 1
        val = 0.5 * (taught/len(topics)) + 0.5 * (notes/len(topics))
        self.prog_bar.value = val
        self.prog_text.value = f"{int(val*100)}%"
        if self.page: self.update()

# -------------------------
# Main App
# -------------------------
class GateTrackerApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "GATE Syllabus Tracker"
        self.page.bgcolor = ft.Colors.BLACK
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 0

        self.data = load_data()
        self.analytics = SmartAnalytics(self.data)
        self.has_unsaved_changes = False
        self.subject_cards = {}
        self.new_topic_refs = {}

        self.save_fab = ft.FloatingActionButton(icon=ft.Icons.SAVE, text="Save", visible=False, on_click=self.save_changes, bgcolor=ft.Colors.AMBER, foreground_color=ft.Colors.BLACK)
        self.setup_ui()

    def log_activity(self, text):
        entry = {"time": datetime.now().strftime("%Y-%m-%d %H:%M"), "text": text}
        self.data["activity_log"].insert(0, entry)
        self.data["activity_log"] = self.data["activity_log"][:20]
        self.mark_unsaved()

    def setup_ui(self):
        self.rail = ft.NavigationRail(
            selected_index=0, label_type=ft.NavigationRailLabelType.ALL, min_width=80, 
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(icon=ft.Icons.DASHBOARD_OUTLINED, selected_icon=ft.Icons.DASHBOARD, label="Overview"),
                ft.NavigationRailDestination(icon=ft.Icons.LIST_ALT, label="Syllabus"),
                ft.NavigationRailDestination(icon=ft.Icons.INSERT_CHART_OUTLINED, selected_icon=ft.Icons.INSERT_CHART, label="Tests"),
            ], on_change=self.nav_change
        )
        self.body = ft.Container(expand=True, padding=20)
        self.page.add(ft.Row([self.rail, ft.VerticalDivider(width=1), self.body], expand=True))
        self.page.floating_action_button = self.save_fab
        self.nav_change(None)

    def nav_change(self, e):
        idx = self.rail.selected_index
        if idx == 0: self.view_dashboard()
        elif idx == 1: self.view_syllabus()
        elif idx == 2: self.view_tests()
        self.page.update()

    def mark_unsaved(self):
        if not self.has_unsaved_changes:
            self.has_unsaved_changes = True
            self.save_fab.visible = True
            self.page.update()

    def save_changes(self, e):
        if save_data_to_file(self.data):
            self.has_unsaved_changes = False
            self.save_fab.visible = False
            self.page.snack_bar = ft.SnackBar(ft.Text("Saved successfully!"), bgcolor=ft.Colors.GREEN)
            self.page.snack_bar.open = True
            self.page.update()

    def update_subject_progress(self, subject):
        if subject in self.subject_cards: self.subject_cards[subject].recalc_progress()

    def add_topic(self, subject):
        ref = self.new_topic_refs.get(subject)
        if ref and ref.current.value.strip():
            val = ref.current.value.strip()
            self.data["syllabus"][subject].append(val)
            self.data["topics"][f"{subject}::{val}"] = {"status":"Not Taught", "difficulty": False}
            self.subject_cards[subject].render_topics()
            self.subject_cards[subject].recalc_progress()
            self.subject_cards[subject].update()
            ref.current.value = ""
            self.log_activity(f"Added topic: {val}")

    def delete_topic_request(self, subject, topic):
        self.data["syllabus"][subject].remove(topic)
        del self.data["topics"][f"{subject}::{topic}"]
        self.subject_cards[subject].render_topics()
        self.subject_cards[subject].recalc_progress()
        self.subject_cards[subject].update()
        self.log_activity(f"Deleted topic: {topic}")

    def delete_subject_request(self, subject):
        del self.data["syllabus"][subject]
        topics_to_delete = [tid for tid in self.data["topics"] if tid.startswith(f"{subject}::")]
        for tid in topics_to_delete:
            del self.data["topics"][tid]
        if subject in self.data["test_series"]["subject_wise"]:
            del self.data["test_series"]["subject_wise"][subject]
        
        self.log_activity(f"Deleted subject: {subject}")
        self.view_syllabus()

    # -------------------------
    # Dashboard View
    # -------------------------
    def view_dashboard(self):
        prog, notes_prog, _, _ = self.analytics.get_progress_stats()
        
        # 1. Target vs Reality
        target = self.data.get("target_score", 75.0)
        mocks = self.data["test_series"]["full_mock"]
        curr_avg = sum((m['marks']/m['total_marks'])*100 for m in mocks)/len(mocks) if mocks else 0.0
        target_color = ft.Colors.GREEN if curr_avg >= target else (ft.Colors.ORANGE if curr_avg >= target-10 else ft.Colors.RED)

        target_card = ft.Container(
            content=ft.Column([
                ft.Text("Performance Target", size=14, color="grey"),
                ft.Row([
                    ft.Text(f"{curr_avg:.1f}%", size=30, weight="bold", color=target_color),
                    ft.Text(f"/ {target}%", size=16, color="grey", weight="bold")
                ], alignment="center"),
                ft.Slider(min=0, max=100, value=target, label="{value}%", on_change_end=self.set_target),
                ft.Text("Set Target Score", size=10, italic=True)
            ], horizontal_alignment="center"),
            padding=15, bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, border_radius=12, width=220
        )

        # 2. Weekly Goals
        def toggle_goal(e, idx):
            self.data["goals"][idx]["done"] = e.control.value
            self.mark_unsaved()
            self.page.update()
        
        def add_goal(e):
            if goal_input.value:
                self.data["goals"].append({"text": goal_input.value, "done": False, "id": str(uuid.uuid4())})
                goal_input.value = ""
                self.log_activity("Added new weekly goal")
                self.view_dashboard()

        def del_goal(e, idx):
            self.data["goals"].pop(idx)
            self.mark_unsaved()
            self.view_dashboard()

        goal_list = ft.Column(spacing=5)
        for i, g in enumerate(self.data["goals"]):
            goal_list.controls.append(ft.Row([
                ft.Checkbox(value=g["done"], on_change=lambda e, idx=i: toggle_goal(e, idx)),
                ft.Text(g["text"], expand=True, size=13),
                ft.IconButton(ft.Icons.CLOSE, icon_size=14, on_click=lambda e, idx=i: del_goal(e, idx))
            ]))
        
        goal_input = ft.TextField(hint_text="Add Weekly Goal...", text_size=12, height=35, content_padding=5, expand=True, on_submit=add_goal)
        goals_card = ft.Container(
            content=ft.Column([
                ft.Row([ft.Icon(ft.Icons.CHECKLIST, color=ft.Colors.BLUE), ft.Text("Weekly Goals", weight="bold")]),
                goal_list,
                ft.Row([goal_input, ft.IconButton(ft.Icons.ADD, on_click=add_goal)])
            ]),
            padding=15, bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, border_radius=12, expand=True
        )

        # 3. Revision Scheduler
        rev_queue = self.analytics.get_revision_queue()
        rev_items = []
        if not rev_queue:
            rev_items.append(ft.Text("🎉 All caught up! Great job.", color=ft.Colors.GREEN))
        else:
            for item in rev_queue:
                rev_items.append(ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CIRCLE, size=10, color=item["color"]),
                        ft.Column([
                            ft.Text(item["topic"], weight="bold", size=13),
                            ft.Text(f"{item['sub']} • {item['msg']}", size=11, color="grey")
                        ], spacing=0)
                    ]),
                    padding=8, bgcolor=ft.Colors.BLACK12, border_radius=6
                ))

        rev_card = ft.Container(
            content=ft.Column([
                ft.Row([ft.Icon(ft.Icons.SCHEDULE, color=ft.Colors.ORANGE), ft.Text("Revision Queue", weight="bold")]),
                ft.Column(rev_items, spacing=5)
            ]),
            padding=15, bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, border_radius=12, width=300
        )

        # 4. Weak Areas & Activity
        weak = self.analytics.get_weak_areas()
        if weak:
            weak_controls = [ft.Row([ft.Icon(ft.Icons.WARNING_AMBER, size=16, color=ft.Colors.RED), ft.Text(f"{w['name']}", color=ft.Colors.RED_200, size=13)]) for w in weak[:5]]
        else:
            weak_controls = [ft.Text("No weak areas detected yet!", color=ft.Colors.GREEN)]
        
        activity_rows = [ft.Text(f"{a['time'].split()[1]} - {a['text']}", size=11, color="grey") for a in self.data["activity_log"][:6]]
        
        info_col = ft.Column([
            ft.Text("Weak Topics Alert", weight="bold"),
            ft.Container(content=ft.Column(weak_controls, spacing=2), padding=10, bgcolor=ft.Colors.RED_900, border_radius=8),
            ft.Divider(),
            ft.Text("Recent Activity", weight="bold"),
            ft.Column(activity_rows, spacing=2)
        ], expand=True)

        quote = ft.Container(content=ft.Text(random.choice(QUOTES), italic=True, text_align="center", size=15), padding=15, bgcolor=ft.Colors.BLUE_GREY_900, border_radius=10, width=float("inf"))

        self.body.content = ft.Column([
            ft.Text("Dashboard", size=28, weight="bold"),
            quote,
            ft.Row([target_card, goals_card], alignment="start", vertical_alignment="start"),
            ft.Row([rev_card, ft.Container(content=info_col, bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, padding=15, border_radius=12, expand=True)], vertical_alignment="start")
        ], scroll="auto")
        self.page.update()

    def set_target(self, e):
        self.data["target_score"] = int(e.control.value)
        self.mark_unsaved()
        self.view_dashboard()

    # -------------------------
    # Syllabus View
    # -------------------------
    def view_syllabus(self):
        cards = []
        for subject in sorted(self.data["syllabus"].keys()):
            c = SubjectCard(self, subject)
            self.subject_cards[subject] = c
            cards.append(c)
        
        new_subj = ft.TextField(hint_text="New Subject", expand=True, height=40)
        def add_sub(e):
            if new_subj.value:
                self.data["syllabus"][new_subj.value] = []
                self.log_activity(f"Created subject: {new_subj.value}")
                self.view_syllabus()

        self.body.content = ft.Column([
            ft.Text("Syllabus Tracker", size=28, weight="bold"),
            ft.Row([new_subj, ft.ElevatedButton("Add Subject", on_click=add_sub)]),
            ft.Divider(),
            ft.Column(cards, spacing=10)
        ], scroll="auto")
        self.page.update()

    # -------------------------
    # Test & Chart Helpers
    # -------------------------
    def _update_chart(self, filter_name, chart_ref):
        """Helper to generate and update the line chart."""
        points = self.analytics.get_chart_data(filter_name)
        if chart_ref.current:
            if not points:
                chart_ref.current.data_series = []
                chart_ref.current.bottom_axis.labels = []
            else:
                chart_ref.current.data_series = [
                    ft.LineChartData(
                        data_points=points,
                        stroke_width=3,
                        color=ft.Colors.CYAN,
                        curved=True,
                        stroke_cap_round=True,
                    )
                ]
                chart_ref.current.bottom_axis.labels = [ft.ChartAxisLabel(value=i, label=ft.Text(str(i+1), size=10)) for i in range(len(points))]
            chart_ref.current.update()

    def _create_chart_skeleton(self, chart_ref):
        """Returns the LineChart container skeleton."""
        return ft.LineChart(
            ref=chart_ref,
            data_series=[], # Data points are updated by _update_chart
            border=ft.border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
            horizontal_grid_lines=ft.ChartGridLines(interval=10, color=ft.Colors.with_opacity(0.1, ft.Colors.WHITE), width=1),
            vertical_grid_lines=ft.ChartGridLines(interval=1, color=ft.Colors.with_opacity(0.1, ft.Colors.WHITE), width=1),
            left_axis=ft.ChartAxis(labels=[ft.ChartAxisLabel(value=v, label=ft.Text(f"{v}%", size=10)) for v in range(0, 110, 20)]),
            bottom_axis=ft.ChartAxis(labels=[]), # Labels updated by _update_chart
            tooltip_bgcolor=ft.Colors.BLUE_GREY_800,
            min_y=0, max_y=100,
            expand=True
        )

    def _build_test_history_table(self, tests, is_mock, subject=None):
        """Builds the history DataTable for mocks or subject tests."""
        rows = []
        # Sort tests by date descending for table
        sorted_tests = sorted(tests, key=lambda x: x['date'], reverse=True)
        
        def delete_test_action(e, tid):
             if is_mock:
                 self.data["test_series"]["full_mock"] = [x for x in self.data["test_series"]["full_mock"] if x['id'] != tid]
             else:
                 self.data["test_series"]["subject_wise"][subject] = [x for x in self.data["test_series"]["subject_wise"][subject] if x['id'] != tid]
             self.mark_unsaved()
             self.view_tests()

        for t in sorted_tests:
            perc = (t['marks']/t['total_marks'])*100
            color = ft.Colors.BLUE_300 if perc > 70 else (ft.Colors.ORANGE if perc > 40 else ft.Colors.RED)
            rows.append(ft.DataRow([
                ft.DataCell(ft.Text(t['date'])), 
                ft.DataCell(ft.Text(t['name'])), 
                ft.DataCell(ft.Text(f"{t['marks']}/{t['total_marks']}")), 
                ft.DataCell(ft.Container(content=ft.Text(f"{perc:.1f}%", color=ft.Colors.BLACK, weight="bold", size=12), bgcolor=color, padding=ft.padding.all(5), border_radius=4)), 
                ft.DataCell(ft.IconButton(ft.Icons.DELETE, icon_size=18, on_click=lambda e, tid=t['id']: delete_test_action(e, tid)))
            ]))
        if not rows:
            return ft.Text("No tests recorded yet.", italic=True)
            
        return ft.DataTable(
            columns=[ft.DataColumn(ft.Text("Date")), ft.DataColumn(ft.Text("Test Name")), ft.DataColumn(ft.Text("Score")), ft.DataColumn(ft.Text("Perf")), ft.DataColumn(ft.Text("Actions"))], 
            rows=rows, 
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT), 
            border_radius=10, 
            heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGHEST
        )
    
    def _build_mistake_log_ui(self, filter_id, filter_type):
        """
        Generic Mistake Log Builder.
        filter_type: "mock" or "subject"
        filter_id: The mock name or subject name to filter by.
        """
        q_field = ft.TextField(label="Wrong Question / Concept", expand=True, dense=True)
        s_field = ft.TextField(label="Correct Solution / Note", expand=True, multiline=True, dense=True, min_lines=2)
        mistake_list_ref = ft.Ref()
        mistake_log_col = ft.Column(scroll="auto", expand=True, spacing=10, ref=mistake_list_ref)

        def add_mistake_entry(e):
            if q_field.value:
                # Store with type and reference
                self.data["mistake_log"].append({
                    "id": str(uuid.uuid4()), 
                    "type": filter_type,
                    "ref": filter_id, 
                    "q": q_field.value, 
                    "sol": s_field.value
                })
                q_field.value=""; s_field.value=""
                self.mark_unsaved()
                self._update_mistake_list_visuals(mistake_list_ref.current, filter_id, filter_type)
                self.page.update()

        def _refresh_list():
             self._update_mistake_list_visuals(mistake_log_col, filter_id, filter_type)

        # Container
        container = ft.Container(
            content=ft.Column([
                ft.Text(f"Mistake Log ({filter_type.title()}: {filter_id})", weight="bold"),
                ft.Row([q_field, s_field, ft.ElevatedButton("Log", on_click=add_mistake_entry)]),
                ft.Divider(),
                mistake_log_col,
            ]),
            padding=15, bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, border_radius=12
        )
        
        # Initial population
        _refresh_list()
        
        return container, _refresh_list

    def _update_mistake_list_visuals(self, mistake_list_col, filter_ref, filter_type):
        mistake_list_col.controls.clear()
        
        def del_m(e, mid):
            self.data["mistake_log"] = [m for m in self.data["mistake_log"] if m['id'] != mid]
            self.mark_unsaved()
            self._update_mistake_list_visuals(mistake_list_col, filter_ref, filter_type)
            self.page.update()

        # Backward compatibility check: older logs used 'mock' key. map them to type='mock' ref=mock_name
        filtered = []
        for m in self.data["mistake_log"]:
            # Normalization for old data
            m_type = m.get("type", "mock") 
            m_ref = m.get("ref", m.get("mock")) # Fallback to old 'mock' key

            if m_type == filter_type and m_ref == filter_ref:
                filtered.append(m)

        if not filtered:
            mistake_list_col.controls.append(ft.Text(f"No logged mistakes for this {filter_type}.", italic=True))
        else:
            for m in filtered:
                mistake_list_col.controls.append(ft.Container(content=ft.Column([
                    ft.Row([ft.Text(f"Q: {m['q']}", weight="bold", color=ft.Colors.RED_200, expand=True), ft.IconButton(ft.Icons.DELETE, icon_size=16, on_click=lambda e, mid=m['id']: del_m(e, mid))]),
                    ft.Text(f"A: {m['sol']}", color=ft.Colors.WHITE70, size=12),
                    ft.Divider()
                ]), padding=5))
        
        if mistake_list_col.page:
            mistake_list_col.update()

    def _build_mock_tab_content(self):
        """Content for the 'Full Mocks' tab."""
        # 1. Input Form (Mock specific)
        t_name = ft.TextField(label="Mock Test Name", expand=True, dense=True, filled=True)
        t_marks = ft.TextField(label="Marks", width=100, dense=True, filled=True)
        t_total = ft.TextField(label="Total", width=100, value="100", dense=True, filled=True)
        
        def add_mock(e):
            if not t_name.value or not t_marks.value: return
            try:
                entry = {"id": str(uuid.uuid4()), "name": t_name.value, "marks": float(t_marks.value), "total_marks": float(t_total.value), "date": datetime.now().strftime("%Y-%m-%d")}
                self.data["test_series"]["full_mock"].append(entry)
                self.mark_unsaved()
                self.view_tests() # Refresh
            except ValueError:
                self.page.snack_bar = ft.SnackBar(ft.Text("Invalid numbers!"), bgcolor=ft.Colors.RED); self.page.snack_bar.open=True; self.page.update()

        input_row = ft.Container(content=ft.Row([t_name, t_marks, t_total, ft.ElevatedButton("Add Mock Score", on_click=add_mock)]), padding=15, bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, border_radius=10)

        # 2. Mistake Log (Mock specific selection)
        # We need a dropdown to select WHICH mock to log mistakes for
        mock_options = [ft.dropdown.Option(m['name']) for m in self.data["test_series"]["full_mock"]]
        m_dd = ft.Dropdown(options=mock_options, label="Select Mock for Mistakes", width=300, dense=True, filled=True, value=mock_options[0].text if mock_options else None)
        
        mistake_container_ref = ft.Ref()
        
        def render_mock_mistakes(mock_name):
            if not mock_name: return ft.Text("Add a mock test to log mistakes.")
            c, _ = self._build_mistake_log_ui(mock_name, "mock")
            return c

        mistake_area = ft.Container(content=render_mock_mistakes(m_dd.value), ref=mistake_container_ref)

        def on_mock_select(e):
            mistake_container_ref.current.content = render_mock_mistakes(e.control.value)
            mistake_container_ref.current.update()
        m_dd.on_change = on_mock_select

        # 3. History
        mock_history = self._build_test_history_table(self.data["test_series"]["full_mock"], True)
        history_container = ft.Container(content=ft.Column([mock_history], scroll="auto"), height=300)

        # 4. Chart
        mock_chart_ref = ft.Ref()
        chart = self._create_chart_skeleton(mock_chart_ref)
        points = self.analytics.get_chart_data("Full Mocks")
        chart.data_series = [ft.LineChartData(data_points=points, stroke_width=3, color=ft.Colors.CYAN, curved=True, stroke_cap_round=True)] if points else []
        if points:
            chart.bottom_axis.labels = [ft.ChartAxisLabel(value=i, label=ft.Text(str(i+1), size=10)) for i in range(len(points))]

        return ft.Column([
            ft.Text("Add Mock Test Data", weight="bold"),
            input_row,
            ft.Divider(),
            ft.Text("Mistake Log", weight="bold"),
            m_dd,
            mistake_area,
            ft.Divider(),
            ft.Text("Full Mock History", weight="bold"),
            history_container,
            ft.Divider(),
            ft.Text("Trend Analysis", weight="bold"),
            ft.Container(content=chart, height=250, padding=10, border_radius=12, bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST),
        ], scroll="auto")

    def _build_subject_tab_content(self):
        """Content for the 'Subject-wise' tab."""
        subj_chart_ref = ft.Ref()
        subj_history_ref = ft.Ref()
        subj_mistake_ref = ft.Ref()

        # 1. Subject Dropdown
        subject_options = [ft.dropdown.Option(s) for s in sorted(self.data["syllabus"].keys())]
        subj_dd = ft.Dropdown(
            options=subject_options,
            label="Select Subject",
            width=300,
            dense=True,
            filled=True,
            value=subject_options[0].text if subject_options else None
        )

        # 2. Input Form (Subject specific)
        t_name = ft.TextField(label="Test Topic/Name", expand=True, dense=True, filled=True)
        t_marks = ft.TextField(label="Marks", width=100, dense=True, filled=True)
        t_total = ft.TextField(label="Total", width=100, value="100", dense=True, filled=True)

        def add_subj_test(e):
            if not subj_dd.value:
                 self.page.snack_bar = ft.SnackBar(ft.Text("Select a subject first!"), bgcolor=ft.Colors.RED); self.page.snack_bar.open=True; self.page.update(); return
            if not t_name.value or not t_marks.value: return
            try:
                entry = {"id": str(uuid.uuid4()), "name": t_name.value, "marks": float(t_marks.value), "total_marks": float(t_total.value), "date": datetime.now().strftime("%Y-%m-%d")}
                self.data["test_series"]["subject_wise"].setdefault(subj_dd.value, []).append(entry)
                self.mark_unsaved()
                self.view_tests() # Full Refresh to simplicity
            except ValueError:
                self.page.snack_bar = ft.SnackBar(ft.Text("Invalid numbers!"), bgcolor=ft.Colors.RED); self.page.snack_bar.open=True; self.page.update()

        input_row = ft.Container(content=ft.Row([t_name, t_marks, t_total, ft.ElevatedButton("Add Score", on_click=add_subj_test)]), padding=15, bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, border_radius=10)

        # 3. Dynamic Content Builder
        def build_dynamic_content(selected_subj):
            if not selected_subj: return ft.Text("Select a subject to view data.")
            
            # Mistake Log
            mistake_ui, _ = self._build_mistake_log_ui(selected_subj, "subject")
            
            # History
            tests = self.data["test_series"]["subject_wise"].get(selected_subj, [])
            history_table = self._build_test_history_table(tests, False, selected_subj)
            hist_cont = ft.Container(content=ft.Column([history_table], scroll="auto"), height=300)
            
            # Chart
            points = self.analytics.get_chart_data(selected_subj)
            chart = self._create_chart_skeleton(ft.Ref()) # No ref needed here as we rebuild
            chart.data_series = [ft.LineChartData(data_points=points, stroke_width=3, color=ft.Colors.CYAN, curved=True, stroke_cap_round=True)] if points else []
            if points:
                chart.bottom_axis.labels = [ft.ChartAxisLabel(value=i, label=ft.Text(str(i+1), size=10)) for i in range(len(points))]
            chart_cont = ft.Container(content=chart, height=250, padding=10, border_radius=12, bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST)

            return ft.Column([
                ft.Text(f"Add Test Data for {selected_subj}", weight="bold"),
                input_row,
                ft.Divider(),
                mistake_ui,
                ft.Divider(),
                ft.Text(f"History: {selected_subj}", weight="bold"),
                hist_cont,
                ft.Divider(),
                ft.Text(f"Trend: {selected_subj}", weight="bold"),
                chart_cont
            ])

        dynamic_area = ft.Container(content=build_dynamic_content(subj_dd.value))

        def on_subj_change(e):
            dynamic_area.content = build_dynamic_content(e.control.value)
            dynamic_area.update()
        
        subj_dd.on_change = on_subj_change

        return ft.Column([
            ft.Row([ft.Text("Subject:", size=16, weight="bold"), subj_dd], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Divider(),
            dynamic_area
        ], scroll="auto")

    def view_tests(self):
        """Main method to display the Test Performance Dashboard."""
        
        mock_content = self._build_mock_tab_content()
        subject_content = self._build_subject_tab_content()

        self.body.content = ft.Column([
            ft.Text("Test Performance Dashboard 📊", size=32, weight="bold"),
            ft.Tabs(
                selected_index=0, 
                animation_duration=300, 
                tabs=[
                    ft.Tab(text="Full Mock Tests", icon=ft.Icons.SECURITY, content=mock_content), 
                    ft.Tab(text="Subject-wise Tests", icon=ft.Icons.MENU_BOOK, content=subject_content)
                ], 
                expand=True
            )
        ], scroll="auto")
        self.page.update()

