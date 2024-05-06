## `flow_manager` scripts from Kytos 2023.1.0

This folder contains `flow_manager` related scripts.

<details><summary><h3>Drop compound index</h3></summary>

### Pre-requisites
- There's no additional Python libraries dependencies required, other than installing the existing flow_manager requirements-dev.txt file.
- Make sure you don't have `kytosd` running with otherwise new request can make flow_manager write to MongoDB, and the application could overwrite the data you're trying to insert with this script.
- Make sure MongoDB replica set is up and running.

```
export MONGO_USERNAME=
export MONGO_PASSWORD=
export MONGO_DBNAME=napps
export MONGO_HOST_SEEDS="mongo1:27017,mongo2:27018,mongo3:27019"
```

On version `2023.1`, this `flows` compound index `switch_1_flow.cookie_1_state_1_inserted_at_1_updated_at_1` has changed. If you're upgrading to `2023.1` froma previous version, you should run the `000_drop_compound_index.py` script to drop it:

```
CMD=drop_index python3 000_drop_compound_index.py
```
</details>

<details><summary><h3>Add `owner` and `table_group` fields to `flows` collections</h3></summary>

### Pre-requisites
- There's no additional Python libraries dependencies required, other than installing the existing flow_manager requirements-dev.txt file.
- Make sure you don't have `kytosd` running with otherwise new request can make flow_manager write to MongoDB, and the application could overwrite the data you're trying to insert with this script.
- Make sure MongoDB replica set is up and running.

```
export MONGO_USERNAME=
export MONGO_PASSWORD=
export MONGO_DBNAME=napps
export MONGO_HOST_SEEDS="mongo1:27017,mongo2:27018,mongo3:27019"
```

### How to use

Run the script to upgrade all flows from `mef_eline`, `of_lldp` and `coloring` with new fields `owner` and `table_group`

```
python3 001_pipeline_related.py
```
</details>