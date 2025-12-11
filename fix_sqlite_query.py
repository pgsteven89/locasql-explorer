import pathlib

# Fix the sqlite_master query in database.py
file_path = pathlib.Path('src/localsql_explorer/database.py')
content = file_path.read_text(encoding='utf-8')

# Replace the problematic query
old_query = 'f"SELECT name FROM {alias}.sqlite_master WHERE type=\'table\' AND name NOT LIKE \'sqlite_%\'"'
new_query = 'f"SELECT name FROM sqlite_scan(\'{sqlite_path}\', \'sqlite_master\') WHERE type=\'table\' AND name NOT LIKE \'sqlite_%\'"'

content = content.replace(old_query, new_query)

file_path.write_text(content, encoding='utf-8')
print('[OK] Fixed sqlite_master query in database.py')
