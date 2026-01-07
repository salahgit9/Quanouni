import os

env_path = 'd:/TEST/QUANOUNI/new/.env'

with open(env_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
found = False
for line in lines:
    if line.strip().startswith('VITE_GEMINI_CHAT_MODEL='):
        print(f'OLD: {line.strip()}')
        new_lines.append('VITE_GEMINI_CHAT_MODEL=gemini-2.0-flash\n')
        print('NEW: VITE_GEMINI_CHAT_MODEL=gemini-2.0-flash')
        found = True
    else:
        new_lines.append(line)

if not found:
    new_lines.append('\nVITE_GEMINI_CHAT_MODEL=gemini-2.0-flash\n')
    print('ADDED: VITE_GEMINI_CHAT_MODEL=gemini-2.0-flash')

with open(env_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('\\n✅ .env updated! Restart backend to apply.')
