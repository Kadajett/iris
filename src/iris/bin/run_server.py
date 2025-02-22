#!/usr/bin/env python

# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

import gc
import logging
import sys
import multiprocessing
import gunicorn.app.base
from gunicorn.six import iteritems
import iris
import iris.config


class StandaloneApplication(gunicorn.app.base.BaseApplication):

    def __init__(self, options=None, skip_build_assets=False):
        self.options = options or {}
        self.skip_build_assets = skip_build_assets
        super(StandaloneApplication, self).__init__()

    def load_config(self):
        config = {key: value for key, value in iteritems(self.options)
                  if key in self.cfg.settings and value is not None}
        for key, value in iteritems(config):
            self.cfg.set(key.lower(), value)

    def load(self):
        import iris
        reload(iris)
        reload(iris.config)
        config = iris.config.load_config(sys.argv[1])

        import iris.api
        app = iris.api.get_api(config)

        if not self.skip_build_assets:
            for r in gc.get_referrers(self):
                if isinstance(r, dict) and '_num_workers' in r:
                    gunicorn_arbiter = r

            # only build assets on one worker to avoid race conditions
            if gunicorn_arbiter['worker_age'] % self.options['workers'] == 0:
                import iris.ui
                iris.ui.build_assets()

        return app


def main():
    if len(sys.argv) <= 1:
        sys.exit('USAGE: %s CONFIG_FILE [--skip-build-assets]' % sys.argv[0])
    elif len(sys.argv) >= 3:
        skip_build_assets = (sys.argv[2] == '--skip-build-assets')
    else:
        skip_build_assets = False

    logging.basicConfig(format='[%(asctime)s] [%(process)d] [%(levelname)s] %(name)s %(message)s',
                        level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S %z')

    config = iris.config.load_config(sys.argv[1])
    server = config['server']

    options = {
        'preload_app': False,
        'reload': True,
        'bind': '%s:%s' % (server['host'], server['port']),
        'worker_class': 'gevent',
        'accesslog': '-',
        'workers': (multiprocessing.cpu_count() * 2) + 1
    }

    gunicorn_server = StandaloneApplication(options, skip_build_assets)
    gunicorn_server.run()


if __name__ == '__main__':
    main()
