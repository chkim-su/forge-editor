#!/bin/bash
# Run Forge E2E tests in Docker
# Usage: ./scripts/run-docker-tests.sh [mode]
#   mode: headless (default) | interactive | validate

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORGE_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$FORGE_ROOT/tests/docker"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

usage() {
    echo "Usage: $0 [mode]"
    echo ""
    echo "Modes:"
    echo "  headless     Run workflow E2E tests in headless mode (default)"
    echo "  interactive  Run with tmux for debugging"
    echo "  validate     Quick plugin validation (legacy script)"
    echo "  schema       Run schema validation on forge plugin"
    echo "  schema-tests Run schema validation E2E tests"
    echo "  all          Run all tests (schema + workflow)"
    echo "  clean        Remove Docker volumes and cleanup"
    echo ""
    echo "Examples:"
    echo "  $0                 # Run headless workflow tests"
    echo "  $0 interactive     # Run with tmux"
    echo "  $0 schema          # Validate forge plugin schema"
    echo "  $0 schema-tests    # Run schema validation tests"
    echo "  $0 all             # Run all tests"
    echo "  $0 clean           # Cleanup Docker resources"
}

build_image() {
    log_info "Building Docker image..."
    cd "$DOCKER_DIR"
    docker-compose build --quiet
    log_success "Docker image built"
}

run_headless() {
    log_info "Running E2E tests in headless mode..."
    cd "$DOCKER_DIR"
    
    # Run tests
    if docker-compose run --rm forge-test; then
        log_success "All tests passed!"
        return 0
    else
        log_error "Tests failed"
        return 1
    fi
}

run_interactive() {
    log_info "Starting interactive test session with tmux..."
    cd "$DOCKER_DIR"
    
    # Run interactive mode
    docker-compose run --rm forge-test-interactive
}

run_validate() {
    log_info "Running quick plugin validation (legacy)..."
    cd "$DOCKER_DIR"
    
    if docker-compose run --rm forge-validate; then
        log_success "Plugin is valid!"
        return 0
    else
        log_error "Validation failed"
        return 1
    fi
}

run_schema() {
    log_info "Running schema validation on forge plugin..."
    cd "$DOCKER_DIR"
    
    if docker-compose run --rm forge-schema-validate; then
        log_success "Schema validation passed!"
        return 0
    else
        log_error "Schema validation failed"
        return 1
    fi
}

run_schema_tests() {
    log_info "Running schema validation E2E tests..."
    cd "$DOCKER_DIR"
    
    if docker-compose run --rm forge-schema-tests; then
        log_success "Schema validation tests passed!"
        return 0
    else
        log_error "Schema validation tests failed"
        return 1
    fi
}

run_all_tests() {
    log_info "Running all tests (schema + workflow)..."
    cd "$DOCKER_DIR"
    
    if docker-compose run --rm forge-all-tests; then
        log_success "All tests passed!"
        return 0
    else
        log_error "Some tests failed"
        return 1
    fi
}

cleanup() {
    log_info "Cleaning up Docker resources..."
    cd "$DOCKER_DIR"
    
    # Stop and remove containers
    docker-compose down -v --remove-orphans 2>/dev/null || true
    
    # Remove volumes
    docker volume rm docker_test-workspace docker_claude-state 2>/dev/null || true
    
    log_success "Cleanup complete"
}

main() {
    local mode="${1:-headless}"
    
    case "$mode" in
        "headless"|"-h"|"")
            build_image
            run_headless
            ;;
        "interactive"|"-i"|"tmux")
            build_image
            run_interactive
            ;;
        "validate"|"-v")
            build_image
            run_validate
            ;;
        "schema")
            build_image
            run_schema
            ;;
        "schema-tests"|"schema-test")
            build_image
            run_schema_tests
            ;;
        "all"|"all-tests"|"full")
            build_image
            run_all_tests
            ;;
        "clean"|"cleanup")
            cleanup
            ;;
        "help"|"--help")
            usage
            ;;
        *)
            log_error "Unknown mode: $mode"
            usage
            exit 1
            ;;
    esac
}

main "$@"
