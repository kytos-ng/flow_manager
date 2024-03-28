|Stable| |Tag| |License| |Build| |Coverage| |Quality|

.. raw:: html

  <div align="center">
    <h1><code>kytos/flow_manager</code></h1>

    <strong>NApp that manages OpenFlow 1.3 entries</strong>

    <h3><a href="https://kytos-ng.github.io/api/flow_manager.html">OpenAPI Docs</a></h3>
  </div>


Features
========

- REST API to create/update/read/delete flows
- Expose events to create/update/delete flows
- Store flows in MongoDB
- Consistency check based on FlowStats to ensure that only expected flows are installed 
- Consistency check ignored flows based on a cookie range and/or table id range
- Send barrier request and replies
- Handle southbound socket connection errors as applicable
- Option to allow to install a flow later on when a switch is connected

Supported Fields
================

This NApp supports a subset of the OpenFlow specification fields in the bodies of
the requests when creating and removing flows:

- Flow attributes:

  - priority: Priority of the flow entry when matching packets;
  - idle_timeout: Time before the flow expires when no packet is matched;
  - hard_timeout: Time before the flow expires, not related to matching;
  - cookie: Flow cookie;
  - match:

    - in_port: Port where the packet came from;
    - dl_src: Ethernet frame source MAC address;
    - dl_dst: Ethernet frame destination MAC address;
    - dl_type: EtherType of the upper layer protocol;
    - dl_vlan: 802.1q VLAN ID;
    - dl_vlan_pcp: 802.1q VLAN PCP;
    - nw_src: IPv4 source address of the packet;
    - nw_dst: IPv4 destination address of the packet;
    - nw_proto: Upper layer protocol number;

  - actions:

    - push_vlan: Add a new VLAN tag to the packet. The type is *tag_type*
      ('s' for service, 'c' for client);
    - set_vlan: Change the VLAN ID of the packet to *vlan_id*;
    - pop_vlan: Remove the outermost VLAN tag of the packet.
    - output: Send the packet through port *port*.

.. note::

    For the Output Action port you may use any port number or the string
    "controller". The string will be interpreted and converted to the correct
    controller port number for the datapath protocol version.

.. note::

    For OpenFlow 1.3, the only Instruction supported is InstructionApplyAction.

Other fields are not supported and will generate error messages from the NApp.

Flow consistency mechanism
==========================

This NApp provides a consistency mechanism for all managed flows. All expected flows are stored in MongoDB and checked when ``kytos/of_core.flow_stats.received`` event is received comparing the installed flows with the stored flows. If flows are missing they will eventually be installed. Similarly, if unexpected flows are installed (alien), they will eventually be removed, unless they are intentionally configured to be ignored. By default, the consistency mechanism is enabled on ``settings.py`` ``ENABLE_CONSISTENCY_CHECK = True``, running every ``STATS_INTERVAL`` (60 seconds). This interval can be adapted as needed on kytos/of_core `settings.py file <https://github.com/kytos-ng/of_core/blob/master/settings.py>`_. Depending on your topology size you might want to set a higher interval.

Installing
==========

To install this NApp, first, make sure to have the same venv activated as you have ``kytos`` installed on:

.. code:: shell

   $ git clone https://github.com/kytos-ng/flow_manager.git
   $ cd flow_manager
   $ python3 -m pip install --editable .

To install the kytos environment, please follow our
`development environment setup <https://github.com/kytos-ng/documentation/blob/master/tutorials/napps/development_environment_setup.rst>`_.

Requirements
============

- `kytos/of_core <https://github.com/kytos-ng/of_core>`_
- `MongoDB <https://github.com/kytos-ng/kytos#how-to-use-with-mongodb>`_

Events
======

Subscribed
----------

- ``kytos/of_core.handshake.completed``
- ``kytos.flow_manager.flows.(install|delete)``
- ``kytos/of_core.flow_stats.received``
- ``kytos/of_core.v0x04.messages.in.ofpt_flow_removed``
- ``kytos/of_core.v0x04.messages.in.ofpt_barrier_reply``
- ``kytos/core.openflow.connection.error``
- ``.*.of_core.*.ofpt_error``

Generated
---------

kytos/flow_manager.flow.pending
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*buffer*: ``app``

Event reporting that a FlowMod was sent to a Datapath.

Content:

.. code-block:: python3

   {
     'datapath': <Switch object>,
     'flow': <Object representing the flow>
   }

kytos/flow_manager.flow.added
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*buffer*: ``app``

Event reporting that an installed Flow was confirmed via Barrier Reply.

Content:

.. code-block:: python3

   {
     'datapath': <Switch object>,
     'flow': <Object representing the installed flow>
   }

kytos/flow_manager.flow.removed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*buffer*: ``app``

Event reporting that a removed Flow was confirmed via ``OFPT_FLOW_REMOVED``

Content:

.. code-block:: python3

   {
     'datapath': <Switch object>,
     'flow': <Object representing the removed flow>
   }


kytos/flow_manager.flow.error
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*buffer*: ``app``

Event reporting that either an OFPT_ERROR error happened or an asynchronous core OpenFlow socket error happened. Clients that send FlowMods via ``flow_manager`` should handle these accordingly. If ``error_exception`` isn't set, then it's a OFPT_ERROR, otherwise, it's a socket exception.

Content:

.. code-block:: python3

   {
     'datapath': <Switch object>,
     'flow': <Object representing the removed flow>,
     'error_command': <error_command>,
     'error_type': <error_type>,
     'error_code': <error_code>,
     'error_exception': <some_exception_content>
   }


.. TAGs

.. |Stable| image:: https://img.shields.io/badge/stability-stable-green.svg
   :target: https://github.com/kytos-ng/flow_manager
.. |License| image:: https://img.shields.io/github/license/kytos-ng/kytos.svg
   :target: https://github.com/kytos-ng/flow_manager/blob/master/LICENSE
.. |Build| image:: https://scrutinizer-ci.com/g/kytos-ng/flow_manager/badges/build.png?b=master
  :alt: Build status
  :target: https://scrutinizer-ci.com/g/kytos-ng/flow_manager/?branch=master
.. |Coverage| image:: https://scrutinizer-ci.com/g/kytos-ng/flow_manager/badges/coverage.png?b=master
  :alt: Code coverage
  :target: https://scrutinizer-ci.com/g/kytos-ng/flow_manager/?branch=master
.. |Quality| image:: https://scrutinizer-ci.com/g/kytos-ng/flow_manager/badges/quality-score.png?b=master
  :alt: Code-quality score
  :target: https://scrutinizer-ci.com/g/kytos-ng/flow_manager/?branch=master
.. |Tag| image:: https://img.shields.io/github/tag/kytos-ng/flow_manager.svg
   :target: https://github.com/kytos-ng/flow_manager/tags
