"""Settings from flow_manager NApp."""
# Pooling frequency
STATS_INTERVAL = 30
FLOWS_DICT_MAX_SIZE = 10000
# Time (in seconds) to wait retrieve box from storehouse
BOX_RESTORE_TIMER = 0.1
ENABLE_CONSISTENCY_CHECK = True

# List of flows ignored by the consistency check
# To filter by a cookie or `table_id` use [value]
# To filter by a cookie or `table_id` range [(value1, value2)]
CONSISTENCY_COOKIE_IGNORED_RANGE = []
CONSISTENCY_TABLE_ID_IGNORED_RANGE = []

# Maximum number of flows to archive per switch
ARCHIVED_MAX_FLOWS_PER_SWITCH = 5000
# Number of old flows to delete whenever 'ARCHIVED_MAX_FLOWS_PER_SWITCH' overflows
ARCHIVED_ROTATION_DELETED = 1000
