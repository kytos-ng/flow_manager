#########
Changelog
#########
All notable changes to the flow_manager NApp project will be documented in this
file.

[UNRELEASED] - Under development
********************************

Added
=====

- Added support for VLAN with mask. ``dl_vlan`` now also supports a string ``"vlan/mask"``.

Changed
=======
- Update endpoint ``GET v2/stored_flows`` to return the flows in descending order by `priority`.

General Information
===================
- ``@rest`` endpoints are now run by ``starlette/uvicorn`` instead of ``flask/werkzeug``.


[2022.3.1] - 2023-02-17
***********************

Added
=====
- Handled ``PackException`` to return bad request if a flow can't be packed.
- Fixed not iterable error when sending a FlowMod during OpenFlow connection.


[2022.3.0] - 2022-12-15
***********************

Added
=====

- Added endpoint ``GET v2/stored_flows`` for listing flows from flows collection. Query parameter filter for `state` and `dpid` is supported. A list of flows per switch is returned.
- Added query parameter filter for `cookie_range` to the endpoint ``GET v2/stored_flows``.
- Added query parameter filter for `state` to the endpoint ``GET v2/stored_flows``.

Fixed
=====
- Fixed handling ``OFPT_ERROR`` correctly when OF negotiation fails
- Fixed consistency check to run immediately when FlowStats is first received.
- Fixed flow ``instructions`` to be stored.
- Handled connection exception corner case before an OpenFlow handshake

Removed
=======
- Removed support for OpenFlow 1.0
- Removed ``serializers`` package


[2022.2.0] - 2022-08-08
***********************

Added
=====
- MongoDB integration with ``pymongo``
- Added and soft deleted flows are stored now on MongoDB ``flows`` collections.
- Consistency checks executions are stored on MongoDB ``flow_checks`` collection
- FlowController and DB models
- Added log.info entry for kytos.flow_manager.flows.(install|delete) handler for troubleshooting
- ``CONSISTENCY_MIN_VERDICT_INTERVAL``, granular control for the minimum expected interval that consistency check should wait before detecting inconsistencies

Changed
=======
- Refactored consistency check to leverage ``flow_id`` and ``match_id``
- Refactored `flows` upsert and delete operations to use `bulk_write` instead for higher performance based on the expected workload
- Endpoint /flow_manager/v2/flows/ writes first to the database now to optimize consistency for bulk operations.
- Set KytosEvent priority for OFPT_FLOW_MOD and OFPT_BARRIER_REQUEST
- OFPT_BARRIER_REQUEST is sent in bulk once per flows
- Consistency check will act slower than ``FLOW_STATS`` to enhance consistency

Deprecated
==========
- Storehouse file system backend

Removed
=======
- Storehouse backend and its locks
- ``match13_strict`` to simplify application logic since match strict was primarily for matching an exact flow, which without wildcards is simpler to do and maintain by using ``flow_id`` (flow.id) instead
- Removed in memory archived_flows

General Information
===================
- ``scripts/storehouse_to_mongo.py`` can be used to migrate data from storehouse to MongoDB

[2022.1.2] - 2022-02-07
***********************

Changed
=======
- Adapted consistency check to skip recent deleted flows
- Extracted ``is_recent_flow`` static method
- Changed ``_del_matched_flows_store`` to also archive flows
- Changed consistency check to also archive alien flows

Added
=====

- Added archived_flows and its lock to store in memory
- Added ``_add_Archived_flows`` method


[2022.1.1] - 2022-02-04
***********************

Changed
=======
- Adding Lock to avoid race conditions at flow_manager's storehouse

[2022.1.0] - 2022-02-02
***********************

Changed
=======
- New versioning schema, following kytos core versioning


[5.7.1] - 2022-01-18
********************

Added
=====
- Subscribed to ``on_connection_lost`` event to reset consistency check executions

[5.7.0] - 2021-12-15
********************

Added
=====
- Added support for retrying ``kytos/core.openflow.connection.error``
- Added retry configuration options


[5.6.0] - 2021-12.17
********************

Added
=====
- Added an upper bound rotating limit for the number of barrier replies

Changed
=======
- Changed ``_flow_mods_sent_error_locks``, ``_pending_barrier_locks``, and ``_check_consistency_locks`` to be safer

[5.5.0] - 2021-11.24
********************

Added
=====
- Added support for ofpt_barrier_request and ofpt_barrier_reply
- Mapped barrier reply xid with flow mod xid to correlate them, and to also to confirm installed flows in an event-driver manner.
- Stored in memory errors of flow mod xids to correlate them when a barrier reply is received.
- Added thread locks accordingly for the dictionaries used.
- Added support to delete the stored_flow once an ofpt_error when receiving a barrier reply, to avoid this flow to keep being sent via consistency check.

[5.4.0] - 2021-11.23
********************

Added
=====
- Added thread concurrency control per switch when executing check_consistency


[5.3.0] - 2021-11.21
********************

Added
=====
- Started listening to ``kytos/core.openflow.connection.error`` and propagating the error
- Added listen_to for ofpt_flow_removed
- Publish the event ``kytos/flow_manager.flow.removed`` on OFPT_FLOW_REMOVED
- Parametrized and added ``_id`` on stored flows to confirm flow operations
- Parametrized the flow on ``SwitchNotConnectedError`` exception
- Added support to update flow ``state`` and flows are confirmed by the consistency check

Changed
=======

- Publish the event ``kytos/flow_manager.flow.added`` only when the flow is confirmed

[5.2.0] - 2021-11.17
********************

Added
=====
- Added support for ``force`` option when sending flow mods


[5.1.0] - 2021-11.08
********************

Added
=====
- Augmented ``_add_flow_store`` to overwrite overlapping flows

[5.0.0] - 2021-11.05
********************

Changed
=======
- ``stored_flows`` are now indexed by cookie, issue 34
- Changed the ``flow_persistence`` data structured on storehouse
- Refactored the consistency checks methods accordingly to use cookie indexes


Deprecated
==========
- The prior ``flow_persistence`` data structure isn't supported anymore. It's required to delete the ``kytos.flow.persistence`` folder, upgrading won't be supported this time.


[4.1.2] - 2021-11.03
********************

Fixed
=====
- Fixed issue 28, early return on ``match13_no_strict``


[4.1] - 2021-10.22
******************

Changed
=======
- Removed 'delete' command persistency
- Faster filtering when removing stored flows

Fixed
=====
- Fixed ``match13_no_strict`` issue 13


[4.0] - 2021-05-27
******************
Added
=====
- Added support to handle with OpenFlow error ``OFPBAC_BAD_OUT_PORT``.
- Added attempt limits to try to recover box from storehouse, avoiding
  a possible thread lock condition.
- Added consistency mechanism information in README file.
- Added support for non-strict exclusion in the consistency check.
- Add support for the list of exceptions in the consistency mechanism.
- Add validation to data sent by REST endpoints in requests to install flows.
- Add support for install or remove flows in the switches using Kytos Events.

Changed
=======
- Update consistency check to use ``DELETE_STRICT`` to remove 'alien' flows in
  switches.
- Consistency check routine to recreate the flows when the switch reconnects 
  to Kytos.

Fixed
=====
- New method to cast ``UBInt`` type to int to solve JSON serialization error.
- Fix the HTTP status code returned when the switch is not found.

 
[3.0] - 2020-12-23
******************
Added
=====
- Added new consistency check to guarantee the consistency of installed flows
  between switches and the controller.
- Added persistence mechanism to save in storehouse all the
  flows installed by ``kytos/flow_manager``.
- Added mechanism to resend stored flows in Kytos bootstrap.
- Include the original command in the list of sent flow mods.

Changed
=======
- Updated flow installation to allow removal of flows from disabled switches.
- Changed setup.py to alert when a test fails on Travis.


[2.3] - 2020-07-07
******************
Added
=====
- Added unit tests, increasing coverage to 97%.
- Added listener to handle OpenFlow errors sent by ``of_core``.
- Added HTTP DELETE method support to REST API on ``/flows``.
- Added the error code of the flow mod message to the content
  of the resulting event.
- Started to use ``FlowFactory`` to check which version of ``Flow`` to use.
- Added ``@tags`` decorator to run tests by type and size.


[2.2.2] - 2019-03-15
********************
Changed
=======
- Continuous integration enabled at scrutinizer.

Fixed
=====
- Improve code organization and fix some linter issues.


[2.2.1] - 2018-12-14
********************

Fixed
=====
 - Fix `flow` being used outside of its scope when installing a flow.


[2.2.0] - 2018-06-15
********************

Changed
=======
- Send flow_mod to only enabled switches.
- Change enabled attributes to use the method is_enabled.


[2.1.0] - 2018-04-20
********************

Changed
=======
- Update kytos.json version form 2.0.0 to 2.1.0.
- Send flow_mod to only enabled switches.
- Return 404 status code when dpid is not found.

Fixed
=====
- Fix actions to have correct type and value pair.
- Fix OpenAPI.yml.
- Some type fixes.


[2.0.0] - 2017-11-30
********************
Added
=====
- Add REST API Version.
- Send app specific events when sending a flow_mod.
- Add documentation for of_flow_manager.
- Implement endpoint for add/delete/list flows.
- Added methods to deal with 1.0/1.3 flows.
- Adding dependencies in kytos.json.

Changed
=======
- Change request body of the rest api.
- Change rest api to return Response with mimetype='application/json'.
- Change list of flows to dictitonary.
- Change actions field from dict to list in bodies.
- Standardize models and examples.
- Change 'Response' to 'Flows'.
- Change HTTP success code for add flows.
- Change Napp name  to `kytos/flow_manager` and tags


[1.1.3] - 2017-06-16
********************
Added
=====
- Added examples of requests/replies to of_flow_manager REST endpoints.
- Added rest api endpoints and JSON input/output.


[0.1.0] - 2016-11-09
********************
Added
=====
- Created application to register REST endpoints to manage flows.
