# -*- coding: utf-8 -*-
# Copyright (C) 2016 Matthias Luescher
#
# Authors:
#  Matthias Luescher
#
# This file is part of edi.
#
# edi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# edi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with edi.  If not, see <http://www.gnu.org/licenses/>.

import logging
import os
import tempfile
import time
import calendar
import yaml
import shutil
from codecs import open
from edi.lib.edicommand import EdiCommand
from edi.commands.bootstrapimage import BootstrapImage
from edi.lib.helpers import chown_to_user


class LxdImage(EdiCommand):

    @classmethod
    def advertise(cls, subparsers):
        help_text = "upgrade a bootstrap image to a lxd image"
        description_text = "Upgrade a bootstrap image to a lxd image."
        parser = subparsers.add_parser(cls._get_command_name(),
                                       help=help_text,
                                       description=description_text)
        cls._require_config_file(parser)

    def run_cli(self, cli_args):
        self.run(cli_args.config_file)

    def run(self, config_file):
        self._setup_parser(config_file)

        if os.path.isfile(self._result()):
            logging.info(("{0} is already there. "
                          "Delete it to regenerate it."
                          ).format(self._result()))
            return self._result()

        self._require_sudo()

        bootstrap_cmd = BootstrapImage()

        # This command is based upon the output of the bootstrap command
        bootstrap_result = bootstrap_cmd.run(config_file)

        workdir = self.config.get_workdir()

        with tempfile.TemporaryDirectory(dir=workdir) as tempdir:
            chown_to_user(tempdir)
            lxdimagedir = os.path.join(tempdir, "lxdimage")
            self._unpack_image(bootstrap_result, lxdimagedir)
            self._write_container_metadata(lxdimagedir)
            archive = self._pack_image(tempdir, lxdimagedir)
            chown_to_user(archive)
            shutil.move(archive, self._result())

        return self._result()

    def _result(self):
        archive_name = ("{0}_{1}.tar.{2}"
                        ).format(self.config.get_project_name(),
                                 self._get_command_name(),
                                 self.config.get_compression())
        return os.path.join(self.config.get_workdir(), archive_name)

    def _write_container_metadata(self, imagedir):
        metadata = {}
        metadata["architecture"] = self.config.get_architecture()
        metadata["creation_date"] = calendar.timegm(time.gmtime())

        metadatafile = os.path.join(imagedir, "metadata.yaml")

        with open(metadatafile, encoding='utf-8', mode='w') as f:
            f.write(yaml.dump(metadata))
