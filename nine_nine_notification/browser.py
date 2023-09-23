import json
from datetime import datetime

import httpx
from parsel import Selector


async def get_projects(page: int = 1) -> list[dict]:
    async with httpx.AsyncClient() as client:
        cookies = httpx.Cookies()
        for cookie in json.load(open('cookies.json')):
            cookies.set(
                cookie['name'], cookie['value'], domain=cookie['domain']
            )
        response = await client.get(
            f'https://www.99freelas.com.br/projects?page={page}',
            cookies=cookies,
        )
        selector = Selector(response.text)
        projects = selector.css('li.result-item')
        return [
            {
                'title': project.css('h1.title a::text').get(),
                'url': (
                    'https://www.99freelas.com.br'
                    f'{project.css("h1.title a").attrib["href"]}'
                ),
                'publication_datetime': get_datetime_of_project(project),
            }
            for project in projects
        ]


def get_datetime_of_project(project: Selector) -> datetime:
    milliseconds = int(project.css('b.datetime').attrib['cp-datetime'])
    return datetime.fromtimestamp(milliseconds / 1000)
