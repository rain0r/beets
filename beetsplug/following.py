# -*- coding: utf-8 -*-
# This file is part of beets.
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
from operator import itemgetter
from collections import OrderedDict
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
        cmd.parser.add_option(u'-A',
                              u'--after',
                              action='store',
                              type="int",
                              help=u'show albums after this year',
                              default=0)
        cmd.func = self.func
        return [cmd]

    def func(self, lib, opts, args):
        """Command handler for the following function.
        """
        query = ui.decargs(args)
        self.albums(lib, query, opts.after)

    def albums(self, lib, query, after):
        """Retrieve and apply info from the autotagger for albums matched by
        query and their items.
        """
        albumartists = self.filter_artists(lib, query)
        sorted_artists = sorted(albumartists.keys(),
                                key=lambda x: x.lower(),
                                reverse=True)

        for albumartist in albumartists:
            mb_id = albumartists[albumartist]
            missing = []
            local_albums = self.get_local_albums(lib, mb_id)
            released_albums = self.get_released_albums(mb_id)
            local_ids = [item.mb_releasegroupid for item in local_albums]

            for album in released_albums:
                exists = album["id"] in local_ids
                if not exists:
                    album['artist'] = albumartist
                    album["year"] = self.extract_release_year(album)

                    if after > 0 and album["year"] <= after:
                        continue

                    missing.append(album)
            missing = sorted(missing, key=operator.itemgetter('year', 'title'))
            if missing:
                print("Missing albums for artist {}:".format(albumartist))
                for item in missing:
                    print("\t{} - {} ({})".format(item["artist"],
                                                  item["title"], item["year"]))

    def filter_artists(self, lib, query):
        mb_albumartist_ids = []
        sorted_artists = {}

        # Process matching albums.
        for album in lib.albums(query):
            if not album.mb_albumid:
                self._log.info(u'Skipping album with no mb_albumid: {0}',
                               format(album))
                continue
            sorted_artists[
                album['albumartist_sort']] = album['mb_albumartistid']
        return sorted_artists

    def get_local_albums(self, lib, mb_albumartist_id):
        q = u'mb_albumartistid::%s' % mb_albumartist_id
        # Map the albums to a list of mb_album_ids
        local_albums = []
        for album in lib.albums(q):
            local_albums.append(album)
        return local_albums

    def get_released_albums(self, mb_albumartist_id):
        releases = musicbrainzngs.browse_release_groups(
            artist=mb_albumartist_id, release_type=[
                'album',
            ])
        filtered = []
        for release in releases['release-group-list']:
            if release["type"] != "Album":
                continue
            filtered.append(release)
        return filtered

    def extract_release_year(self, album):
        try:
            return int(album["first-release-date"].split("-")[0])
        except (KeyError, ValueError):
            return 0
