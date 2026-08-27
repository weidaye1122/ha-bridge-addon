#!/bin/sh
set -eu

previous_ref=${1:?Pass the previous Add-on image reference.}
release_ref=${2:?Pass the new Add-on image reference.}
expected_version=${3:?Pass the expected HA Bridge application version.}

verify_root=$(mktemp -d "${TMPDIR:-/tmp}/ha-bridge-addon-upgrade.XXXXXX")
container_name="ha-bridge-addon-release-verify-$$"
mkdir -p "$verify_root/data" "$verify_root/secrets"

cleanup() {
  docker rm --force "$container_name" >/dev/null 2>&1 || true
  rm -rf "$verify_root"
}
trap cleanup EXIT INT TERM HUP

start_container() {
  image_ref=$1
  docker run --detach --name "$container_name" \
    --env APP_DATA_DIR=/data \
    --env APP_PORT=18080 \
    --env APP_HA_CREDENTIAL_FILE=/run/secrets/ha_credentials.key \
    --env APP_DISPLAY_PAIRING_KEY_FILE=/run/secrets/display_pairing_codes.key \
    --env APP_LICENSE_CREDENTIAL_FILE=/run/secrets/license_credentials.key \
    --volume "$verify_root/data:/data" \
    --volume "$verify_root/secrets:/run/secrets" \
    "$image_ref" >/dev/null
}

wait_ready() {
  expected=$1
  attempt=0
  while [ "$attempt" -lt 60 ]; do
    if response=$(docker exec "$container_name" /opt/venv/bin/python -c \
      'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:18080/health/ready", timeout=2).read().decode())' \
      2>/dev/null); then
      if printf '%s\n' "$response" | grep '"status":"ready"' >/dev/null && \
         printf '%s\n' "$response" | grep "\"version\":\"$expected\"" >/dev/null; then
        return 0
      fi
    fi
    attempt=$((attempt + 1))
    sleep 1
  done
  docker logs "$container_name" >&2 || true
  echo "Add-on readiness verification timed out for application $expected" >&2
  return 1
}

previous_version=${previous_ref##*:}
previous_base=${previous_version%-*}
start_container "$previous_ref"
wait_ready "$previous_base"
docker stop "$container_name" >/dev/null
docker rm "$container_name" >/dev/null

start_container "$release_ref"
wait_ready "$expected_version"
runtime_uid=$(docker exec "$container_name" awk '/^Uid:/ {print $2}' /proc/1/status)
if [ "$runtime_uid" != "100" ]; then
  echo "Add-on application must run as UID 100 after initialization; got $runtime_uid" >&2
  exit 1
fi

printf 'Add-on upgrade verified: %s -> %s, application=%s, runtime_uid=%s\n' \
  "$previous_ref" "$release_ref" "$expected_version" "$runtime_uid"
