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
