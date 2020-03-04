# SPDX-License-Identifier: GPL-2.0-or-later
from prometheus_client import start_http_server, Counter, Gauge, Summary

matchmaker_queue_size = Gauge(
    'matchmaker_queue_size',
    'Number of item in the match queue',
)

matchmaker_managed_champion_count = Gauge(
    'matchmaker_managed_champion_count',
    'Number of champions managed by matchmaker',
)

matchmaker_latest_champion_age_seconds = Gauge(
    'matchmaker_last_champion_age_seconds',
    'Age in second of the latest champion',
)

matchmaker_managed_match_count = Gauge(
    'matchmaker_managed_match_count',
    'Number of matches managed by matchmaker',
)

matchmaker_scheduled_matches_total = Counter(
    'matchmaker_scheduled_matches_total',
    'Number of matches scheduled by matchmaker',
)

matchmaker_cancelled_matches = Counter(
    'matchmaker_cancelled_matches', 'Number of matches cancelled by matchmaker'
)

matchmaker_match_limit_reached = Gauge(
    'matchmaker_match_limit_reached',
    'Match limit status: 0 when not reached, 1 when reached',
)

matchmaker_new_champions_watch_latency_seconds = Summary(
    'matchmaker_new_champions_watch_latency_seconds',
    'Latency of the new champion watch step',
)

matchmaker_create_matches_latency_seconds = Summary(
    'matchmaker_create_matches_latency_seconds',
    'Latency of the match create step',
)

matchmaker_insert_latency_seconds = Summary(
    'matchmaker_insert_latency_seconds', 'Latency of the match insertion step'
)


def monitoring_start():
    start_http_server(9050)
