#!/usr/bin/env python
import random
from collections import defaultdict

from aiohttp import web, ClientSession

from utils import get_logger, random_string

logger = get_logger()

MAX_SESSION_PER_DOMAIN = 2
MAX_REQUESTS_PER_SESSION = 3
SESSION_POOL = defaultdict(list)  # make it as class


async def create_session(domain):
    async with ClientSession() as result:
        response = await result.get('http://127.0.0.1:8080/login')
        assert response.status == 200
        logger.info('Create new session with token %s', response.cookies.get('token'))
        return {'id': random_string(), 'cookie': response.cookies, 'lock': False, 'count': 0}


async def get_session(request):
    domain = request.query.get('domain')
    sessions = SESSION_POOL.get(domain, [])
    available = list(filter(lambda s: not s['lock'], sessions))
    if len(available) == 0 and len(sessions) < MAX_SESSION_PER_DOMAIN:
        session = await create_session(domain)
        SESSION_POOL[domain].append(session)
    elif len(available) == 0 and len(sessions) == MAX_SESSION_PER_DOMAIN:
        logger.info('All connections are busy')
        return web.json_response({'result': 'temporary unavailable'})

    sessions = SESSION_POOL.get(domain, [])
    available = list(filter(lambda s: not s['lock'], sessions))  # race condition
    result = random.choice(available)
    result['lock'] = True
    logger.info('Lock %s', result['id'])
    return web.json_response({'id': result['id']})


def find_session(id):
    for items in SESSION_POOL.values():
        for item in items:
            if item['id'] == id:
                return item
    return None


def remove_session(id):
    for items in SESSION_POOL.values():
        try:
            index = [x['id'] for x in items].index(id)
            del items[index]
        except ValueError:
            pass


async def handle(request):
    session_id = request.query.get('id')
    if session_id is None:
        return web.Response(text='Bad request', status=400)
    item = find_session(session_id)
    if item is None:
        return web.Response(text='Wrong session id', status=400)

    async with ClientSession(cookies=item['cookie']) as session:
        response = await session.get('http://127.0.0.1:8080/html')
        logger.info('Response status: %s', response.status)
        item['count'] += 1
        return web.Response(text=await response.text())


async def close(request):
    session_id = request.query.get('id')
    if session_id is None:
        return web.Response(text='Bad request', status=400)
    item = find_session(session_id)
    if item['count'] > MAX_REQUESTS_PER_SESSION:
        logger.info('Close connection %s', item['id'])
        remove_session(item['id'])
    else:
        item['lock'] = False
    return web.json_response({'result': 'ok'})


app = web.Application(logger=logger)
app.add_routes([
    web.get('/open', get_session),
    web.get('/request', handle),
    web.get('/close', close),
])

web.run_app(app, port=8000)
