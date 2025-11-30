#!/bin/bash

# ==============================================================================
# launch_bot.sh — Launch a trading bot container with per-user settings
# ==============================================================================
# Supports both:
#   --flag-based modern CLI
#   legacy positional CLI
# ==============================================================================

set -euo pipefail

# ------------------------
# Defaults
# ------------------------
TAG="latest"
USER_ID=""

print_usage() {
  cat <<EOF
Usage:
  $0 --bot <id> --username <name> --account-id <id> --broker-key <key> --mode <live|practice> [--tag <tag>]
  $0 <bot_id> <username> <account_id> <broker_key> <mode> [tag]    # legacy mode
EOF
}

# ------------------------
# Argument Parsing
# ------------------------
if [[ $# -eq 0 ]]; then
  print_usage && exit 1
fi

if [[ $# -eq 5 && $1 != --* ]]; then
  BOT_ID=$1
  USERNAME=$2
  ACCOUNT_ID=$3
  BROKER_KEY=$4
  MODE=$5
elif [[ $# -eq 6 && $1 != --* ]]; then
  BOT_ID=$1
  USERNAME=$2
  ACCOUNT_ID=$3
  BROKER_KEY=$4
  MODE=$5
  TAG=$6
else
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --bot|-b) BOT_ID="$2"; shift 2 ;;
      --username|-u) USERNAME="$2"; shift 2 ;;
      --account-id|-a) ACCOUNT_ID="$2"; shift 2 ;;
      --broker-key|-k) BROKER_KEY="$2"; shift 2 ;;
      --mode|-m) MODE="$2"; shift 2 ;;
      --tag|-t) TAG="$2"; shift 2 ;;
      --user-id) USER_ID="$2"; shift 2 ;;
      --help|-h) print_usage; exit 0 ;;
      *) echo "❌ Unknown option: $1"; print_usage; exit 1 ;;
    esac
  done
fi

# ------------------------
# Fallback / Validation
# ------------------------
if [[ -z "${USERNAME:-}" && -n "${USER_ID:-}" ]]; then
  USERNAME="$USER_ID"
fi

if [[ -z "${BOT_ID:-}" || -z "${USERNAME:-}" || -z "${ACCOUNT_ID:-}" || -z "${BROKER_KEY:-}" || -z "${MODE:-}" ]]; then
  echo "❌ Missing required argument(s)."
  print_usage
  exit 1
fi

# ------------------------
# Derived Paths & Values
# ------------------------
BOT_FOLDER="/home/admintrader/tradermain/bots/bot-${BOT_ID}"
USER_FOLDER="${BOT_FOLDER}/users/${USERNAME}"
CONFIG_PATH="${USER_FOLDER}/config.json"
ENV_FILE="${USER_FOLDER}/.env"
CONTAINER_NAME="bot-${BOT_ID}-${USERNAME}"
IMAGE_NAME="bot-${BOT_ID}:${TAG}"

# ------------------------
# Check config.json exists
# ------------------------
if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "❌ Missing config.json at: $CONFIG_PATH"
  echo "➡️  Make sure the onboarding step created it before launching."
  exit 1
fi

# ------------------------
# Create .env file securely
# ------------------------
/bin/mkdir -p "$USER_FOLDER"

/bin/cat > "$ENV_FILE" <<EOF
ACCOUNT_ID=${ACCOUNT_ID}
BROKER_KEY=${BROKER_KEY}
TRADING_MODE=${MODE}
USERNAME=${USERNAME}
EOF

/bin/chmod 600 "$ENV_FILE"

# ------------------------
# Remove old container (if any)
# ------------------------
if /usr/bin/docker ps -a --format '{{.Names}}' | /bin/grep -q "^${CONTAINER_NAME}$"; then
  echo "🧹 Removing existing container $CONTAINER_NAME..."
  /usr/bin/docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
fi

# ------------------------
# Launch container
# ------------------------
echo "🚀 Launching bot container: $CONTAINER_NAME"
echo "🔧 Image: $IMAGE_NAME"
echo "📂 User Dir: $USER_FOLDER"

/usr/bin/docker run -d \
  --name "$CONTAINER_NAME" \
  --env-file "$ENV_FILE" \
  -v "${USER_FOLDER}:/app/user_data" \
  "$IMAGE_NAME"

STATUS=$?
if [[ $STATUS -eq 0 ]]; then
  echo "✅ Bot container '$CONTAINER_NAME' launched successfully."
else
  echo "❌ Failed to launch bot container '$CONTAINER_NAME'."
  exit $STATUS
fi
