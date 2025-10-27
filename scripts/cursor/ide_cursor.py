import sqlite3
import os
import shutil

# Your knkdigital keys
devDeviceId = "377b01ce-692b-42e1-a880-51c0aef0a16a"
machineId = "32db4207bb796582ed9512f30309203191425c425eabe0367e282cca91015a8b"
macMachineId = "527256a05467261eb0da6804377ca80eaeaf5864d6202877095b771b4601082c3b7ea101e8e81b6111408039860b5cc2594df18805e61fd24b41ae8bcab2d827"
sqmId = "{596696E0-0E4B-4036-B37D-2DE2328962F9}"

db_path = os.path.expandvars(r"%APPDATA%\Cursor\User\globalStorage\state.vscdb")

if os.path.exists(db_path):
    # Create backup
    backup_path = db_path + ".backup"
    shutil.copy2(db_path, backup_path)
    print(f"Created backup at {backup_path}")

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Update values
    cursor.execute("UPDATE ItemTable SET value = ? WHERE key = 'telemetry.devDeviceId'", (devDeviceId,))
    cursor.execute("UPDATE ItemTable SET value = ? WHERE key = 'telemetry.machineId'", (machineId,))
    cursor.execute("UPDATE ItemTable SET value = ? WHERE key = 'telemetry.macMachineId'", (macMachineId,))
    cursor.execute("UPDATE ItemTable SET value = ? WHERE key = 'telemetry.sqmId'", (sqmId,))
    cursor.execute("UPDATE ItemTable SET value = ? WHERE key = 'storage.serviceMachineId'", (devDeviceId,))

    # Commit changes and close
    conn.commit()
    conn.close()
    print("Successfully updated Cursor database")
else:
    print(f"Database not found at {db_path}")