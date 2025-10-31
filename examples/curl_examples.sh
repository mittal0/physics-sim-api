#!/bin/bash
# Curl examples for the Physics Simulation API

# Configuration
API_BASE_URL="http://localhost:8000"
CONTENT_TYPE="Content-Type: application/json"

echo "Physics Simulation API - Curl Examples"
echo "======================================"

# Function to check if API is running
check_api() {
    echo "Checking API health..."
    curl -s "${API_BASE_URL}/health" | python -m json.tool
    echo ""
}

# Function to submit a single job
submit_single_job() {
    echo "1. Submitting a single simulation job..."
    
    JOB_RESPONSE=$(curl -s -X POST "${API_BASE_URL}/api/v1/jobs" \
        -H "${CONTENT_TYPE}" \
        -d '{
            "container_image": "sim:local",
            "params": {
                "length": 1.0,
                "time_steps": 100,
                "diffusivity": 0.01,
                "initial_temp": 100.0
            },
            "metadata": {
                "project": "curl-example",
                "user": "test-user",
                "description": "Single job submitted via curl"
            },
            "created_by": "curl-user"
        }')
    
    echo "Response:"
    echo "$JOB_RESPONSE" | python -m json.tool
    
    # Extract job ID for later use
    JOB_ID=$(echo "$JOB_RESPONSE" | python -c "import json,sys; print(json.load(sys.stdin)['jobs'][0])")
    echo "Job ID: $JOB_ID"
    echo ""
    
    return 0
}

# Function to submit a parameter sweep
submit_parameter_sweep() {
    echo "2. Submitting a parameter sweep..."
    
    SWEEP_RESPONSE=$(curl -s -X POST "${API_BASE_URL}/api/v1/jobs" \
        -H "${CONTENT_TYPE}" \
        -d '{
            "container_image": "sim:local",
            "sweep": [
                {"length": 1.0, "time_steps": 50, "diffusivity": 0.01},
                {"length": 1.0, "time_steps": 100, "diffusivity": 0.01},
                {"length": 1.0, "time_steps": 200, "diffusivity": 0.01}
            ],
            "metadata": {
                "project": "time-step-study",
                "user": "researcher",
                "description": "Parameter sweep for time step analysis"
            },
            "created_by": "curl-user"
        }')
    
    echo "Response:"
    echo "$SWEEP_RESPONSE" | python -m json.tool
    echo ""
}

# Function to get job details
get_job_details() {
    if [ -z "$JOB_ID" ]; then
        echo "No job ID available. Skipping job details example."
        return
    fi
    
    echo "3. Getting job details for Job ID: $JOB_ID"
    
    curl -s "${API_BASE_URL}/api/v1/jobs/${JOB_ID}" | python -m json.tool
    echo ""
}

# Function to list jobs
list_jobs() {
    echo "4. Listing jobs..."
    
    echo "All jobs (first page):"
    curl -s "${API_BASE_URL}/api/v1/jobs?page=1&size=5" | python -m json.tool
    echo ""
    
    echo "Queued jobs only:"
    curl -s "${API_BASE_URL}/api/v1/jobs?status=queued&size=3" | python -m json.tool
    echo ""
}

# Function to get job logs
get_job_logs() {
    if [ -z "$JOB_ID" ]; then
        echo "No job ID available. Skipping logs example."
        return
    fi
    
    echo "5. Getting job logs for Job ID: $JOB_ID"
    
    curl -s "${API_BASE_URL}/api/v1/jobs/${JOB_ID}/logs" | python -m json.tool
    echo ""
}

# Function to download job results
download_results() {
    if [ -z "$JOB_ID" ]; then
        echo "No job ID available. Skipping download example."
        return
    fi
    
    echo "6. Attempting to download results for Job ID: $JOB_ID"
    
    # Check if results are available
    JOB_STATUS=$(curl -s "${API_BASE_URL}/api/v1/jobs/${JOB_ID}" | python -c "import json,sys; data=json.load(sys.stdin); print(data.get('status', 'unknown'))")
    
    if [ "$JOB_STATUS" = "success" ]; then
        echo "Job completed successfully. Downloading results..."
        curl -s -o "results_${JOB_ID}.zip" "${API_BASE_URL}/api/v1/jobs/${JOB_ID}/result"
        
        if [ -f "results_${JOB_ID}.zip" ]; then
            echo "Results downloaded to: results_${JOB_ID}.zip"
            ls -la "results_${JOB_ID}.zip"
        else
            echo "Download failed or no results available"
        fi
    else
        echo "Job status: $JOB_STATUS (results not available yet)"
    fi
    echo ""
}

# Function to get job statistics
get_job_stats() {
    echo "7. Getting job statistics..."
    
    curl -s "${API_BASE_URL}/api/v1/jobs/stats" | python -m json.tool
    echo ""
}

# Function to cancel a job
cancel_job() {
    if [ -z "$JOB_ID" ]; then
        echo "No job ID available. Skipping cancel example."
        return
    fi
    
    echo "8. Canceling job (if still running): $JOB_ID"
    
    curl -s -X DELETE "${API_BASE_URL}/api/v1/jobs/${JOB_ID}" | python -m json.tool
    echo ""
}

# Function to demonstrate streaming logs
stream_logs() {
    if [ -z "$JOB_ID" ]; then
        echo "No job ID available. Skipping streaming example."
        return
    fi
    
    echo "9. Streaming logs for Job ID: $JOB_ID (first 5 lines)"
    
    # Stream logs and show first few lines
    timeout 5s curl -s "${API_BASE_URL}/api/v1/jobs/${JOB_ID}/logs/stream" | head -5
    echo ""
    echo "Log streaming example completed."
    echo ""
}

# Function to show API documentation
show_api_docs() {
    echo "10. API Documentation is available at:"
    echo "    ${API_BASE_URL}/docs (Interactive Swagger UI)"
    echo "    ${API_BASE_URL}/redoc (ReDoc Documentation)"
    echo ""
}

# Main execution
main() {
    echo "Starting API examples..."
    echo "Make sure the Physics Simulation API is running on ${API_BASE_URL}"
    echo ""
    
    # Check if API is available
    if ! curl -s "${API_BASE_URL}/health" > /dev/null; then
        echo "Error: API is not responding at ${API_BASE_URL}"
        echo "Please start the API with: make up"
        exit 1
    fi
    
    # Run examples
    check_api
    submit_single_job
    submit_parameter_sweep
    list_jobs
    get_job_details
    get_job_logs
    get_job_stats
    stream_logs
    download_results
    cancel_job
    show_api_docs
    
    echo "Examples completed!"
    echo ""
    echo "Tips:"
    echo "- Use 'make logs' to see service logs"
    echo "- Use 'make health' to check service status"
    echo "- Visit ${API_BASE_URL}/docs for interactive API testing"
}

# Function to show usage
usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --url URL     Set API base URL (default: http://localhost:8000)"
    echo "  --help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                  # Use default URL"
    echo "  $0 --url http://api.example.com     # Use custom URL"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --url)
            API_BASE_URL="$2"
            shift 2
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Run main function
main