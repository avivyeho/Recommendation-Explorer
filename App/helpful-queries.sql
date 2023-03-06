-- get all datasets and their user's usernames:
SELECT setid,username FROM dataset INNER JOIN users ON dataset.uid = users.uid;

-- get all info for a certain table (about columns, constraints, ....)
\d+ tableName;

-- get count of distinct entries for a rowName in a certain tableName where conditionsHold
SELECT COUNT(DISTINCT rowName) FROM tableName WHERE conditionsHold;

-- give app all permissions
ALTER USER app WITH SUPERUSER;

-- get all queries
SELECT * FROM pg_stat_activity;

-- force stop a specific query from the list above:
SELECT pg_cancel_backend(PID);

-- get all users and their item histories in a nice table for a subset of a dataset
select user_id, string_agg(item_id::varchar(255),',')  from subset_of_dataset WHERE setid = (givenSetId) AND scenario_name = (givenScenarioName) GROUP BY user_id;

