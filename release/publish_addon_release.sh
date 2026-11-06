#!/bin/sh
set -eu

action=${1:-}
if [ "$action" != "preflight" ] && [ "$action" != "publish" ] && [ "$action" != "resume" ]; then
  echo "usage: BASE_VERSION=X.Y.Z ADDON_REVISION=N $0 preflight|publish|resume" >&2
  exit 2
fi

project_root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd -P)
cd "$project_root"

: "${BASE_VERSION:?Set BASE_VERSION to the published HA Bridge version.}"
ADDON_REVISION=${ADDON_REVISION:-1}
BASE_IMAGE_REPOSITORY=${BASE_IMAGE_REPOSITORY:-crpi-w1apw3w3zzp43y80.cn-shanghai.personal.cr.aliyuncs.com/weidaye1122/ha_bridge}
ADDON_IMAGE_REPOSITORY=${ADDON_IMAGE_REPOSITORY:-crpi-w1apw3w3zzp43y80.cn-shanghai.personal.cr.aliyuncs.com/weidaye1122/ha-bridge-addon}
BUILDER_NAME=${BUILDER_NAME:-ha-bridge-release-builder}
PLATFORMS=${PLATFORMS:-linux/amd64,linux/arm64}

if ! printf '%s\n' "$BASE_VERSION" | grep -Eq '^[0-9]\.[0-9]\.[0-9]$'; then
  echo "BASE_VERSION must use the HA Bridge X.Y.Z one-digit version policy" >&2
  exit 2
fi
case "$ADDON_REVISION" in
  ''|*[!0-9]*|0*) echo "ADDON_REVISION must be a positive integer" >&2; exit 2 ;;
esac
addon_version="$BASE_VERSION-$ADDON_REVISION"
tag_name="v$addon_version"
release_ref="$ADDON_IMAGE_REPOSITORY:$addon_version"
latest_ref="$ADDON_IMAGE_REPOSITORY:latest"
base_ref="$BASE_IMAGE_REPOSITORY:$BASE_VERSION"

# New stable releases are coordinated by the main candidate transaction.
# Keep format1 recovery available for already-published historical images.
if [ "$action" = publish ]; then
  echo 'Use the main publish_full_release.sh prepare/check/publish flow; direct Add-on publication is disabled.' >&2
  exit 2
fi
legacy_full_digest=""
if [ "$action" = resume ] && ! python3 release/release_state.py exists "$addon_version"; then
  legacy_full_digest=$(python3 - "$BASE_VERSION" "$ADDON_REVISION" "$BASE_IMAGE_REPOSITORY" <<'PYRECEIPT'
import json,os,subprocess,sys
from pathlib import Path
path=os.environ.get('HABRIDGE_LEGACY_FULL_RELEASE_RECEIPT','')
if not path:
    raise SystemExit('No legacy Add-on receipt; resume the owning full publication')
s=json.loads(Path(path).read_text())
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
if (s.get('format')!=1 or s.get('version')!=sys.argv[1] or s.get('revision')!=sys.argv[2]
        or s.get('phase')!='main-ready' or s.get('addonSource')!=head or not s.get('digest')
        or sys.argv[3] not in {s.get('image'),s.get('aliyun')}):
    raise SystemExit('Legacy full receipt does not authorize this unfinished Add-on tail')
print(s['digest'])
PYRECEIPT
)
fi

if [ -n "$(git status --porcelain --untracked-files=normal)" ]; then
  echo "formal Add-on publishing requires a clean source tree" >&2
  exit 2
fi
git_name=$(git config user.name || true)
git_email=$(git config user.email || true)
if [ -z "$git_name" ] || [ -z "$git_email" ]; then
  echo "configure Git user.name and user.email before Add-on publishing" >&2
  exit 2
fi

git fetch origin main --tags
local_head=$(git rev-parse HEAD)
remote_main=$(git rev-parse refs/remotes/origin/main)
if ! git merge-base --is-ancestor "$remote_main" "$local_head"; then
  echo "Add-on HEAD must contain origin/main without divergence before publishing" >&2
  exit 2
fi
resuming=false
if [ "$action" = resume ] && python3 release/release_state.py exists "$addon_version"; then
  resuming=true
fi
if [ "$resuming" = false ] && { git show-ref --verify --quiet "refs/tags/$tag_name" ||
   git ls-remote --exit-code --tags origin "refs/tags/$tag_name" >/dev/null 2>&1; }; then
  echo "Add-on Git tag $tag_name already exists; refusing to overwrite it" >&2
  exit 2
fi

existing_image=""
image_exists=false
if existing_image=$(docker buildx imagetools inspect "$release_ref" 2>&1); then
  image_exists=true
  if [ "$resuming" = false ]; then
    echo "Add-on image $release_ref already exists; refusing to overwrite it" >&2
    exit 2
  fi
else
  case "$existing_image" in
    *not\ found*|*manifest\ unknown*|*MANIFEST_UNKNOWN*) ;;
    *) printf '%s\n' "$existing_image" >&2; echo "unable to confirm that $release_ref is unused" >&2; exit 1 ;;
  esac
fi

if [ "$resuming" = false ]; then
  python3 release/release_state.py pending "$addon_version"
fi
if [ "$action" = "preflight" ]; then
  printf 'Add-on release preflight passed: %s\n' "$addon_version"
  exit 0
fi

base_inspect=$(docker buildx imagetools inspect "$base_ref")
base_digest=$(printf '%s\n' "$base_inspect" | sed -n 's/^Digest:[[:space:]]*//p' | head -n 1)
if [ -z "$base_digest" ]; then
  echo "unable to resolve immutable HA Bridge base digest: $base_ref" >&2
  exit 1
fi
if [ -n "$legacy_full_digest" ] && [ "$base_digest" != "$legacy_full_digest" ]; then
  echo 'Published main image differs from the owning legacy full receipt' >&2
  exit 2
fi
for platform in linux/amd64 linux/arm64; do
  printf '%s\n' "$base_inspect" | grep -E "Platform:[[:space:]]+$platform$" >/dev/null || {
    echo "HA Bridge base image is missing $platform: $base_ref" >&2
    exit 1
  }
done

immutable_base="$base_ref@$base_digest"
if [ "$resuming" = true ]; then
  python3 release/release_state.py verify "$addon_version" "$immutable_base" "$release_ref"
  previous_version=$(python3 release/release_state.py get "$addon_version" previous)
  saved_digest=$(python3 release/release_state.py get "$addon_version" digest)
  observed_digest=$(printf '%s\n' "$existing_image" | sed -n 's/^Digest:[[:space:]]*//p' | head -n 1)
  if [ "$image_exists" = true ]; then
    if [ -z "$saved_digest" ] || [ -z "$observed_digest" ] || [ "$observed_digest" != "$saved_digest" ]; then
      echo 'Existing Add-on image has no matching receipt; inspect the interrupted push before recovery.' >&2
      exit 2
    fi
  elif [ -n "$saved_digest" ]; then
    echo 'The recorded Add-on image is missing; refusing to rebuild an immutable publication.' >&2
    exit 2
  fi
else
  previous_version=$(python3 release/version.py current)
  python3 release/release_state.py begin "$addon_version" "$previous_version" "$immutable_base" "$release_ref"
fi
if [ "$resuming" = false ] || [ -z "$saved_digest" ]; then
docker buildx build \
  --builder "$BUILDER_NAME" \
  --file release/Dockerfile \
  --platform "$PLATFORMS" \
  --build-arg "BASE_IMAGE=$immutable_base" \
  --build-arg "ADDON_VERSION=$addon_version" \
  --provenance=mode=min \
  --output type=image,oci-artifact=false \
  --tag "$release_ref" \
  --push \
  release
fi

release_inspect=$(docker buildx imagetools inspect "$release_ref")
release_digest=$(printf '%s\n' "$release_inspect" | sed -n 's/^Digest:[[:space:]]*//p' | head -n 1)
if [ -z "$release_digest" ]; then
  echo "unable to resolve Add-on release digest: $release_ref" >&2
  exit 1
fi
python3 release/release_state.py image-ready "$addon_version" "$release_digest"
for platform in linux/amd64 linux/arm64; do
  printf '%s\n' "$release_inspect" | grep -E "Platform:[[:space:]]+$platform$" >/dev/null || {
    echo "Add-on release is missing $platform: $release_ref" >&2
    exit 1
  }
done

anonymous_config=$(mktemp -d "${TMPDIR:-/tmp}/ha-bridge-addon-anonymous.XXXXXX")
cleanup_anonymous() {
  rm -rf "$anonymous_config"
}
trap cleanup_anonymous EXIT INT TERM HUP
DOCKER_CONFIG="$anonymous_config" docker manifest inspect "$release_ref" >/dev/null

previous_ref="$ADDON_IMAGE_REPOSITORY:$previous_version"
./release/verify_addon_upgrade.sh "$previous_ref" "$release_ref" "$BASE_VERSION"

docker buildx imagetools create --tag "$latest_ref" "$release_ref"
latest_inspect=$(docker buildx imagetools inspect "$latest_ref")
latest_digest=$(printf '%s\n' "$latest_inspect" | sed -n 's/^Digest:[[:space:]]*//p' | head -n 1)
if [ "$latest_digest" != "$release_digest" ]; then
  echo "Add-on exact version and latest digests do not match" >&2
  exit 1
fi

python3 release/version.py set "$BASE_VERSION" "$ADDON_REVISION"
python3 release/version.py check "$BASE_VERSION" "$ADDON_REVISION"
git diff --check
git add -- ha_bridge/config.yaml ha_bridge/CHANGELOG.md
if ! git diff --cached --quiet; then
  git commit -m "release: HA Bridge Add-on $addon_version"
fi
if ! git show-ref --verify --quiet "refs/tags/$tag_name"; then
  git tag -a "$tag_name" -m "HA Bridge Add-on $addon_version"
fi
[ "$(git rev-list -n 1 "$tag_name")" = "$(git rev-parse HEAD)" ] || {
  echo 'Add-on tag does not match the interrupted release source.' >&2; exit 2;
}
git push --atomic origin "HEAD:refs/heads/main" "refs/tags/$tag_name"

remote_main=$(git ls-remote origin refs/heads/main | awk '{print $1}')
remote_tag=$(git ls-remote origin "refs/tags/$tag_name^{}" | awk '{print $1}')
local_head=$(git rev-parse HEAD)
if [ "$remote_main" != "$local_head" ] || [ "$remote_tag" != "$local_head" ]; then
  echo "Add-on GitHub main/tag verification failed for $tag_name" >&2
  exit 1
fi

python3 release/release_state.py complete "$addon_version"
trap - EXIT INT TERM HUP
rm -rf "$anonymous_config"
printf 'Published HA Bridge Add-on %s from %s (%s).\n' \
  "$addon_version" "$immutable_base" "$release_digest"
