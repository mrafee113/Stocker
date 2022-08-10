psql postgres -c "revoke connect on database stocker from public;"
psql postgres -c "SELECT
                    pg_terminate_backend(pid)
                  FROM
                    pg_stat_activity
                  WHERE
                    pid <> pg_backend_pid()
                    AND datname = 'stocker'
                  ;"
psql postgres -c "drop database if exists stocker;"
psql postgres -c "drop role if exists stocker;"
psql postgres -c "create database stocker;"
psql postgres -c "grant connect on database stocker to public;"

psql stocker -c "create role stocker;"
psql stocker -c "alter role stocker with login;"
psql stocker -c "alter role stocker with password 'stocker';"
psql stocker -c "grant all privileges on database stocker to stocker;"
psql stocker -c "alter role stocker superuser;"

psql stocker -c "alter role stocker set client_encoding to 'utf8'"
psql stocker -c "alter role stocker set timezone to 'UTC'"
# fixme
