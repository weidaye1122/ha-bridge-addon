#!/bin/sh
set -eu

previous_ref=${1:?Pass the previous Add-on image reference.}
release_ref=${2:?Pass the new Add-on image reference.}
expected_version=${3:?Pass the expected HA Bridge application version.}
previous_base=${4:-}
platform=${VERIFY_PLATFORM:-}
project_root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd -P)

verify_root=$(mktemp -d "${TMPDIR:-/tmp}/ha-bridge-addon-upgrade.XXXXXX")
container_name="ha-bridge-addon-release-verify-$$"
mkdir -p "$verify_root/data" "$verify_root/secrets"

cleanup() {
  cleanup_status=$?
  if cleanup_output=$(docker rm --force "$container_name" 2>&1); then
    :
  else
    case "$cleanup_output" in
      *No\ such\ container:*) ;;
      *)
        printf 'Unable to remove owned container %s; temporary data retained at %s\n%s\n' \
          "$container_name" "$verify_root" "$cleanup_output" >&2
        return 1
        ;;
    esac
  fi
  rm -rf "$verify_root"
  return "$cleanup_status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP

start_container() {
  image_ref=$1
  set --
  if [ -n "$platform" ]; then set -- --platform "$platform"; fi
  docker run "$@" --detach --name "$container_name" \
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

if [ -z "$previous_base" ]; then
  case "$previous_ref" in *@*) echo "Pass the previous application version for digest-pinned upgrades" >&2; exit 2;; esac
  previous_version=${previous_ref##*:}
  previous_base=${previous_version%-*}
fi
start_container "$previous_ref"
wait_ready "$previous_base"
docker exec -i "$container_name" /opt/venv/bin/python - seed < "$project_root/release/upgrade_data_probe.py"
docker stop "$container_name" >/dev/null
docker rm "$container_name" >/dev/null

# Snapshot and back up only the stopped, internally consistent anonymous fixture.
start_container "$previous_ref"
wait_ready "$previous_base"
docker exec -i "$container_name" /opt/venv/bin/python - snapshot < "$project_root/release/upgrade_data_probe.py" > "$verify_root/before.json"
docker stop "$container_name" >/dev/null
docker rm "$container_name" >/dev/null
cp -Rp "$verify_root/data" "$verify_root/data-backup"
cp -Rp "$verify_root/secrets" "$verify_root/secrets-backup"

start_container "$release_ref"
wait_ready "$expected_version"
runtime_uid=$(docker exec "$container_name" awk '/^Uid:/ {print $2}' /proc/1/status)
if [ "$runtime_uid" != "100" ]; then
  echo "Add-on application must run as UID 100 after initialization; got $runtime_uid" >&2
  exit 1
fi

docker exec -i "$container_name" /opt/venv/bin/python - snapshot < "$project_root/release/upgrade_data_probe.py" > "$verify_root/after.json"
cmp "$verify_root/before.json" "$verify_root/after.json"
docker restart "$container_name" >/dev/null
wait_ready "$expected_version"
docker exec -i "$container_name" /opt/venv/bin/python - snapshot < "$project_root/release/upgrade_data_probe.py" > "$verify_root/restarted.json"
cmp "$verify_root/before.json" "$verify_root/restarted.json"
docker stop "$container_name" >/dev/null
docker rm "$container_name" >/dev/null
rm -rf "$verify_root/data" "$verify_root/secrets"
mv "$verify_root/data-backup" "$verify_root/data"
mv "$verify_root/secrets-backup" "$verify_root/secrets"
start_container "$previous_ref"
wait_ready "$previous_base"
docker exec -i "$container_name" /opt/venv/bin/python - snapshot < "$project_root/release/upgrade_data_probe.py" > "$verify_root/restored.json"
cmp "$verify_root/before.json" "$verify_root/restored.json"

trap - EXIT INT TERM HUP
cleanup
printf 'Add-on upgrade verified: %s -> %s, application=%s, runtime_uid=%s\n' \
  "$previous_ref" "$release_ref" "$expected_version" "$runtime_uid"
