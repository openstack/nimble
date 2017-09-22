# Copyright 2016 Huawei Technologies Co.,LTD.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import sys

from oslo_config import cfg
from oslo_reports import guru_meditation_report as gmr
from oslo_reports import opts as gmr_opts
import pecan

from mogan.api import config
from mogan.api import hooks
from mogan.api import middleware
from mogan.api.middleware import auth_token
from mogan import version


def get_pecan_config():
    # Set up the pecan configuration
    filename = config.__file__.replace('.pyc', '.py')
    return pecan.configuration.conf_from_file(filename)


def setup_app(pecan_config=None, extra_hooks=None):
    if not pecan_config:
        pecan_config = get_pecan_config()
    pecan.configuration.set_config(dict(pecan_config), overwrite=True)

    gmr_opts.set_defaults(cfg.CONF)
    gmr.TextGuruMeditation.setup_autorun(version, conf=cfg.CONF)

    app_hooks = [hooks.ConfigHook(),
                 hooks.DBHook(),
                 hooks.EngineAPIHook(),
                 hooks.ContextHook(pecan_config.app.acl_public_routes),
                 hooks.NoExceptionTracebackHook(),
                 hooks.PublicUrlHook()]
    if extra_hooks:
        app_hooks.extend(extra_hooks)

    app = pecan.make_app(
        pecan_config.app.root,
        static_root=pecan_config.app.static_root,
        debug=False,
        force_canonical=getattr(pecan_config.app, 'force_canonical', True),
        hooks=app_hooks,
        wrap_app=middleware.ParsableErrorMiddleware,
    )

    app = auth_token.AuthTokenMiddleware(
        app, dict(cfg.CONF),
        public_api_routes=pecan_config.app.acl_public_routes)

    return app


class VersionSelectorApplication(object):
    def __init__(self):
        pc = get_pecan_config()
        self.v1 = setup_app(pecan_config=pc)

    def __call__(self, environ, start_response):
        return self.v1(environ, start_response)


def build_wsgi_app():
    from mogan.common import service as mogan_service
    mogan_service.prepare_service(sys.argv)
    return setup_app()
