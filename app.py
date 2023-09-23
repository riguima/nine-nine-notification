import webbrowser
from time import sleep

from pygame import mixer
from sqlalchemy import select
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, ScrollableContainer
from textual.widgets import Button, Footer, Header, Label, Static

from nine_nine_notification.database import Session
from nine_nine_notification.models import Project
from nine_nine_notification import browser

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
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'see_project':
            webbrowser.open(self.url, new=0)


class NineNineApp(App):
    current_page = 1
    PAGINATION = 10
    MAX_PROJECTS = 200
    CSS_PATH = 'nine-nine-app.tcss'
    BINDINGS = [
        ('d', 'toggle_dark', 'Trocar tema'),
        ('f', 'filters', 'Filtros'),
        ('p', 'previous', 'Anterior'),
        ('n', 'next', 'Próximo'),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer(id='projects'):
            with Session() as session:
                query = select(Project).order_by(Project.publication_datetime.desc())
                projects = session.scalars(query).all()[
                    : self.PAGINATION * self.current_page
                ]
                for project in projects:
                    yield ProjectWidget(project.title, project.url)
        yield Footer()

    async def on_mount(self) -> None:
        self.get_projects()

    @work(exclusive=True)
    async def get_projects(self) -> None:
        while True:
            with Session() as session:
                for i in range(1, self.MAX_PROJECTS // 10):
                    projects = await browser.get_projects(page=i)
                    if not projects:
                        break
                    for project in projects:
                        query = select(Project).where(
                            Project.url == project['url']
                        )
                        if not session.scalars(query).first():
                            model = Project(
                                title=project['title'],
                                url=project['url'],
                                publication_datetime=project[
                                    'publication_datetime'
                                ],
                            )
                            session.add(model)
                            session.commit()
                            self.refresh_projects()
                            mixer.music.play()
            if len(session.scalars(select(Project)).all()) > self.MAX_PROJECTS:
                query = select(Project).order_by(Project.publication_datetime.desc())
                for model in session.scalars(query).all()[self.MAX_PROJECTS:]:
                    session.delete(model)
                session.commit()
            sleep(60)

    def action_previous(self) -> None:
        self.current_page = max(self.current_page - 1, 1)
        self.refresh_projects()

    def action_next(self) -> None:
        with Session() as session:
            number_of_projects = len(
                session.scalars(select(Project)).all()
            )
            number_of_pages = number_of_projects // 20
            if number_of_projects % 20 != 0:
                number_of_pages += 1
            self.current_page = min(
                self.current_page + 1, number_of_pages
            )
        self.refresh_projects()

    def refresh_projects(self) -> None:
        with Session() as session:
            projects_widget = self.query_one('#projects')
            projects_widget.remove_children()
            index = self.PAGINATION * self.current_page
            query = select(Project).order_by(Project.publication_datetime.desc())
            projects = session.scalars(query).all()[
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
