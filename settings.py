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
CONSISTENCY_MIN_VERDICT_INTERVAL = 60 * 2
"""
Consistency check is eventually consistent, so the minimum interval is recommended
to be at least greater than FLOW_STATS and ideally it slightly greater than
whichever longest network convergence FlowMods operations that your network has.
"""

# Rate limits for sending flow mods this can be set per NApp,
# and the pacing is per DPID when in the context of that NApp
# The NApp that the flow pertains to is determined via the `owner` attribute of the flow.
ACTION_PACES = {
    "send_flow_mod.no_owner": {
        "pace": "100/second",
        "strategy": "fixed_window",
    },
    "send_flow_mod.mef_eline": {
        "pace": "100/second",
        "strategy": "fixed_window",
    },
    "send_flow_mod.of_multi_table": {
        "pace": "100/second",
        "strategy": "fixed_window",
    },
    "send_flow_mod.telemetry_int": {
        "pace": "100/second",
        "strategy": "fixed_window",
    },
    "send_flow_mod.of_lldp": {
        "pace": "100/second",
        "strategy": "fixed_window",
    },
    "send_flow_mod.coloring": {
        "pace": "100/second",
        "strategy": "fixed_window",
    },
}
