#!/usr/bin/env bash
#
# Build Wireless Android Auto Dongle SD-card images with Docker Compose.
#
# Usage:
#   ./build.sh                Choose a board from an interactive menu
#   ./build.sh rpi4           Build a single board
#   ./build.sh rpi4 rpi5      Build several boards, in the order given
#   ./build.sh all            Build every board
#
# Images are written to images/sdcard-<defconfig>.img
#
set -euo pipefail

cd "$(dirname "$0")"

die() {
	printf 'error: %s\n' "$1" >&2
	exit 1
}

board_label() {
	case "$1" in
		rpi0w) echo "Raspberry Pi Zero W" ;;
		rpi02w) echo "Raspberry Pi Zero 2 W" ;;
		rpi3a) echo "Raspberry Pi 3 A+" ;;
		rpi4) echo "Raspberry Pi 4" ;;
		rpi5) echo "Raspberry Pi 5" ;;
		*) echo "$1" ;;
	esac
}

usage() {
	local board
	cat <<-EOF
		Build Wireless Android Auto Dongle SD-card images.

		Usage:
		  ${0##*/}                Choose a board from an interactive menu
		  ${0##*/} <board>...     Build the given boards, in the order listed
		  ${0##*/} all            Build every board

		Boards:
	EOF
	for board in "${BOARDS[@]}"; do
		printf '  %-7s %s\n' "$board" "$(board_label "$board")"
	done
	printf '\nImages are written to images/sdcard-<defconfig>.img\n'
}

# Show 3661 as "1h 01m 01s", 61 as "1m 01s".
format_duration() {
	local total=$1
	if [ "$total" -ge 3600 ]; then
		printf '%dh %02dm %02ds' $((total / 3600)) $((total % 3600 / 60)) $((total % 60))
	elif [ "$total" -ge 60 ]; then
		printf '%dm %02ds' $((total / 60)) $((total % 60))
	else
		printf '%ds' "$total"
	fi
}

check_tooling() {
	[ "${BASH_VERSINFO[0]}" -ge 4 ] ||
		die "bash 4 or newer is required, this is ${BASH_VERSION}."
	command -v docker > /dev/null 2>&1 ||
		die "docker is not installed. See BUILDING.md for the build requirements."
	docker compose version > /dev/null 2>&1 ||
		die "Docker Compose v2 is required ('docker compose', not 'docker-compose')."
}

check_build_prerequisites() {
	docker info > /dev/null 2>&1 ||
		die "cannot reach the Docker daemon. Is it running, and may your user use it?"
	[ -f buildroot/Makefile ] ||
		die "the buildroot submodule is empty. Run: git submodule update --init --recursive"
}

# The board list comes from docker-compose.yml so the two cannot drift apart.
# Board services are named rpi*; 'bash' and the shared 'generate_image_*'
# template are not build targets. Compose does not promise an order, so sort
# for a stable menu.
read_boards() {
	local services
	services=$(docker compose config --services) ||
		die "could not read the services from docker-compose.yml"

	mapfile -t BOARDS < <(printf '%s\n' "$services" | grep '^rpi' | sort -V)
	[ "${#BOARDS[@]}" -gt 0 ] ||
		die "docker-compose.yml defines no rpi* board services"
}

is_board() {
	local candidate=$1 board
	for board in "${BOARDS[@]}"; do
		[ "$board" = "$candidate" ] && return 0
	done
	return 1
}

# Ask which boards to build; the answer lands in SELECTED. This has to run in
# the main shell rather than a subshell, or quitting the menu could not stop
# the script.
choose_boards() {
	local choice board labels=()

	[ -t 0 ] ||
		die "no board given and no terminal to ask on. Run '${0##*/} --help'."

	for board in "${BOARDS[@]}"; do
		labels+=("$(board_label "$board") ($board)")
	done

	printf 'Which image do you want to build?\n'
	PS3="Board: "
	select choice in "${labels[@]}" "All boards" "Quit"; do
		case "$choice" in
			"")
				printf 'Please enter a number from the list.\n' >&2
				;;
			"Quit")
				exit 0
				;;
			"All boards")
				SELECTED=("${BOARDS[@]}")
				return
				;;
			*)
				# REPLY indexes BOARDS directly, labels share its order.
				SELECTED=("${BOARDS[$((REPLY - 1))]}")
				return
				;;
		esac
	done

	# select only falls through on end of input (Ctrl-D).
	exit 0
}

build_board() {
	local board=$1
	printf '\n==> Building %s (%s)\n' "$(board_label "$board")" "$board"
	docker compose run --rm --build "$board"
}

main() {
	check_tooling
	read_boards

	case "${1-}" in
		-h | --help)
			usage
			return 0
			;;
	esac

	SELECTED=()
	if [ "$#" -eq 0 ]; then
		check_build_prerequisites
		choose_boards
	elif [ "$#" -eq 1 ] && [ "$1" = "all" ]; then
		check_build_prerequisites
		SELECTED=("${BOARDS[@]}")
	else
		local argument
		for argument in "$@"; do
			is_board "$argument" ||
				die "unknown board '$argument'. Run '${0##*/} --help' for the board list."
			SELECTED+=("$argument")
		done
		check_build_prerequisites
	fi

	local board start built=() failed=()
	for board in "${SELECTED[@]}"; do
		start=$SECONDS
		if build_board "$board"; then
			built+=("$board ($(format_duration $((SECONDS - start))))")
		else
			failed+=("$board")
			printf '\n!!! %s failed after %s\n' \
				"$board" "$(format_duration $((SECONDS - start)))" >&2
		fi
	done

	# A single board speaks for itself through its own output and exit status.
	if [ "${#SELECTED[@]}" -gt 1 ]; then
		printf '\n=== Summary ===\n'
		for board in "${built[@]}"; do printf '  built   %s\n' "$board"; done
		for board in "${failed[@]}"; do printf '  FAILED  %s\n' "$board"; done
	fi

	[ "${#failed[@]}" -eq 0 ] || return 1
}

main "$@"
