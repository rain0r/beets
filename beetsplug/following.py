# -*- coding: utf-8 -*-
# This file is part of beets.
# Copyright 2016, Jakob Schnitzer.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
"""Update library's tags using MusicBrainz.
"""
from __future__ import division, absolute_import, print_function

import musicbrainzngs
import operator

from beets import ui
from beets.plugins import BeetsPlugin

MBID_REGEX = r"(\d|\w){8}-(\d|\w){4}-(\d|\w){4}-(\d|\w){4}-(\d|\w){12}"


class FollowingPlugin(BeetsPlugin):
    def __init__(self):
        super(FollowingPlugin, self).__init__()

    def commands(self):
        cmd = ui.Subcommand('following',
                            help=u'update metadata from musicbrainz')
        cmd.parser.add_format_option()
        cmd.func = self.func
        return [cmd]

    def func(self, lib, opts, args):
        """Command handler for the following function.
        """
        query = ui.decargs(args)
        self.albums(lib, query)

    def albums(self, lib, query):
        """Retrieve and apply info from the autotagger for albums matched by
        query and their items.
        """
        mb_albumartist_ids = self.filter_artists(lib, query)

        for mb_albumartist_id in mb_albumartist_ids:
            local_albums = self.get_local_albums(lib, mb_albumartist_id)
            released_albums = self.get_released_albums(mb_albumartist_id)
            local_ids = [item.mb_releasegroupid for item in local_albums]

            missing = []
            for album in released_albums:
                exists = album["id"] in local_ids
                if not exists:
                    try:
                        artist = album['artist-credit'][0]['artist']['name']
                    except KeyError:
                        artist = "Could not extract artist"
                    album['artist'] = artist
                    album["year"] = album["first-release-date"].split("-")[0]
                    missing.append(album)

            missing = sorted(missing, key=operator.itemgetter('year', 'title'))

            if missing:
                print("Missing albums:")
                for item in missing:
                    print("{} - {} ({})".format(item["artist"], item["title"],
                                                item["year"]))
            else:
                print("No missing albums")

    def filter_artists(self, lib, query):
        mb_albumartist_ids = set()

        # Process matching albums.
        for album in lib.albums(query):
            album_formatted = format(album)

            if not album.mb_albumid:
                self._log.info(u'Skipping album with no mb_albumid: {0}',
                               album_formatted)
                continue
            mb_albumartist_ids.add(album['mb_albumartistid'])
        return mb_albumartist_ids

    def get_local_albums(self, lib, mb_albumartist_id):
        q = u'mb_albumartistid::%s' % mb_albumartist_id
        # Map the albums to a list of mb_album_ids
        local_albums = []
        for album in lib.albums(q):
            local_albums.append(album)
        return local_albums

    def get_released_albums(self, mb_albumartist_id):
        releases = musicbrainzngs.browse_release_groups(
            artist=mb_albumartist_id,
            release_type='album',
            includes=['artist-credits'])
        return releases['release-group-list']
