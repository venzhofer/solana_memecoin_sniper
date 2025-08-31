#!/usr/bin/env python3
"""Fix the SQL statement in papertrading/db.py"""

# Read the file
with open('papertrading/db.py', 'r') as f:
    content = f.read()

# Fix the VALUES clause - remove one ? since we only have 8 columns
content = content.replace(
    'VALUES(?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)',
    'VALUES(?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)'
)

# Write the fixed content back
with open('papertrading/db.py', 'w') as f:
    f.write(content)

print("Fixed the SQL statement in papertrading/db.py")
