# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2015, 2016 Canonical Ltd
# Copyright (C) 2016 Harald Sitter <sitter@kde.org>
# Copyright (C) 2017 Simon Stürz <simon.stuerz@guh.io>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""The autotools plugin is used for autotools based parts.

Autotools based projects are the ones that have the usual
`./configure && make && make install` instruction set.

The plugin tries to build using ./configure first, if it is not there
it will run ./autogen and if autogen is not there it will run autoreconf.

This plugin uses the common plugin keywords as well as those for "sources".
For more information check the 'plugins' topic for the former and the
'sources' topic for the latter.

In addition, this plugin uses the following plugin-specific keywords:

    - configflags:
      (list of strings)
      configure flags to pass to the build such as those shown by running
      './configure --help'
    - install-via:
      (enum, 'destdir' or 'prefix')
      Whether to install via DESTDIR or by using --prefix (default is
      'prefix')
"""

import os
import stat

import snapcraft


class XAutotoolsPlugin(snapcraft.BasePlugin):

    @classmethod
    def schema(cls):
        schema = super().schema()
        schema['properties']['configflags'] = {
            'type': 'array',
            'minitems': 1,
            'uniqueItems': False,
            'items': {
                'type': 'string',
            },
            'default': [],
        }

        schema['properties']['install-via'] = {
            'enum': ['destdir', 'prefix'],
            'default': 'prefix',
        }

        return schema

    @classmethod
    def get_build_properties(cls):
        # Inform Snapcraft of the properties associated with building. If these
        # change in the YAML Snapcraft will consider the build step dirty.
        return super().get_build_properties() + ["configflags", "install-via"]

    def __init__(self, name, options, project):
        super().__init__(name, options, project)
        self.build_packages.extend([
            'autoconf',
            'automake',
            'autopoint',
            'libtool',
            'make',
        ])

        if options.install_via == 'destdir':
            self.install_via_destdir = True
        elif options.install_via == 'prefix':
            self.install_via_destdir = False
        else:
            raise RuntimeError('Unsupported installation method: "{}"'.format(
                options.install_via))

    def build(self):
        super().build()
        if not os.path.exists(os.path.join(self.builddir, "configure")):
            generated = False
            scripts = ["autogen.sh", "bootstrap"]
            for script in scripts:
                path = os.path.join(self.builddir, script)
                if not os.path.exists(path) or os.path.isdir(path):
                    continue
                # Make sure it's executable
                if not os.access(path, os.X_OK):
                    os.chmod(path,
                             stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                             stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP |
                             stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH)
                self.run(['env', 'NOCONFIGURE=1', './{}'.format(script)])
                generated = True
                break
            if not generated:
                self.run(['autoreconf', '-i'])

        configure_command = ['./configure']
        make_install_command = ['make', 'install']

        if self.install_via_destdir:
            # Use an empty prefix since we'll install via DESTDIR
            #configure_command.append('--prefix=')
            make_install_command.append('DESTDIR=' + self.installdir)

        self.run(configure_command + ['-prefix', self.installdir] + self.options.configflags)
        self.run(['make', '-j{}'.format(self.parallel_build_count)])
        self.run(make_install_command)

    def snap_fileset(self):
        fileset = super().snap_fileset()
        # Remove .la files which don't work when they are moved around
        fileset.append("-**/*.la")
        return fileset



