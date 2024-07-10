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

On version `2024.1`, flows `match_id` and `_id` document values have changed just so the `cookie` isn't a factor of the computed `match_id` hashed value anymore. This script will insert new updated flows and delete the old ones if the expected `match_id` is different.

- You can use the `count` command to check how many flows have their `match_id` outdated, this will include all flows, including flows marked as deleted:

```
❯ CMD=count python3 scripts/db/2024.1.0/000_update_match_id.py

{'to_delete': 809}
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
