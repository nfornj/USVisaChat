#!/bin/bash
"""
Setup Daily Article Pipeline Cron Jobs
This script configures cron jobs to run the daily article scraping pipeline.
"""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
PIPELINE_SCRIPT="$PROJECT_ROOT/pipeline/scripts/daily_article_scraper.py"
LOG_DIR="$PROJECT_ROOT/pipeline/logs"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Create wrapper script for cron
WRAPPER_SCRIPT="$PROJECT_ROOT/pipeline/cron/run_daily_pipeline.sh"
cat > "$WRAPPER_SCRIPT" << 'EOF'
#!/bin/bash
# Daily Pipeline Wrapper Script

# Set up environment
export PATH=/usr/local/bin:$PATH
export PYTHONPATH="PROJECT_ROOT:PROJECT_ROOT/backend"

# Navigate to project root
cd "PROJECT_ROOT"

# Run daily pipeline
echo "$(date): Starting daily article pipeline..." >> "PROJECT_ROOT/pipeline/logs/cron.log"
uv run python "PROJECT_ROOT/pipeline/scripts/daily_article_scraper.py" >> "PROJECT_ROOT/pipeline/logs/cron.log" 2>&1

# Check exit status
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "$(date): Daily pipeline completed successfully" >> "PROJECT_ROOT/pipeline/logs/cron.log"
else
    echo "$(date): Daily pipeline failed with exit code $EXIT_CODE" >> "PROJECT_ROOT/pipeline/logs/cron.log"
fi
EOF

# Replace placeholders with actual paths
sed -i.bak "s|PROJECT_ROOT|$PROJECT_ROOT|g" "$WRAPPER_SCRIPT"
rm "$WRAPPER_SCRIPT.bak"

# Make wrapper script executable
chmod +x "$WRAPPER_SCRIPT"

# Create crontab entry
CRON_ENTRY="# Visa Community Platform - Daily Article Pipeline
# Run every day at 6:00 AM
0 6 * * * $WRAPPER_SCRIPT

# Alternative schedules (commented out):
# Every 12 hours: 0 */12 * * *
# Every 6 hours: 0 */6 * * *
# Twice daily (6AM and 6PM): 0 6,18 * * *"

echo "📋 Cron job configuration:"
echo "$CRON_ENTRY"
echo ""

# Save cron configuration to file
echo "$CRON_ENTRY" > "$SCRIPT_DIR/daily_pipeline_cron.txt"

echo "🔧 Setup instructions:"
echo "1. Review the cron configuration in: $SCRIPT_DIR/daily_pipeline_cron.txt"
echo "2. To install the cron job, run:"
echo "   crontab $SCRIPT_DIR/daily_pipeline_cron.txt"
echo "3. To view current cron jobs:"
echo "   crontab -l"
echo "4. To edit cron jobs:"
echo "   crontab -e"
echo ""
echo "📁 Files created:"
echo "   - Wrapper script: $WRAPPER_SCRIPT"
echo "   - Cron config: $SCRIPT_DIR/daily_pipeline_cron.txt"
echo "   - Logs will be written to: $LOG_DIR/"
echo ""
echo "⚙️  Test the wrapper script manually:"
echo "   $WRAPPER_SCRIPT"