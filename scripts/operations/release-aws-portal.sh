#!/usr/bin/env bash
set -euo pipefail

release=${1:?release required}
checksum=${2:?checksum required}
expected=${3:?image ID required}
entry=${4:?frontend entry required}
[[ $release =~ ^release-[0-9]{14}-[a-f0-9]{8}$ &&
   $checksum =~ ^[a-f0-9]{64}$ &&
   $expected =~ ^sha256:[a-f0-9]{64}$ &&
   $entry =~ ^/static/ui/assets/main-[a-zA-Z0-9_-]+\.js$ ]]
archive="/home/ubuntu/$release.tar"
trap 'rm -f -- "$archive"' EXIT
active=cloud-storage-portal:native
candidate="cloudbox-portal:$release"

exec 9>/home/ubuntu/.cloudbox-portal-release.lock
flock -n 9 || { printf 'A CloudBox release is already running.\n' >&2; exit 1; }
cd /opt/cloudbox
compose=(sudo -n docker compose -f compose.aws.yml -f compose.tunnel.yml)
"${compose[@]}" config -q

storage_volume() {
    sudo -n docker inspect --format '{{range .Mounts}}{{if eq .Destination "/data/cloudbox"}}{{.Name}}{{end}}{{end}}' "$1"
}

verify_ready() {
    curl -fsS --max-time 8 --retry 3 http://127.0.0.1:8000/readyz |
        grep -F '"status":"ok"' >/dev/null
}

old_portal=$("${compose[@]}" ps -q portal)
old_db=$("${compose[@]}" ps -q db)
old_tunnel=$("${compose[@]}" ps -q tunnel)
[[ -n $old_portal && -n $old_db && -n $old_tunnel ]]
old_image=$(sudo -n docker inspect --format '{{.Image}}' "$old_portal")
old_storage=$(storage_volume "$old_portal")
[[ $old_storage == cloud-storage_cloudbox_data ]]
verify_ready
curl -fsS --max-time 8 http://127.0.0.1:20241/ready -o /dev/null
printf '%s  %s\n' "$checksum" "$archive" | sha256sum --check
sudo -n docker load -i "$archive"
[[ $(sudo -n docker image inspect --format '{{.Id}}' "$candidate") == "$expected" ]]

replace_portal() {
    "${compose[@]}" up -d --no-deps --force-recreate --wait --wait-timeout 90 portal
}

verify_release() {
    local portal
    portal=$("${compose[@]}" ps -q portal)
    [[ -n $portal &&
       $(sudo -n docker inspect --format '{{.Image}}' "$portal") == "$expected" &&
       $(storage_volume "$portal") == "$old_storage" &&
       $("${compose[@]}" ps -q db) == "$old_db" &&
       $("${compose[@]}" ps -q tunnel) == "$old_tunnel" ]] &&
       verify_ready &&
       curl -fsS --max-time 8 http://127.0.0.1:8000/ |
           grep -F "$entry" >/dev/null
}

sudo -n docker tag "$candidate" "$active"
if replace_portal && verify_release; then
    printf 'Portal ready with image %s\n' "$expected"
else
    printf 'Portal checks failed. Restoring the previous image.\n' >&2
    sudo -n docker tag "$old_image" "$active"
    replace_portal
    verify_ready
    printf 'Previous Portal restored.\n' >&2
    exit 1
fi
