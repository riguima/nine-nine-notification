import itertools
from time import sleep

from sqlalchemy import select

from nine_nine_notification import browser
from nine_nine_notification.database import Session
from nine_nine_notification.models import Project

if __name__ == '__main__':
    while True:
        with Session() as session:
            for i in itertools.count(1):
                projects = browser.get_projects(page=i)
                if not projects:
                    break
                for project in projects:
                    query = select(Project).where(
                        Project.url == project['url']
                    )
                    if session.scalars(query).first():
                        break
                    else:
                        model = Project(
                            title=project['title'],
                            url=project['url'],
                            publication_datetime=project[
                                'publication_datetime'
                            ],
                        )
                        session.add(model)
                session.commit()
        sleep(60)
