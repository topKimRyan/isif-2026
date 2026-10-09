#!/usr/bin/env bash
# Builds the public website into dist/ for Cloudflare Pages.
#   /            -> report service (report_page/)
#   /dashboard/  -> detection dashboard (docs/)
# Only browser files are copied; the worker code (report_page/server/), design mockups,
# and notes stay out of the public site.
set -euo pipefail

cd "$(dirname "$0")/.."

rm -rf dist
mkdir -p dist/dashboard

cp report_page/*.html report_page/supabase_client.js dist/
cp -r report_page/js report_page/style report_page/img dist/

cp docs/index.html docs/app.js docs/style.css dist/dashboard/
cp -r docs/brand dist/dashboard/

cat > dist/_headers <<'EOF'
/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: DENY
EOF

echo "Built site into dist/:"
find dist -type f | sort
