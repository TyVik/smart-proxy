#!/usr/bin/env python

from aiohttp import web

from utils import random_string, get_logger

logger = get_logger()


async def login(request):
    response = web.json_response({'result': 'ok'})
    token = random_string()
    response.set_cookie('login', token)
    logger.info('New client %s', token)
    return response


async def handle(request):
    token = request.cookies.get('login')
    if token is None:
        logger.info('Non-authorizing request.')
        return web.Response(text='Authorization required!', status=401)
    logger.info('Handle request from %s', token)
    data = {'token': token, 'data': random_string()}
    return web.json_response(data)


app = web.Application(logger=logger)
app.add_routes([web.get('/login', login),
                web.get('/html', handle)])

web.run_app(app)
