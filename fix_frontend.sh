#!/bin/bash
# Run this from the root of your drivelegal project

echo "Fixing API_BASE in all frontend pages..."

# 1. Update API_BASE from localhost to relative path (works with Flask serving frontend)
find frontend/pages -name "*.html" -exec sed -i \
  "s|const API_BASE = 'http://localhost:5000';|const API_BASE = 'http://localhost:5000';|g" {} \;

# 2. Update all old API endpoint paths to /api/ prefix
find frontend/pages -name "*.html" -exec sed -i \
  "s|/validate-challan|/api/validate-challan|g; \
   s|/route-briefing|/api/route-briefing|g; \
   s|/calculate|/api/calculate|g; \
   s|/cop-mode|/api/cop-mode|g; \
   s|/violations|/api/violations|g; \
   s|/chat|/api/chat|g" {} \;

# 3. Fix back-button href in all pages (pages link to index.html, should be /)
find frontend/pages -name "*.html" -exec sed -i \
  "s|href=\"index.html\"|href=\"/\"|g; \
   s|href='index.html'|href='/'|g" {} \;

# 4. Fix state selector options — ensure all use correct codes
# (chatbot.html, scanner.html, route.html used names instead of codes)
# Replace the broken selectors with correct ones
for f in frontend/pages/chatbot.html frontend/pages/scanner.html frontend/pages/route.html; do
  sed -i \
    "s|value=\"Maharashtra\"|value=\"MH\"|g; \
     s|value=\"Delhi\"|value=\"DL\"|g; \
     s|value=\"Karnataka\"|value=\"KA\"|g; \
     s|value=\"Gujarat\"|value=\"GJ\"|g; \
     s|value=\"Rajasthan\"|value=\"RJ\"|g" "$f"
done

echo "✅ Done! Now copy the new app.py and index.html from outputs/"
echo ""
echo "Final steps:"
echo "  1. Replace backend/app.py with the new app.py"
echo "  2. Replace frontend/index.html with the new index.html"
echo "  3. Run: bash fix_frontend.sh  (from project root)"
echo "  4. Start server: cd backend && python app.py"
echo "  5. Open: http://localhost:5000"