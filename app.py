import webbrowser

from pygame import mixer
from sqlalchemy import select
from textual.app import App, ComposeResult
from textual.containers import Horizontal, ScrollableContainer
from textual.widgets import Button, Footer, Header, Label, Static

from nine_nine_notification.database import Session
from nine_nine_notification.models import Project

mixer.init()
mixer.music.load('assets/bell.wav')


class ProjectWidget(Static):
    def __init__(self, title: str, url: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.title = title
        self.url = url

    def compose(self) -> ComposeResult:
        yield Horizontal(Label(self.title))
        yield Horizontal(
            Button('Ver Projeto', id='see_project'),
            id='see_project_container',
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'see_project':
            webbrowser.open(self.url, new=0)


class NineNineApp(App):
    current_page = 1
    PAGINATION = 20
    CSS_PATH = 'nine-nine-app.tcss'
    BINDINGS = [
        ('d', 'toggle_dark', 'Trocar tema'),
        ('f', 'filters', 'Filtros'),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer(id='projects'):
            with Session() as session:
                projects = session.scalars(select(Project)).all()[
                    : self.PAGINATION * self.current_page
                ]
                for project in projects:
                    yield ProjectWidget(project.title, project.url)
        yield Horizontal(
            Button('Anterior', id='previous'),
            Button('Próximo', id='next'),
            id='control_buttons',
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        with Session() as session:
            if event.button.id == 'previous':
                self.current_page = max(self.current_page - 1, 1)
            elif event.button.id == 'next':
                number_of_projects = len(
                    session.scalars(select(Project)).all()
                )
                number_of_pages = number_of_projects // 20
                if number_of_projects % 20 != 0:
                    number_of_pages += 1
                self.current_page += min(
                    self.current_page + 1, number_of_pages
                )
            projects_widget = self.query_one('#projects')
            projects_widget.remove_children()
            index = self.PAGINATION * self.current_page
            projects = session.scalars(select(Project)).all()[
                index - self.PAGINATION : index
            ]
            for project in projects:
                projects_widget.mount(
                    ProjectWidget(project.title, project.url)
                )

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    def action_filters(self) -> None:
        pass


if __name__ == '__main__':
    app = NineNineApp()
    app.run()
