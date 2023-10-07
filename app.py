import webbrowser
from asyncio import sleep
from pathlib import Path

import toml
from httpx import ConnectTimeout
from pygame import mixer
from sqlalchemy import select
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, ScrollableContainer
from textual.validation import Number
from textual.widgets import Button, Footer, Header, Input, Label, Static

from nine_nine_notification import browser
from nine_nine_notification.database import Session
from nine_nine_notification.models import Project

mixer.init()
mixer.music.load('assets/bell.wav')

config_path = Path('config.toml')
if not config_path.exists():
    file = open(config_path, 'w')
    file.close()
config = toml.load(open(config_path))


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


class FiltersWidget(Static):
    def compose(self) -> ComposeResult:
        yield Horizontal(
            Label('Filtros', id='filters_info'),
            id='filters_info_container',
        )
        yield Horizontal(Label('Dias'))
        yield Horizontal(
            Label('De'),
            Input(validators=[Number(minimum=0)], id='between_day'),
            Label('Até'),
            Input(validators=[Number(minimum=0)], id='until_day'),
        )
        yield Horizontal(
            Button('Salvar', id='save'),
            Button('Sair', id='quit'),
            id='save_container',
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'save':
            between_day = int(self.query_one('#between_day').value)
            until_day = int(self.query_one('#until_day').value)
            self.query_one('#filters_info_container').remove_class('error')
            if until_day < between_day:
                self.query_one('#filters_info').update(
                    'Filtro de dia inválido'
                )
                self.query_one('#filters_info_container').add_class('error')
            else:
                if config.get('filters') is None:
                    config['filters'] = {}
                config['filters']['BETWEEN_DAY'] = between_day
                config['filters']['UNTIL_DAY'] = until_day
                toml.dump(config, open(config_path, 'w'))
                self.query_one('#filters_info').update('Salvo')
        elif event.button.id == 'quit':
            pass

    @on(Input.Changed)
    def show_invalid_reasons(self, event: Input.Changed) -> None:
        if not event.validation_result.is_valid:
            event.input.value = event.input.value[:-1]


class NineNineApp(App):
    current_page = 1
    PAGINATION = 10
    MAX_PROJECTS = 200
    CSS_PATH = 'styles.tcss'
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
                query = select(Project).order_by(
                    Project.publication_datetime.desc()
                )
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
                    try:
                        projects = await browser.get_projects(page=i)
                    except ConnectTimeout:
                        continue
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
                            query = select(Project).order_by(
                                Project.publication_datetime.desc()
                            )
                            if session.scalars(query).first() == model:
                                self.refresh_projects()
                                mixer.music.play()
            if len(session.scalars(select(Project)).all()) > self.MAX_PROJECTS:
                query = select(Project).order_by(
                    Project.publication_datetime.desc()
                )
                for model in session.scalars(query).all()[self.MAX_PROJECTS :]:
                    session.delete(model)
                session.commit()
            await sleep(60)

    def action_previous(self) -> None:
        self.current_page = max(self.current_page - 1, 1)
        self.refresh_projects()

    def action_next(self) -> None:
        with Session() as session:
            number_of_projects = len(session.scalars(select(Project)).all())
            number_of_pages = number_of_projects // 20
            if number_of_projects % 20 != 0:
                number_of_pages += 1
            self.current_page = min(self.current_page + 1, number_of_pages)
        self.refresh_projects()

    def refresh_projects(self) -> None:
        with Session() as session:
            projects_widget = self.query_one('#projects')
            projects_widget.remove_children()
            index = self.PAGINATION * self.current_page
            query = select(Project).order_by(
                Project.publication_datetime.desc()
            )
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
        projects_widget = self.query_one('#projects')
        projects_widget.remove_children()
        projects_widget.mount(FiltersWidget())


if __name__ == '__main__':
    app = NineNineApp()
    app.run()
