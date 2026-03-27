import flet as ft
from ui import GateTrackerApp

def main(page: ft.Page):
    GateTrackerApp(page)

if __name__ == "__main__":
    ft.app(target=main)
