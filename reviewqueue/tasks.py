import transaction

from celerycfg import celery
from celery.signals import worker_init

from . import models as M


@worker_init.connect
def bootstrap_pyramid(signal, sender):
    import os
    from pyramid.paster import bootstrap, get_appsettings
    from sqlalchemy import engine_from_config

    sender.app.settings = bootstrap(
        '%s.ini' % os.environ.get('ENV', 'development'))['registry'].settings
    settings = get_appsettings('%s.ini' %
                               os.environ.get('ENV', 'development'),
                               options={})

    engine = engine_from_config(settings, 'sqlalchemy.')

    M.DBSession.configure(bind=engine)
    M.Base.metadata.bind = engine


@celery.task
def refresh_review(review):
    with transaction.manager:
        M.DBSession.add(review)
        review.refresh_tests(celery.settings)
        if review.channel:
            review.refresh_revisions(celery.settings)


@celery.task
def refresh_reviews():
    for a in M.Review.get_active_reviews():
        refresh_review.delay(a)
