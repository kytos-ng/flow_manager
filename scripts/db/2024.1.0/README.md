## `flow_manager` scripts from Kytos 2024.1.0

This folder contains `flow_manager` related scripts.

<details><summary><h3>Update match_id</h3></summary>

### Pre-requisites

- There's no additional Python libraries dependencies required, other than installing the existing `flow_manager` dependencies.
- Make sure you don't have `kytosd` running with otherwise new request can make `flow_manager` write to MongoDB, and the application could overwrite the data you're trying to insert with this script.
- Make sure MongoDB replica set is up and running.

```
export MONGO_USERNAME=
export MONGO_PASSWORD=
export MONGO_DBNAME=napps
export MONGO_HOST_SEEDS="mongo1:27017,mongo2:27018,mongo3:27019"
```

### Backup and restore procedure

- In addition, it's recommended that you backup the `flows` collection of the `napps` database before running this script (make sure to set `-o <dir>` to a persistent directory):

```
mongodump -d napps -c flows -o /tmp/napps_flows
```

If you ever need to restore the backup:

```
mongorestore -d napps -c flows /tmp/napps_flows/napps/flows.bson
```

### How to use

On version `2024.1`, flows `match_id` and `_id` document values have changed just so the `cookie` isn't a factor of the computed `match_id` hashed value anymore. This script will insert new updated flows and delete the old ones if the expected `match_id` is different. Before using this script, you're recommended to hard delete old soft deleted flows check out `scripts/db/2024.1.0/000_hard_delete_old.py` in the next section below.

- You can use the `count` command to check how many flows have their `match_id` outdated, this will include all flows, including flows marked as deleted:

```
❯ CMD=count python3 scripts/db/2024.1.0/000_update_match_id.py

{'to_delete': 3209}
```

- Finally, you update (insert + deletion) with the `update` command:

```
❯ CMD=update python3 scripts/db/2024.1.0/000_update_match_id.py

{'inserted': 809, 'deleted': 809, 'pre_updated': 0}
```

- If you try to update again, since the flows `match_id` have been updated, it shouldn't update anymore:

```
❯ CMD=update python3 scripts/db/2024.1.0/000_update_match_id.py

{'inserted': 0, 'deleted': 0, 'pre_updated': 0}
```

</details>

<details><summary><h3>Hard delete old updated_at flows</h3></summary>

### Pre-requisites

- There's no additional Python libraries dependencies required, other than installing the existing `flow_manager` dependencies.
- Make sure you don't have `kytosd` running with otherwise new request can make `flow_manager` write to MongoDB, and the application could overwrite the data you're trying to insert with this script.
- Make sure MongoDB replica set is up and running.

```
export MONGO_USERNAME=
export MONGO_PASSWORD=
export MONGO_DBNAME=napps
export MONGO_HOST_SEEDS="mongo1:27017,mongo2:27018,mongo3:27019"
```

### Backup and restore procedure

- In addition, it's recommended that you backup the `flows` collection of the `napps` database before running this script (make sure to set `-o <dir>` to a persistent directory):

```
mongodump -d napps -c flows -o /tmp/napps_flows
```

If you ever need to restore the backup:

```
mongorestore -d napps -c flows /tmp/napps_flows/napps/flows.bson
```

### How to use

This script `scripts/db/2024.1.0/000_hard_delete_old.py` is a general purpose script to hard delete flows that have been soft deleted before string UTC datetime that you'll specify. You're are encouraged to use this script from time to time until `flow_manager` provides an automatic functionality for this procedure.


- You can count flows that will be deleted with the `count` command. You need to set `UTC_DATETIME` which will be the `updated_at` datetime that will include flows which `updated_at` is less than or equal this datetime, the example bellow hard deletes flows that have been deleted prior to `"2024-07-17 13:53:24"` UTC:

```
❯ CMD=count UTC_DATETIME="2024-07-17 13:53:24" python3 scripts/db/2024.1.0/000_hard_delete_old.py
{'counted': 8}
```

- (Optional step) if you wish to list the filtered flows you can use  the `list` command:
 
```
❯ CMD=list UTC_DATETIME="2024-07-17 13:53:24" python scripts/db/2024.1.0/000_hard_delete_old.py
{'_id': '528dc723714952cebb1e4e08b84521c4', 'flow': {'table_id': 0, 'owner': 'mef_eline', 'table_group': 'evpl', 'priority': 20000, 'cookie': Decimal128('12297755378995773006'), 'idle_ti meout': 0, 'hard_timeout': 0, 'match': {'in_port': 1, 'dl_vlan': 1003}, 'actions': [{'action_type': 'push_vlan', 'tag_type': 's'}, {'action_type': 'set_vlan', 'vlan_id': 401}, {'action_t ype': 'output', 'port': 4}]}, 'flow_id': '67d799f8c82cfea34a567f523f0c30ee', 'id': '528dc723714952cebb1e4e08b84521c4', 'inserted_at': datetime.datetime(2024, 7, 17, 13, 52, 27, 514000), 'state': 'deleted', 'switch': '00:00:00:00:00:00:00:01', 'updated_at': datetime.datetime(2024, 7, 17, 13, 52, 44, 743000)}
{'_id': '4c4a557b3c2a06fedbb86ca1662d9ff5', 'flow': {'table_id': 0, 'owner': 'mef_eline', 'table_group': 'evpl', 'priority': 20000, 'cookie': Decimal128('12297755378995773006'), 'idle_ti meout': 0, 'hard_timeout': 0, 'match': {'in_port': 4, 'dl_vlan': 401}, 'actions': [{'action_type': 'pop_vlan'}, {'action_type': 'output', 'port': 1}]}, 'flow_id': '6685b00a0d77da02fe51d9 8b61048bbb', 'id': '4c4a557b3c2a06fedbb86ca1662d9ff5', 'inserted_at': datetime.datetime(2024, 7, 17, 13, 52, 27, 514000), 'state': 'deleted', 'switch': '00:00:00:00:00:00:00:01', 'updated_at': datetime.datetime(2024, 7, 17, 13, 52, 44, 743000)}
{'_id': '4863b0d09c70703e821a7c324db71687', 'flow': {'table_id': 0, 'owner': 'mef_eline', 'table_group': 'evpl', 'priority': 20000, 'cookie': Decimal128('12297755378995773006'), 'idle_ti meout': 0, 'hard_timeout': 0, 'match': {'in_port': 1, 'dl_vlan': 1003}, 'actions': [{'action_type': 'push_vlan', 'tag_type': 's'}, {'action_type': 'set_vlan', 'vlan_id': 401}, {'action_t ype': 'output', 'port': 3}]}, 'flow_id': '4c1dd3293e6ddc39de812be70caca2ba', 'id': '4863b0d09c70703e821a7c324db71687', 'inserted_at': datetime.datetime(2024, 7, 17, 13, 52, 27, 527000), 'state': 'deleted', 'switch': '00:00:00:00:00:00:00:03', 'updated_at': datetime.datetime(2024, 7, 17, 13, 52, 44, 729000)}
{'_id': 'e9758b6008dbabbebfbc0f7db2399a17', 'flow': {'table_id': 0, 'owner': 'mef_eline', 'table_group': 'evpl', 'priority': 20000, 'cookie': Decimal128('12297755378995773006'), 'idle_ti meout': 0, 'hard_timeout': 0, 'match': {'in_port': 3, 'dl_vlan': 401}, 'actions': [{'action_type': 'pop_vlan'}, {'action_type': 'output', 'port': 1}]}, 'flow_id': 'fbb2f8d5ab5350ef4ca663 9595fbaa78', 'id': 'e9758b6008dbabbebfbc0f7db2399a17', 'inserted_at': datetime.datetime(2024, 7, 17, 13, 52, 27, 527000), 'state': 'deleted', 'switch': '00:00:00:00:00:00:00:03', 'updated_at': datetime.datetime(2024, 7, 17, 13, 52, 44, 729000)} 
{'_id': 'a91755a792a375dcbd1bc41eb8ad0bb3', 'flow': {'table_id': 0, 'owner': 'mef_eline', 'table_group': 'evpl', 'priority': 20000, 'cookie': Decimal128('12297755378995773006'), 'idle_ti meout': 0, 'hard_timeout': 0, 'match': {'in_port': 2, 'dl_vlan': 401}, 'actions': [{'action_type': 'set_vlan', 'vlan_id': 401}, {'action_type': 'output', 'port': 3}]}, 'flow_id': '9ec845 c20b60b3fc93b515ff8ec8d650', 'id': 'a91755a792a375dcbd1bc41eb8ad0bb3', 'inserted_at': datetime.datetime(2024, 7, 17, 13, 52, 27, 553000), 'state': 'deleted', 'switch': '00:00:00:00:00:00 :00:02', 'updated_at': datetime.datetime(2024, 7, 17, 13, 52, 44, 756000)}
{'_id': 'e67e65564f5ed8b2f1de8e96500265de', 'flow': {'table_id': 0, 'owner': 'mef_eline', 'table_group': 'evpl', 'priority': 20000, 'cookie': Decimal128('12297755378995773006'), 'idle_ti meout': 0, 'hard_timeout': 0, 'match': {'in_port': 3, 'dl_vlan': 401}, 'actions': [{'action_type': 'set_vlan', 'vlan_id': 401}, {'action_type': 'output', 'port': 2}]}, 'flow_id': 'badd30 1c6d3edef6a5282bc264c0360b', 'id': 'e67e65564f5ed8b2f1de8e96500265de', 'inserted_at': datetime.datetime(2024, 7, 17, 13, 52, 27, 553000), 'state': 'deleted', 'switch': '00:00:00:00:00:00 :00:02', 'updated_at': datetime.datetime(2024, 7, 17, 13, 52, 44, 756000)}
{'_id': '251273d71eaa438db046d21c1cc4e09f', 'flow': {'table_id': 0, 'owner': 'mef_eline', 'table_group': 'evpl', 'priority': 20000, 'cookie': Decimal128('12297755378995773006'), 'idle_ti meout': 0, 'hard_timeout': 0, 'match': {'in_port': 3, 'dl_vlan': 401}, 'actions': [{'action_type': 'pop_vlan'}, {'action_type': 'output', 'port': 1}]}, 'flow_id': 'ff28f308d5e789687be1b5 7a8ad095ea', 'id': '251273d71eaa438db046d21c1cc4e09f', 'inserted_at': datetime.datetime(2024, 7, 17, 13, 52, 27, 565000), 'state': 'deleted', 'switch': '00:00:00:00:00:00:00:01', 'updated_at': datetime.datetime(2024, 7, 17, 13, 52, 44, 743000)}
{'_id': '6b83900a439e802478e83bd57f2f832c', 'flow': {'table_id': 0, 'owner': 'mef_eline', 'table_group': 'evpl', 'priority': 20000, 'cookie': Decimal128('12297755378995773006'), 'idle_ti meout': 0, 'hard_timeout': 0, 'match': {'in_port': 2, 'dl_vlan': 401}, 'actions': [{'action_type': 'pop_vlan'}, {'action_type': 'output', 'port': 1}]}, 'flow_id': '898f23a7bd9ff1e1ed10c5 ce385960c5', 'id': '6b83900a439e802478e83bd57f2f832c', 'inserted_at': datetime.datetime(2024, 7, 17, 13, 52, 27, 575000), 'state': 'deleted', 'switch': '00:00:00:00:00:00:00:03', 'updated_at': datetime.datetime(2024, 7, 17, 13, 52, 44, 729000)}
None
```

- Finally, to hard delete you can use the `delete` command, this command uses the same filer that the `count|write_file` command use:

```
❯ CMD=delete UTC_DATETIME="2024-07-17 13:53:24" python3 scripts/db/2024.1.0/000_hard_delete_old.py
{'deleted': 8}
```

- If you try to run again but there isn't flows to be deleted, it won't delete as you'd expect:

```
❯ CMD=delete UTC_DATETIME="2024-07-17 13:53:24" python3 scripts/db/2024.1.0/000_hard_delete_old.py
{'deleted': 0}
```

</details>
