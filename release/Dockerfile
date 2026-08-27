# Home Assistant Add-on compatibility layer.
# HA Bridge application files remain entirely in the already-published base image.
# A deliberately unavailable default keeps Dockerfile linting valid while still
# making omission of the release script's immutable BASE_IMAGE fail closed.
ARG BASE_IMAGE=ha-bridge-base-image-must-be-set:invalid
FROM ${BASE_IMAGE}

ARG ADDON_VERSION
ARG BASE_IMAGE
LABEL org.opencontainers.image.title="HA Bridge Home Assistant Add-on" \
      org.opencontainers.image.version="${ADDON_VERSION}" \
      io.habridge.addon.base-image="${BASE_IMAGE}"

# HA Bridge's existing entrypoint initializes Supervisor-mounted directories as
# root, then drops to the ha-bridge user before Uvicorn starts.
USER root
