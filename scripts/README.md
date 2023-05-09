## `flow_manager` scripts

This folder contains `flow_manager` related scripts.

### Data migration from `storehouse` to MongoDB

[`storehouse_to_mongo.py`](./storehouse_to_mongo.py) is a script to migrate OpenFlow1.3 flow data entries from certain namespaces from `storehouse` to MongoDB.

#### Pre-requisites

- There's no additional Python libraries dependencies required, other than installing the existing flow_manager requirements-dev.txt file.
- Make sure you don't have `kytosd` running with otherwise new request can make flow_manager write to MongoDB, and the application could overwrite the data you're trying to insert with this script.
- Make sure MongoDB replica set is up and running.

```
export MONGO_USERNAME=
export MONGO_PASSWORD=
export MONGO_DBNAME=napps
export MONGO_HOST_SEEDS="mongo1:27017,mongo2:27018,mongo3:27019"
```

#### How to use

- Export these two environment variables, based on where storehouse and kytos are installed, if you're running `amlight/kytos:latest` docker image they should be:
```
export STOREHOUSE_NAMESPACES_DIR=/var/tmp/kytos/storehouse/
export PYTHONPATH=/var/lib/kytos
```

- Parametrize the environment variable `CMD` command and execute `storehouse_to_mongo.py` script (the command is passed via an env var to avoid conflicts with `kytosd`, since depending how you set the `PYTHONPATH` it can interfere)

- The following `CMD` commands are available:

```
insert_flows
load_flows
```

The `load_*` commands are meant to be used to double check what would actually be loaded, so it's encouraged to try out the load command to confirm the data can be loaded properly, and if they are, feel free to use any of the `insert_*` commands, which will rely internally on the load functions to the either insert or update the documents.

For example, to double check what would be loaded from storehouse namespace `kytos.flow.persistence`:

```
CMD=load_flows python3 scripts/storehouse_to_mongo.py
```

And then, to insert (or update) the flows:

```
CMD=insert_flows python3 scripts/storehouse_to_mongo.py
```

### Add `owner` and `table_group` fields to `flows` collections

### Pre-requisites
Same requisites as above

### How to use

Run the script to upgrade all flows from `mef_eline`, `of_lldp` and `coloring` with new fields `owner` and `table_group`

```
python3 pipeline_related.py
```
