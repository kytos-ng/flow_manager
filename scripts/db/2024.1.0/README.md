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

This script `scripts/db/2024.1.0/001_hard_delete_old.py` is a general purpose script to hard delete flows that have been soft deleted before string UTC datetime that you'll specify. You're are encouraged to use this script from time to time until `flow_manager` provides an automatic funcionality for this procedure. 


- You can count flows that will be deleted with the `count` command. You need to set `UTC_DATETIME` which will be the `updated_at` datetime that will include flows which `updated_at` is less than or equal this datetime, the example bellow hard deletes flows that have been deleted prior to `"2024-07-11 17:47:24"` UTC:

```
❯ CMD=count UTC_DATETIME="2024-07-11 17:47:24" python scripts/db/2024.1.0/001_hard_delete_old.py
{'to_delete': 8}
```

- (Optional step) if you wish to further analize and write the flows to a file you can use  the `write_file` command setting the `OUT_FILE` env var:
 ```
❯ CMD=write_file OUT_FILE=out.json UTC_DATETIME="2024-07-11 17:47:24" python scripts/db/2024.1.0/001_hard_delete_old.py
out.json

❯ cat out.json | grep -E "state|updated_at"
    "state": "deleted",
    "updated_at": "2024-07-11 12:14:46.876000"
    "state": "deleted",
    "updated_at": "2024-07-11 12:14:46.876000"
    "state": "deleted",
    "updated_at": "2024-07-11 12:14:46.849000"
    "state": "deleted",
    "updated_at": "2024-07-11 12:14:46.849000"
    "state": "deleted",
    "updated_at": "2024-07-11 12:14:46.893000"
    "state": "deleted",
    "updated_at": "2024-07-11 12:14:46.893000"
    "state": "deleted",
    "updated_at": "2024-07-11 12:14:46.876000"
    "state": "deleted",
    "updated_at": "2024-07-11 12:14:46.849000"

```

- Finally, to hard delete you can use the `delete` command, this command uses the same filer that the `count|write_file` command use:

```
❯ CMD=delete UTC_DATETIME="2024-07-11 17:47:24" python scripts/db/2024.1.0/001_hard_delete_old.py
{'deleted': 8}
```

- If you try to run again but there isn't flows to be deleted, it won't delete as you'd expect:

```
❯ CMD=delete UTC_DATETIME="2024-07-11 17:47:24" python scripts/db/2024.1.0/001_hard_delete_old.py
{'deleted': 0}
```

</details>
