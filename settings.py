"""Settings from flow_manager NApp."""
FLOWS_DICT_MAX_SIZE = 10000
ENABLE_CONSISTENCY_CHECK = True
ENABLE_BARRIER_REQUEST = True

# List of flows ignored by the consistency check
# To filter by a cookie or `table_id` use [value]
# To filter by a cookie or `table_id` range [(value1, value2)]
CONSISTENCY_COOKIE_IGNORED_RANGE = []
CONSISTENCY_TABLE_ID_IGNORED_RANGE = []

# Retries options for `kytos/core.openflow.connection.error`
CONN_ERR_MAX_RETRIES = 3
CONN_ERR_MIN_WAIT = 1  # minimum wait between iterations in seconds
CONN_ERR_MULTIPLIER = 2  # multiplier for the accumulated wait on each iteration

# Minimum consistency check verdict interval for start to consider inconsistencies.
CONSISTENCY_MIN_VERDICT_INTERVAL = 60*2 + 60//2
"""
Consistency check is eventually consistent, so the minimum interval is recommended
to be at least greater than FLOW_STATS and ideally it slightly greater than
whichever longest convergence network sequence of operations you have in your
network, you don't want consistency check to try to keep running while the network is
still convergning with lots of FlowMods.
"""
