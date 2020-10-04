# SPDX-License-Identifier: GPL-2.0-or-later
"""MatchMaker is a service that manages the matches of a tournament.

MatchMaker creates all the expected matches of a tournament and keeps track of
new champions.

MatchMaker configuration elements are:

* **port** the TCP port to listen on.
* **author_username** the username of the user to use to create matches
* **tournament_name** the name of the tournament to create matches in
* **include_staff** a boolean, whether staff champions are included in the
  tournament
* **deadline** a ISO 8601 date after which champions are not accepted
  (optional)
* **match_repeat** the replication factor of created matches, 1 is the default,
  2 means each unique match is created twice

On startup, it updates the set of matches in the tournament to account for new
champions while it was stopped.

After startup, MatchMaker waits for the list of champions to change. When a
user uploads a new champion, MatchMaker retires matches with the previous
champion of that user and creates new matches as required for the tournament.

Matches are created in batches of size ``match_batch_size``. The matches are
created with the user of set in the configuration file, and with the
:data:`MatchPriority.TOURNAMENT` priority. MatchMaker will stop creating
matches once the global ``match_pending_limit`` number of matches are in
``pending`` or ``new`` status.
"""
