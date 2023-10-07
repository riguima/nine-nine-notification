import webbrowser
from asyncio import sleep
from datetime import datetime, timedelta
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
if config_path.exists():
    config = toml.load(open(config_path))
else:
    file = open(config_path, 'w')
    file.close()
    config = toml.load(open(config_path))
    config['filters'] = {}
    config['filters']['BETWEEN_DAY'] = -1
    config['filters']['UNTIL_DAY'] = -1


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
        yield Horizontal(
            Label('Dias:'),
            Input(
                str(config['filters']['BETWEEN_DAY']),
                placeholder='De',
                validators=[Number(minimum=0)],
                id='between_day',
            ),
            Input(
                str(config['filters']['UNTIL_DAY']),
                placeholder='Até',
                validators=[Number(minimum=0)],
                id='until_day',
            ),
        )
        yield Horizontal(
            Button('Salvar', id='save'),
            id='save_container',
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'save':
            between_day_input = self.query_one('#between_day')
            between_day = int(between_day_input.value) if between_day_input.value else -1
            until_day_input = self.query_one('#until_day')
            until_day = int(until_day_input.value) if until_day_input.value else -1
            self.query_one('#filters_info_container').remove_class('error')
            if until_day < between_day:
                self.query_one('#filters_info').update(
                    'Filtro de dia inválido'
                )
                self.query_one('#filters_info_container').add_class('error')
            else:
                config['filters']['BETWEEN_DAY'] = between_day
                config['filters']['UNTIL_DAY'] = until_day
                toml.dump(config, open(config_path, 'w'))
                self.query_one('#filters_info').update('Salvo')
                self.app.query_one('#projects').remove_children()
                self.app.refresh_projects()

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
        projects_widget = ScrollableContainer(id='projects')
        yield projects_widget
        self.refresh_projects(projects_widget)
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
                            if self.get_projects_by_filters()[
                                0
                            ] == model and not self.query('#save'):
                                self.refresh_projects()
                                mixer.music.play()
            if len(self.get_projects_by_filters()) > self.MAX_PROJECTS:
                for model in self.get_projects_by_filters()[
                    self.MAX_PROJECTS :
                ]:
                    session.delete(model)
                session.commit()
            await sleep(60)

    def action_previous(self) -> None:
        self.current_page = max(self.current_page - 1, 1)
        self.refresh_projects()

    def action_next(self) -> None:
        number_of_projects = len(self.get_projects_by_filters())
        number_of_pages = number_of_projects // 20
        if number_of_projects % 20 != 0:
            number_of_pages += 1
        self.current_page = min(self.current_page + 1, number_of_pages)
        self.refresh_projects()

    def refresh_projects(
        self, projects_widget: ScrollableContainer = None
    ) -> None:
        if projects_widget is None:
            projects_widget = self.query_one('#projects')
        projects_widget.remove_children()
        index = self.PAGINATION * self.current_page
        projects = self.get_projects_by_filters()[
            index - self.PAGINATION : index
        ]
        for project in projects:
            between_day = config['filters']['BETWEEN_DAY']
            until_day = config['filters']['UNTIL_DAY']
            publication_timedelta = (
                datetime.now() - project.publication_datetime
            )
            if (
                between_day == -1
                or publication_timedelta >= timedelta(days=between_day)
            ) and (
                until_day == -1
                or publication_timedelta <= timedelta(days=until_day)
            ):
                projects_widget.mount(
                    ProjectWidget(project.title, project.url)
                )

    def get_projects_by_filters(self) -> list[Project]:
        with Session() as session:
            between_day = config['filters']['BETWEEN_DAY']
            until_day = config['filters']['UNTIL_DAY']
            query = select(Project)
            if between_day != -1:
                query = query.where(
                    Project.publication_datetime
                    <= (datetime.now() - timedelta(days=between_day))
                )
            if until_day != -1:
                query = query.where(
                    Project.publication_datetime
                    >= (datetime.now() - timedelta(days=until_day))
                )
            query = query.order_by(Project.publication_datetime.desc())
            return session.scalars(query).all()

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    def action_filters(self) -> None:
        projects_widget = self.query_one('#projects')
        projects_widget.remove_children()
        projects_widget.mount(FiltersWidget())


if __name__ == '__main__':
    app = NineNineApp()
    app.run()
