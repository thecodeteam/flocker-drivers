CREATE KEYSPACE EMCXtremIO WITH REPLICATION = { 'class' : 'SimpleStrategy'};
CREATE TABLE EMCXtremIO.users (userid text PRIMARY KEY, first_name text, last_name text, emails set<text>, top_scores list<int>, todo map<timestamp, text>);
