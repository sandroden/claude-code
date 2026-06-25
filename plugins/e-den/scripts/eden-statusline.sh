#!/bin/bash
# EDEN status line - modello, context window, nome progetto, branch
# Installato da /e-den:installa-statusline
# Riceve JSON via stdin da Claude Code
# Configurazione: ~/.claude/scripts/eden-statusline.conf

# --- Default (override in eden-statusline.conf) ---
PROFILES=(
    "300000:30:50:75"
    "2000000:12:25:60"
)
ZONE_COLORS=(green amber yellow)
ZONE_BLOCKS=(4 8 11)
BLOCKS_TOTAL=12
COLOR_OVER=red

CONF_FILE="$(dirname "${BASH_SOURCE[0]}")/eden-statusline.conf"
[ -f "$CONF_FILE" ] && source "$CONF_FILE"

color_code() {
    case "$1" in
        green)  printf '\033[32m' ;;
        amber)  printf '\033[93m' ;;
        yellow) printf '\033[33m' ;;
        red)    printf '\033[31m' ;;
        *)      printf '\033[0m'  ;;
    esac
}

# Seleziona soglie dal profilo con context_max >= total (profili ordinati dal più piccolo)
select_thresholds() {
    local total="$1"
    local last_thresholds
    for profile in "${PROFILES[@]}"; do
        IFS=: read -r max t1 t2 t3 <<< "$profile"
        last_thresholds="$t1 $t2 $t3"
        [ -z "$total" ] || [ "$total" -le "$max" ] && echo "$last_thresholds" && return
    done
    echo "$last_thresholds"  # fallback: usa il profilo più grande
}

input=$(cat)

# JSON appiattito su una riga: rende grep affidabile anche con input pretty-printed
json=$(printf '%s' "$input" | tr '\n' ' ')

# Estrae un valore stringa JSON ("key":"value") senza jq (portabile su Git Bash)
json_str() {
    printf '%s' "$1" | grep -oE "\"$2\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" | head -1 \
        | sed -E "s/.*:[[:space:]]*\"([^\"]*)\".*/\1/"
}

# Estrae un valore numerico JSON ("key":12.3) senza jq
json_num() {
    printf '%s' "$1" | grep -oE "\"$2\"[[:space:]]*:[[:space:]]*[0-9.]+" | head -1 \
        | sed -E "s/.*:[[:space:]]*([0-9.]+).*/\1/"
}

# --- Modello ---
# Isola l'oggetto "model" (flat) per non confondere "id" con altre chiavi id
model_block=$(printf '%s' "$json" | grep -oE "\"model\"[[:space:]]*:[[:space:]]*\{[^}]*\}")
model=$(json_str "$model_block" id)
[ -z "$model" ] && model="unknown"
model=$(printf '%s' "$model" | sed 's/claude-//; s/-[0-9].*//')
printf '%s' "$model"

# --- Context window ---
used=$(json_num "$json" used_percentage)
total=$(json_num "$json" context_window_size)

if [ -n "$used" ]; then
    pct=$(echo "$used" | awk '{printf "%d", int($1+0.5)}')

    # Soglie per questo modello/context
    read -ra ZONE_THRESHOLDS <<< "$(select_thresholds "$total")"

    # Trova zona e calcola blocchi per interpolazione lineare
    n=${#ZONE_THRESHOLDS[@]}
    color=$(color_code "$COLOR_OVER")
    filled=$BLOCKS_TOTAL
    zone_start_pct=0
    zone_start_blocks=0

    for ((i=0; i<n; i++)); do
        if [ "$pct" -le "${ZONE_THRESHOLDS[$i]}" ]; then
            color=$(color_code "${ZONE_COLORS[$i]}")
            filled=$(awk "BEGIN{
                s=$zone_start_blocks; e=${ZONE_BLOCKS[$i]}
                p0=$zone_start_pct;   p1=${ZONE_THRESHOLDS[$i]}
                if (p1==p0) { printf \"%d\", e }
                else        { printf \"%d\", int(s + ($pct-p0)/(p1-p0)*(e-s)) }
            }")
            break
        fi
        zone_start_pct=${ZONE_THRESHOLDS[$i]}
        zone_start_blocks=${ZONE_BLOCKS[$i]}
    done

    empty=$((BLOCKS_TOTAL - filled))
    bar=$(printf '█%.0s' $(seq 1 "$filled" 2>/dev/null))
    [ "$empty" -gt 0 ] && bar+=$(printf '░%.0s' $(seq 1 "$empty" 2>/dev/null))
    printf ' | context [%b%s\033[0m] %d%%' "$color" "$bar" "$pct"

    if [ -n "$total" ]; then
        used_tokens=$(echo "$total $pct" | awk '{printf "%.0f", $1*$2/100}')
        if [ "$used_tokens" -ge 1000000 ]; then
            usize=$(echo "$used_tokens" | awk '{printf "%.1fM", $1/1000000}')
        else
            usize=$(echo "$used_tokens" | awk '{printf "%.0fK", $1/1000}')
        fi
        if [ "$total" -ge 1000000 ]; then
            tsize=$(echo "$total" | awk '{printf "%.0fM", $1/1000000}')
        else
            tsize=$(echo "$total" | awk '{printf "%.0fK", $1/1000}')
        fi
        printf ' (%s/%s)' "$usize" "$tsize"
    fi
fi

# --- Progetto e branch ---
get_project_name() {
    if [ -f pyproject.toml ]; then
        sed -n '/^\[project\]/,/^\[/{s/^name *= *"\(.*\)"/\1/p}' pyproject.toml 2>/dev/null | head -1
    fi
}

get_project_type() {
    if [ -f Dockerfile ] || [ -f manage.py ]; then
        echo "app"
    elif [ -f pyproject.toml ]; then
        echo "pkg"
    fi
}

get_branch() {
    if [ -d .hg ]; then
        local b topic
        b=$(hg branch 2>/dev/null)
        topic=$(hg topics --current 2>/dev/null)
        if [ -n "$topic" ]; then echo "$b/$topic"; else echo "$b"; fi
    elif [ -d .git ] || git rev-parse --git-dir >/dev/null 2>&1; then
        git branch --show-current 2>/dev/null
    fi
}

name=$(get_project_name)
[ -z "$name" ] && name=$(basename "$PWD")
type=$(get_project_type)
branch=$(get_branch)

YELLOW='\033[33m'
CYAN='\033[36m'
RESET='\033[0m'

part="${YELLOW}${name}${RESET}"
[ -n "$type" ]   && part="$part($type)"
[ -n "$branch" ] && part="$part${CYAN}@${branch}${RESET}"

printf ' | %b\n' "$part"
