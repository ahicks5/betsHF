import sqlite3

conn = sqlite3.connect('props.db')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(player_game_stats)')
rows = cursor.fetchall()

print('Column Info for player_game_stats:')
print('ID | Name | Type | NotNull | Default | PK')
print('-'*70)
for row in rows:
    print(f'{row[0]:2} | {row[1]:20} | {row[2]:15} | {row[3]} | {row[4]} | {row[5]}')

print('\n')
print('game_id column details:')
for row in rows:
    if row[1] == 'game_id':
        print(f'  NotNull: {row[3]} (should be 0 for nullable)')
