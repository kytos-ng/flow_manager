"""Match for OF 1.3."""


def _get_match_fields(flow_dict):
    """Generate match fields."""
    match_fields = {}
    if "match" in flow_dict:
        for key, value in flow_dict["match"].items():
            match_fields[key] = value
    return match_fields


def _match_cookie(flow_to_install, stored_flow_dict):
    """Check if a the cookie and its mask matches between the flows."""
    cookie = flow_to_install.get("cookie", 0) & flow_to_install.get("cookie_mask", 0)
    cookie_stored = stored_flow_dict.get("cookie", 0) & flow_to_install.get(
        "cookie_mask", 0
    )
    if cookie and cookie != cookie_stored:
        return False
    return True


def _match_keys(flow_to_install, stored_flow_dict, flow_to_install_keys):
    """Check if certain keys on flow_to_install match on stored_flow_dict."""
    for key in flow_to_install_keys:
        if key not in stored_flow_dict["match"]:
            return False
        if flow_to_install["match"][key] != stored_flow_dict["match"].get(key):
            return False
    return True


def match13_no_strict(flow_to_install, stored_flow_dict):
    """Match a flow that is either exact or more specific (non-strict) (OF1.3).

    Return the flow if any fields match, otherwise, return False.
    """
    if not _match_cookie(flow_to_install, stored_flow_dict):
        return False

    if "match" not in flow_to_install or "match" not in stored_flow_dict:
        return stored_flow_dict
    if not flow_to_install["match"]:
        return stored_flow_dict
    if len(flow_to_install["match"]) > len(stored_flow_dict["match"]):
        return False

    if not _match_keys(
        flow_to_install, stored_flow_dict, flow_to_install["match"].keys()
    ):
        return False
    return stored_flow_dict


def match13_strict(flow_to_install, stored_flow_dict):
    """Match a flow strictly (OF1.3).

    Return the flow if all fields match, otherwise, return False.
    """
    if not _match_cookie(flow_to_install, stored_flow_dict):
        return False
    if flow_to_install.get("priority", 0) != stored_flow_dict.get("priority", 0):
        return False

    if "match" not in flow_to_install and "match" not in stored_flow_dict:
        return stored_flow_dict
    if "match" not in flow_to_install and "match" in stored_flow_dict:
        return False
    if "match" in flow_to_install and "match" not in stored_flow_dict:
        return False

    if len(flow_to_install["match"]) != len(stored_flow_dict["match"]):
        return False

    if not _match_keys(
        flow_to_install, stored_flow_dict, flow_to_install["match"].keys()
    ):
        return False
    return stored_flow_dict
