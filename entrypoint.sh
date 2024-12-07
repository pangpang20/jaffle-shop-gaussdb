#!/bin/bash
envsubst < /dbt_app/sample-profiles.yml > /dbt_app/profiles.yml
exec "$@"
