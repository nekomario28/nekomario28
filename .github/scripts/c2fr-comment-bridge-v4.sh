#!/usr/bin/env bash
set -Eeuo pipefail

: "${TARGET_SHA:?}"
: "${EXPECTED_JAR_SHA256:?}"
: "${PRIOR_EVIDENCE_SHA256:?}"
: "${NEOFORGE_VERSION:?}"
: "${MINECRAFT_VERSION:?}"
: "${NEOFORGE_INSTALLER_SHA256:?}"
: "${EVIDENCE_DIR:?}"
: "${GH_TOKEN:?}"
: "${PR_NUMBER:?}"

PAYLOAD_B64="$RUNNER_TEMP/c2fr-bridge/payload.b64"
KEY_B64="$RUNNER_TEMP/c2fr-bridge/key.b64"
READY=0
for _ in $(seq 1 120); do
  COMMENTS_JSON="$(gh api --paginate --slurp \
    "repos/$GITHUB_REPOSITORY/issues/$PR_NUMBER/comments?per_page=100" 2>/dev/null || true)"
  if [[ -n "$COMMENTS_JSON" ]] && python3 - "$GITHUB_RUN_ID" "$PAYLOAD_B64" "$KEY_B64" \
      <<<"$COMMENTS_JSON"; then
    READY=1
    break
  fi
  rm -f "$PAYLOAD_B64" "$KEY_B64"
  sleep 5
done
[[ "$READY" -eq 1 ]]
base64 -d "$PAYLOAD_B64" > "$RUNNER_TEMP/c2fr-bridge/payload.enc"
base64 -d "$KEY_B64" > "$RUNNER_TEMP/c2fr-bridge/key.enc"
printf 'encrypted_payload_received=PASS\ntransport=ordered-pr-comments\n' \
  >> "$EVIDENCE_DIR/key-exchange.txt"

openssl pkeyutl -decrypt \
  -inkey "$RUNNER_TEMP/c2fr-bridge/private.pem" \
  -in "$RUNNER_TEMP/c2fr-bridge/key.enc" \
  -out "$RUNNER_TEMP/c2fr-bridge/passphrase.txt" \
  -pkeyopt rsa_padding_mode:oaep \
  -pkeyopt rsa_oaep_md:sha256
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
  -in "$RUNNER_TEMP/c2fr-bridge/payload.enc" \
  -out "$RUNNER_TEMP/c2fr-bridge/production.jar" \
  -pass file:"$RUNNER_TEMP/c2fr-bridge/passphrase.txt"
ACTUAL_SHA="$(sha256sum "$RUNNER_TEMP/c2fr-bridge/production.jar" | awk '{print $1}')"
[[ "$ACTUAL_SHA" == "$EXPECTED_JAR_SHA256" ]]
jar tf "$RUNNER_TEMP/c2fr-bridge/production.jar" \
  > "$EVIDENCE_DIR/production-jar-contents.txt"
grep -Fq 'com/nekomario28/civitasresidents/CivitasResidents.class' \
  "$EVIDENCE_DIR/production-jar-contents.txt"
grep -Fq 'ResidentsIdentityProviderRegistration.class' \
  "$EVIDENCE_DIR/production-jar-contents.txt"
grep -Fq 'ResidentsIdentityProviderExtension.class' \
  "$EVIDENCE_DIR/production-jar-contents.txt"
! grep -Fq 'C2fRProviderRegistrationTestMain' \
  "$EVIDENCE_DIR/production-jar-contents.txt"
printf 'production_jar_sha256=%s\nproduction_jar_identity=PASS\n' "$ACTUAL_SHA" \
  > "$EVIDENCE_DIR/production-jar.txt"
rm -f "$RUNNER_TEMP/c2fr-bridge/passphrase.txt" \
  "$RUNNER_TEMP/c2fr-bridge/private.pem" \
  "$RUNNER_TEMP/c2fr-bridge/key.enc" \
  "$RUNNER_TEMP/c2fr-bridge/payload.enc" \
  "$PAYLOAD_B64" "$KEY_B64"

SERVER_DIR="$RUNNER_TEMP/c2fr-server"
mkdir -p "$SERVER_DIR/mods"
curl --fail --location --retry 3 --retry-all-errors \
  -o "$SERVER_DIR/neoforge-installer.jar" \
  "https://maven.neoforged.net/releases/net/neoforged/neoforge/$NEOFORGE_VERSION/neoforge-$NEOFORGE_VERSION-installer.jar"
printf '%s  %s\n' "$NEOFORGE_INSTALLER_SHA256" "$SERVER_DIR/neoforge-installer.jar" \
  | sha256sum --check -
(cd "$SERVER_DIR" && java -jar neoforge-installer.jar --installServer) \
  > "$EVIDENCE_DIR/installer.log" 2>&1
cp "$RUNNER_TEMP/c2fr-bridge/production.jar" "$SERVER_DIR/mods/"
printf 'eula=true\n' > "$SERVER_DIR/eula.txt"
PORT="$(python3 - <<'PY'
import socket
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
)"
cat > "$SERVER_DIR/server.properties" <<EOF
difficulty=peaceful
enable-command-block=false
enable-query=false
enable-rcon=false
enforce-secure-profile=false
generate-structures=false
level-name=c2fr-m4-world
level-type=minecraft:flat
max-players=1
motd=C2f-R M4 bridge
online-mode=false
server-ip=127.0.0.1
server-port=$PORT
simulation-distance=2
spawn-protection=0
sync-chunk-writes=true
view-distance=2
white-list=false
EOF
cp "$SERVER_DIR/server.properties" "$EVIDENCE_DIR/server-properties.txt"

(
  cd "$SERVER_DIR"
  exec java \
    -Xms512M -Xmx2G \
    -Djava.awt.headless=true \
    -Djava.security.egd=file:/dev/urandom \
    -Dterminal.jline=false \
    -Dterminal.ansi=false \
    @user_jvm_args.txt \
    "@libraries/net/neoforged/neoforge/$NEOFORGE_VERSION/unix_args.txt" nogui \
    </dev/null
) > "$EVIDENCE_DIR/residents-only-server.log" 2>&1 &
PID=$!
STARTED=0
ELAPSED=0
while (( ELAPSED < 600 )); do
  if grep -Eq 'Done \([0-9.]+s\)!|For help, type' \
    "$EVIDENCE_DIR/residents-only-server.log"; then
    STARTED=1
    break
  fi
  if ! kill -0 "$PID" 2>/dev/null; then
    break
  fi
  sleep 1
  ELAPSED=$((ELAPSED + 1))
done
if (( STARTED != 1 )); then
  kill -TERM "$PID" 2>/dev/null || true
  sleep 5
  kill -KILL "$PID" 2>/dev/null || true
  wait "$PID" || true
  printf 'server_startup=FAIL\nserver_wait_seconds=%s\n' "$ELAPSED" \
    > "$EVIDENCE_DIR/server.txt"
  exit 1
fi
grep -Fq 'Civitas Residents canonical runtime initialized' \
  "$EVIDENCE_DIR/residents-only-server.log"
grep -Eq 'Done \([0-9.]+s\)!|For help, type' \
  "$EVIDENCE_DIR/residents-only-server.log"
kill -TERM "$PID" 2>/dev/null || true
for _ in $(seq 1 30); do
  kill -0 "$PID" 2>/dev/null || break
  sleep 1
done
kill -KILL "$PID" 2>/dev/null || true
wait "$PID" || true
printf 'server_startup=PASS\nserver_wait_seconds=%s\nserver_port=%s\nresidents_runtime_initialized=PASS\n' \
  "$ELAPSED" "$PORT" > "$EVIDENCE_DIR/server.txt"

rm -f "$RUNNER_TEMP/c2fr-bridge/production.jar"
cat > "$EVIDENCE_DIR/manifest.txt" <<EOF
evidence_type=ENCRYPTED_HOSTED_SUPPLEMENTAL_SERVER_START
source_repository=nekomario28/civitas-residents
exact_head=$TARGET_SHA
production_jar_sha256=$EXPECTED_JAR_SHA256
prior_local_evidence_sha256=$PRIOR_EVIDENCE_SHA256
minecraft_version=$MINECRAFT_VERSION
neoforge_version=$NEOFORGE_VERSION
github_bridge_repository=$GITHUB_REPOSITORY
github_run_id=$GITHUB_RUN_ID
server_startup=PASS
residents_runtime_initialized=PASS
plaintext_jar_uploaded=false
transport=ordered-pr-comments
EOF
(
  cd "$EVIDENCE_DIR"
  find . -maxdepth 1 -type f ! -name SHA256SUMS -printf '%P\n' \
    | LC_ALL=C sort | xargs -r sha256sum > SHA256SUMS
  sha256sum --check SHA256SUMS
)

exit 0

# Python parser is appended below and extracted by the workflow before execution.
