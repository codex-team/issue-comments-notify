import logging
import json
import os

import yaml
import requests
import argparse
import html
import urllib.parse

from pathlib import Path
from string import Template
from dateutil.relativedelta import relativedelta
import dateutil.parser
from datetime import datetime, timezone
from logs import init_logger


class BotIssues:

    def __init__(self, graphql="./static/query.graphql", config="./static/config.yaml", debug=False):
        self.debug = debug
        if self.debug:
            logger.setLevel(logging.DEBUG)
        self.gql_query = Template(open(Path(graphql)).read())

        with Path(config).open('r') as stream:
            try:
                self.config = yaml.safe_load(stream)
            except yaml.YAMLError as e:
                logger.error(e)
                exit(1)
        logger.debug(f"Initialized BotIssues: {json.dumps(self.config)}")

        self.headers = {
            "Authorization": "Bearer {}".format(self.config['token'])
        }

    def update_all(self):
        for _, repository in self.config['repositories'].items():
            self.process(repository)

    def process(self, settings):
        query = self.gql_query.substitute(owner=settings['owner'], name=settings['name'])
        result = requests.post('https://api.github.com/graphql', json={'query': query}, headers=self.headers)
        content = result.json()

        logger.debug(content)

        issues = content['data']['repository']['issues']['edges']
        pull_requests = content['data']['repository']['pullRequests']['edges']

        results = []

        for nature in [issues, pull_requests]:
            for issue in nature:
                issue_node = issue['node']
                comments = issue_node['comments']['edges']

                if len(comments):
                    comment_author = comments[0]['node']['author']['login']
                    if comment_author not in settings['maintainers']:
                        comment_url = comments[0]['node']['url']
                        comment_date = comments[0]['node']['publishedAt']
                        results.append((issue_node['title'], comment_author, comment_url, comment_date))

        messages = []
        for title, author, url, dt in results:
            dt_obj = dateutil.parser.parse(dt)
            delta = datetime.now(dt_obj.tzinfo) - dt_obj
            messages.append((delta.days, """➔ ({delta} days) {author}  <a href="{url}">{title}</a>""".format(url=url, title=html.escape(title), delta=delta.days, author=author)))

        if len(messages):
            messages.sort(key=lambda x: int(x[0]), reverse=True)
            message = '<b>🚨 List of unanswered issues for {}/{}</b>\n\n'.format(settings['owner'], settings['name']) + '\n'.join([m[1] for m in messages])

            r = requests.post("https://notify.bot.codex.so/u/{}".format(settings['chat']), {"message": message, "parse_mode": "HTML"})
            if r.status_code != 200:
                logger.error("Send to Codex.Bot exception", r.text)

        logger.info("Updated {}/{}".format(settings['owner'], settings['name']))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--debug', action='store_true', default=False, help='Toggle DEBUG logging mode')
    parser.add_argument('--logs', default='logs.log', help='Logs filepath')
    parser.add_argument('--config', required=True, help='Configuration file')
    args = parser.parse_args()

    logger = init_logger(__name__, filename=args.logs)

    app = BotIssues(debug=args.debug, config=args.config, graphql=Path(os.path.dirname(os.path.abspath(__file__))) / "static" / "query.graphql")
    app.update_all()
